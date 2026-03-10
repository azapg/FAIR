from uuid import UUID, uuid4
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.api.schema.workflow import (
    WorkflowCreate,
    WorkflowRead,
    WorkflowStep,
    WorkflowUpdate,
)
from fair_platform.backend.core.security.dependencies import require_capability
from fair_platform.backend.core.security.permissions import (
    has_capability,
    has_capability_and_owner,
)
from fair_platform.backend.data.database import session_dependency
from fair_platform.backend.data.models.course import Course
from fair_platform.backend.data.models.user import User
from fair_platform.backend.data.models.workflow import Workflow

router = APIRouter()


def _normalize_steps(payload_steps: list[WorkflowStep] | None) -> list[WorkflowStep]:
    steps = [WorkflowStep.model_validate(step) for step in (payload_steps or [])]
    if not steps:
        return []
    steps.sort(key=lambda step: step.order)
    for index, step in enumerate(steps):
        step.order = index
        step.plugin.plugin_type = step.plugin_type
        step.settings = step.settings or step.plugin.settings or {}
        step.plugin.settings = step.settings
    return steps


def _db_workflow_to_read(wf: Workflow) -> WorkflowRead:
    steps = [WorkflowStep.model_validate(step) for step in (wf.steps or [])]
    steps.sort(key=lambda step: step.order)
    return WorkflowRead(
        id=wf.id,
        course_id=wf.course_id,
        name=wf.name,
        description=wf.description,
        created_by=wf.created_by,
        created_at=wf.created_at,
        updated_at=wf.updated_at,
        archived=wf.archived,
        steps=steps,
    )


@router.post(
    "/",
    response_model=WorkflowRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_capability("create_workflow"))],
)
def create_workflow(
    payload: WorkflowCreate,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    if not has_capability(current_user, "create_workflow"):
        raise HTTPException(status_code=403, detail="Not authorized to create workflows")
    course = db.get(Course, payload.course_id)
    if not course:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Course not found")
    if not has_capability_and_owner(current_user, "create_workflow", course.instructor_id):
        raise HTTPException(status_code=403, detail="Only the course instructor or admin can create workflows")

    steps = _normalize_steps(payload.steps)
    wf = Workflow(
        id=uuid4(),
        course_id=payload.course_id,
        name=payload.name,
        description=payload.description,
        created_by=current_user.id,
        created_at=datetime.now(timezone.utc),
        steps=[step.model_dump(mode="json", by_alias=True) for step in steps],
    )
    db.add(wf)
    db.commit()
    db.refresh(wf)
    return _db_workflow_to_read(wf)


@router.get("/", response_model=list[WorkflowRead])
def list_workflows(
    course_id: UUID | None = None,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    if course_id:
        course = db.get(Course, course_id)
        if not course:
            raise HTTPException(status_code=400, detail="Course not found")
        if not has_capability_and_owner(current_user, "read_workflow", course.instructor_id):
            raise HTTPException(status_code=403, detail="Not authorized to list workflows for this course")
    elif not has_capability(current_user, "read_workflow"):
        raise HTTPException(status_code=403, detail="Not authorized to list workflows")

    q = db.query(Workflow)
    if course_id:
        q = q.filter(Workflow.course_id == course_id)
    elif not has_capability(current_user, "update_any_course"):
        q = q.join(Course, Workflow.course_id == Course.id).filter(Course.instructor_id == current_user.id)
    workflows = q.filter(Workflow.archived.is_(False)).all()
    return [_db_workflow_to_read(wf) for wf in workflows]


@router.get("/{workflow_id}", response_model=WorkflowRead)
def get_workflow(
    workflow_id: UUID,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    wf = db.get(Workflow, workflow_id)
    if not wf or wf.archived:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
    course = db.get(Course, wf.course_id)
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    if not has_capability_and_owner(current_user, "read_workflow", course.instructor_id):
        raise HTTPException(status_code=403, detail="Not authorized to get this workflow")
    return _db_workflow_to_read(wf)


@router.put("/{workflow_id}", response_model=WorkflowRead)
def update_workflow(
    workflow_id: UUID,
    payload: WorkflowUpdate,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    wf = db.get(Workflow, workflow_id)
    if not wf or wf.archived:
        raise HTTPException(status_code=404, detail="Workflow not found")
    course = db.get(Course, wf.course_id)
    if not course:
        raise HTTPException(status_code=400, detail="Cannot find course for this workflow")
    if not has_capability_and_owner(current_user, "update_workflow", course.instructor_id):
        raise HTTPException(status_code=403, detail="Only the course instructor or admin can update this workflow")

    if payload.name is not None:
        wf.name = payload.name
    if payload.description is not None:
        wf.description = payload.description
    if payload.steps is not None:
        steps = _normalize_steps(payload.steps)
        wf.steps = [step.model_dump(mode="json", by_alias=True) for step in steps]
    wf.updated_at = datetime.now(timezone.utc)
    db.add(wf)
    db.commit()
    db.refresh(wf)
    return _db_workflow_to_read(wf)


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workflow(
    workflow_id: UUID,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    wf = db.get(Workflow, workflow_id)
    if not wf:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
    if wf.archived:
        return None
    course = db.get(Course, wf.course_id)
    if not course:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Course not found")
    if not has_capability_and_owner(current_user, "delete_workflow", course.instructor_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the course instructor or admin can delete this workflow")
    wf.archived = True
    wf.updated_at = datetime.now(timezone.utc)
    db.add(wf)
    db.commit()
    return None


__all__ = ["router"]
