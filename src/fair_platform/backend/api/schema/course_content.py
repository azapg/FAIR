from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from fair_platform.backend.api.schema.utils import schema_config
from fair_platform.backend.data.models.lms_content import CourseContentVisibility


CourseItemKind = Literal["heading", "page", "link", "file", "assignment", "quiz"]


class CourseSectionCreate(BaseModel):
    model_config = schema_config

    title: str = Field(min_length=1, max_length=255)
    summary: str | None = None
    visibility: CourseContentVisibility = CourseContentVisibility.draft


class CourseSectionUpdate(BaseModel):
    model_config = schema_config

    title: str | None = Field(default=None, min_length=1, max_length=255)
    summary: str | None = None
    visibility: CourseContentVisibility | None = None


class CourseItemCreate(BaseModel):
    model_config = schema_config

    title: str = Field(min_length=1, max_length=255)
    kind: CourseItemKind
    visibility: CourseContentVisibility = CourseContentVisibility.draft
    resource_id: UUID | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class CourseItemUpdate(BaseModel):
    model_config = schema_config

    title: str | None = Field(default=None, min_length=1, max_length=255)
    visibility: CourseContentVisibility | None = None
    payload: dict[str, Any] | None = None


class ExactOrderUpdate(BaseModel):
    model_config = schema_config

    ordered_ids: list[UUID]


class CourseItemRead(BaseModel):
    model_config = schema_config

    id: UUID
    course_id: UUID
    section_id: UUID
    title: str
    position: int
    kind: CourseItemKind
    visibility: CourseContentVisibility
    resource_type: str | None = None
    resource_id: UUID | None = None
    payload_schema_uri: str | None = None
    payload: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class CourseSectionRead(BaseModel):
    model_config = schema_config

    id: UUID
    course_id: UUID
    title: str
    summary: str | None = None
    position: int
    visibility: CourseContentVisibility
    created_at: datetime
    updated_at: datetime
    items: list[CourseItemRead]


class CourseContentRead(BaseModel):
    model_config = schema_config

    course_id: UUID
    can_manage: bool
    sections: list[CourseSectionRead]


__all__ = [
    "CourseContentRead",
    "CourseItemCreate",
    "CourseItemKind",
    "CourseItemRead",
    "CourseItemUpdate",
    "CourseSectionCreate",
    "CourseSectionRead",
    "CourseSectionUpdate",
    "ExactOrderUpdate",
]
