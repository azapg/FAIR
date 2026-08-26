from __future__ import annotations

import hashlib
from datetime import date, datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from fair_platform.backend.data.models import (
    AdmissionRule,
    AdmissionRuleKind,
    AICapabilityClassification,
    AICapabilityPolicy,
    AIEntitlement,
    AIEntitlementState,
    AIUsageCharge,
    CapabilityDefinition,
    Execution,
    ExtensionInstallation,
    PlatformPolicy,
    RegistrationInvite,
    User,
)
from fair_platform.backend.core.config import validate_security_configuration
from fair_platform.backend.services.access_control import (
    AccessPolicyError,
    utc_month_start,
)
from fair_platform.backend.services.execution_store import create_execution
from tests.conftest import create_sample_user_data, get_auth_token
from tests.execution_protocol_helpers import add_agent_capability, execution_headers


def _admin_headers(client: TestClient, admin_user) -> dict[str, str]:
    token = get_auth_token(client, str(admin_user.email))
    return {"Authorization": f"Bearer {token}"}


def test_open_registration_remains_the_upgrade_default(test_client, test_db):
    response = test_client.post("/api/auth/register", json=create_sample_user_data())
    assert response.status_code == 201
    config = test_client.get("/api/v1/system/config").json()
    assert config["registration"] == {"mode": "open", "invite_required": False}
    assert config["features"]["ai_controls_enabled"] is False


def test_allowlist_accepts_exact_domain_and_normalizes_identity(
    test_client, test_db, admin_user
):
    with test_db() as session:
        session.add_all(
            [
                PlatformPolicy(
                    id=1, admission_mode="allowlist", ai_controls_enabled=False
                ),
                AdmissionRule(
                    kind=AdmissionRuleKind.domain,
                    normalized_value="example.edu",
                    created_by_user_id=admin_user.id,
                ),
            ]
        )
        session.commit()

    allowed = test_client.post(
        "/api/auth/register",
        json={
            "name": "Allowed",
            "email": "Allowed@EXAMPLE.edu",
            "password": "password-123",
        },
    )
    denied_subdomain = test_client.post(
        "/api/auth/register",
        json={
            "name": "Denied",
            "email": "denied@sub.example.edu",
            "password": "password-123",
        },
    )

    assert allowed.status_code == 201
    assert denied_subdomain.status_code == 403
    assert denied_subdomain.json()["code"] == "registration_not_permitted"
    with test_db() as session:
        row = (
            session.query(User)
            .filter(User.normalized_email == "allowed@example.edu")
            .one()
        )
        assert str(row.email) == "Allowed@example.edu"


def test_allowlist_supports_exact_individual_addresses(
    test_client, test_db, admin_user
):
    with test_db() as session:
        session.add_all(
            [
                PlatformPolicy(
                    id=1, admission_mode="allowlist", ai_controls_enabled=False
                ),
                AdmissionRule(
                    kind=AdmissionRuleKind.email,
                    normalized_value="person@outside.example",
                    created_by_user_id=admin_user.id,
                ),
            ]
        )
        session.commit()
    response = test_client.post(
        "/api/auth/register",
        json={
            "name": "Person",
            "email": "PERSON@outside.example",
            "password": "password-123",
        },
    )
    assert response.status_code == 201


def test_invitation_is_email_bound_single_use_and_does_not_verify_email(
    test_client, test_db, admin_user, monkeypatch
):
    monkeypatch.setenv("FAIR_EMAIL_ENABLED", "1")
    headers = _admin_headers(test_client, admin_user)
    policy = test_client.patch(
        "/api/v1/admin/platform-policy",
        json={"admissionMode": "invite_only"},
        headers=headers,
    )
    assert policy.status_code == 200
    created = test_client.post(
        "/api/v1/admin/invites",
        json={"email": "invitee@example.edu", "expiresInDays": 7},
        headers=headers,
    )
    assert created.status_code == 201
    token = created.json()["token"]
    assert token not in created.json()["registrationUrl"].split("#", 1)[0]

    wrong_email = test_client.post(
        "/api/auth/register",
        json={
            "name": "Wrong",
            "email": "wrong@example.edu",
            "password": "password-123",
            "inviteToken": token,
        },
    )
    assert wrong_email.status_code == 403
    with test_db() as session:
        assert (
            session.query(User)
            .filter(User.normalized_email == "invitee@example.edu")
            .count()
            == 0
        )

    accepted = test_client.post(
        "/api/auth/register",
        json={
            "name": "Invitee",
            "email": "INVITEE@example.edu",
            "password": "password-123",
            "inviteToken": token,
        },
    )
    assert accepted.status_code == 201, accepted.text
    reused = test_client.post(
        "/api/auth/register",
        json={
            "name": "Again",
            "email": "invitee@example.edu",
            "password": "password-123",
            "inviteToken": token,
        },
    )
    assert reused.status_code in {400, 403}

    with test_db() as session:
        user = (
            session.query(User)
            .filter(User.normalized_email == "invitee@example.edu")
            .one()
        )
        invite = session.query(RegistrationInvite).one()
        assert user.is_verified is False
        assert invite.redeemed_by_user_id == user.id
        assert invite.token_hash != token


