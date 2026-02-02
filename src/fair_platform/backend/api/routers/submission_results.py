from typing import List, Optional
from uuid import UUID

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing_extensions import deprecated

from fair_platform.backend.api.schema.submission_result import (
    SubmissionResultRead,
    SubmissionResultUpdate,
)
from fair_platform.backend.data.database import session_dependency
from fair_platform.backend.data.models import (
    Assignment,
    Course,
    Submission,
    SubmissionResult,
    UserRole,
)
from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.data.models.user import User


router = APIRouter()


@router.get("/{result_id}", response_model=SubmissionResultRead)
@deprecated("SubmissionResult API is deprecated. Use Submission events and draft/published fields.")
def get_result(
    result_id: UUID,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    result = db.get(SubmissionResult, result_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    # TODO: Permission checks based on current_user and related submission
    return result


@router.get("/", response_model=List[SubmissionResultRead])
@deprecated("SubmissionResult API is deprecated. Use Submission events and draft/published fields.")
def list_results(
    submission_id: Optional[UUID] = Query(None),
    workflow_run_id: Optional[UUID] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    query = db.query(SubmissionResult)
    if submission_id:
        query = query.filter(SubmissionResult.submission_id == submission_id)
    if workflow_run_id:
        query = query.filter(SubmissionResult.workflow_run_id == workflow_run_id)
    return query.offset(skip).limit(limit).all()


@router.patch("/{result_id}", response_model=SubmissionResultRead)
@deprecated("SubmissionResult API is deprecated. Use Submission events and draft/published fields.")
def update_result(
    result_id: UUID,
    payload: SubmissionResultUpdate,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    result = db.get(SubmissionResult, result_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    submission = db.get(Submission, result.submission_id)
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found"
        )
    if not submission.official_run_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Run workflow first to generate a result",
        )
    if submission.official_run_id != result.workflow_run_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only the official result can be edited",
        )

    if current_user.role != UserRole.admin:
        assignment = db.get(Assignment, submission.assignment_id)
        course = db.get(Course, assignment.course_id) if assignment else None
        if current_user.role != UserRole.professor or not course:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only instructors or admin can update results",
            )
        if course.instructor_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the course instructor or admin can update results",
            )

    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide score and/or feedback to update",
        )
    if "score" in data:
        result.score = data["score"]
    if "feedback" in data:
        result.feedback = data["feedback"]

    meta = result.grading_meta or {}
    meta["modified_by"] = str(current_user.id)
    meta["modified_at"] = datetime.now(timezone.utc).isoformat()
    result.grading_meta = dict(meta)
    result.graded_at = result.graded_at or datetime.now(timezone.utc)

    db.commit()
    db.refresh(result)
    return result


__all__ = ["router"]
