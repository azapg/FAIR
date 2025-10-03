from uuid import UUID, uuid4
from typing import List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from pydantic import BaseModel
from pydantic.v1 import EmailStr
from sqlalchemy.orm import Session

from fair_platform.backend.data.database import session_dependency
from fair_platform.backend.data.models.submission import (
    Submission,
    SubmissionStatus,
    submission_artifacts,
)
from fair_platform.backend.data.models.assignment import Assignment
from fair_platform.backend.data.models.user import User, UserRole
from fair_platform.backend.data.models.artifact import Artifact, ArtifactStatus, AccessLevel
from fair_platform.backend.api.schema.submission import (
    SubmissionRead,
    SubmissionUpdate,
)
from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.services.artifact_manager import get_artifact_manager

router = APIRouter()


class SyntheticSubmission(BaseModel):
    assignment_id: UUID
    submitter: str
    artifacts_ids: Optional[List[UUID]] = None

    class Config:
        from_attributes = True
        alias_generator = lambda field_name: "".join(
            word.capitalize() if i > 0 else word
            for i, word in enumerate(field_name.split("_"))
        )
        validate_by_name = True


# TODO: Implement enrollments table to be able to check
@router.post("/", response_model=SubmissionRead, status_code=status.HTTP_201_CREATED)
def create_submission(
    payload: SyntheticSubmission,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    """Create submission and optionally attach existing artifacts."""
    if not db.get(Assignment, payload.assignment_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Assignment not found"
        )

    if current_user.role != UserRole.admin and current_user.role != UserRole.professor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to create submission for this user",
        )

    try:
        submitted_at = datetime.now(timezone.utc)
        status_value = SubmissionStatus.pending
        user_id = uuid4()

        synthetic_user = User(
            id=user_id,
            name=payload.submitter,
            email=EmailStr(f"{user_id}@fair.com"),
            role=UserRole.student,
        )
        db.add(synthetic_user)
        db.flush()

        sub = Submission(
            id=uuid4(),
            assignment_id=payload.assignment_id,
            submitter_id=synthetic_user.id,
            submitted_at=submitted_at,
            status=status_value,
        )
        db.add(sub)
        db.flush()

        if payload.artifacts_ids:
            manager = get_artifact_manager(db)
            
            for aid in payload.artifacts_ids:
                manager.attach_to_submission(aid, sub.id, current_user)

        db.commit()
        db.refresh(sub)
        return sub
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create submission: {str(e)}"
        )


@router.get("/", response_model=List[SubmissionRead])
def list_submissions(
    assignment_id: Optional[UUID] = None, db: Session = Depends(session_dependency)
):
    q = db.query(Submission)
    if assignment_id:
        q = q.filter(Submission.assignment_id == assignment_id)
    return q.all()


@router.post("/create-with-files", response_model=SubmissionRead, status_code=status.HTTP_201_CREATED)
async def create_submission_with_files(
    assignment_id: UUID = Form(...),
    submitter_name: str = Form(...),
    files: List[UploadFile] = File(...),
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    """
    Create a submission with file uploads atomically.
    
    This endpoint creates the submission and uploads artifacts in a single
    transaction. If any step fails, everything is rolled back, preventing
    orphaned artifacts.
    
    Form fields:
    - assignment_id: UUID of the assignment
    - submitter_name: Name of the submitter (creates synthetic user)
    - files: List of files to upload
    """
    try:
        assignment = db.get(Assignment, assignment_id)
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assignment not found"
            )

        if current_user.role != UserRole.admin and current_user.role != UserRole.professor:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to create submission for this user",
            )

        user_id = uuid4()

        synthetic_user = User(
            id=user_id,
            name=submitter_name,
            email=EmailStr(f"{user_id}@fair.com"),
            role=UserRole.student,
        )
        db.add(synthetic_user)
        db.flush()

        sub = Submission(
            id=uuid4(),
            assignment_id=assignment_id,
            submitter_id=synthetic_user.id,
            submitted_at=datetime.now(timezone.utc),
            status=SubmissionStatus.pending,
        )
        db.add(sub)
        db.flush()

        manager = get_artifact_manager(db)
        
        for file in files:
            artifact = manager.create_artifact(
                file=file,
                creator=current_user,
                status=ArtifactStatus.attached,
                access_level=AccessLevel.private,
                course_id=assignment.course_id,
                assignment_id=assignment_id,
            )
            
            sub.artifacts.append(artifact)

        db.commit()
        db.refresh(sub)
        return sub
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create submission with files: {str(e)}"
        )


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


    # TODO: As with run_ids, I don't think people should be able to update these fields.
    #   These fields should only be managed by the workflow runner service.
    if payload.submitted_at is not None:
        sub.submitted_at = payload.submitted_at
    if payload.status is not None:
        sub.status = (
            payload.status
            if isinstance(payload.status, str)
            else SubmissionStatus.pending
        )

    if payload.artifact_ids is not None:
        manager = get_artifact_manager(db)
        
        old_artifacts = db.query(Artifact).join(
            submission_artifacts,
            submission_artifacts.c.artifact_id == Artifact.id
        ).filter(
            submission_artifacts.c.submission_id == sub.id
        ).all()
        
        for artifact in old_artifacts:
            manager.detach_from_submission(artifact.id, sub.id, current_user)
        
        for aid in payload.artifact_ids:
            manager.attach_to_submission(aid, sub.id, current_user)
        
        db.commit()
        
    # TODO: I think I won't consider run_ids for now.

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
