from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel
from fair_platform.backend.api.schema.user import UserRead
from fair_platform.backend.api.schema.assignment import AssignmentRead
from fair_platform.backend.api.schema.workflow import WorkflowRead
from fair_platform.backend.api.schema.utils import schema_config


class CourseBase(BaseModel):
    model_config = schema_config
    
    name: str
    description: Optional[str] = None
    instructor_id: UUID


class CourseCreate(CourseBase):
    pass


class CourseUpdate(BaseModel):
    model_config = schema_config
    
    name: Optional[str] = None
    description: Optional[str] = None
    instructor_id: Optional[UUID] = None


class CourseRead(CourseBase):
    id: UUID
    instructor_name: str
    assignments_count: int
    enrollment_code: Optional[str] = None
    is_enrollment_enabled: Optional[bool] = None


class CourseDetailRead(BaseModel):
    model_config = schema_config
    
    id: UUID
    name: str
    description: Optional[str] = None
    instructor: UserRead
    assignments: List[AssignmentRead] = []
    workflows: List[WorkflowRead] = []
    enrollment_code: Optional[str] = None
    is_enrollment_enabled: Optional[bool] = None


class CourseSettingsUpdate(BaseModel):
    model_config = schema_config

    is_enrollment_enabled: Optional[bool] = None


__all__ = [
    "CourseBase",
    "CourseCreate",
    "CourseUpdate",
    "CourseRead",
    "CourseDetailRead",
    "CourseSettingsUpdate",
]
