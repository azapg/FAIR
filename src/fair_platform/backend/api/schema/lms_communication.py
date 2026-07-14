from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from fair_platform.backend.api.schema.artifact import ArtifactRead
from fair_platform.backend.api.schema.utils import schema_config
from fair_platform.backend.data.models.lms_communication import CoursePostKind


class CoursePostCreate(BaseModel):
    model_config = schema_config

    kind: CoursePostKind = CoursePostKind.announcement
    title: str = Field(min_length=1, max_length=255)
    body: str | None = None
    artifact_ids: list[UUID] = Field(default_factory=list)


class CoursePostRead(BaseModel):
    model_config = schema_config

    id: UUID
    course_id: UUID
    author_id: UUID
    author_name: str
    kind: CoursePostKind
    title: str
    body: str | None = None
    artifacts: list[ArtifactRead] = Field(default_factory=list)
    comments_count: int = 0
    created_at: datetime
    updated_at: datetime


class CourseCommentCreate(BaseModel):
    model_config = schema_config

    body: str = Field(min_length=1)


class CourseCommentRead(BaseModel):
    model_config = schema_config

    id: UUID
    post_id: UUID
    author_id: UUID
    author_name: str
    body: str
    created_at: datetime
    updated_at: datetime


class NotificationRead(BaseModel):
    model_config = schema_config

    id: UUID
    kind: str
    title: str
    body: str | None = None
    link: str | None = None
    created_at: datetime
    read_at: datetime | None = None


class SubmissionCommentCreate(BaseModel):
    model_config = schema_config

    body: str = Field(min_length=1)


class SubmissionCommentRead(BaseModel):
    model_config = schema_config

    id: UUID
    submission_id: UUID
    author_id: UUID
    author_name: str
    body: str
    created_at: datetime
    updated_at: datetime


__all__ = [
    "CourseCommentCreate",
    "CourseCommentRead",
    "CoursePostCreate",
    "CoursePostRead",
    "NotificationRead",
    "SubmissionCommentCreate",
    "SubmissionCommentRead",
]
