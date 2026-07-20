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
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.core.security.permissions import (
    has_capability,
    has_capability_and_owner,
)
from fair_platform.backend.services.execution_authorization import (
    ExecutionAuthorization,
    issue_execution_token,
    require_execution_authorization,
)
from fair_platform.backend.services.capability_validation import (
    CapabilityOutputError,
    validate_capability_output,
)
from fair_platform.backend.api.schema.execution import (
    ExecutionEventBatch,
    FunctionInvoke,
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
    Assignment,
    Execution,
    ExecutionEvent,
    CapabilityDefinition,
    Course,
    ExtensionInstallation,
    ExtensionInstallationStatus,
    InteractionRequest,
    Message,
    MessagePart,
    MessageRole,
    MessageStatus,
    Submission,
    Thread,
    Turn,
    TurnStatus,
    User,
)
from fair_platform.backend.services.course_access import (
    can_manage_course,
    can_view_course,
)
from fair_platform.backend.data.models.execution import MessageAuthorType
from fair_platform.backend.data.models.execution import EventVisibility
from fair_platform.backend.data.models.execution import DispatchCommandKind
from fair_platform.extension_sdk.contracts.protocol import (
    DelegatedExecutionAuthorization,
)
from fair_platform.backend.services.execution_outbox import enqueue_dispatch
from fair_platform.backend.services.capability_validation import (
    CapabilityInputError,
    validate_capability_input,
)
from fair_platform.backend.services.extension_grants import resolve_extension_effects
from fair_platform.backend.services.execution_projection import (
    ExecutionProjectionError,
    append_and_project_event,
    replay_execution_events,
)
from fair_platform.backend.services.execution_store import (
    EventIdentityConflict,
    ExecutionStoreError,
    create_execution,
    normalize_standard_event_payload,
)
from fair_platform.backend.services.flow_runtime import (
    FlowRuntimeError,
    advance_flow_execution,
    fail_flow_execution,
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found"
        )
    if thread.owner_user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Thread access denied"
        )
    return thread


def _resolve_thread_scope(
    db: Session,
    payload: ThreadCreate,
    user: User,
) -> tuple[UUID | None, UUID | None, UUID | None]:
    """Resolve and authorize typed educational context before it reaches a token."""

    course_id = payload.course_id
    assignment_id = payload.assignment_id
    submission_id = payload.submission_id
    submission = db.get(Submission, submission_id) if submission_id else None
    if submission_id is not None and submission is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    if submission is not None:
        if assignment_id is not None and assignment_id != submission.assignment_id:
            raise HTTPException(
                status_code=422,
                detail="Submission does not belong to the requested assignment",
            )
        assignment_id = submission.assignment_id

    assignment = db.get(Assignment, assignment_id) if assignment_id else None
    if assignment_id is not None and assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    if assignment is not None:
        if course_id is not None and course_id != assignment.course_id:
            raise HTTPException(
                status_code=422,
                detail="Assignment does not belong to the requested course",
            )
        course_id = assignment.course_id

    course = db.get(Course, course_id) if course_id else None
    if course_id is not None and course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    if course is not None and not can_view_course(db, course, user):
        raise HTTPException(status_code=403, detail="Course access denied")
    can_manage = course is not None and can_manage_course(db, course, user)
    if (
        assignment is not None
        and not can_manage
        and _enum_value(assignment.status) == "draft"
    ):
        raise HTTPException(status_code=404, detail="Assignment not found")
    if (
        submission is not None
        and course is not None
        and not can_manage
        and submission.submitter.user_id != user.id
    ):
        raise HTTPException(status_code=403, detail="Submission access denied")
    return course_id, assignment_id, submission_id


def _assert_execution_access(execution: Execution | None, user: User) -> Execution:
    if execution is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found"
        )
    if execution.initiated_by_user_id == user.id:
        return execution
    if execution.thread is not None and execution.thread.owner_user_id == user.id:
        return execution
    if execution.course is not None and has_capability_and_owner(
        user,
        "read_executions",
        execution.course.instructor_id,
    ):
        return execution
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail="Execution access denied"
    )


