from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel
from fair_platform.backend.api.schema.utils import schema_config
from fair_platform.backend.data.models.assignment import AssignmentStatus


class AssignmentBase(BaseModel):
    model_config = schema_config
    
    course_id: UUID
    title: str
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    max_grade: Optional[Dict[str, Any]] = None
    status: AssignmentStatus = AssignmentStatus.published
    published_at: Optional[datetime] = None
    allow_resubmissions: bool = True


class AssignmentCreate(AssignmentBase):
    artifacts: Optional[List[UUID]] = None
    allow_resubmissions: Optional[bool] = None


class AssignmentUpdate(BaseModel):
    model_config = schema_config
    
    title: Optional[str] = None
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    max_grade: Optional[Dict[str, Any]] = None
    artifacts: Optional[List[UUID]] = None


class AssignmentRead(AssignmentBase):
    id: UUID


class AssignmentStatusUpdate(BaseModel):
    model_config = schema_config

    status: AssignmentStatus


__all__ = [
    "AssignmentBase",
    "AssignmentCreate",
    "AssignmentUpdate",
    "AssignmentRead",
    "AssignmentStatusUpdate",
]
