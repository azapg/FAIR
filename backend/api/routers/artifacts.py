from uuid import UUID, uuid4
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from data.database import session_dependency
from data.models.artifact import Artifact
from api.schema.artifact import ArtifactCreate, ArtifactRead, ArtifactUpdate

router = APIRouter()


@router.post("/", response_model=ArtifactRead, status_code=status.HTTP_201_CREATED)
def create_artifact(payload: ArtifactCreate, db: Session = Depends(session_dependency)):
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


@router.get("/{artifact_id}", response_model=ArtifactRead)
def get_artifact(artifact_id: UUID, db: Session = Depends(session_dependency)):
    artifact = db.get(Artifact, artifact_id)
    if not artifact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")
    return artifact


@router.put("/{artifact_id}", response_model=ArtifactRead)
def update_artifact(artifact_id: UUID, payload: ArtifactUpdate, db: Session = Depends(session_dependency)):
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
def delete_artifact(artifact_id: UUID, db: Session = Depends(session_dependency)):
    artifact = db.get(Artifact, artifact_id)
    if not artifact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")
    db.delete(artifact)
    db.commit()
    return None


__all__ = ["router"]