def _event_read(event) -> ExecutionEventRead:
    # Protocol 1 §2 makes camel-case the wire contract. Extensions and FAIR's
    # own services both write standard payloads in their native casing, so
    # normalize on the way out: every client then reads one shape, and the
    # durable log still records exactly what the producer sent.
    payload = normalize_standard_event_payload(event.type, event.payload)
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
        payload=payload,
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
        course_id=execution.course_id,
        assignment_id=execution.assignment_id,
        submission_ids=[submission.id for submission in execution.submissions],
        parent_execution_id=execution.parent_execution_id,
        root_execution_id=execution.root_execution_id,
        retry_of_execution_id=execution.retry_of_execution_id,
        attempt=execution.attempt,
        idempotency_key=execution.idempotency_key,
        kind=_enum_value(execution.kind),
        capability_id=execution.capability_id,
        capability_version=execution.capability_version,
        capability_definition_id=execution.capability_definition_id,
        flow_version_id=execution.flow_version_id,
        initiated_by_user_id=execution.initiated_by_user_id,
        extension_installation_id=execution.extension_installation_id,
        status=_enum_value(execution.status),
        waiting_reason=execution.waiting_reason,
        created_at=execution.created_at,
        started_at=execution.started_at,
        finished_at=execution.finished_at,
        error_code=execution.error_code,
        error_summary=execution.error_summary,
        output_summary=execution.output_summary,
        snapshot=snapshot_payload,
    )


def _turn_read(session: Session, turn: Turn) -> TurnRead:
    execution = session.scalar(
        select(Execution)
        .where(Execution.turn_id == turn.id)
        .order_by(Execution.created_at)
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
    course_id, assignment_id, submission_id = _resolve_thread_scope(
        db, payload, current_user
    )
    thread = Thread(
        owner_user_id=current_user.id,
        title=payload.title,
        course_id=course_id,
        assignment_id=assignment_id,
        submission_id=submission_id,
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
    thread = _assert_thread_access(
        db.scalar(select(Thread).where(Thread.id == thread_id).with_for_update()),
        current_user,
    )
    client_request_id = payload.client_request_id or str(uuid4())
    execution_input = (
        payload.input if payload.input is not None else {"content": payload.content}
    )
    existing_turn = db.scalar(
        select(Turn).where(
            Turn.thread_id == thread.id,
            Turn.client_request_id == client_request_id,
        )
    )
    if existing_turn is not None:
        existing_execution = db.scalar(
            select(Execution)
            .where(Execution.turn_id == existing_turn.id)
            .order_by(Execution.created_at)
        )
        existing_text = db.scalar(
            select(MessagePart.text_content)
            .join(Message, Message.id == MessagePart.message_id)
            .where(
                Message.turn_id == existing_turn.id,
                Message.author_type == MessageAuthorType.user,
                Message.author_user_id == current_user.id,
                MessagePart.ordinal == 1,
            )
        )
        if (
            existing_execution is None
            or existing_execution.capability_definition_id
            != payload.capability_definition_id
            or existing_execution.input != execution_input
            or existing_text != payload.content
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="clientRequestId was already used for a different Turn request",
            )
        return _turn_read(db, existing_turn)

    ordinal = (
        int(
            db.scalar(select(func.max(Turn.ordinal)).where(Turn.thread_id == thread.id))
            or 0
        )
        + 1
    )
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

    capability = db.get(CapabilityDefinition, payload.capability_definition_id)
    if capability is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Capability definition not found",
        )
    if capability.surface != "chat.agent":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A conversational Turn requires a chat.agent capability",
        )
    installation = db.get(ExtensionInstallation, capability.installation_id)
    if installation is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Capability installation is missing",
        )
    if _enum_value(installation.status) != ExtensionInstallationStatus.enabled.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Capability installation is not enabled",
        )

    try:
        validate_capability_input(capability, execution_input)
    except CapabilityInputError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    resolutions = resolve_extension_effects(
        db,
        installation_id=installation.id,
        capability_definition_id=capability.id,
        effects=tuple(capability.declared_effects or ()),
        course_id=thread.course_id,
        assignment_id=thread.assignment_id,
    )
    denied_effects = sorted(
        effect for effect, resolution in resolutions.items() if not resolution.allowed
    )
    if denied_effects:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Capability is not granted effects: {', '.join(denied_effects)}",
        )

    execution = create_execution(
        db,
        kind="agent",
        thread_id=thread.id,
        turn_id=turn.id,
        initiated_by_user_id=current_user.id,
        extension_installation_id=installation.id,
        capability_id=capability.capability_id,
        capability_version=capability.version,
        capability_definition_id=capability.id,
        input=execution_input,
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
            "capability_definition_id": str(capability.id),
            "capability_id": capability.capability_id,
            "capability_version": capability.version,
        },
    )
    enqueue_dispatch(
        db,
        execution_id=execution.id,
        target=installation.extension_id,
        payload=execution_input,
    )
    db.commit()
    return _turn_read(db, turn)


