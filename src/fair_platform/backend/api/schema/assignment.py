from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel
from fair_platform.backend.api.schema.utils import to_camel_case


class AssignmentBase(BaseModel):
    course_id: UUID
    title: str
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    max_grade: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True
        alias_generator = to_camel_case
        populate_by_name = True


class AssignmentCreate(AssignmentBase):
    artifacts: Optional[List[UUID]] = None


class AssignmentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    max_grade: Optional[Dict[str, Any]] = None
    artifacts: Optional[List[UUID]] = None

    class Config:
        from_attributes = True
        alias_generator = to_camel_case
        populate_by_name = True


class AssignmentRead(AssignmentBase):
    id: UUID


__all__ = [
    "AssignmentBase",
    "AssignmentCreate",
    "AssignmentUpdate",
    "AssignmentRead",
]
