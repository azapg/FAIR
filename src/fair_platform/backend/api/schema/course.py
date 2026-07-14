from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel
from fair_platform.backend.api.schema.user import UserRead
from fair_platform.backend.api.schema.assignment import AssignmentRead
from fair_platform.backend.api.schema.flow import FlowRead
from fair_platform.backend.api.schema.utils import schema_config
from datetime import datetime
from fair_platform.backend.data.models.enrollment import CourseMembershipRole


class CourseBase(BaseModel):
    model_config = schema_config
    
    name: str
    description: Optional[str] = None
    instructor_id: UUID
    section: Optional[str] = None
    term: Optional[str] = None


class CourseCreate(CourseBase):
    pass


class CourseUpdate(BaseModel):
    model_config = schema_config
    
    name: Optional[str] = None
    description: Optional[str] = None
    instructor_id: Optional[UUID] = None
    section: Optional[str] = None
    term: Optional[str] = None


class CourseRead(CourseBase):
    id: UUID
    instructor_name: str
    assignments_count: int
    enrollment_code: Optional[str] = None
    is_enrollment_enabled: Optional[bool] = None
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    membership_role: Optional[CourseMembershipRole] = None


class CourseDetailRead(BaseModel):
    model_config = schema_config
    
    id: UUID
    name: str
    description: Optional[str] = None
    instructor: UserRead
    assignments: List[AssignmentRead] = []
    flows: List[FlowRead] = []
    enrollment_code: Optional[str] = None
    is_enrollment_enabled: Optional[bool] = None
    section: Optional[str] = None
    term: Optional[str] = None
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    membership_role: Optional[CourseMembershipRole] = None


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
