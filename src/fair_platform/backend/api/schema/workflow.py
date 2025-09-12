from typing import Optional
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel


class WorkflowBase(BaseModel):
    course_id: UUID
    name: str
    description: Optional[str] = None
    created_by: UUID

    class Config:
        orm_mode = True


class WorkflowCreate(WorkflowBase):
    pass


class WorkflowUpdate(BaseModel):
    course_id: Optional[UUID] = None
    name: Optional[str] = None
    description: Optional[str] = None
    created_by: Optional[UUID] = None

    class Config:
        orm_mode = True


class WorkflowRead(WorkflowBase):
    id: UUID
    created_at: datetime


__all__ = [
    "WorkflowBase",
    "WorkflowCreate",
    "WorkflowUpdate",
    "WorkflowRead",
]

