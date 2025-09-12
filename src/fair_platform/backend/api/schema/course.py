from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel
from fair_platform.backend.api.schema.user import UserRead
from fair_platform.backend.api.schema.assignment import AssignmentRead
from fair_platform.backend.api.schema.workflow import WorkflowRead


class CourseBase(BaseModel):
    name: str
    description: Optional[str] = None
    instructor_id: UUID

    class Config:
        orm_mode = True


class CourseCreate(CourseBase):
    pass


class CourseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    instructor_id: Optional[UUID] = None

    class Config:
        orm_mode = True


class CourseRead(CourseBase):
    id: UUID
    instructor_name: str
    assignments_count: int


class CourseDetailRead(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    instructor: UserRead
    assignments: List[AssignmentRead] = []
    workflows: List[WorkflowRead] = []

    class Config:
        orm_mode = True


__all__ = [
    "CourseBase",
    "CourseCreate",
    "CourseUpdate",
    "CourseRead",
    "CourseDetailRead",
]