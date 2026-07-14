import json
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.api.routers.extensions import router
from fair_platform.backend.data.database import session_dependency
from fair_platform.backend.data.models import User, UserRole
from fair_platform.extension_sdk.contracts.extension import ExtensionManifest


FIXTURE = Path("specs/fixtures/extension-manifest.json")


def _client(test_db, user):
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/extensions")
    app.dependency_overrides[get_current_user] = lambda: user

    def sessions():
        with test_db() as session:
            yield session

    app.dependency_overrides[session_dependency] = sessions
    return TestClient(app)


def test_manifest_fixture_round_trips_and_rejects_invalid_schema():
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    manifest = ExtensionManifest.model_validate(raw)
    assert manifest.capabilities[0].input_schema.required == ["submissionId"]
    dumped = manifest.model_dump(by_alias=True, mode="json")
    assert ExtensionManifest.model_validate(dumped) == manifest
    assert dumped["extensionId"] == raw["extensionId"]

    invalid = json.loads(FIXTURE.read_text(encoding="utf-8"))
    invalid["capabilities"][0]["inputSchema"]["required"] = ["missing"]
    with pytest.raises(ValidationError, match="lack property definitions"):
        ExtensionManifest.model_validate(invalid)

    duplicate = json.loads(FIXTURE.read_text(encoding="utf-8"))
    duplicate["capabilities"].append(duplicate["capabilities"][0])
    with pytest.raises(ValidationError, match="must be unique"):
        ExtensionManifest.model_validate(duplicate)


def test_admin_installs_manifest_and_manages_declared_grant(test_db):
    admin = User(
        id=uuid4(), name="Admin", email=f"{uuid4()}@example.test", role=UserRole.admin
    )
    with test_db() as session:
        session.add(admin)
        session.commit()
    client = _client(test_db, admin)
    manifest = json.loads(FIXTURE.read_text(encoding="utf-8"))

    created = client.post("/api/v1/extensions/installations", json={"manifest": manifest})
    assert created.status_code == 201, created.text
    installation = created.json()
    capability = installation["capabilities"][0]
    assert capability["inputSchema"]["$id"] == "urn:fair:example:review-input"

    grant = client.post("/api/v1/extensions/grants", json={
        "installationId": installation["id"],
        "capabilityDefinitionId": capability["id"],
        "effect": "feedback:write",
        "decision": "allow",
        "reason": "Approved for this installation"
    })
    assert grant.status_code == 201, grant.text
    assert grant.json()["grantedByUserId"] == str(admin.id)

    undeclared = client.post("/api/v1/extensions/grants", json={
        "installationId": installation["id"],
        "capabilityDefinitionId": capability["id"],
        "effect": "grades:write",
        "decision": "allow"
    })
    assert undeclared.status_code == 422


def test_non_admin_can_discover_enabled_capabilities_but_not_mutate(test_db):
    admin = User(id=uuid4(), name="Admin", email=f"{uuid4()}@example.test", role=UserRole.admin)
    user = User(id=uuid4(), name="User", email=f"{uuid4()}@example.test", role=UserRole.user)
    with test_db() as session:
        session.add_all([admin, user])
        session.commit()
    manifest = json.loads(FIXTURE.read_text(encoding="utf-8"))
    admin_client = _client(test_db, admin)
    created = admin_client.post("/api/v1/extensions/installations", json={"manifest": manifest})
    assert created.status_code == 201

    user_client = _client(test_db, user)
    capabilities = user_client.get("/api/v1/extensions/capabilities")
    assert capabilities.status_code == 200
    assert capabilities.json()[0]["capabilityId"] == "review.assignment"
    denied = user_client.post("/api/v1/extensions/installations", json={"manifest": manifest})
    assert denied.status_code == 403


def test_admin_manages_extension_ingest_credentials_on_v1_surface(test_db):
    admin = User(
        id=uuid4(), name="Admin", email=f"{uuid4()}@example.test", role=UserRole.admin
    )
    with test_db() as session:
        session.add(admin)
        session.commit()
    client = _client(test_db, admin)

    created = client.post(
        "/api/v1/extensions/clients",
        json={
            "extensionId": "example.credential-client",
            "scopes": ["executions:events"],
            "enabled": True,
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["extensionSecret"]

    updated = client.patch(
        "/api/v1/extensions/clients/example.credential-client",
        json={
            "scopes": ["executions:events", "executions:events", "  "],
            "enabled": False,
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["scopes"] == ["executions:events"]
    assert updated.json()["enabled"] is False
