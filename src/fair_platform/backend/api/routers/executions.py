from __future__ import annotations

import asyncio
import hashlib
import json
from collections.abc import AsyncIterable, Callable
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from fastapi.sse import EventSourceResponse, format_sse_event
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.core.security.dependencies import require_extension_client
from fair_platform.backend.api.schema.execution import (
    ExecutionEventBatch,
    ExecutionEventRead,
    ExecutionRead,
    InteractionRead,
    InteractionResolve,
    ThreadCreate,
    ThreadRead,
    TurnCreate,
    TurnRead,
)
from fair_platform.backend.data.database import SessionLocal, session_dependency
from fair_platform.backend.data.models import (
    Execution,
    ExecutionEvent,
    ExtensionClient,
    ExtensionInstallation,
    ExtensionInstallationStatus,
    InteractionRequest,
    Message,
    MessagePart,
    MessageRole,
    MessageStatus,
    Thread,
    Turn,
    TurnStatus,
    User,
)
from fair_platform.backend.data.models.execution import MessageAuthorType
from fair_platform.backend.data.models.execution import EventVisibility
from fair_platform.backend.services.execution_outbox import enqueue_dispatch
from fair_platform.backend.services.execution_projection import (
    ExecutionProjectionError,
    append_and_project_event,
    replay_execution_events,
)
from fair_platform.backend.services.execution_store import (
    EventIdentityConflict,
    ExecutionStoreError,
    create_execution,
)


router = APIRouter()

# User-authenticated callers may only add explicitly user-authored, non-state-
# changing events. Lifecycle, message, artifact, and interaction events are
# accepted only from the platform or the authenticated producing extension.
USER_APPENDABLE_EVENT_TYPES = frozenset({"user.feedback"})


def get_stream_session_factory() -> Callable[[], Session]:
    """Return the session factory used by the long-lived SSE polling loop."""

    return SessionLocal


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _enum_value(value: object) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _assert_thread_access(thread: Thread | None, user: User) -> Thread:
    if thread is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")
    if thread.owner_user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Thread access denied")
    return thread


def _assert_execution_access(execution: Execution | None, user: User) -> Execution:
    if execution is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found"
        )
    if execution.initiated_by_user_id == user.id:
        return execution
    if execution.thread is not None and execution.thread.owner_user_id == user.id:
        return execution
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Execution access denied")


def _event_read(event) -> ExecutionEventRead:
    return ExecutionEventRead(
        id=event.id,
        execution_id=event.execution_id,
        sequence=event.sequence,
        producer_source=event.producer_source,
        producer_event_id=event.producer_event_id,
        producer_sequence=event.producer_sequence,
        type=event.type,
        schema_uri=event.schema_uri,
        occurred_at=event.occurred_at,
        received_at=event.received_at,
        visibility=_enum_value(event.visibility),
        durability="durable",
        payload=event.payload,
        parent_event_id=event.parent_event_id,
        trace_id=event.trace_id,
        span_id=event.span_id,
    )


def _execution_read(execution: Execution) -> ExecutionRead:
    snapshot = execution.snapshot
    snapshot_payload = None
    if snapshot is not None:
        snapshot_payload = dict(snapshot.projection)
        snapshot_aliases = {
            "last_event_type": "lastEventType",
            "event_count": "eventCount",
            "waiting_reason": "waitingReason",
        }
        for source, target in snapshot_aliases.items():
            if source in snapshot_payload:
                snapshot_payload[target] = snapshot_payload.pop(source)
    return ExecutionRead(
        id=execution.id,
        thread_id=execution.thread_id,
        turn_id=execution.turn_id,
        parent_execution_id=execution.parent_execution_id,
        root_execution_id=execution.root_execution_id,
        retry_of_execution_id=execution.retry_of_execution_id,
        attempt=execution.attempt,
        kind=_enum_value(execution.kind),
        capability_id=execution.capability_id,
        capability_version=execution.capability_version,
        status=_enum_value(execution.status),
        waiting_reason=execution.waiting_reason,
        created_at=execution.created_at,
        started_at=execution.started_at,
        finished_at=execution.finished_at,
        error_code=execution.error_code,
        error_summary=execution.error_summary,
        snapshot=snapshot_payload,
    )


