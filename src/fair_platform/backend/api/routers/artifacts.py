from uuid import UUID
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, Query
from sqlalchemy.orm import Session

from fair_platform.backend.data.database import session_dependency
from fair_platform.backend.data.models.artifact import AccessLevel, ArtifactStatus
from fair_platform.backend.api.schema.artifact import (
    ArtifactRead,
    ArtifactUpdate,
)
from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.data.models.user import User, UserRole
from fair_platform.backend.services.artifact_manager import get_artifact_manager

router = APIRouter()

@router.post(
    "/", status_code=status.HTTP_201_CREATED, response_model=List[ArtifactRead]
)
def create_artifact(
    files: List[UploadFile],
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    """
    Upload one or more artifacts.
    
    Creates artifacts in 'pending' status. They must be attached to
    assignments or submissions to become 'attached'.
    """
    if current_user.role != UserRole.admin and current_user.role != UserRole.professor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors or admin can create artifacts",
        )

    manager = get_artifact_manager(db)
    
    try:
        artifacts = manager.create_artifacts_bulk(files, creator=current_user)
        db.commit()
        return artifacts
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/", response_model=List[ArtifactRead])
def list_artifacts(
    creator_id: Optional[UUID] = Query(None),
    course_id: Optional[UUID] = Query(None),
    assignment_id: Optional[UUID] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    access_level: Optional[str] = Query(None),
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    """
    List artifacts with optional filters.
    
    Filters are applied before permission checking, so users will only
    see artifacts they have permission to view.
    """
    manager = get_artifact_manager(db)
    
    filters = {}
    if creator_id:
        filters["creator_id"] = creator_id
    if course_id:
        filters["course_id"] = course_id
    if assignment_id:
        filters["assignment_id"] = assignment_id
    if status_filter:
        filters["status"] = status_filter
    if access_level:
        filters["access_level"] = access_level

    return manager.list_artifacts(user=current_user, filters=filters)


@router.get("/{artifact_id}", response_model=ArtifactRead)
def get_artifact(
    artifact_id: UUID,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    """Get specific artifact with permission check."""
    manager = get_artifact_manager(db)
    
    try:
        return manager.get_artifact(artifact_id, current_user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{artifact_id}", response_model=ArtifactRead)
def update_artifact(
    artifact_id: UUID,
    payload: ArtifactUpdate,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    """Update artifact metadata with permission check."""
    manager = get_artifact_manager(db)
    
    try:
        access_level = AccessLevel(payload.access_level) if payload.access_level else None
        status_val = ArtifactStatus(payload.status) if payload.status else None
        
        artifact = manager.update_artifact(
            artifact_id=artifact_id,
            user=current_user,
            title=payload.title,
            meta=payload.meta,
            access_level=access_level,
            status=status_val,
            course_id=payload.course_id,
            assignment_id=payload.assignment_id,
        )
        db.commit()
        return artifact
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{artifact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_artifact(
    artifact_id: UUID,
    hard_delete: bool = Query(False, description="Permanently delete (admin only)"),
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    """
    Delete artifact (soft delete by default, hard delete for admins).
    
    Soft delete marks the artifact as archived but preserves the file.
    Hard delete removes both the database record and the physical file.
    """
    manager = get_artifact_manager(db)
    
    try:
        # TODO: I do not like this API, it is doing too much logic here
        manager.delete_artifact(artifact_id, current_user, hard_delete=hard_delete)
        db.commit()
        return None
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ATTACHMENT ENDPOINTS
# ============================================================================

@router.post("/{artifact_id}/attach/assignment/{assignment_id}", response_model=ArtifactRead)
def attach_artifact_to_assignment(
    artifact_id: UUID,
    assignment_id: UUID,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    """
    Attach existing artifact to an assignment.
    
    Updates the artifact's status to 'attached' if it was 'pending'.
    """
    manager = get_artifact_manager(db)
    
    try:
        artifact = manager.attach_to_assignment(artifact_id, assignment_id, current_user)
        db.commit()
        return artifact
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{artifact_id}/attach/submission/{submission_id}", response_model=ArtifactRead)
def attach_artifact_to_submission(
    artifact_id: UUID,
    submission_id: UUID,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    """
    Attach existing artifact to a submission.
    
    Updates the artifact's status to 'attached' if it was 'pending'.
    """
    manager = get_artifact_manager(db)
    
    try:
        artifact = manager.attach_to_submission(artifact_id, submission_id, current_user)
        db.commit()
        return artifact
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{artifact_id}/detach/assignment/{assignment_id}", response_model=ArtifactRead)
def detach_artifact_from_assignment(
    artifact_id: UUID,
    assignment_id: UUID,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    """
    Detach artifact from assignment.
    
    If artifact has no other attachments, it will be marked as 'orphaned'.
    """
    manager = get_artifact_manager(db)
    
    try:
        artifact = manager.detach_from_assignment(artifact_id, assignment_id, current_user)
        db.commit()
        return artifact
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{artifact_id}/detach/submission/{submission_id}", response_model=ArtifactRead)
def detach_artifact_from_submission(
    artifact_id: UUID,
    submission_id: UUID,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    """
    Detach artifact from submission.
    
    If artifact has no other attachments, it will be marked as 'orphaned'.
    """
    manager = get_artifact_manager(db)
    
    try:
        artifact = manager.detach_from_submission(artifact_id, submission_id, current_user)
        db.commit()
        return artifact
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ADMIN ENDPOINTS
# ============================================================================

@router.post("/admin/cleanup-orphaned")
def cleanup_orphaned_artifacts(
    older_than_days: int = Query(7, description="Clean artifacts orphaned for N days"),
    hard_delete: bool = Query(False, description="Permanently delete files (requires admin)"),
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    """
    Cleanup orphaned artifacts (admin only).
    
    Removes artifacts that have been in 'orphaned' status for longer than
    the specified number of days. By default, soft deletes (archives) them.
    """
    if current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=403,
            detail="Only admins can cleanup orphaned artifacts"
        )
    
    manager = get_artifact_manager(db)
    
    try:
        count = manager.cleanup_orphaned(older_than_days, hard_delete)
        db.commit()
        return {
            "cleaned_up": count,
            "hard_delete": hard_delete,
            "older_than_days": older_than_days
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


__all__ = ["router"]
