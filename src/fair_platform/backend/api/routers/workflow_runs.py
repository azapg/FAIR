from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.api.schema.submission import SubmissionBase
from fair_platform.backend.api.schema.workflow_run import WorkflowRunRead
from fair_platform.backend.data.database import session_dependency
from fair_platform.backend.data.models import (
    Assignment,
    Course,
    Submission,
    User,
    UserRole,
    Workflow,
    WorkflowRun,
)

router = APIRouter()


def _assert_course_access(db: Session, user: User, course_id: UUID):
    if user.role == UserRole.admin:
        return
    if user.role != UserRole.professor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors or admin can access workflow runs",
        )

    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    if course.instructor_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the course instructor or admin can access these workflow runs",
        )


def _serialize_run(run: WorkflowRun) -> WorkflowRunRead:
    submissions = (
        [SubmissionBase.model_validate(sub) for sub in run.submissions] if run.submissions else None
    )
    return WorkflowRunRead(
        id=run.id,
        workflow_id=run.workflow_id,
        run_by=run.run_by,
        status=run.status,
        started_at=run.started_at,
        finished_at=run.finished_at,
        logs=run.logs,
        submissions=submissions,
    )


@router.get("/", response_model=List[WorkflowRunRead])
def list_workflow_runs(
    course_id: Optional[UUID] = Query(None, description="Filter runs by course"),
    assignment_id: Optional[UUID] = Query(None, description="Filter runs by assignment"),
    workflow_id: Optional[UUID] = Query(None, description="Filter runs by workflow"),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in (UserRole.admin, UserRole.professor):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors or admin can access workflow runs",
        )

    inferred_course_id = course_id

    if assignment_id:
        assignment = db.get(Assignment, assignment_id)
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found"
            )
        if inferred_course_id and assignment.course_id != inferred_course_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assignment does not belong to the provided course",
            )
        inferred_course_id = assignment.course_id

    if workflow_id:
        workflow = db.get(Workflow, workflow_id)
        if not workflow:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
        if inferred_course_id and workflow.course_id != inferred_course_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Workflow does not belong to the provided course",
            )
        inferred_course_id = inferred_course_id or workflow.course_id

    allowed_course_ids: Optional[List[UUID]] = None
    if inferred_course_id:
        _assert_course_access(db, current_user, inferred_course_id)
    elif current_user.role == UserRole.professor:
        allowed_course_ids = [
            row[0] for row in db.query(Course.id).filter(Course.instructor_id == current_user.id).all()
        ]
        if not allowed_course_ids:
            return []

    query = (
        db.query(WorkflowRun)
        .options(
            joinedload(WorkflowRun.submissions),
            joinedload(WorkflowRun.workflow),
        )
    )

    if assignment_id:
        query = query.join(WorkflowRun.submissions).filter(
            Submission.assignment_id == assignment_id
        )

    if workflow_id:
        query = query.filter(WorkflowRun.workflow_id == workflow_id)

    if inferred_course_id:
        query = query.join(Workflow, WorkflowRun.workflow_id == Workflow.id).filter(
            Workflow.course_id == inferred_course_id
        )
    elif allowed_course_ids is not None:
        query = query.join(Workflow, WorkflowRun.workflow_id == Workflow.id).filter(
            Workflow.course_id.in_(allowed_course_ids)
        )

    runs = (
        query.order_by(WorkflowRun.started_at.desc())
        .distinct()
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [_serialize_run(run) for run in runs]


@router.get("/{workflow_run_id}", response_model=WorkflowRunRead)
def get_workflow_run(
    workflow_run_id: UUID,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in (UserRole.admin, UserRole.professor):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors or admin can access workflow runs",
        )

    run = (
        db.query(WorkflowRun)
        .options(
            joinedload(WorkflowRun.submissions),
            joinedload(WorkflowRun.workflow),
        )
        .filter(WorkflowRun.id == workflow_run_id)
        .first()
    )
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workflow run not found"
        )

    course_id = run.workflow.course_id if run.workflow else None
    if not course_id:
        workflow = db.get(Workflow, run.workflow_id)
        course_id = workflow.course_id if workflow else None

    if course_id:
        _assert_course_access(db, current_user, course_id)
    elif current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workflow run is missing its course relationship",
        )

    return _serialize_run(run)


__all__ = ["router"]