def _turn_read(session: Session, turn: Turn) -> TurnRead:
    execution = session.scalar(
        select(Execution).where(Execution.turn_id == turn.id).order_by(Execution.created_at)
    )
    user_message = session.scalar(
        select(Message)
        .where(Message.turn_id == turn.id, Message.role == MessageRole.user)
        .order_by(Message.ordinal)
    )
    if execution is None or user_message is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Turn is missing its foundational Execution or user Message",
        )
    return TurnRead(
        id=turn.id,
        thread_id=turn.thread_id,
        ordinal=turn.ordinal,
        client_request_id=turn.client_request_id,
        created_by_user_id=turn.created_by_user_id,
        status=_enum_value(turn.status),
        created_at=turn.created_at,
        completed_at=turn.completed_at,
        execution_id=execution.id,
        user_message_id=user_message.id,
    )


def _interaction_read(interaction: InteractionRequest) -> InteractionRead:
    return InteractionRead(
        id=interaction.id,
        execution_id=interaction.execution_id,
        kind=interaction.kind,
        schema_=interaction.schema,
        message=interaction.message,
        choices=interaction.choices,
        target_url=interaction.target_url,
        status=_enum_value(interaction.status),
        requested_by_extension_installation_id=(
            interaction.requested_by_extension_installation_id
        ),
        expires_at=interaction.expires_at,
        resolved_by_user_id=interaction.resolved_by_user_id,
        response=interaction.response,
        resolved_at=interaction.resolved_at,
        created_at=interaction.created_at,
    )


@router.post("/threads", response_model=ThreadRead, status_code=status.HTTP_201_CREATED)
def create_thread(
    payload: ThreadCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
) -> ThreadRead:
    thread = Thread(
        owner_user_id=current_user.id,
        title=payload.title,
        course_id=payload.course_id,
        assignment_id=payload.assignment_id,
        submission_id=payload.submission_id,
    )
    db.add(thread)
    db.flush()
    db.commit()
    return ThreadRead.model_validate(thread)


@router.post(
    "/threads/{thread_id}/turns",
    response_model=TurnRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_turn(
    thread_id: UUID,
    payload: TurnCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
) -> TurnRead:
    thread = _assert_thread_access(db.get(Thread, thread_id), current_user)
    client_request_id = payload.client_request_id or str(uuid4())
    existing_turn = db.scalar(
        select(Turn).where(
            Turn.thread_id == thread.id,
            Turn.client_request_id == client_request_id,
        )
    )
    if existing_turn is not None:
        return _turn_read(db, existing_turn)

    ordinal = int(
        db.scalar(select(func.max(Turn.ordinal)).where(Turn.thread_id == thread.id)) or 0
    ) + 1
    turn = Turn(
        thread_id=thread.id,
        ordinal=ordinal,
        client_request_id=client_request_id,
        created_by_user_id=current_user.id,
        status=TurnStatus.open,
    )
    db.add(turn)
    db.flush()

    user_message = Message(
        id=uuid4(),
        thread_id=thread.id,
        turn_id=turn.id,
        role=MessageRole.user,
        author_type=MessageAuthorType.user,
        author_user_id=current_user.id,
        ordinal=1,
        status=MessageStatus.completed,
        completed_at=_now(),
    )
    db.add(user_message)
    db.flush()
    db.add(
        MessagePart(
            id=uuid4(),
            message_id=user_message.id,
            ordinal=1,
            part_type="text",
            media_type="text/plain; charset=utf-8",
            text_content=payload.content,
        )
    )

    installation = db.scalar(
        select(ExtensionInstallation).where(
            ExtensionInstallation.extension_id == payload.target
        )
    )
    if installation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target extension installation not found",
        )
    if _enum_value(installation.status) != ExtensionInstallationStatus.enabled.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Target extension installation is not enabled",
        )

    execution = create_execution(
        db,
        kind="agent",
        thread_id=thread.id,
        turn_id=turn.id,
        initiated_by_user_id=current_user.id,
        extension_installation_id=installation.id,
        capability_id=payload.capability_id,
        input={"content": payload.content},
    )
    append_and_project_event(
        db,
        execution_id=execution.id,
        producer_source="fair.platform",
        producer_event_id=f"turn:{turn.id}:accepted",
        event_type="execution.created",
        schema_uri="urn:fair:event:execution.created:v1",
        payload={
            "thread_id": str(thread.id),
            "turn_id": str(turn.id),
            "user_message_id": str(user_message.id),
            "capability_id": payload.capability_id,
        },
    )
    enqueue_dispatch(
        db,
        execution_id=execution.id,
        target=payload.target,
        payload={
            "execution_id": str(execution.id),
            "thread_id": str(thread.id),
            "turn_id": str(turn.id),
            "input": {"content": payload.content},
            "capability_id": payload.capability_id,
        },
    )
    db.commit()
    return _turn_read(db, turn)


