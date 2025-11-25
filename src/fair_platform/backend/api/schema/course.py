from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel
from fair_platform.backend.api.schema.user import UserRead
from fair_platform.backend.api.schema.assignment import AssignmentRead
from fair_platform.backend.api.schema.workflow import WorkflowRead
from fair_platform.backend.api.schema.utils import to_camel_case


class CourseBase(BaseModel):
    name: str
    description: Optional[str] = None
    instructor_id: UUID

    class Config:
        from_attributes = True
        alias_generator = to_camel_case
        populate_by_name = True


class CourseCreate(CourseBase):
    pass


class CourseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    instructor_id: Optional[UUID] = None

    class Config:
        from_attributes = True
        alias_generator = to_camel_case
        populate_by_name = True


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
        from_attributes = True
        alias_generator = to_camel_case
        populate_by_name = True


__all__ = [
    "CourseBase",
    "CourseCreate",
    "CourseUpdate",
    "CourseRead",
    "CourseDetailRead",
]
