from uuid import UUID, uuid4
from typing import List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from pydantic.v1 import EmailStr
from sqlalchemy import delete
from sqlalchemy.orm import Session

from fair_platform.backend.data.database import session_dependency
from fair_platform.backend.data.models.submission import (
    Submission,
    SubmissionStatus,
    submission_artifacts,
    submission_workflow_runs,
)
from fair_platform.backend.data.models.assignment import Assignment
from fair_platform.backend.data.models.user import User, UserRole
from fair_platform.backend.data.models.artifact import Artifact
from fair_platform.backend.data.models.workflow_run import WorkflowRun
from fair_platform.backend.api.schema.submission import (
    SubmissionCreate,
    SubmissionRead,
    SubmissionUpdate,
)
from fair_platform.backend.api.routers.auth import get_current_user

router = APIRouter()

class SyntheticSubmission(BaseModel):
    assignment_id: UUID
    submitter: str
    artifacts_ids: Optional[List[UUID]] = None

    class Config:
        from_attributes = True
        alias_generator = lambda field_name: ''.join(word.capitalize() if i > 0 else word for i, word in enumerate(field_name.split('_')))
        validate_by_name = True


# TODO: Implement enrollments table to be able to check
@router.post("/", response_model=SubmissionRead, status_code=status.HTTP_201_CREATED)
def create_submission(
    payload: SyntheticSubmission,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    if not db.get(Assignment, payload.assignment_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assignment not found")

    if current_user.role != UserRole.admin and current_user.role != UserRole.professor:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to create submission for this user")

    submitted_at = datetime.now(timezone.utc)
    status_value = SubmissionStatus.pending

    synthetic_user = User(id=uuid4(), name=payload.submitter, email=EmailStr("student@fair.com"), role=UserRole.student)
    db.add(synthetic_user)
    db.commit()
    db.refresh(synthetic_user)


    sub = Submission(
        id=uuid4(),
        assignment_id=payload.assignment_id,
        submitter_id=synthetic_user.id,
        submitted_at=submitted_at,
        status=status_value,
    )
    db.add(sub)
    db.commit()

    if payload.artifacts_ids:
        for aid in payload.artifacts_ids:
            if not db.get(Artifact, aid):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Artifact {aid} not found",
                )
            db.execute(
                submission_artifacts.insert().values(
                    id=uuid4(), submission_id=sub.id, artifact_id=aid
                )
            )
            db.refresh(submission_artifacts)
        db.commit()

    db.refresh(sub)
    return sub


@router.get("/", response_model=List[SubmissionRead])
def list_submissions(
    assignment_id: Optional[UUID] = None, db: Session = Depends(session_dependency)
):
    q = db.query(Submission)
    if assignment_id:
        q = q.filter(Submission.assignment_id == assignment_id)
    return q.all()


@router.get("/{submission_id}", response_model=SubmissionRead)
def get_submission(submission_id: UUID, db: Session = Depends(session_dependency)):
    sub = db.get(Submission, submission_id)
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found"
        )
    return sub


@router.put("/{submission_id}", response_model=SubmissionRead)
def update_submission(
    submission_id: UUID,
    payload: SubmissionUpdate,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    sub = db.get(Submission, submission_id)
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found"
        )

    if current_user.role != UserRole.admin and current_user.id != sub.submitter_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this submission",
        )

    if payload.submitted_at is not None:
        sub.submitted_at = payload.submitted_at
    if payload.status is not None:
        sub.status = (
            payload.status
            if isinstance(payload.status, str)
            else getattr(payload.status, "value", payload.status)
        )
    if payload.official_run_id is not None:
        run = db.get(WorkflowRun, payload.official_run_id)
        if not run:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="official_run_id not found",
            )
        sub.official_run_id = payload.official_run_id
        existing = db.execute(
            submission_workflow_runs.select().where(
                submission_workflow_runs.c.submission_id == sub.id,
                submission_workflow_runs.c.workflow_run_id == payload.official_run_id,
            )
        ).first()
        if not existing:
            db.execute(
                submission_workflow_runs.insert().values(
                    submission_id=sub.id, workflow_run_id=payload.official_run_id
                )
            )
            db.commit()

    db.add(sub)
    db.commit()

    # replaces artifacts if provided
    if payload.artifact_ids is not None:
        db.execute(
            delete(submission_artifacts).where(
                lambda: submission_artifacts.c.submission_id == sub.id
            )
        )
        db.commit()
        for aid in payload.artifact_ids:
            if not db.get(Artifact, aid):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Artifact {aid} not found",
                )
            db.execute(
                submission_artifacts.insert().values(
                    id=uuid4(), submission_id=sub.id, artifact_id=aid
                )
            )
        db.commit()

    # replaces runs if provided
    if payload.run_ids is not None:
        db.execute(
            delete(submission_workflow_runs).where(
                lambda: submission_workflow_runs.c.submission_id == sub.id
            )
        )
        db.commit()
        for rid in payload.run_ids:
            if not db.get(WorkflowRun, rid):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"WorkflowRun {rid} not found",
                )
            db.execute(
                submission_workflow_runs.insert().values(
                    submission_id=sub.id, workflow_run_id=rid
                )
            )
        db.commit()
        if sub.official_run_id is not None:
            existing = db.execute(
                submission_workflow_runs.select().where(
                    submission_workflow_runs.c.submission_id == sub.id,
                    submission_workflow_runs.c.workflow_run_id == sub.official_run_id,
                )
            ).first()
            if not existing:
                db.execute(
                    submission_workflow_runs.insert().values(
                        submission_id=sub.id, workflow_run_id=sub.official_run_id
                    )
                )
                db.commit()

    db.refresh(sub)
    return sub


@router.delete("/{submission_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_submission(
    submission_id: UUID,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    sub = db.get(Submission, submission_id)
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found"
        )

    if current_user.role != UserRole.admin and current_user.id != sub.submitter_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this submission",
        )

    db.delete(sub)
    db.commit()
    return None


__all__ = ["router"]