@router.get("/executions/{execution_id}", response_model=ExecutionRead)
def read_execution(
    execution_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
) -> ExecutionRead:
    execution = _assert_execution_access(db.get(Execution, execution_id), current_user)
    return _execution_read(execution)


@router.get("/executions/{execution_id}/events", response_model=list[ExecutionEventRead])
def read_execution_events(
    execution_id: UUID,
    after_sequence: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
) -> list[ExecutionEventRead]:
    execution = _assert_execution_access(db.get(Execution, execution_id), current_user)
    return [
        _event_read(event)
        for event in replay_execution_events(
            db,
            execution.id,
            after_sequence=after_sequence,
            limit=limit,
            visibility=EventVisibility.user,
        )
    ]


@router.post(
    "/executions/{execution_id}/events",
    response_model=list[ExecutionEventRead],
    status_code=status.HTTP_202_ACCEPTED,
)
def append_execution_events(
    execution_id: UUID,
    batch: ExecutionEventBatch,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
) -> list[ExecutionEventRead]:
    execution = _assert_execution_access(db.get(Execution, execution_id), current_user)
    accepted = []
    try:
        for event in batch.events:
            if event.type not in USER_APPENDABLE_EVENT_TYPES:
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Event type is not accepted from user-authenticated callers",
                )
            result = append_and_project_event(
                db,
                execution_id=execution.id,
                producer_source=f"user:{current_user.id}",
                producer_event_id=event.producer_event_id,
                producer_sequence=event.producer_sequence,
                event_type=event.type,
                schema_uri=event.schema_uri,
                occurred_at=event.occurred_at,
                visibility=EventVisibility.user,
                payload=event.payload,
                parent_event_id=event.parent_event_id,
                trace_id=event.trace_id,
                span_id=event.span_id,
            )
            accepted.append(_event_read(result.event))
        db.commit()
    except EventIdentityConflict as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except (ExecutionStoreError, ExecutionProjectionError) as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return accepted


@router.post(
    "/executions/{execution_id}/events/ingest",
    response_model=list[ExecutionEventRead],
    status_code=status.HTTP_202_ACCEPTED,
)
def ingest_extension_events(
    execution_id: UUID,
    batch: ExecutionEventBatch,
    extension_client: ExtensionClient = Depends(
        require_extension_client(("executions:events",))
    ),
    db: Session = Depends(session_dependency),
) -> list[ExecutionEventRead]:
    execution = db.get(Execution, execution_id)
    if execution is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found"
        )
    installation = db.get(ExtensionInstallation, execution.extension_installation_id)
    if (
        installation is None
        or installation.extension_id != extension_client.extension_id
        or _enum_value(installation.status) != ExtensionInstallationStatus.enabled.value
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Extension is not the producing installation for this Execution",
        )

    accepted = []
    try:
        for event in batch.events:
            if event.type == "interaction.resolved":
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Extensions cannot resolve user interactions",
                )
            if event.producer_source != extension_client.extension_id:
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="producer_source must match the authenticated extension",
                )
            result = append_and_project_event(
                db,
                execution_id=execution.id,
                producer_source=extension_client.extension_id,
                producer_event_id=event.producer_event_id,
                producer_sequence=event.producer_sequence,
                event_type=event.type,
                schema_uri=event.schema_uri,
                occurred_at=event.occurred_at,
                visibility=event.visibility,
                payload=event.payload,
                parent_event_id=event.parent_event_id,
                trace_id=event.trace_id,
                span_id=event.span_id,
            )
            accepted.append(_event_read(result.event))
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except EventIdentityConflict as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except (ExecutionStoreError, ExecutionProjectionError) as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return accepted


