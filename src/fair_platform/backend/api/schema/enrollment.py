from typing import List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel
from fair_platform.backend.api.schema.utils import schema_config
from fair_platform.backend.data.models.enrollment import CourseMembershipRole, EnrollmentStatus


class EnrollmentCreate(BaseModel):
    model_config = schema_config

    user_id: UUID
    course_id: UUID
    role: CourseMembershipRole = CourseMembershipRole.student


class EnrollmentBulkCreate(BaseModel):
    model_config = schema_config

    user_ids: List[UUID]
    course_id: UUID
    role: CourseMembershipRole = CourseMembershipRole.student


class EnrollmentRead(BaseModel):
    model_config = schema_config

    id: UUID
    user_id: UUID
    course_id: UUID
    enrolled_at: datetime
    role: CourseMembershipRole
    status: EnrollmentStatus
    updated_at: datetime
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    course_name: Optional[str] = None


class EnrollmentUpdate(BaseModel):
    model_config = schema_config

    role: CourseMembershipRole


class EnrollmentJoin(BaseModel):
    model_config = schema_config

    code: str


__all__ = [
    "EnrollmentCreate",
    "EnrollmentBulkCreate",
    "EnrollmentRead",
    "EnrollmentUpdate",
    "EnrollmentJoin",
]
