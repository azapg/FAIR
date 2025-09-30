from uuid import UUID, uuid4
from typing import List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile
from sqlalchemy.orm import Session

from fair_platform.backend import storage
from fair_platform.backend.data.database import session_dependency
from fair_platform.backend.data.models.artifact import Artifact, ArtifactStatus, AccessLevel
from fair_platform.backend.data.models.course import Course
from fair_platform.backend.api.schema.artifact import (
    ArtifactRead,
    ArtifactUpdate,
)
from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.data.models.user import User, UserRole

router = APIRouter()

@router.post(
    "/", status_code=status.HTTP_201_CREATED, response_model=List[ArtifactRead]
)
def create_artifact(
    files: List[UploadFile],
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.admin and current_user.role != UserRole.professor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors or admin can create artifacts",
        )

    uploads_folder = storage.uploads_dir
    created_artifacts = []

    try:
        for file in files:
            if not file.filename:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="File must have a filename",
                )
            
            artifact_id = uuid4()
            artifact_folder = uploads_folder / str(artifact_id)
            artifact_folder.mkdir(parents=True, exist_ok=True)
            file_location = artifact_folder / file.filename

            artifact = Artifact(
                id=artifact_id,
                title=file.filename,
                # TODO: I want to make this a cleaner and more useful mime for plugins and other things, currently just "file"
                artifact_type="file",
                mime=file.content_type or "application/octet-stream",
                storage_path=str(artifact_id) + "/" + file.filename,
                storage_type="local",
                meta=None,
                creator_id=current_user.id,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                status=ArtifactStatus.pending,
                access_level=AccessLevel.private,
            )

            with open(file_location, "wb+") as buffer:
                buffer.write(file.file.read())

            db.add(artifact)
            db.commit()
            db.refresh(artifact)
            created_artifacts.append(artifact)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {e}",
        )

    return created_artifacts


@router.get("/", response_model=List[ArtifactRead])
def list_artifacts(db: Session = Depends(session_dependency), user: User = Depends(get_current_user)):
    # TODO: Allow filtering by user, course, assignment, access level, etc.
    return db.query(Artifact).filter(Artifact.creator_id == user.id).all()
    
    


@router.get("/{artifact_id}", response_model=ArtifactRead)
def get_artifact(artifact_id: UUID, db: Session = Depends(session_dependency)):
    artifact = db.get(Artifact, artifact_id)
    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found"
        )
    return artifact


@router.put("/{artifact_id}", response_model=ArtifactRead)
def update_artifact(
    artifact_id: UUID,
    payload: ArtifactUpdate,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    artifact = db.get(Artifact, artifact_id)
    if not artifact:
        raise HTTPException(404, detail="Artifact not found")

    if (
        artifact.creator_id != current_user.id
        and current_user.role != UserRole.admin
        and current_user.role != UserRole.professor
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the creator, instructors, or admin can update artifacts",
        )

    if payload.title is not None:
        artifact.title = payload.title
    if payload.meta is not None:
        artifact.meta = payload.meta
    if payload.course_id is not None:
        artifact.course_id = payload.course_id
    if payload.assignment_id is not None:
        artifact.assignment_id = payload.assignment_id
    if payload.access_level is not None:
        artifact.access_level = AccessLevel(payload.access_level)
    if payload.status is not None:
        artifact.status = ArtifactStatus(payload.status)
    
    artifact.updated_at = datetime.now()

    db.add(artifact)
    db.commit()
    db.refresh(artifact)
    return artifact


@router.delete("/{artifact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_artifact(
    artifact_id: UUID,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    artifact = db.get(Artifact, artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    can_professor_delete = False
    valid_access_levels = [AccessLevel.course, AccessLevel.assignment, AccessLevel.public]
    if artifact.course_id and current_user.role == UserRole.professor and artifact.access_level in valid_access_levels:
        course = db.get(Course, artifact.course_id)
        if course and course.instructor_id == current_user.id:
            can_professor_delete = True   
    

    if (
        artifact.creator_id != current_user.id
        and current_user.role != UserRole.admin
        and not can_professor_delete
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the creator, instructors, or admin can delete artifacts",
        )

    db.delete(artifact)
    db.commit()
    return None


__all__ = ["router"]