@router.get(
    "/executions/{execution_id}/interactions",
    response_model=list[InteractionRead],
)
def list_execution_interactions(
    execution_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
) -> list[InteractionRead]:
    execution = _assert_execution_access(db.get(Execution, execution_id), current_user)
    interactions = list(
        db.scalars(
            select(InteractionRequest)
            .where(InteractionRequest.execution_id == execution.id)
            .order_by(InteractionRequest.created_at, InteractionRequest.id)
        )
    )
    return [_interaction_read(interaction) for interaction in interactions]


@router.post(
    "/interactions/{interaction_id}/resolve",
    response_model=InteractionRead,
)
def resolve_interaction(
    interaction_id: UUID,
    payload: InteractionResolve,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
) -> InteractionRead:
    interaction = db.get(InteractionRequest, interaction_id)
    if interaction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Interaction not found"
        )
    execution = _assert_execution_access(db.get(Execution, interaction.execution_id), current_user)
    request_id = payload.client_request_id or str(uuid4())
    request_fingerprint = hashlib.sha256(request_id.encode("utf-8")).hexdigest()
    producer_event_id = f"interaction-resolve:{interaction.id}:{request_fingerprint}"
    if _enum_value(interaction.status) != "pending":
        existing = db.scalar(
            select(ExecutionEvent).where(
                ExecutionEvent.producer_source == f"user:{current_user.id}",
                ExecutionEvent.producer_event_id == producer_event_id,
            )
        )
        if existing is not None:
            return _interaction_read(interaction)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Interaction is no longer pending",
        )

    try:
        append_and_project_event(
            db,
            execution_id=execution.id,
            producer_source=f"user:{current_user.id}",
            producer_event_id=producer_event_id,
            event_type="interaction.resolved",
            schema_uri="urn:fair:event:interaction.resolved:v1",
            payload={
                "interaction_id": str(interaction.id),
                "status": payload.status,
                "response": payload.response,
                "resolved_by_user_id": str(current_user.id),
            },
        )
        db.commit()
    except EventIdentityConflict as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except (ExecutionStoreError, ExecutionProjectionError) as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    db.refresh(interaction)
    return _interaction_read(interaction)


@router.get("/executions/{execution_id}/stream")
async def stream_execution_events(
    execution_id: UUID,
    after_sequence: int = Query(default=0, ge=0),
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
    stream_session_factory: Callable[[], Session] = Depends(get_stream_session_factory),
) -> EventSourceResponse:
    execution = _assert_execution_access(db.get(Execution, execution_id), current_user)
    cursor = after_sequence
    if last_event_id:
        try:
            cursor = max(cursor, int(last_event_id))
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Last-Event-ID must be a non-negative event sequence",
            ) from exc

    async def event_stream() -> AsyncIterable[bytes]:
        nonlocal cursor
        heartbeat_count = 0
        try:
            while True:
                with stream_session_factory() as stream_db:
                    stream_execution = stream_db.get(Execution, execution.id)
                    if stream_execution is None:
                        return
                    events = replay_execution_events(
                        stream_db,
                        execution.id,
                        after_sequence=cursor,
                        limit=500,
                        visibility=EventVisibility.user,
                    )
                    stream_status = _enum_value(stream_execution.status)

                for event in events:
                    cursor = event.sequence
                    heartbeat_count = 0
                    payload = jsonable_encoder(_event_read(event).model_dump(by_alias=True))
                    yield format_sse_event(
                        id=str(event.sequence),
                        event=event.type,
                        data_str=json.dumps(payload, separators=(",", ":")),
                    )

                if stream_status in {
                    "completed",
                    "failed",
                    "cancelled",
                    "expired",
                }:
                    return

                heartbeat_count += 1
                if heartbeat_count >= 15:
                    heartbeat_count = 0
                    yield format_sse_event(comment="keep-alive")
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            return

    return EventSourceResponse(
        event_stream(),
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


__all__ = ["get_stream_session_factory", "router"]
