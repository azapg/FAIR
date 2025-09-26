from uuid import UUID, uuid4
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from fair_platform.backend.data.database import session_dependency
from fair_platform.backend.data.models.artifact import Artifact
from fair_platform.backend.api.schema.artifact import ArtifactCreate, ArtifactRead, ArtifactUpdate
from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.data.models.user import User, UserRole

router = APIRouter()

# TODO: Artifacts not having owners means we can't enforce permissions easily.
#   Most assignments will only be managed by their instructors/admin, but
#   there students might want to update their submissions. Since in beta there
#   are no students, this is not a concern yet, and we can just let instructors/admin
#   manage everything.

@router.post("/", response_model=ArtifactRead, status_code=status.HTTP_201_CREATED)
def create_artifact(payload: ArtifactCreate, db: Session = Depends(session_dependency), current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.admin and current_user.role != UserRole.professor:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only instructors or admin can create artifacts")

    artifact = Artifact(
        id=uuid4(),
        title=payload.title,
        artifact_type=payload.artifact_type,
        mime=payload.mime,
        storage_path=payload.storage_path,
        storage_type=payload.storage_type,
        meta=payload.meta,
    )
    db.add(artifact)
    db.commit()
    db.refresh(artifact)
    return artifact


@router.get("/", response_model=List[ArtifactRead])
def list_artifacts(db: Session = Depends(session_dependency)):
    return db.query(Artifact).all()

# TODO: You shouldn't be able to get artifacts you don't have access to.
#   This is related to the ownership problem mentioned above.
#   I think the solution would be to relate artifacts to assignments/submissions,
#   and then check if the user has access to those. (e.g. if the user is the instructor of the course
#   the assignment belongs to, or if the user is the student who made the submission)
#   But since there are no students in beta, this is not a concern yet.
@router.get("/{artifact_id}", response_model=ArtifactRead)
def get_artifact(artifact_id: UUID, db: Session = Depends(session_dependency)):
    artifact = db.get(Artifact, artifact_id)
    if not artifact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")
    return artifact


@router.put("/{artifact_id}", response_model=ArtifactRead)
def update_artifact(artifact_id: UUID, payload: ArtifactUpdate, db: Session = Depends(session_dependency), current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.admin and current_user.role != UserRole.professor:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only instructors or admin can update artifacts")
    
    artifact = db.get(Artifact, artifact_id)
    if not artifact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")

    if payload.title is not None:
        artifact.title = payload.title
    if payload.artifact_type is not None:
        artifact.artifact_type = payload.artifact_type
    if payload.mime is not None:
        artifact.mime = payload.mime
    if payload.storage_path is not None:
        artifact.storage_path = payload.storage_path
    if payload.storage_type is not None:
        artifact.storage_type = payload.storage_type
    if payload.meta is not None:
        artifact.meta = payload.meta

    db.add(artifact)
    db.commit()
    db.refresh(artifact)
    return artifact


@router.delete("/{artifact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_artifact(artifact_id: UUID, db: Session = Depends(session_dependency), current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.admin and current_user.role != UserRole.professor:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only instructors or admin can delete artifacts")

    artifact = db.get(Artifact, artifact_id)
    if not artifact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")
    
    db.delete(artifact)
    db.commit()
    return None


__all__ = ["router"]

