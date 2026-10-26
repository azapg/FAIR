from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.core.security.permissions import (
    has_capability,
    has_capability_and_owner,
)
from fair_platform.backend.api.schema.flow import (
    FlowCreate,
    FlowExecutionRead,
    FlowExecutionStart,
    FlowRead,
    FlowUpdate,
    FlowVersionCreate,
    FlowVersionRead,
)
from fair_platform.backend.data.database import session_dependency
from fair_platform.backend.data.models import Course, Flow, FlowVersion, User
from fair_platform.backend.services.flow_service import (
    FlowNotFound,
    FlowStateError,
    archive_flow_version,
    create_flow,
    create_flow_version,
    get_owned_flow,
    publish_flow_version,
    start_flow_execution,
)


router = APIRouter(prefix="/flows")


def _require_capability(user: User, capability: str) -> None:
    if not has_capability(user, capability):
        raise HTTPException(status_code=403, detail=f"{capability} capability required")


def _state(value: object) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _version_read(version: FlowVersion) -> FlowVersionRead:
    return FlowVersionRead(
        id=version.id,
        flow_id=version.flow_id,
        ordinal=version.ordinal,
        state=_state(version.state),
        definition=version.definition,
        capability_pins=version.capability_pins,
        config_snapshot=version.config_snapshot,
        definition_hash=version.definition_hash or "",
        created_by_user_id=version.created_by_user_id,
        created_at=version.created_at,
        published_at=version.published_at,
        archived_at=version.archived_at,
    )


def _flow_read(flow: Flow) -> FlowRead:
    return FlowRead(
        id=flow.id,
        owner_user_id=flow.owner_user_id,
        course_id=flow.course_id,
        name=flow.name,
        description=flow.description,
        archived_at=flow.archived_at,
        created_at=flow.created_at,
        updated_at=flow.updated_at,
        versions=[_version_read(version) for version in flow.versions],
    )


def _owned_flow(db: Session, flow_id: UUID, user: User) -> Flow:
    _require_capability(user, "read_flow")
    try:
        return get_owned_flow(db, flow_id, user.id)
    except FlowNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


def _version(flow: Flow, version_id: UUID) -> FlowVersion:
    for version in flow.versions:
        if version.id == version_id:
            return version
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="FlowVersion not found"
    )


@router.post("", response_model=FlowRead, status_code=status.HTTP_201_CREATED)
def create_flow_route(
    payload: FlowCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
) -> FlowRead:
    _require_capability(current_user, "create_flow")
    if payload.course_id is not None:
        course = db.get(Course, payload.course_id)
        if course is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
            )
        if not has_capability_and_owner(
            current_user, "update_own_course", course.instructor_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the course owner can create a course-scoped Flow",
            )
    flow = create_flow(
        db,
        owner_user_id=current_user.id,
        name=payload.name,
        description=payload.description,
        course_id=payload.course_id,
    )
    db.commit()
    return _flow_read(flow)


@router.get("", response_model=list[FlowRead])
def list_flows(
    include_archived: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
) -> list[FlowRead]:
    _require_capability(current_user, "read_flow")
    query = select(Flow).where(Flow.owner_user_id == current_user.id)
    if not include_archived:
        query = query.where(Flow.archived_at.is_(None))
    flows = db.scalars(query.order_by(Flow.updated_at.desc())).unique().all()
    return [_flow_read(flow) for flow in flows]


@router.get("/{flow_id}", response_model=FlowRead)
def get_flow(
    flow_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
) -> FlowRead:
    return _flow_read(_owned_flow(db, flow_id, current_user))


@router.patch("/{flow_id}", response_model=FlowRead)
def update_flow(
    flow_id: UUID,
    payload: FlowUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
) -> FlowRead:
    _require_capability(current_user, "update_flow")
    flow = _owned_flow(db, flow_id, current_user)
    if flow.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Flow is archived")
    if payload.name is not None:
        flow.name = payload.name
    if "description" in payload.model_fields_set:
        flow.description = payload.description
    db.commit()
    return _flow_read(flow)


@router.delete("/{flow_id}", response_model=FlowRead)
def archive_flow(
    flow_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
) -> FlowRead:
    _require_capability(current_user, "update_flow")
    flow = _owned_flow(db, flow_id, current_user)
    if flow.archived_at is None:
        flow.archived_at = datetime.now(timezone.utc)
        db.commit()
    return _flow_read(flow)


@router.post(
    "/{flow_id}/versions",
    response_model=FlowVersionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_version(
    flow_id: UUID,
    payload: FlowVersionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
) -> FlowVersionRead:
    _require_capability(current_user, "update_flow")
    flow = _owned_flow(db, flow_id, current_user)
    try:
        version = create_flow_version(
            db,
            flow=flow,
            created_by_user_id=current_user.id,
            definition=payload.definition,
            config_snapshot=payload.config_snapshot,
        )
        db.commit()
    except FlowStateError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _version_read(version)


@router.get("/{flow_id}/versions", response_model=list[FlowVersionRead])
def list_versions(
    flow_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
) -> list[FlowVersionRead]:
    flow = _owned_flow(db, flow_id, current_user)
    return [_version_read(version) for version in flow.versions]


@router.post("/{flow_id}/versions/{version_id}/publish", response_model=FlowVersionRead)
def publish_version(
    flow_id: UUID,
    version_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
) -> FlowVersionRead:
    _require_capability(current_user, "update_flow")
    flow = _owned_flow(db, flow_id, current_user)
    try:
        version = publish_flow_version(db, _version(flow, version_id))
        db.commit()
    except FlowStateError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _version_read(version)


@router.post("/{flow_id}/versions/{version_id}/archive", response_model=FlowVersionRead)
def archive_version(
    flow_id: UUID,
    version_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
) -> FlowVersionRead:
    _require_capability(current_user, "update_flow")
    flow = _owned_flow(db, flow_id, current_user)
    try:
        version = archive_flow_version(db, _version(flow, version_id))
        db.commit()
    except FlowStateError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _version_read(version)


@router.post(
    "/{flow_id}/executions",
    response_model=FlowExecutionRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def start_execution(
    flow_id: UUID,
    payload: FlowExecutionStart,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
) -> FlowExecutionRead:
    _require_capability(current_user, "execute_flow")
    flow = _owned_flow(db, flow_id, current_user)
    if flow.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Flow is archived")
    try:
        execution, version, step, dispatch = start_flow_execution(
            db,
            flow=flow,
            initiated_by_user_id=current_user.id,
            input_payload=payload.input,
            flow_version_id=payload.flow_version_id,
            assignment_id=payload.assignment_id,
            submission_ids=payload.submission_ids,
        )
        db.commit()
    except FlowStateError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return FlowExecutionRead(
        execution_id=execution.id,
        flow_version_id=version.id,
        status=_state(execution.status),
        dispatch_id=dispatch.id,
        step_execution_id=step.id,
    )


__all__ = ["router"]