def test_expired_and_revoked_invitations_fail_closed(test_client, test_db, admin_user):
    expired_token = "expired-registration-token"
    revoked_token = "revoked-registration-token"
    now = datetime.now(timezone.utc)
    with test_db() as session:
        session.add(
            PlatformPolicy(
                id=1, admission_mode="invite_only", ai_controls_enabled=False
            )
        )
        session.add_all(
            [
                RegistrationInvite(
                    token_hash=hashlib.sha256(expired_token.encode()).hexdigest(),
                    normalized_email="expired@example.edu",
                    expires_at=now - timedelta(minutes=1),
                    created_by_user_id=admin_user.id,
                ),
                RegistrationInvite(
                    token_hash=hashlib.sha256(revoked_token.encode()).hexdigest(),
                    normalized_email="revoked@example.edu",
                    expires_at=now + timedelta(days=1),
                    revoked_at=now,
                    created_by_user_id=admin_user.id,
                ),
            ]
        )
        session.commit()
    expired = test_client.post(
        "/api/auth/register",
        json={
            "name": "Expired",
            "email": "expired@example.edu",
            "password": "password-123",
            "inviteToken": expired_token,
        },
    )
    revoked = test_client.post(
        "/api/auth/register",
        json={
            "name": "Revoked",
            "email": "revoked@example.edu",
            "password": "password-123",
            "inviteToken": revoked_token,
        },
    )
    for response in (expired, revoked):
        assert response.status_code == 403
        assert response.json()["code"] == "registration_not_permitted"


def test_admission_policy_does_not_block_existing_login(
    test_client, test_db, student_user
):
    with test_db() as session:
        session.add(
            PlatformPolicy(
                id=1, admission_mode="invite_only", ai_controls_enabled=False
            )
        )
        session.commit()
    response = test_client.post(
        "/api/auth/login",
        data={
            "username": str(student_user.email).upper(),
            "password": "test_password_123",
        },
    )
    assert response.status_code == 200


def test_environment_policy_is_effective_and_admin_locked(
    test_client, admin_user, monkeypatch
):
    monkeypatch.setenv("FAIR_ADMISSION_MODE", "invite_only")
    monkeypatch.setenv("FAIR_AI_CONTROLS_ENABLED", "true")
    headers = _admin_headers(test_client, admin_user)
    read = test_client.get("/api/v1/admin/platform-policy", headers=headers)
    assert read.status_code == 200
    assert read.json()["effectiveAdmissionMode"] == "invite_only"
    assert read.json()["admissionLocked"] is True
    assert read.json()["aiControlsLocked"] is True
    update = test_client.patch(
        "/api/v1/admin/platform-policy",
        json={"admissionMode": "open"},
        headers=headers,
    )
    assert update.status_code == 409


def test_database_managed_ai_controls_require_capability_classification(
    test_client, test_db, admin_user
):
    with test_db() as session:
        installation = ExtensionInstallation(extension_id="needs.classification")
        add_agent_capability(session, installation)
        session.commit()
    response = test_client.patch(
        "/api/v1/admin/platform-policy",
        json={"aiControlsEnabled": True},
        headers=_admin_headers(test_client, admin_user),
    )
    assert response.status_code == 409
    assert "1 unclassified" in response.json()["detail"]


