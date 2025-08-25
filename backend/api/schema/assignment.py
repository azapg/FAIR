from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel


class AssignmentArtifactLink(BaseModel):
    artifact_id: UUID
    role: str

    class Config:
        orm_mode = True


class AssignmentBase(BaseModel):
    course_id: UUID
    title: str
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    max_grade: Dict[str, Any]

    class Config:
        orm_mode = True


class AssignmentCreate(AssignmentBase):
    artifacts: Optional[List[AssignmentArtifactLink]] = None


class AssignmentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    max_grade: Optional[Dict[str, Any]] = None
    artifacts: Optional[List[AssignmentArtifactLink]] = None  # full-replace semantics if provided

    class Config:
        orm_mode = True


class AssignmentRead(AssignmentBase):
    id: UUID


__all__ = [
    "AssignmentArtifactLink",
    "AssignmentBase",
    "AssignmentCreate",
    "AssignmentUpdate",
    "AssignmentRead",
]

