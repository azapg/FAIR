from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fair_platform.backend.data.models.execution import (
    Execution,
    ExecutionEvent,
    ExecutionSnapshot,
    ExecutionStatus,
    EventVisibility,
    InteractionRequest,
    InteractionStatus,
    Message,
    MessageAuthorType,
    MessagePart,
    MessageRole,
    MessageStatus,
)
from fair_platform.backend.services.execution_store import (
    EventAppendResult,
    append_execution_event,
)


REDUCER_VERSION = "execution-projection-v1"
TERMINAL_STATUSES = {
    ExecutionStatus.completed.value,
    ExecutionStatus.failed.value,
    ExecutionStatus.cancelled.value,
    ExecutionStatus.expired.value,
}


class ExecutionProjectionError(ValueError):
    """The event is valid JSON but cannot be projected into product state."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _value(value: object) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _payload_value(payload: dict[str, Any], field: str, default: Any = None) -> Any:
    if field in payload:
        return payload[field]
    camel = field.split("_")[0] + "".join(part.title() for part in field.split("_")[1:])
    return payload.get(camel, default)


def _uuid(payload: dict[str, Any], field: str, *, required: bool = True) -> UUID | None:
    raw = _payload_value(payload, field)
    if raw is None:
        if required:
            raise ExecutionProjectionError(f"event payload requires {field}")
        return None
    try:
        return UUID(str(raw))
    except (TypeError, ValueError) as exc:
        raise ExecutionProjectionError(f"event payload field {field} must be a UUID") from exc


def _datetime(payload: dict[str, Any], field: str) -> datetime | None:
    raw = _payload_value(payload, field)
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ExecutionProjectionError(f"event payload field {field} must be an ISO datetime") from exc


def _next_message_ordinal(session: Session, execution: Execution) -> int:
    query = select(func.max(Message.ordinal)).where(Message.thread_id == execution.thread_id)
    if execution.turn_id is not None:
        query = query.where(Message.turn_id == execution.turn_id)
    return int(session.scalar(query) or 0) + 1


def _message_ordinal_is_taken(
    session: Session,
    *,
    thread_id: UUID,
    turn_id: UUID | None,
    ordinal: int,
) -> bool:
    query = select(Message.id).where(
        Message.thread_id == thread_id,
        Message.ordinal == ordinal,
    )
    if turn_id is None:
        query = query.where(Message.turn_id.is_(None))
    else:
        query = query.where(Message.turn_id == turn_id)
    return session.scalar(query) is not None


def _ensure_message(
    session: Session,
    execution: Execution,
    payload: dict[str, Any],
) -> Message:
    message_id = _uuid(payload, "message_id")
    message = session.get(Message, message_id)
    if message is not None:
        return message

    role_raw = _payload_value(payload, "role", MessageRole.assistant.value)
    author_raw = _payload_value(payload, "author_type", MessageAuthorType.platform.value)
    try:
        role = MessageRole(role_raw)
        author_type = MessageAuthorType(author_raw)
    except ValueError as exc:
        raise ExecutionProjectionError("message role/author_type is not supported") from exc

    message_thread_id = _uuid(payload, "thread_id", required=False) or execution.thread_id
    message_turn_id = _uuid(payload, "turn_id", required=False) or execution.turn_id
    requested_ordinal = int(_payload_value(payload, "ordinal") or 1)
    ordinal = requested_ordinal
    if _message_ordinal_is_taken(
        session,
        thread_id=message_thread_id,
        turn_id=message_turn_id,
        ordinal=requested_ordinal,
    ):
        ordinal = _next_message_ordinal(session, execution)

    message = Message(
        id=message_id,
        thread_id=message_thread_id,
        turn_id=message_turn_id,
        producing_execution_id=execution.id,
        role=role,
        author_type=author_type,
        ordinal=ordinal,
        status=MessageStatus.streaming,
    )
    session.add(message)
    session.flush()
    return message


def _ensure_part(
    session: Session,
    message: Message,
    payload: dict[str, Any],
) -> MessagePart:
    part_id = _uuid(payload, "part_id")
    part = session.get(MessagePart, part_id)
    if part is not None:
        return part

    part = MessagePart(
        id=part_id,
        message_id=message.id,
        ordinal=int(_payload_value(payload, "ordinal") or 1),
        part_type=str(_payload_value(payload, "part_type") or "text"),
        media_type=_payload_value(payload, "media_type"),
        schema_uri=_payload_value(payload, "schema_uri"),
        text_content=_payload_value(payload, "text"),
        data=_payload_value(payload, "data"),
        artifact_version_id=_uuid(payload, "artifact_version_id", required=False),
    )
    session.add(part)
    session.flush()
    return part


def _ensure_interaction(
    session: Session,
    execution: Execution,
    payload: dict[str, Any],
) -> InteractionRequest:
    interaction_id = _uuid(payload, "interaction_id")
    interaction = session.get(InteractionRequest, interaction_id)
    if interaction is not None:
        if interaction.execution_id != execution.id:
            raise ExecutionProjectionError(
                "interaction_id must reference an InteractionRequest in the same Execution"
            )
        return interaction

    interaction = InteractionRequest(
        id=interaction_id,
        execution_id=execution.id,
        kind=str(_payload_value(payload, "kind") or "confirmation"),
        schema=_payload_value(payload, "schema") or {},
        message=str(_payload_value(payload, "message") or ""),
        choices=_payload_value(payload, "choices"),
        target_url=_payload_value(payload, "target_url"),
        requested_by_extension_installation_id=execution.extension_installation_id,
        expires_at=_datetime(payload, "expires_at"),
        status=InteractionStatus.pending,
    )
    if not interaction.message:
        raise ExecutionProjectionError("interaction.requested requires message")
    session.add(interaction)
    session.flush()
    return interaction


def _apply_execution_lifecycle(
    execution: Execution,
    event: ExecutionEvent,
) -> None:
    suffix = event.type.removeprefix("execution.")
    payload = event.payload or {}
    status_by_event = {
        "started": ExecutionStatus.running.value,
        "waiting": ExecutionStatus.waiting.value,
        "completed": ExecutionStatus.completed.value,
        "failed": ExecutionStatus.failed.value,
        "cancelled": ExecutionStatus.cancelled.value,
        "expired": ExecutionStatus.expired.value,
    }
    next_status = (
        str(_payload_value(payload, "status"))
        if suffix == "status"
        else status_by_event.get(suffix)
    )
    if next_status is None:
        return
    allowed = {status.value for status in ExecutionStatus}
    if next_status not in allowed:
        raise ExecutionProjectionError(f"unsupported Execution status {next_status!r}")

    execution.status = next_status
    if next_status == ExecutionStatus.running.value and execution.started_at is None:
        execution.started_at = event.occurred_at
    if next_status == ExecutionStatus.waiting.value:
        execution.waiting_reason = _payload_value(payload, "reason") or _payload_value(
            payload, "waiting_reason"
        )
    else:
        execution.waiting_reason = None
    if next_status in TERMINAL_STATUSES:
        execution.finished_at = execution.finished_at or event.received_at
    if next_status == ExecutionStatus.completed.value:
        execution.output_summary = _payload_value(payload, "output_summary") or _payload_value(
            payload, "output"
        )
    if next_status == ExecutionStatus.failed.value:
        execution.error_code = _payload_value(payload, "error_code")
        execution.error_summary = _payload_value(payload, "error_summary") or _payload_value(
            payload, "error"
        )


def apply_execution_event(
    session: Session,
    event: ExecutionEvent,
    *,
    force: bool = False,
) -> ExecutionSnapshot:
    """Apply one accepted event to the Execution and message projections.

    Projection application is idempotent by `(execution_id, sequence)`. This
    lets duplicate ingestion repair a projection after a worker crash between
    event persistence and projection commit.
    """

    execution = session.get(Execution, event.execution_id)
    if execution is None:
        raise ExecutionProjectionError(f"Execution {event.execution_id} does not exist")

    snapshot = session.get(ExecutionSnapshot, execution.id)
    if snapshot is not None and not force and snapshot.last_sequence >= event.sequence:
        return snapshot

    _apply_execution_lifecycle(execution, event)
    payload = event.payload or {}

    if event.type == "message.started":
        _ensure_message(session, execution, payload)
    elif event.type in {"message.part.created", "message.delta"}:
        message = _ensure_message(session, execution, payload)
        if event.type == "message.delta":
            part_payload = dict(payload)
            part_payload.pop("text", None)
            part_payload.pop("delta", None)
            part = _ensure_part(session, message, part_payload)
            delta = _payload_value(payload, "text") or _payload_value(payload, "delta") or ""
            part.text_content = (part.text_content or "") + str(delta)
        else:
            _ensure_part(session, message, payload)
    elif event.type in {"message.completed", "message.failed", "message.cancelled"}:
        message = _ensure_message(session, execution, payload)
        message.status = {
            "message.completed": MessageStatus.completed,
            "message.failed": MessageStatus.failed,
            "message.cancelled": MessageStatus.cancelled,
        }[event.type]
        message.completed_at = event.received_at
    elif event.type == "interaction.requested":
        _ensure_interaction(session, execution, payload)
    elif event.type == "interaction.resolved":
        interaction_id = _uuid(payload, "interaction_id")
        interaction = session.get(InteractionRequest, interaction_id)
        if interaction is None or interaction.execution_id != execution.id:
            raise ExecutionProjectionError(
                "interaction.resolved must reference an InteractionRequest in the same Execution"
            )
        try:
            interaction.status = InteractionStatus(
                _payload_value(payload, "status") or InteractionStatus.resolved.value
            )
        except ValueError as exc:
            raise ExecutionProjectionError("interaction status is not supported") from exc
        interaction.response = _payload_value(payload, "response")
        interaction.resolved_by_user_id = _uuid(
            payload, "resolved_by_user_id", required=False
        )
        interaction.resolved_at = event.received_at

    projection = dict(snapshot.projection) if snapshot is not None else {}
    projection.update(
        {
            "status": _value(execution.status),
            "last_event_type": event.type,
            "event_count": event.sequence,
        }
    )
    if execution.waiting_reason:
        projection["waiting_reason"] = execution.waiting_reason
    else:
        projection.pop("waiting_reason", None)

    if snapshot is None:
        snapshot = ExecutionSnapshot(
            execution_id=execution.id,
            last_sequence=event.sequence,
            reducer_version=REDUCER_VERSION,
            projection=projection,
        )
        session.add(snapshot)
    else:
        snapshot.last_sequence = event.sequence
        snapshot.reducer_version = REDUCER_VERSION
        snapshot.projection = projection
        snapshot.updated_at = _utc_now()
    session.flush()
    return snapshot


def append_and_project_event(session: Session, **kwargs: Any) -> EventAppendResult:
    result = append_execution_event(session, **kwargs)
    apply_execution_event(session, result.event)
    return result


def replay_execution_events(
    session: Session,
    execution_id: UUID,
    *,
    after_sequence: int = 0,
    limit: int = 100,
    visibility: EventVisibility | None = None,
) -> list[ExecutionEvent]:
    if after_sequence < 0:
        raise ValueError("after_sequence must be non-negative")
    if limit < 1 or limit > 500:
        raise ValueError("limit must be between 1 and 500")
    filters = [
        ExecutionEvent.execution_id == execution_id,
        ExecutionEvent.sequence > after_sequence,
    ]
    if visibility is not None:
        filters.append(ExecutionEvent.visibility == visibility)
    return list(
        session.scalars(
            select(ExecutionEvent)
            .where(*filters)
            .order_by(ExecutionEvent.sequence)
            .limit(limit)
        )
    )


def rebuild_execution_projection(
    session: Session,
    execution_id: UUID,
) -> ExecutionSnapshot | None:
    execution = session.get(Execution, execution_id)
    if execution is None:
        raise ExecutionProjectionError(f"Execution {execution_id} does not exist")
    snapshot = session.get(ExecutionSnapshot, execution_id)
    if snapshot is not None:
        session.delete(snapshot)
        session.flush()

    # Message projections produced by this Execution are derived state. Clear
    # them before replay so message.delta events do not append their text a
    # second time. User-authored messages are not owned by the Execution and
    # remain intact.
    produced_messages = list(
        session.scalars(
            select(Message).where(Message.producing_execution_id == execution_id)
        )
    )
    for message in produced_messages:
        session.delete(message)
    if produced_messages:
        session.flush()

    produced_interactions = list(
        session.scalars(
            select(InteractionRequest).where(InteractionRequest.execution_id == execution_id)
        )
    )
    for interaction in produced_interactions:
        session.delete(interaction)
    if produced_interactions:
        session.flush()

    events = list(
        session.scalars(
            select(ExecutionEvent)
            .where(ExecutionEvent.execution_id == execution_id)
            .order_by(ExecutionEvent.sequence)
        )
    )
    for event in events:
        apply_execution_event(session, event, force=True)
    return session.get(ExecutionSnapshot, execution_id)


__all__ = [
    "ExecutionProjectionError",
    "REDUCER_VERSION",
    "TERMINAL_STATUSES",
    "append_and_project_event",
    "apply_execution_event",
    "rebuild_execution_projection",
    "replay_execution_events",
]