@pytest.mark.parametrize(
    ("name", "value", "message"),
    [
        ("FAIR_ADMISSION_MODE", "private", "must be one of"),
        ("FAIR_AI_CONTROLS_ENABLED", "sometimes", "must be a boolean"),
    ],
)
def test_invalid_policy_environment_values_fail_startup(
    monkeypatch, name, value, message
):
    monkeypatch.delenv("FAIR_ADMISSION_MODE", raising=False)
    monkeypatch.delenv("FAIR_AI_CONTROLS_ENABLED", raising=False)
    monkeypatch.setenv(name, value)
    with pytest.raises(RuntimeError, match=message):
        validate_security_configuration("configured-secret")


def _seed_metered_capability(
    test_db,
    user,
    admin_user,
    *,
    controls_enabled=True,
    state="limited",
    limit=3,
    cost=2,
):
    with test_db() as session:
        installation = ExtensionInstallation(extension_id=f"metered.{uuid4()}")
        capability = add_agent_capability(session, installation)
        session.add(
            PlatformPolicy(
                id=1, admission_mode="open", ai_controls_enabled=controls_enabled
            )
        )
        session.add(
            AICapabilityPolicy(
                capability_definition_id=capability.id,
                classification=AICapabilityClassification.ai,
                cost_units=cost,
                updated_by_user_id=admin_user.id,
            )
        )
        session.add(
            AIEntitlement(
                user_id=user.id,
                state=AIEntitlementState(state),
                monthly_limit_units=limit if state == "limited" else None,
                used_units=0,
                period_start=date.today().replace(day=1),
                updated_by_user_id=admin_user.id,
            )
        )
        session.commit()
        return capability.id, installation.id


def test_weighted_credits_are_reserved_before_execution_dispatch(
    test_db, student_user, admin_user
):
    capability_id, installation_id = _seed_metered_capability(
        test_db, student_user, admin_user
    )
    with test_db() as session:
        first = create_execution(
            session,
            kind="agent",
            initiated_by_user_id=student_user.id,
            capability_definition_id=capability_id,
            extension_installation_id=installation_id,
        )
        session.commit()
        assert first.id is not None

    with test_db() as session:
        with pytest.raises(AccessPolicyError) as captured:
            create_execution(
                session,
                kind="agent",
                initiated_by_user_id=student_user.id,
                capability_definition_id=capability_id,
                extension_installation_id=installation_id,
            )
        assert captured.value.code == "ai_quota_exhausted"
        session.rollback()

    with test_db() as session:
        entitlement = session.get(AIEntitlement, student_user.id)
        assert entitlement.used_units == 2
        assert session.query(AIUsageCharge).count() == 1


def test_controls_disabled_preserve_existing_execution_behavior(
    test_db, student_user, admin_user
):
    capability_id, installation_id = _seed_metered_capability(
        test_db, student_user, admin_user, controls_enabled=False
    )
    with test_db() as session:
        create_execution(
            session,
            kind="agent",
            initiated_by_user_id=student_user.id,
            capability_definition_id=capability_id,
            extension_installation_id=installation_id,
        )
        session.commit()
        assert session.query(AIUsageCharge).count() == 0


def test_stale_monthly_counter_resets_before_atomic_reservation(
    test_db, student_user, admin_user
):
    capability_id, installation_id = _seed_metered_capability(
        test_db, student_user, admin_user
    )
    with test_db() as session:
        entitlement = session.get(AIEntitlement, student_user.id)
        entitlement.period_start = date(2000, 1, 1)
        entitlement.used_units = entitlement.monthly_limit_units
        session.commit()

    with test_db() as session:
        create_execution(
            session,
            kind="agent",
            initiated_by_user_id=student_user.id,
            capability_definition_id=capability_id,
            extension_installation_id=installation_id,
        )
        session.commit()
        entitlement = session.get(AIEntitlement, student_user.id)
        assert entitlement.period_start == utc_month_start()
        assert entitlement.used_units == 2
        assert session.query(AIUsageCharge).count() == 1


