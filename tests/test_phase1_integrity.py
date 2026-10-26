from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from fair_platform.backend.data.models import (
    Artifact,
    ArtifactPart,
    ArtifactVersion,
    ArtifactVersionMutationError,
    ExtensionGrant,
    ExtensionInstallation,
    Flow,
    FlowVersion,
    FlowVersionState,
    GradeDecision,
    GradeProposal,
    GrantDecision,
    User,
    UserRole,
)
from fair_platform.backend.services.extension_grants import resolve_extension_effects
from fair_platform.backend.services.execution_store import (
    ExecutionStoreError,
    create_execution,
)
from fair_platform.backend.data.models import Thread, Turn


def _user() -> User:
    return User(
        id=uuid4(),
        name="Phase 1 integrity user",
        email=f"{uuid4()}@example.test",
        role=UserRole.professor,
    )


def test_artifact_part_requires_exactly_one_content_source(test_db):
    with test_db() as session:
        user = _user()
        session.add(user)
        artifact = Artifact(
            id=uuid4(), title="A", artifact_type="document", creator_id=user.id
        )
        session.add(artifact)
        session.flush()
        version = ArtifactVersion(artifact_id=artifact.id, ordinal=1, provenance={})
        session.add(version)
        session.flush()
        session.add(
            ArtifactPart(
                artifact_version_id=version.id,
                ordinal=1,
                name="content",
                role="primary",
                media_type="application/json",
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()


def test_published_flow_versions_are_immutable(test_db):
    with test_db() as session:
        user = _user()
        session.add(user)
        session.flush()
        flow = Flow(owner_user_id=user.id, name="Deterministic baseline")
        session.add(flow)
        session.flush()
        version = FlowVersion(
            flow_id=flow.id,
            ordinal=1,
            state=FlowVersionState.published,
            definition={"nodes": []},
            capability_pins=[],
            config_snapshot={},
            definition_hash="sha256:test",
            created_by_user_id=user.id,
        )
        session.add(version)
        session.commit()

        version.definition = {"nodes": [{"id": "changed"}]}
        with pytest.raises(ValueError, match="immutable once published"):
            session.commit()


def test_extension_effects_are_deny_by_default_and_duplicate_scope_is_rejected(test_db):
    with test_db() as session:
        installation = ExtensionInstallation(extension_id="phase1.test")
        session.add(installation)
        session.flush()
        missing = resolve_extension_effects(
            session, installation_id=installation.id, effects=["artifacts:write"]
        )
        assert missing["artifacts:write"].allowed is False

        session.add(
            ExtensionGrant(
                installation_id=installation.id,
                effect="artifacts:write",
                decision=GrantDecision.allow,
            )
        )
        session.flush()
        session.add(
            ExtensionGrant(
                installation_id=installation.id,
                effect="artifacts:write",
                decision=GrantDecision.deny,
            )
        )
        with pytest.raises(IntegrityError):
            session.flush()


def test_grade_tables_expose_phase1_lifecycle_constraints():
    proposal_constraints = {
        constraint.name for constraint in GradeProposal.__table__.constraints
    }
    decision_constraints = {
        constraint.name for constraint in GradeDecision.__table__.constraints
    }
    assert "uq_grade_proposals_submission_ordinal" in proposal_constraints
    assert "ck_grade_proposals_ordinal_positive" in proposal_constraints
    assert "ck_grade_proposals_confidence_range" in proposal_constraints
    assert "ck_grade_proposals_actor_present" in proposal_constraints
    assert "ck_grade_decisions_manual_replacement_content" in decision_constraints


def test_execution_turn_must_belong_to_its_thread(test_db):
    with test_db() as session:
        user = _user()
        session.add(user)
        session.flush()
        first = Thread(owner_user_id=user.id)
        second = Thread(owner_user_id=user.id)
        session.add_all([first, second])
        session.flush()
        turn = Turn(
            thread_id=first.id,
            ordinal=1,
            client_request_id=str(uuid4()),
            created_by_user_id=user.id,
        )
        session.add(turn)
        session.flush()
        with pytest.raises(ExecutionStoreError, match="must belong"):
            create_execution(
                session,
                kind="agent",
                thread_id=second.id,
                turn_id=turn.id,
                initiated_by_user_id=user.id,
            )


def test_abandoned_artifact_version_does_not_require_finalized_hashes(test_db):
    with test_db() as session:
        user = _user()
        artifact = Artifact(
            id=uuid4(), title="A", artifact_type="document", creator_id=user.id
        )
        session.add_all([user, artifact])
        session.flush()
        session.add(
            ArtifactVersion(
                artifact_id=artifact.id,
                ordinal=1,
                state="abandoned",
                provenance={},
            )
        )
        session.commit()


def test_artifact_current_version_cannot_point_to_another_artifact(test_db):
    with test_db() as session:
        user = _user()
        first = Artifact(
            id=uuid4(), title="A", artifact_type="document", creator_id=user.id
        )
        second = Artifact(
            id=uuid4(), title="B", artifact_type="document", creator_id=user.id
        )
        session.add_all([user, first, second])
        session.flush()
        version = ArtifactVersion(artifact_id=second.id, ordinal=1, provenance={})
        session.add(version)
        session.flush()
        first.current_version_id = version.id
        with pytest.raises(ArtifactVersionMutationError, match="same Artifact"):
            session.flush()


def test_artifact_version_can_only_supersede_earlier_same_artifact_version(test_db):
    with test_db() as session:
        user = _user()
        first = Artifact(
            id=uuid4(), title="A", artifact_type="document", creator_id=user.id
        )
        second = Artifact(
            id=uuid4(), title="B", artifact_type="document", creator_id=user.id
        )
        session.add_all([user, first, second])
        session.flush()
        prior = ArtifactVersion(artifact_id=second.id, ordinal=1, provenance={})
        session.add(prior)
        session.flush()
        session.add(
            ArtifactVersion(
                artifact_id=first.id,
                ordinal=2,
                provenance={},
                supersedes_version_id=prior.id,
            )
        )
        with pytest.raises(ArtifactVersionMutationError, match="same Artifact"):
            session.flush()
