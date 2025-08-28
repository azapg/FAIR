from typing import Optional
from uuid import UUID

from pydantic import BaseModel


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


__all__ = ["CourseBase", "CourseCreate", "CourseUpdate", "CourseRead"]