def test_unclassified_capability_fails_closed_when_controls_enabled(
    test_db, student_user, admin_user
):
    with test_db() as session:
        installation = ExtensionInstallation(extension_id="unclassified.agent")
        capability = add_agent_capability(session, installation)
        session.add(
            PlatformPolicy(id=1, admission_mode="open", ai_controls_enabled=True)
        )
        session.commit()
        capability_id = capability.id
        installation_id = installation.id
    with test_db() as session:
        with pytest.raises(AccessPolicyError) as captured:
            create_execution(
                session,
                kind="agent",
                initiated_by_user_id=student_user.id,
                capability_definition_id=capability_id,
                extension_installation_id=installation_id,
            )
        assert captured.value.code == "ai_policy_unconfigured"


def test_unlimited_entitlement_is_still_audited(test_db, student_user, admin_user):
    capability_id, installation_id = _seed_metered_capability(
        test_db, student_user, admin_user, state="unlimited", limit=None, cost=5
    )
    with test_db() as session:
        create_execution(
            session,
            kind="agent",
            initiated_by_user_id=student_user.id,
            capability_definition_id=capability_id,
            extension_installation_id=installation_id,
        )
        session.commit()
        entitlement = session.get(AIEntitlement, student_user.id)
        assert entitlement.used_units == 5
        assert session.query(AIUsageCharge).one().units == 5


def test_unmetered_capability_requires_no_entitlement(
    test_db, student_user, admin_user
):
    with test_db() as session:
        installation = ExtensionInstallation(extension_id="unmetered.agent")
        capability = add_agent_capability(session, installation)
        session.add(
            PlatformPolicy(id=1, admission_mode="open", ai_controls_enabled=True)
        )
        session.add(
            AICapabilityPolicy(
                capability_definition_id=capability.id,
                classification=AICapabilityClassification.unmetered,
                cost_units=0,
                updated_by_user_id=admin_user.id,
            )
        )
        session.commit()
        create_execution(
            session,
            kind="agent",
            initiated_by_user_id=student_user.id,
            capability_definition_id=capability.id,
            extension_installation_id=installation.id,
        )
        session.commit()
        assert session.query(AIUsageCharge).count() == 0


