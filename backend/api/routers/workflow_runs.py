from uuid import UUID, uuid4
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from data.database import session_dependency
from data.models.workflow_run import WorkflowRun, WorkflowRunStatus
from data.models.workflow import Workflow
from data.models.user import User
from api.schema.workflow_run import WorkflowRunCreate, WorkflowRunRead, WorkflowRunUpdate

router = APIRouter()


@router.post("/", response_model=WorkflowRunRead, status_code=status.HTTP_201_CREATED)
def create_workflow_run(payload: WorkflowRunCreate, db: Session = Depends(session_dependency)):
    if not db.get(Workflow, payload.workflow_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Workflow not found")
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
def update_workflow_run(run_id: UUID, payload: WorkflowRunUpdate, db: Session = Depends(session_dependency)):
    run = db.get(WorkflowRun, run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="WorkflowRun not found")

    if payload.status is not None:
        run.status = payload.status if isinstance(payload.status, str) else getattr(payload.status, "value", payload.status)
    if payload.finished_at is not None:
        run.finished_at = payload.finished_at
    if payload.logs is not None:
        run.logs = payload.logs

    db.add(run)
    db.commit()
    db.refresh(run)
    return run


@router.delete("/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workflow_run(run_id: UUID, db: Session = Depends(session_dependency)):
    run = db.get(WorkflowRun, run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="WorkflowRun not found")
    db.delete(run)
    db.commit()
    return None


__all__ = ["router"]
