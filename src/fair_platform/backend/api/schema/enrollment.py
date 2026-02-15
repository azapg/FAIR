from typing import List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel
from fair_platform.backend.api.schema.utils import schema_config


class EnrollmentCreate(BaseModel):
    model_config = schema_config

    user_id: UUID
    course_id: UUID


class EnrollmentBulkCreate(BaseModel):
    model_config = schema_config

    user_ids: List[UUID]
    course_id: UUID


class EnrollmentRead(BaseModel):
    model_config = schema_config

    id: UUID
    user_id: UUID
    course_id: UUID
    enrolled_at: datetime
    user_name: Optional[str] = None
    course_name: Optional[str] = None


class EnrollmentJoin(BaseModel):
    model_config = schema_config

    code: str


__all__ = [
    "EnrollmentCreate",
    "EnrollmentBulkCreate",
    "EnrollmentRead",
    "EnrollmentJoin",
]
