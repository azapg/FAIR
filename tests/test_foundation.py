from datetime import datetime, timezone
from uuid import uuid4

import pytest

from fair_platform.backend.data.database import Base
from fair_platform.backend.data.models import (
    Artifact,
    ArtifactPart,
    ArtifactVersion,
    ArtifactVersionState,
    ArtifactVersionMutationError,
    DispatchStatus,
    Execution,
    ExecutionStatus,
    InteractionRequest,
    InteractionStatus,
    Message,
    MessagePart,
    MessageRole,
    Thread,
    Turn,
    TurnStatus,
    User,
    UserRole,
)
from fair_platform.backend.services.artifact_version_service import (
    ArtifactVersionError,
    canonical_json_bytes,
    finalize_artifact_version,
    sha256_hex,
)
from fair_platform.backend.services.execution_outbox import (
    claim_dispatch,
    enqueue_dispatch,
    mark_dispatched,
)
from fair_platform.backend.services.execution_projection import (
    append_and_project_event,
    rebuild_execution_projection,
    replay_execution_events,
)
from fair_platform.backend.services.execution_store import (
    EventIdentityConflict,
    append_execution_event,
    create_execution,
)


def _user() -> User:
    return User(
        id=uuid4(),
        name="Foundation test user",
        email=f"{uuid4()}@example.test",
        role=UserRole.student,
    )


def _execution(session, user: User) -> Execution:
    thread = Thread(owner_user_id=user.id, title="Foundation thread")
    session.add(thread)
    session.flush()
    turn = Turn(
        thread_id=thread.id,
        ordinal=1,
        client_request_id=str(uuid4()),
        created_by_user_id=user.id,
        status=TurnStatus.open,
    )
    session.add(turn)
    session.flush()
    return create_execution(
        session,
        thread_id=thread.id,
        turn_id=turn.id,
        kind="agent",
        status=ExecutionStatus.queued,
        initiated_by_user_id=user.id,
    )


def test_foundation_table_inventory_is_registered():
    expected = {
        "threads",
        "turns",
        "executions",
        "execution_events",
        "execution_snapshots",
        "interaction_requests",
        "execution_dispatch_outbox",
        "execution_legacy_refs",
        "messages",
        "message_parts",
        "artifact_versions",
        "artifact_parts",
        "artifact_links",
        "grade_proposals",
        "grade_decisions",
        "extension_installations",
        "capability_definitions",
        "extension_grants",
        "flows",
        "flow_versions",
    }
    assert expected <= set(Base.metadata.tables)


def test_execution_events_are_ordered_and_idempotent(test_db):
    with test_db() as session:
        user = _user()
        session.add(user)
        session.flush()
        execution = _execution(session, user)
        session.commit()

        first = append_execution_event(
            session,
            execution_id=execution.id,
            producer_source="test-extension",
            producer_event_id="event-1",
            event_type="message.started",
            schema_uri="urn:fair:event:message.started:v1",
            payload={"message_id": str(uuid4())},
        )
        session.commit()

        duplicate = append_execution_event(
            session,
            execution_id=execution.id,
            producer_source="test-extension",
            producer_event_id="event-1",
            event_type="message.started",
            schema_uri="urn:fair:event:message.started:v1",
            payload=first.event.payload,
        )
        second = append_execution_event(
            session,
            execution_id=execution.id,
            producer_source="test-extension",
            producer_event_id="event-2",
            event_type="execution.completed",
            schema_uri="urn:fair:event:execution.completed:v1",
            payload={},
        )
        session.commit()

        assert duplicate.duplicate is True
        assert duplicate.event.id == first.event.id
        assert second.event.sequence == 2

        with pytest.raises(EventIdentityConflict):
            append_execution_event(
                session,
                execution_id=execution.id,
                producer_source="test-extension",
                producer_event_id="event-1",
                event_type="message.started",
                schema_uri="urn:fair:event:message.started:v1",
                payload={"different": True},
            )


def test_artifact_finalization_hashes_inline_parts_and_updates_current_pointer(test_db):
    with test_db() as session:
        user = _user()
        session.add(user)
        session.flush()
        artifact = Artifact(
            id=uuid4(),
            title="Feedback",
            artifact_type="feedback",
            creator_id=user.id,
        )
        session.add(artifact)
        session.flush()
        version = ArtifactVersion(
            artifact_id=artifact.id,
            ordinal=1,
            provenance={"source": "test"},
        )
        session.add(version)
        session.flush()
        part = ArtifactPart(
            artifact_version_id=version.id,
            ordinal=1,
            name="feedback.json",
            role="feedback",
            media_type="application/json",
            inline_json={"b": 2, "a": 1},
        )
        session.add(part)
        session.commit()

        finalized = finalize_artifact_version(session, version.id)
        session.commit()

        expected_part_bytes = canonical_json_bytes({"b": 2, "a": 1})
        assert finalized.state is ArtifactVersionState.finalized
        assert part.content_hash == sha256_hex(expected_part_bytes)
        assert part.size_bytes == len(expected_part_bytes)
        assert finalized.size_bytes == len(expected_part_bytes)
        assert finalized.content_hash is not None
        assert artifact.current_version_id == finalized.id

        finalized.media_type = "text/plain"
        with pytest.raises(ArtifactVersionMutationError):
            session.commit()
        session.rollback()

        with pytest.raises(ArtifactVersionError):
            finalize_artifact_version(session, version.id)


