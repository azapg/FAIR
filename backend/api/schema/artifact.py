from typing import Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel


class ArtifactBase(BaseModel):
    title: str
    artifact_type: str
    mime: str
    storage_path: str
    storage_type: str
    meta: Optional[Dict[str, Any]] = None

    class Config:
        orm_mode = True


class ArtifactCreate(ArtifactBase):
    pass


class ArtifactUpdate(BaseModel):
    title: Optional[str] = None
    artifact_type: Optional[str] = None
    mime: Optional[str] = None
    storage_path: Optional[str] = None
    storage_type: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None

    class Config:
        orm_mode = True


class ArtifactRead(ArtifactBase):
    id: UUID


__all__ = [
    "ArtifactBase",
    "ArtifactCreate",
    "ArtifactUpdate",
    "ArtifactRead",
]