@router.post(
    "/functions/invoke",
    response_model=ExecutionRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def invoke_function(
    payload: FunctionInvoke,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
) -> ExecutionRead:
    """Run the capability that implements a FAIR contract.

    Callers name a *contract* ("fair.rubric.generate@1"), not an extension.
    That is what lets one generic button work wherever a contract declares a
    placement, and lets a different Extension take over the contract without
    the UI changing.
    """

    capability = db.scalar(
        select(CapabilityDefinition)
        .join(ExtensionInstallation)
        .where(
            CapabilityDefinition.contract == payload.contract,
            CapabilityDefinition.surface == "function",
            ExtensionInstallation.status == ExtensionInstallationStatus.enabled,
        )
        .order_by(CapabilityDefinition.created_at.desc())
    )
    if capability is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No enabled Extension implements {payload.contract}",
        )
    installation = db.get(ExtensionInstallation, capability.installation_id)

    course_id, assignment_id = _resolve_function_scope(db, payload, current_user)

    try:
        validate_capability_input(capability, payload.input)
    except CapabilityInputError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    resolutions = resolve_extension_effects(
        db,
        installation_id=installation.id,
        capability_definition_id=capability.id,
        effects=tuple(capability.declared_effects or ()),
        course_id=course_id,
        assignment_id=assignment_id,
    )
    denied = sorted(
        effect for effect, resolution in resolutions.items() if not resolution.allowed
    )
    if denied:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Capability is not granted effects: {', '.join(denied)}",
        )

    execution = create_execution(
        db,
        kind="action",
        initiated_by_user_id=current_user.id,
        extension_installation_id=installation.id,
        capability_id=capability.capability_id,
        capability_version=capability.version,
        capability_definition_id=capability.id,
        course_id=course_id,
        assignment_id=assignment_id,
        input=payload.input,
    )
    append_and_project_event(
        db,
        execution_id=execution.id,
        producer_source="fair.platform",
        producer_event_id=f"function:{execution.id}:accepted",
        event_type="execution.created",
        schema_uri="urn:fair:event:execution.created:v1",
        payload={
            "contract": payload.contract,
            "capabilityDefinitionId": str(capability.id),
            "capabilityId": capability.capability_id,
            "capabilityVersion": capability.version,
        },
    )
    enqueue_dispatch(
        db,
        execution_id=execution.id,
        target=installation.extension_id,
        payload=payload.input,
    )
    db.commit()
    db.refresh(execution)
    return _execution_read(execution)


def _resolve_function_scope(
    db: Session, payload: FunctionInvoke, user: User
) -> tuple[UUID | None, UUID | None]:
    """Authorize the course/assignment a function run claims to act in."""

    assignment = db.get(Assignment, payload.assignment_id) if payload.assignment_id else None
    if payload.assignment_id is not None and assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    course_id = assignment.course_id if assignment else payload.course_id
    course = db.get(Course, course_id) if course_id else None
    if course_id is not None and course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    if course is not None and not can_view_course(db, course, user):
        raise HTTPException(status_code=403, detail="Course access denied")
    return course_id, (assignment.id if assignment else None)


@router.get("/executions/{execution_id}", response_model=ExecutionRead)
def read_execution(
    execution_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
) -> ExecutionRead:
    execution = _assert_execution_access(db.get(Execution, execution_id), current_user)
    return _execution_read(execution)