def test_outbox_claims_and_completes_a_dispatch(test_db):
    with test_db() as session:
        user = _user()
        session.add(user)
        session.flush()
        execution = _execution(session, user)
        dispatch = enqueue_dispatch(
            session,
            execution_id=execution.id,
            target="mock.extension",
            payload={"execution_id": str(execution.id)},
        )
        session.commit()

        claimed = claim_dispatch(
            session,
            worker_id="worker-1",
            now=datetime.now(timezone.utc),
        )
        session.commit()
        assert claimed is not None
        assert claimed.id == dispatch.id
        assert claimed.attempt_count == 1
        assert claimed.status is DispatchStatus.leased

        completed = mark_dispatched(session, claimed.id)
        session.commit()
        assert completed.status is DispatchStatus.dispatched


def test_message_projection_keeps_ordered_typed_parts(test_db):
    with test_db() as session:
        user = _user()
        session.add(user)
        session.flush()
        execution = _execution(session, user)
        turn = session.get(Turn, execution.turn_id)
        message = Message(
            thread_id=execution.thread_id,
            turn_id=turn.id,
            producing_execution_id=execution.id,
            role=MessageRole.assistant,
            author_type="platform",
            ordinal=1,
        )
        session.add(message)
        session.flush()
        session.add_all(
            [
                MessagePart(
                    message_id=message.id,
                    ordinal=1,
                    part_type="text",
                    text_content="hello",
                ),
                MessagePart(
                    message_id=message.id,
                    ordinal=2,
                    part_type="citation",
                    data={"source": "example"},
                ),
            ]
        )
        session.commit()

        stored = session.get(Message, message.id)
        assert [part.ordinal for part in stored.parts] == [1, 2]
        assert stored.parts[0].text_content == "hello"


def test_event_projection_and_rebuild_are_replayable(test_db):
    with test_db() as session:
        user = _user()
        session.add(user)
        session.flush()
        execution = _execution(session, user)
        message_id = uuid4()
        part_id = uuid4()

        append_and_project_event(
            session,
            execution_id=execution.id,
            producer_source="test-extension",
            producer_event_id="message-started",
            event_type="message.started",
            schema_uri="urn:fair:event:message.started:v1",
            payload={
                "message_id": str(message_id),
                "role": "assistant",
                "author_type": "platform",
                "ordinal": 1,
            },
        )
        append_and_project_event(
            session,
            execution_id=execution.id,
            producer_source="test-extension",
            producer_event_id="message-delta",
            event_type="message.delta",
            schema_uri="urn:fair:event:message.delta:v1",
            payload={
                "message_id": str(message_id),
                "part_id": str(part_id),
                "ordinal": 1,
                "part_type": "text",
                "text": "Hello replay",
            },
        )
        append_and_project_event(
            session,
            execution_id=execution.id,
            producer_source="test-extension",
            producer_event_id="message-completed",
            event_type="message.completed",
            schema_uri="urn:fair:event:message.completed:v1",
            payload={"message_id": str(message_id)},
        )
        append_and_project_event(
            session,
            execution_id=execution.id,
            producer_source="test-extension",
            producer_event_id="execution-completed",
            event_type="execution.completed",
            schema_uri="urn:fair:event:execution.completed:v1",
            payload={"output_summary": {"answer": "ok"}},
        )
        session.commit()

        message = session.get(Message, message_id)
        assert message is not None
        assert message.parts[0].text_content == "Hello replay"
        assert _enum_value(message.status) == "completed"
        assert _enum_value(execution.status) == "completed"
        assert execution.snapshot.projection["event_count"] == 4
        assert len(replay_execution_events(session, execution.id, after_sequence=2)) == 2

        snapshot = rebuild_execution_projection(session, execution.id)
        session.commit()
        rebuilt_message = session.get(Message, message_id)
        assert snapshot.last_sequence == 4
        assert rebuilt_message.parts[0].text_content == "Hello replay"


def test_interaction_events_project_to_rebuildable_requests(test_db):
    with test_db() as session:
        user = _user()
        session.add(user)
        session.flush()
        execution = _execution(session, user)
        interaction_id = uuid4()

        append_and_project_event(
            session,
            execution_id=execution.id,
            producer_source="test-extension",
            producer_event_id="interaction-requested",
            event_type="interaction.requested",
            schema_uri="urn:fair:event:interaction.requested:v1",
            payload={
                "interaction_id": str(interaction_id),
                "kind": "confirmation",
                "schema": {"type": "object"},
                "message": "Approve?",
            },
        )
        append_and_project_event(
            session,
            execution_id=execution.id,
            producer_source="test-extension",
            producer_event_id="interaction-resolved",
            event_type="interaction.resolved",
            schema_uri="urn:fair:event:interaction.resolved:v1",
            payload={
                "interaction_id": str(interaction_id),
                "response": {"approved": True},
            },
        )
        session.commit()

        interaction = session.get(InteractionRequest, interaction_id)
        assert interaction is not None
        assert _enum_value(interaction.status) == InteractionStatus.resolved.value
        assert interaction.response == {"approved": True}

        rebuild_execution_projection(session, execution.id)
        session.commit()
        rebuilt = session.get(InteractionRequest, interaction_id)
        assert rebuilt is not None
        assert _enum_value(rebuilt.status) == InteractionStatus.resolved.value


def _enum_value(value: object) -> str:
    return value.value if hasattr(value, "value") else str(value)
