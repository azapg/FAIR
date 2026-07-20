from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from collections.abc import Iterable
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from fair_platform.backend.data.models.execution import (
    EventDurability,
    EventVisibility,
    Execution,
    ExecutionEvent,
    ExecutionInputArtifact,
    ExecutionStatus,
    Turn,
    Thread,
)
from fair_platform.backend.data.models.artifact import Artifact
from fair_platform.backend.data.models.assignment import Assignment
from fair_platform.backend.data.models.course import Course
from fair_platform.backend.data.models.submission import Submission
from fair_platform.backend.data.models.user import User


class ExecutionStoreError(ValueError):
    """Base error for invalid durable Execution operations."""


class EventIdentityConflict(ExecutionStoreError):
    """A producer reused an event identity for different content or work."""


class ExecutionNotFound(ExecutionStoreError):
    """The referenced Execution does not exist."""


@dataclass(frozen=True)
class EventAppendResult:
    event: ExecutionEvent
    duplicate: bool


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def create_execution(
    session: Session,
    *,
    kind: str,
    thread_id: UUID | None = None,
    turn_id: UUID | None = None,
    initiated_by_user_id: UUID | None = None,
    parent_execution_id: UUID | None = None,
    retry_of_execution_id: UUID | None = None,
    course_id: UUID | None = None,
    assignment_id: UUID | None = None,
    submission_ids: Iterable[UUID] | None = None,
    **values: Any,
) -> Execution:
    """Create an Execution with valid lineage and typed LMS scope."""

    parent = (
        session.get(Execution, parent_execution_id)
        if parent_execution_id is not None
        else None
    )
    retry_of = (
        session.get(Execution, retry_of_execution_id)
        if retry_of_execution_id is not None
        else None
    )
    if parent_execution_id is not None and parent is None:
        raise ExecutionNotFound(
            f"parent Execution {parent_execution_id} does not exist"
        )
    if retry_of_execution_id is not None and retry_of is None:
        raise ExecutionNotFound(
            f"retry Execution {retry_of_execution_id} does not exist"
        )
    if parent is not None and retry_of is not None:
        if parent.root_execution_id != retry_of.root_execution_id:
            raise ExecutionStoreError(
                "parent and retry Executions must belong to the same root lineage"
            )
        if retry_of.parent_execution_id != parent.id:
            raise ExecutionStoreError(
                "a retried child Execution must retain its original parent"
            )

    lineage_source = parent or retry_of
    resolved_submission_ids = (
        list(dict.fromkeys(submission_ids)) if submission_ids is not None else None
    )
    if lineage_source is not None:
        if course_id is not None and course_id != lineage_source.course_id:
            raise ExecutionStoreError(
                "child and retry Executions must retain the root course scope"
            )
        if assignment_id is not None and assignment_id != lineage_source.assignment_id:
            raise ExecutionStoreError(
                "child and retry Executions must retain the root assignment scope"
            )
        course_id = lineage_source.course_id
        assignment_id = lineage_source.assignment_id
        if resolved_submission_ids is None:
            resolved_submission_ids = [item.id for item in lineage_source.submissions]

    thread = None
    if thread_id is not None:
        thread = session.get(Thread, thread_id)
        if thread is None:
            raise ExecutionStoreError(f"Thread {thread_id} does not exist")
        if course_id is not None and thread.course_id not in {None, course_id}:
            raise ExecutionStoreError(
                "Execution course scope conflicts with its Thread"
            )
        if assignment_id is not None and thread.assignment_id not in {
            None,
            assignment_id,
        }:
            raise ExecutionStoreError(
                "Execution assignment scope conflicts with its Thread"
            )
        course_id = course_id or thread.course_id
        assignment_id = assignment_id or thread.assignment_id
        if resolved_submission_ids is None and thread.submission_id is not None:
            resolved_submission_ids = [thread.submission_id]

    if turn_id is not None:
        turn = session.get(Turn, turn_id)
        if turn is None:
            raise ExecutionStoreError(f"Turn {turn_id} does not exist")
        if thread_id is None or turn.thread_id != thread_id:
            raise ExecutionStoreError(
                "turn_id must belong to the Execution's thread_id"
            )

    submissions: list[Submission] = []
    if resolved_submission_ids:
        submissions = list(
            session.scalars(
                select(Submission).where(Submission.id.in_(resolved_submission_ids))
            )
        )
        found_ids = {item.id for item in submissions}
        missing_ids = [
            item for item in resolved_submission_ids if item not in found_ids
        ]
        if missing_ids:
            raise ExecutionStoreError(
                f"Submission scope contains unknown IDs: {missing_ids}"
            )
        submission_assignment_ids = {item.assignment_id for item in submissions}
        if len(submission_assignment_ids) != 1:
            raise ExecutionStoreError(
                "one Execution cannot span submissions from multiple assignments"
            )
        submission_assignment_id = next(iter(submission_assignment_ids))
        if assignment_id is not None and assignment_id != submission_assignment_id:
            raise ExecutionStoreError(
                "Execution submissions must belong to its assignment scope"
            )
        assignment_id = assignment_id or submission_assignment_id

    if assignment_id is not None:
        assignment = session.get(Assignment, assignment_id)
        if assignment is None:
            raise ExecutionStoreError(f"Assignment {assignment_id} does not exist")
        if course_id is not None and course_id != assignment.course_id:
            raise ExecutionStoreError(
                "Execution assignment must belong to its course scope"
            )
        course_id = course_id or assignment.course_id
    elif course_id is not None and session.get(Course, course_id) is None:
        raise ExecutionStoreError(f"Course {course_id} does not exist")

    execution_id = uuid4()
    root_id = (
        (parent or retry_of).root_execution_id if (parent or retry_of) else execution_id
    )
    execution = Execution(
        id=execution_id,
        thread_id=thread_id,
        turn_id=turn_id,
        course_id=course_id,
        assignment_id=assignment_id,
        parent_execution_id=parent_execution_id,
        root_execution_id=root_id,
        retry_of_execution_id=retry_of_execution_id,
        attempt=(retry_of.attempt + 1) if retry_of is not None else 1,
        kind=kind,
        initiated_by_user_id=initiated_by_user_id,
        **values,
    )
    execution.submissions = submissions
    session.add(execution)
    session.flush()
    if lineage_source is not None:
        inherited_artifacts = list(
            session.scalars(
                select(ExecutionInputArtifact).where(
                    ExecutionInputArtifact.execution_id == lineage_source.id
                )
            )
        )
        for item in inherited_artifacts:
            session.add(
                ExecutionInputArtifact(
                    execution_id=execution.id,
                    artifact_id=item.artifact_id,
                    artifact_version_id=item.artifact_version_id,
                )
            )
    else:
        artifact_filters = []
        if execution.assignment_id is not None:
            artifact_filters.extend(
                [
                    Artifact.assignment_id == execution.assignment_id,
                    Artifact.assignments.any(id=execution.assignment_id),
                ]
            )
        if execution.submissions:
            artifact_filters.append(
                Artifact.submissions.any(
                    Submission.id.in_(
                        [submission.id for submission in execution.submissions]
                    )
                )
            )
        if artifact_filters:
            initiating_user = (
                session.get(User, execution.initiated_by_user_id)
                if execution.initiated_by_user_id is not None
                else None
            )
            if initiating_user is None:
                raise ExecutionStoreError(
                    "Artifact-scoped Executions require an initiating user"
                )
            from fair_platform.backend.services.artifact_manager import (
                get_artifact_manager,
            )

            artifact_manager = get_artifact_manager(session)
            for artifact in session.scalars(
                select(Artifact).where(or_(*artifact_filters))
            ):
                if not artifact_manager.can_view(initiating_user, artifact):
                    continue
                session.add(
                    ExecutionInputArtifact(
                        execution_id=execution.id,
                        artifact_id=artifact.id,
                        artifact_version_id=artifact.current_version_id,
                    )
                )
    session.flush()
    return execution


