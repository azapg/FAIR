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
        from_attributes = True
        alias_generator = lambda field_name: ''.join(word.capitalize() if i > 0 else word for i, word in enumerate(field_name.split('_')))
        validate_by_name = True

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
        from_attributes = True
        alias_generator = lambda field_name: ''.join(word.capitalize() if i > 0 else word for i, word in enumerate(field_name.split('_')))
        validate_by_name = True


class ArtifactRead(ArtifactBase):
    id: UUID


__all__ = [
    "ArtifactBase",
    "ArtifactCreate",
    "ArtifactUpdate",
    "ArtifactRead",
]

