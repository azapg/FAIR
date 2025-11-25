from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel


class ArtifactBase(BaseModel):
    title: str
    meta: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True
        alias_generator = lambda field_name: "".join(
            word.capitalize() if i > 0 else word
            for i, word in enumerate(field_name.split("_"))
        )
        populate_by_name = True


class ArtifactCreate(ArtifactBase):
    creator_id: Optional[UUID] = None
    course_id: Optional[UUID] = None
    assignment_id: Optional[UUID] = None
    access_level: Optional[str] = None
    status: Optional[str] = None


class ArtifactUpdate(BaseModel):
    title: Optional[str] = None
    course_id: Optional[UUID] = None
    assignment_id: Optional[UUID] = None
    access_level: Optional[str] = None
    status: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True
        alias_generator = lambda field_name: "".join(
            word.capitalize() if i > 0 else word
            for i, word in enumerate(field_name.split("_"))
        )
        populate_by_name = True


class ArtifactRead(ArtifactBase):
    id: UUID
    storage_path: str
    storage_type: str
    creator_id: UUID
    created_at: datetime
    updated_at: datetime
    status: str
    course_id: Optional[UUID] = None
    assignment_id: Optional[UUID] = None
    access_level: str


__all__ = [
    "ArtifactBase",
    "ArtifactCreate",
    "ArtifactUpdate",
    "ArtifactRead",
]
