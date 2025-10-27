from uuid import UUID, uuid4
from typing import List, Optional
from datetime import datetime, timezone
import json

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
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
from fair_platform.backend.api.schema.submission_result import SubmissionResultRead
from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.services.artifact_manager import get_artifact_manager

router = APIRouter()


@router.post("/", response_model=SubmissionRead, status_code=status.HTTP_201_CREATED)
async def create_submission(
    assignment_id: UUID = Form(...),
    submitter_name: str = Form(...),
    artifact_ids: str = Form(None),
    files: List[UploadFile] = File(None),
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    """
    Create a submission with optional file uploads and/or existing artifact references.
    
    This endpoint supports both multipart/form-data (for file uploads) and can reference
    existing artifacts by ID. All operations are atomic - if any step fails, everything
    is rolled back.
    
    Form fields:
    - assignment_id: UUID of the assignment (required)
    - submitter_name: Name of the submitter (required)
    - artifact_ids: Optional JSON array of existing artifact UUIDs: ["uuid1", "uuid2"]
    - files: Optional list of files to upload as new artifacts
    """
    assignment = db.get(Assignment, assignment_id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Assignment not found"
        )

    if current_user.role != UserRole.admin and current_user.role != UserRole.professor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to create submission for this user",
        )

    try:
        existing_artifact_ids = []
        if artifact_ids:
            try:
                existing_artifact_ids = json.loads(artifact_ids)
                if not isinstance(existing_artifact_ids, list):
                    raise ValueError("artifact_ids must be an array")
            except (json.JSONDecodeError, ValueError) as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid artifact_ids JSON. Expected array of UUIDs: {str(e)}"
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
        
        if existing_artifact_ids:
            for artifact_id in existing_artifact_ids:
                try:
                    manager.attach_to_submission(UUID(artifact_id), sub.id, current_user)
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid artifact ID format: {artifact_id}"
                    )
        
        if files:
            for file in files:
                artifact = manager.create_artifact(
                    file=file,
                    creator=current_user,
                    status=ArtifactStatus.attached,
                    access_level=AccessLevel.private,
                    course_id=assignment.course_id,
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
            detail=f"Failed to create submission: {str(e)}"
        )


@router.get("/", response_model=List[SubmissionRead])
def list_submissions(
    db: Session = Depends(session_dependency),
    assignment_id: UUID = Query(None, description="Filter submissions by assignment ID"),
    include_results: bool = Query(
        True, description="Include all results in response (optional)"
    ),
    current_user: User = Depends(get_current_user),
):
    """List all submissions, optionally filtered by assignment ID."""
    query = db.query(Submission)
    if assignment_id is not None:
        if not db.get(Assignment, assignment_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found"
            )
        query = query.filter(Submission.assignment_id == assignment_id)
    
    submissions = query.all()
    
    # Fetch all submitters in one query to avoid N+1
    submitter_ids = [sub.submitter_id for sub in submissions]
    submitters = db.query(User).filter(User.id.in_(submitter_ids)).all()
    submitter_map = {user.id: user for user in submitters}
    
    # Manually construct response with submitter data
    result = []
    for sub in submissions:
        sub_dict = {
            "id": sub.id,
            "assignment_id": sub.assignment_id,
            "submitter_id": sub.submitter_id,
            "submitter": submitter_map.get(sub.submitter_id),
            "submitted_at": sub.submitted_at,
            "status": sub.status,
            "artifacts": sub.artifacts,
        }

        # Attach official_result if present
        if sub.official_run_id and include_results:
            # Lazy import to avoid circulars
            from fair_platform.backend.data.models import SubmissionResult as SRModel

            sr = (
                db.query(SRModel)
                .filter(
                    SRModel.submission_id == sub.id,
                    SRModel.workflow_run_id == sub.official_run_id,
                )
                .first()
            )
            if sr:
                sub_dict["official_result"] = SubmissionResultRead.model_validate(
                    sr
                )
            else:
                sub_dict["official_result"] = None
        else:
            sub_dict["official_result"] = None
        result.append(sub_dict)
    
    return result


@router.get("/{submission_id}", response_model=SubmissionRead)
def get_submission(
    submission_id: UUID,
    run_id: Optional[UUID] = Query(
        None, description="If provided, return result for this workflow run"
    ),
    db: Session = Depends(session_dependency),
):
    sub = db.query(Submission).filter(Submission.id == submission_id).first()
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found"
        )
    
    submitter = db.get(User, sub.submitter_id)
    
    response = {
        "id": sub.id,
        "assignment_id": sub.assignment_id,
        "submitter_id": sub.submitter_id,
        "submitter": submitter,
        "submitted_at": sub.submitted_at,
        "status": sub.status,
        "artifacts": sub.artifacts,
    }

    selected_run_id = run_id or sub.official_run_id
    if selected_run_id:
        from fair_platform.backend.data.models import SubmissionResult as SRModel

        sr = (
            db.query(SRModel)
            .filter(
                SRModel.submission_id == sub.id,
                SRModel.workflow_run_id == selected_run_id,
            )
            .first()
        )
        if sr:
            response["official_result"] = SubmissionResultRead.model_validate(sr)
        else:
            response["official_result"] = None
    else:
        response["official_result"] = None

    return response


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