def test_admin_endpoints_require_admin(test_client, student_user):
    token = get_auth_token(test_client, str(student_user.email))
    response = test_client.get(
        "/api/v1/admin/platform-policy",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_user_can_read_only_their_own_entitlement(
    test_client, test_db, student_user, admin_user
):
    _seed_metered_capability(test_db, student_user, admin_user)
    token = get_auth_token(test_client, str(student_user.email))
    response = test_client.get(
        "/api/v1/ai/entitlement",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["state"] == "limited"
    assert response.json()["monthlyLimitUnits"] == 3


def test_admin_workflow_surfaces_cost_and_complete_filtered_usage(
    test_client, test_db, student_user, admin_user
):
    with test_db() as session:
        installation = ExtensionInstallation(extension_id="admin.workflow.agent")
        capability = add_agent_capability(session, installation)
        session.commit()
        capability_id = capability.id
        installation_id = installation.id

    admin_headers = _admin_headers(test_client, admin_user)
    policies = test_client.get(
        "/api/v1/admin/capability-cost-policies", headers=admin_headers
    )
    assert policies.status_code == 200
    assert policies.json()[0]["classification"] == "unclassified"
    classified = test_client.put(
        f"/api/v1/admin/capability-cost-policies/{capability_id}",
        json={"classification": "ai", "costUnits": 2},
        headers=admin_headers,
    )
    assert classified.status_code == 200
    entitlement = test_client.put(
        f"/api/v1/admin/users/{student_user.id}/ai-entitlement",
        json={"state": "limited", "monthlyLimitUnits": 5},
        headers=admin_headers,
    )
    assert entitlement.status_code == 200
    enabled = test_client.patch(
        "/api/v1/admin/platform-policy",
        json={"aiControlsEnabled": True},
        headers=admin_headers,
    )
    assert enabled.status_code == 200

    student_headers = {
        "Authorization": f"Bearer {get_auth_token(test_client, str(student_user.email))}"
    }
    available = test_client.get(
        "/api/v1/extensions/capabilities", headers=student_headers
    )
    assert available.status_code == 200
    assert available.json()[0]["costControl"] == {
        "controlsEnabled": True,
        "classification": "ai",
        "costUnits": 2,
        "executable": True,
        "reason": None,
    }

    with test_db() as session:
        for _ in range(2):
            create_execution(
                session,
                kind="agent",
                initiated_by_user_id=student_user.id,
                capability_definition_id=capability_id,
                extension_installation_id=installation_id,
            )
            session.commit()

    exhausted = test_client.get(
        "/api/v1/extensions/capabilities", headers=student_headers
    ).json()[0]["costControl"]
    assert exhausted["executable"] is False
    assert exhausted["reason"] == "ai_quota_exhausted"
    usage = test_client.get(
        f"/api/v1/admin/ai-usage?user_id={student_user.id}&limit=1",
        headers=admin_headers,
    )
    assert usage.status_code == 200
    assert usage.json()["totalUnits"] == 4
    assert len(usage.json()["charges"]) == 1


def test_later_flow_step_quota_denial_fails_root_without_dispatch(
    test_client, test_db, student_user, admin_user
):
    extension_id = "metered.flow-extension"
    with test_db() as session:
        installation = ExtensionInstallation(
            extension_id=extension_id,
            display_name="Metered Flow Extension",
            version="1.0.0",
        )
        session.add(installation)
        session.flush()
        capability = CapabilityDefinition(
            installation_id=installation.id,
            capability_id="metered.transform",
            surface="function",
            version="1.0.0",
            declared_effects=[],
            manifest_snapshot={
                "capabilityId": "metered.transform",
                "kind": "action",
                "version": "1.0.0",
                "inputSchema": {"type": "object"},
                "outputSchema": {"type": "object"},
            },
        )
        session.add(capability)
        session.flush()
        session.add_all(
            [
                PlatformPolicy(id=1, admission_mode="open", ai_controls_enabled=True),
                AICapabilityPolicy(
                    capability_definition_id=capability.id,
                    classification=AICapabilityClassification.ai,
                    cost_units=2,
                    updated_by_user_id=admin_user.id,
                ),
                AIEntitlement(
                    user_id=student_user.id,
                    state=AIEntitlementState.limited,
                    monthly_limit_units=2,
                    used_units=0,
                    period_start=date.today().replace(day=1),
                    updated_by_user_id=admin_user.id,
                ),
            ]
        )
        session.commit()
        capability_id = capability.id

    headers = {
        "Authorization": f"Bearer {get_auth_token(test_client, str(student_user.email))}"
    }
    flow = test_client.post(
        "/api/v1/flows", json={"name": "Quota Flow"}, headers=headers
    )
    assert flow.status_code == 201, flow.text
    version = test_client.post(
        f"/api/v1/flows/{flow.json()['id']}/versions",
        json={
            "definition": {
                "mode": "ordered",
                "nodes": [
                    {"id": "first", "capabilityDefinitionId": str(capability_id)},
                    {"id": "second", "capabilityDefinitionId": str(capability_id)},
                ],
            }
        },
        headers=headers,
    )
    assert version.status_code == 201, version.text
    published = test_client.post(
        f"/api/v1/flows/{flow.json()['id']}/versions/{version.json()['id']}/publish",
        headers=headers,
    )
    assert published.status_code == 200, published.text
    started = test_client.post(
        f"/api/v1/flows/{flow.json()['id']}/executions",
        json={},
        headers=headers,
    )
    assert started.status_code == 202, started.text
    root_id = started.json()["executionId"]
    first_id = started.json()["stepExecutionId"]

    completed = test_client.post(
        f"/api/v1/executions/{first_id}/events/ingest",
        headers=execution_headers(test_db, first_id),
        json={
            "events": [
                {
                    "producerSource": extension_id,
                    "producerEventId": "first-completed",
                    "type": "execution.completed",
                    "schemaUri": "urn:fair:event:execution.completed:v1",
                    "occurredAt": datetime.now(timezone.utc).isoformat(),
                    "visibility": "user",
                    "payload": {"outputSummary": {"value": 1}},
                }
            ]
        },
    )
    assert completed.status_code == 202, completed.text
    with test_db() as session:
        root = session.get(Execution, UUID(root_id))
        children = list(
            session.query(Execution).filter(Execution.parent_execution_id == root.id)
        )
        assert root.status == "failed"
        assert root.error_code == "ai_quota_exhausted"
        assert [child.flow_node_id for child in children] == ["first"]
        assert session.query(AIUsageCharge).count() == 1