@router.post(
    "/executions/{execution_id}/cancel",
    response_model=ExecutionRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def cancel_execution(
    execution_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
) -> ExecutionRead:
    execution = _assert_execution_access(db.get(Execution, execution_id), current_user)
    if _enum_value(execution.status) in {"completed", "failed", "cancelled", "expired"}:
        return _execution_read(execution)
    if execution.cancellation_requested_at is not None:
        return _execution_read(execution)

    capability = db.get(CapabilityDefinition, execution.capability_definition_id)
    installation = (
        db.get(ExtensionInstallation, execution.extension_installation_id)
        if execution.extension_installation_id is not None
        else None
    )
    requested_at = _now()
    execution.cancellation_requested_at = requested_at
    if (
        capability is not None
        and installation is not None
        and _enum_value(installation.status)
        == ExtensionInstallationStatus.enabled.value
        and capability.supports_cancellation
    ):
        enqueue_dispatch(
            db,
            execution_id=execution.id,
            target=installation.extension_id,
            command_kind=DispatchCommandKind.cancel,
            job_id=f"execution:{execution.id}:cancel",
            payload={"reason": "user_requested"},
        )
    else:
        append_and_project_event(
            db,
            execution_id=execution.id,
            producer_source="fair.platform",
            producer_event_id=f"execution:{execution.id}:cancelled",
            event_type="execution.cancelled",
            schema_uri="urn:fair:event:execution.cancelled:v1",
            payload={"reason": "user_requested"},
        )
    db.commit()
    db.refresh(execution)
    return _execution_read(execution)


@router.post(
    "/executions/{execution_id}/authorization/refresh",
    response_model=DelegatedExecutionAuthorization,
)
def refresh_execution_authorization(
    execution_id: UUID,
    authority: ExecutionAuthorization = Depends(require_execution_authorization()),
) -> DelegatedExecutionAuthorization:
    """Rotate short-lived authority without expanding its original scopes."""

    execution = authority.execution
    if execution.id != execution_id:
        raise HTTPException(
            status_code=403, detail="Execution token is not valid for this Execution"
        )
    if execution.cancellation_requested_at is not None:
        raise HTTPException(
            status_code=409, detail="Execution cancellation has been requested"
        )
    issued = issue_execution_token(
        execution=execution,
        installation=authority.installation,
        capability=authority.capability,
        scopes=set(authority.scopes),
        submission_ids=[item.id for item in execution.submissions],
        artifact_ids=[item.artifact_id for item in execution.input_artifacts],
    )
    return DelegatedExecutionAuthorization(
        access_token=issued.token,
        expires_at=issued.expires_at,
        scopes=list(issued.scopes),
    )


@router.get("/executions", response_model=list[ExecutionRead])
def list_executions(
    course_id: UUID | None = None,
    assignment_id: UUID | None = None,
    submission_id: UUID | None = None,
    flow_version_id: UUID | None = None,
    execution_status: str | None = Query(default=None, alias="status"),
    kind: str | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
) -> list[ExecutionRead]:
    query = select(Execution).options(
        selectinload(Execution.snapshot),
        selectinload(Execution.submissions),
        selectinload(Execution.course),
        selectinload(Execution.thread),
    )
    if course_id is not None:
        query = query.where(Execution.course_id == course_id)
    if assignment_id is not None:
        query = query.where(Execution.assignment_id == assignment_id)
    if submission_id is not None:
        query = query.where(Execution.submissions.any(id=submission_id))
    if flow_version_id is not None:
        query = query.where(Execution.flow_version_id == flow_version_id)
    if execution_status is not None:
        query = query.where(Execution.status == execution_status)
    if kind is not None:
        query = query.where(Execution.kind == kind)

    if not has_capability(current_user, "update_any_course"):
        owned_courses = select(Course.id).where(Course.instructor_id == current_user.id)
        query = query.where(
            or_(
                Execution.initiated_by_user_id == current_user.id,
                Execution.thread.has(Thread.owner_user_id == current_user.id),
                Execution.course_id.in_(owned_courses),
            )
        )

    executions = (
        db.scalars(
            query.order_by(Execution.created_at.desc()).offset(offset).limit(limit)
        )
        .unique()
        .all()
    )
    return [_execution_read(execution) for execution in executions]


@router.get(
    "/executions/{execution_id}/events", response_model=list[ExecutionEventRead]
)
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
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    except (ExecutionStoreError, ExecutionProjectionError) as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    return accepted


@router.post(
    "/executions/{execution_id}/events/ingest",
    response_model=list[ExecutionEventRead],
    status_code=status.HTTP_202_ACCEPTED,
)
def ingest_extension_events(
    execution_id: UUID,
    batch: ExecutionEventBatch,
    authority: ExecutionAuthorization = Depends(
        require_execution_authorization(
            ("executions:events",), allow_terminal_retry=True
        )
    ),
    db: Session = Depends(session_dependency),
) -> list[ExecutionEventRead]:
    execution = authority.execution
    installation = authority.installation
    if execution.id != execution_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Execution token is not valid for this Execution",
        )

    terminal_retry = _enum_value(execution.status) in {
        "completed",
        "failed",
        "cancelled",
        "expired",
    }
    if terminal_retry:
        for event in batch.events:
            existing = db.scalar(
                select(ExecutionEvent).where(
                    ExecutionEvent.producer_source == installation.extension_id,
                    ExecutionEvent.producer_event_id == event.producer_event_id,
                )
            )
            if existing is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Execution authority has been revoked",
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
            if (
                event.type == "interaction.requested"
                and not authority.capability.supports_resume
            ):
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Capability must declare supportsResume to request interactions",
                )
            if execution.cancellation_requested_at is not None and event.type not in {
                "execution.cancelled",
                "execution.failed",
            }:
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Execution is cancelling and only a terminal cancellation result is accepted",
                )
            if event.producer_source != installation.extension_id:
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="producer_source must match the authenticated extension",
                )
            if event.type == "execution.completed":
                output = event.payload.get(
                    "outputSummary",
                    event.payload.get(
                        "output_summary", event.payload.get("output", {})
                    ),
                )
                validate_capability_output(authority.capability, output)
            result = append_and_project_event(
                db,
                execution_id=execution.id,
                producer_source=installation.extension_id,
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
        if _enum_value(execution.kind) == "flow_step" and _enum_value(
            execution.status
        ) in {"completed", "failed", "cancelled", "expired"}:
            try:
                advance_flow_execution(db, execution.root_execution_id)
            except FlowRuntimeError as exc:
                fail_flow_execution(db, execution.root_execution_id, str(exc))
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except EventIdentityConflict as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    except (
        CapabilityOutputError,
        ExecutionStoreError,
        ExecutionProjectionError,
    ) as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
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
    execution = _assert_execution_access(
        db.get(Execution, interaction.execution_id), current_user
    )
    if execution.cancellation_requested_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Execution cancellation has already been requested",
        )
    request_id = payload.client_request_id or str(uuid4())
    request_fingerprint = hashlib.sha256(request_id.encode("utf-8")).hexdigest()
    producer_event_id = f"interaction-resolve:{interaction.id}:{request_fingerprint}"
    event_payload = {
        "interaction_id": str(interaction.id),
        "status": payload.status,
        "response": payload.response,
        "resolved_by_user_id": str(current_user.id),
    }
    if _enum_value(interaction.status) != "pending":
        existing = db.scalar(
            select(ExecutionEvent).where(
                ExecutionEvent.producer_source == f"user:{current_user.id}",
                ExecutionEvent.producer_event_id == producer_event_id,
            )
        )
        if existing is not None:
            if existing.payload != event_payload:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "clientRequestId was already used for a different "
                        "interaction response"
                    ),
                )
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
            payload=event_payload,
        )
        capability = db.get(CapabilityDefinition, execution.capability_definition_id)
        if capability is not None and capability.supports_resume:
            enqueue_dispatch(
                db,
                execution_id=execution.id,
                target=capability.installation.extension_id,
                command_kind=DispatchCommandKind.resume,
                job_id=f"interaction:{interaction.id}:resume",
                payload={
                    "interactionId": str(interaction.id),
                    "status": payload.status,
                    "response": payload.response,
                },
            )
        db.commit()
    except EventIdentityConflict as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    except (ExecutionStoreError, ExecutionProjectionError) as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
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
                    payload = jsonable_encoder(
                        _event_read(event).model_dump(by_alias=True)
                    )
                    yield format_sse_event(
                        id=str(event.sequence),
                        event=event.type,
                        data_str=json.dumps(payload, separators=(",", ":")),
                    )

                if (
                    stream_status
                    in {
                        "completed",
                        "failed",
                        "cancelled",
                        "expired",
                    }
                    and len(events) < 500
                ):
                    return

                if events:
                    # Drain an existing backlog without adding polling latency.
                    continue

                heartbeat_count += 1
                if heartbeat_count >= 15:
                    heartbeat_count = 0
                    yield format_sse_event(comment="keep-alive")
                await asyncio.sleep(0.5)
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
