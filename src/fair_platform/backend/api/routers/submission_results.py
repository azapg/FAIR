from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from fair_platform.backend.api.schema.submission_result import SubmissionResultRead
from fair_platform.backend.data.database import session_dependency
from fair_platform.backend.data.models import SubmissionResult
from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.data.models.user import User


router = APIRouter()


@router.get("/{result_id}", response_model=SubmissionResultRead)
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


__all__ = ["router"]