# Event types whose payload shape FAIR defines (and therefore may normalize).
# Anything else -- including custom research events -- is author data.
_STANDARD_EVENT_PREFIXES = ("execution.", "message.", "interaction.", "artifact.")


def _to_camel(key: str) -> str:
    head, *rest = key.split("_")
    return head + "".join(part[:1].upper() + part[1:] for part in rest)


def normalize_standard_event_payload(
    event_type: str, payload: dict[str, Any]
) -> dict[str, Any]:
    """Rewrite snake_case keys to camelCase for FAIR-defined event types."""

    if not event_type.startswith(_STANDARD_EVENT_PREFIXES):
        return payload
    normalized: dict[str, Any] = {}
    for key, value in payload.items():
        camel = _to_camel(key)
        # An explicit camel key already present always wins over a converted one.
        if camel in normalized and key != camel:
            continue
        normalized[camel] = value
    return normalized


def append_execution_event(
    session: Session,
    *,
    execution_id: UUID,
    producer_source: str,
    producer_event_id: str,
    event_type: str,
    schema_uri: str,
    payload: dict[str, Any],
    occurred_at: Optional[datetime] = None,
    producer_sequence: Optional[int] = None,
    visibility: EventVisibility = EventVisibility.user,
    durability: EventDurability = EventDurability.durable,
    parent_event_id: Optional[UUID] = None,
    trace_id: Optional[str] = None,
    span_id: Optional[str] = None,
) -> EventAppendResult:
    """Append one accepted durable event with server-assigned ordering.

    The Execution row is locked before allocating the next sequence. PostgreSQL
    uses that lock for concurrent writers; SQLite serializes the write through
    its normal transaction lock. Producer identity makes retries idempotent.
    """

    if durability is not EventDurability.durable:
        raise ExecutionStoreError(
            "ephemeral events must not enter the durable event store"
        )
    if not producer_source or len(producer_source) > 255:
        raise ExecutionStoreError("producer_source must be 1-255 characters")
    if not producer_event_id or len(producer_event_id) > 255:
        raise ExecutionStoreError("producer_event_id must be 1-255 characters")
    if not event_type or len(event_type) > 255:
        raise ExecutionStoreError("event_type must be 1-255 characters")
    if not schema_uri or len(schema_uri) > 2048:
        raise ExecutionStoreError("schema_uri must be 1-2048 characters")
    if producer_sequence is not None and (
        isinstance(producer_sequence, bool) or producer_sequence < 1
    ):
        raise ExecutionStoreError("producer_sequence must be a positive integer")

    existing = session.scalar(
        select(ExecutionEvent).where(
            ExecutionEvent.producer_source == producer_source,
            ExecutionEvent.producer_event_id == producer_event_id,
        )
    )
    if existing is not None:
        same_event = (
            existing.execution_id == execution_id
            and existing.type == event_type
            and existing.schema_uri == schema_uri
            and existing.payload == payload
            and existing.producer_sequence == producer_sequence
        )
        if not same_event:
            raise EventIdentityConflict(
                f"producer event {producer_source!r}/{producer_event_id!r} "
                "was already accepted with different content"
            )
        return EventAppendResult(event=existing, duplicate=True)

    execution = session.scalar(
        select(Execution).where(Execution.id == execution_id).with_for_update()
    )
    if execution is None:
        raise ExecutionNotFound(f"Execution {execution_id} does not exist")
    if execution.status in {
        ExecutionStatus.completed,
        ExecutionStatus.failed,
        ExecutionStatus.cancelled,
        ExecutionStatus.expired,
        ExecutionStatus.completed.value,
        ExecutionStatus.failed.value,
        ExecutionStatus.cancelled.value,
        ExecutionStatus.expired.value,
    }:
        raise ExecutionStoreError(
            f"Execution {execution_id} is terminal and cannot accept new events"
        )

    # Re-check after locking so a concurrent writer that committed between the
    # first lookup and the row lock is still handled idempotently.
    existing = session.scalar(
        select(ExecutionEvent).where(
            ExecutionEvent.producer_source == producer_source,
            ExecutionEvent.producer_event_id == producer_event_id,
        )
    )
    if existing is not None:
        same_event = (
            existing.execution_id == execution_id
            and existing.type == event_type
            and existing.schema_uri == schema_uri
            and existing.payload == payload
            and existing.producer_sequence == producer_sequence
        )
        if not same_event:
            raise EventIdentityConflict(
                f"producer event {producer_source!r}/{producer_event_id!r} "
                "was already accepted with different content"
            )
        return EventAppendResult(event=existing, duplicate=True)

    if parent_event_id is not None:
        parent_event = session.get(ExecutionEvent, parent_event_id)
        if parent_event is None:
            raise ExecutionStoreError(f"parent event {parent_event_id} does not exist")
        if parent_event.execution_id != execution_id:
            raise ExecutionStoreError(
                "parent_event_id must reference an event in the same Execution"
            )

    last_sequence = session.scalar(
        select(func.max(ExecutionEvent.sequence)).where(
            ExecutionEvent.execution_id == execution_id
        )
    )
    event = ExecutionEvent(
        execution_id=execution_id,
        sequence=int(last_sequence or 0) + 1,
        producer_source=producer_source,
        producer_event_id=producer_event_id,
        producer_sequence=producer_sequence,
        type=event_type,
        schema_uri=schema_uri,
        occurred_at=occurred_at or _utc_now(),
        visibility=visibility,
        durability=durability,
        payload=payload,
        parent_event_id=parent_event_id,
        trace_id=trace_id,
        span_id=span_id,
    )
    session.add(event)
    session.flush()
    return EventAppendResult(event=event, duplicate=False)


__all__ = [
    "EventAppendResult",
    "EventIdentityConflict",
    "ExecutionNotFound",
    "ExecutionStoreError",
    "append_execution_event",
    "create_execution",
]
