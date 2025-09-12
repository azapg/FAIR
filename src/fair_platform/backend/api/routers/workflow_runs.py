from uuid import UUID, uuid4
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from fair_platform.backend.data.database import session_dependency
from fair_platform.backend.data.models.workflow_run import WorkflowRun, WorkflowRunStatus
from fair_platform.backend.data.models.workflow import Workflow
from fair_platform.backend.data.models.course import Course
from fair_platform.backend.data.models.user import User, UserRole
from fair_platform.backend.api.schema.workflow_run import WorkflowRunCreate, WorkflowRunRead, WorkflowRunUpdate
from fair_platform.backend.api.routers.auth import get_current_user

router = APIRouter()


@router.post("/", response_model=WorkflowRunRead, status_code=status.HTTP_201_CREATED)
def create_workflow_run(
    payload: WorkflowRunCreate,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.admin and current_user.role != UserRole.instructor:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admin and instructor users can create workflow runs")

    workflow = db.get(Workflow, payload.workflow_id)
    if not workflow:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Workflow not found")

    if current_user.role == UserRole.instructor:
        course = db.get(Course, workflow.course_id)
        if not course or course.instructor_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Instructors may only create runs for their own course workflows")

    if not db.get(User, payload.run_by):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Runner not found")

    status_value = (
        payload.status if isinstance(payload.status, str) else getattr(payload.status, "value", payload.status)
    ) or WorkflowRunStatus.pending.value

    run = WorkflowRun(
        id=uuid4(),
        workflow_id=payload.workflow_id,
        run_by=payload.run_by,
        started_at=datetime.now(timezone.utc),
        finished_at=None,
        status=status_value,
        logs=payload.logs,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


@router.get("/", response_model=List[WorkflowRunRead])
def list_workflow_runs(workflow_id: UUID | None = None, db: Session = Depends(session_dependency)):
    q = db.query(WorkflowRun)
    if workflow_id:
        q = q.filter(WorkflowRun.workflow_id == workflow_id)
    return q.all()


@router.get("/{run_id}", response_model=WorkflowRunRead)
def get_workflow_run(run_id: UUID, db: Session = Depends(session_dependency)):
    run = db.get(WorkflowRun, run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="WorkflowRun not found")
    return run


@router.put("/{run_id}", response_model=WorkflowRunRead)
def update_workflow_run(
    run_id: UUID,
    payload: WorkflowRunUpdate,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    # TODO: Workflows Runs in the DB are mutable, you need to change statuses and logs,
    #  I wonder if we should allow updates to certain fields
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admin users can manage workflow runs")
    raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED, detail="Workflow runs are immutable and cannot be updated")


@router.delete("/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workflow_run(run_id: UUID, db: Session = Depends(session_dependency), current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admin users can delete workflow runs")

    run = db.get(WorkflowRun, run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="WorkflowRun not found")
    db.delete(run)
    db.commit()
    return None


__all__ = ["router"]
