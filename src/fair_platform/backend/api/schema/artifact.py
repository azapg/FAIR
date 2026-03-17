from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, Field
from fair_platform.backend.api.schema.utils import schema_config


class ArtifactBase(BaseModel):
    model_config = schema_config
    
    title: str
    meta: Optional[Dict[str, Any]] = None


class ArtifactCreate(ArtifactBase):
    creator_id: Optional[UUID] = None
    course_id: Optional[UUID] = None
    assignment_id: Optional[UUID] = None
    access_level: Optional[str] = None
    status: Optional[str] = None


class ArtifactUpdate(BaseModel):
    model_config = schema_config
    
    title: Optional[str] = None
    course_id: Optional[UUID] = None
    assignment_id: Optional[UUID] = None
    access_level: Optional[str] = None
    status: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


class ArtifactDerivativeRead(BaseModel):
    model_config = schema_config

    id: UUID
    artifact_id: UUID
    derivative_type: str
    storage_uri: str
    mime_type: str
    created_at: datetime
    updated_at: datetime


class ArtifactRead(ArtifactBase):
    id: UUID
    artifact_type: str
    mime: str
    creator_id: UUID
    created_at: datetime
    updated_at: datetime
    status: str
    course_id: Optional[UUID] = None
    assignment_id: Optional[UUID] = None
    access_level: str
    derivatives: list[ArtifactDerivativeRead] = Field(default_factory=list)


__all__ = [
    "ArtifactBase",
    "ArtifactCreate",
    "ArtifactDerivativeRead",
    "ArtifactUpdate",
    "ArtifactRead",
]
