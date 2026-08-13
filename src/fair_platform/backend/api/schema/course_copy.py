from datetime import datetime
from typing import Literal, Self
from uuid import UUID
from pydantic import BaseModel, Field, model_validator
from fair_platform.backend.api.schema.utils import schema_config


class CourseCopySelection(BaseModel):
    model_config = schema_config
    content: bool = True
    assignments: bool = True
    rubrics: bool = True
    gradebook: bool = True
    quizzes: bool = True
    flows: bool = True

    @model_validator(mode="after")
    def validate_dependencies(self) -> Self:
        if self.quizzes and not self.content:
            raise ValueError("Quiz copies require course content placement")
        if self.rubrics and not self.assignments:
            raise ValueError("Rubric copies require assignments")
        if not any(self.model_dump().values()):
            raise ValueError("Select at least one course component")
        return self


class CourseCopyRequest(BaseModel):
    model_config = schema_config
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    section: str | None = None
    term: str | None = None
    selection: CourseCopySelection = Field(default_factory=CourseCopySelection)
    date_policy: Literal["clear", "shift"] = "clear"
    date_shift_days: int = Field(default=0, ge=-3650, le=3650)
    idempotency_key: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def validate_date_policy(self) -> Self:
        if self.date_policy == "clear" and self.date_shift_days != 0:
            raise ValueError("dateShiftDays must be zero when dates are cleared")
        return self


class CourseCopyObjectPreview(BaseModel):
    model_config = schema_config

    source_id: UUID
    object_type: str
    title: str
    action: Literal["copy", "transform", "skip", "unsupported"]
    reason: str


class CourseCopyPreview(BaseModel):
    model_config = schema_config
    copied: dict[str, int]
    transformed: dict[str, int]
    skipped: dict[str, int]
    unsupported: dict[str, int]
    date_policy: str
    date_shift_days: int
    warnings: list[str]
    objects: list[CourseCopyObjectPreview]


class CourseCopyResult(BaseModel):
    model_config = schema_config
    job_id: UUID
    destination_course_id: UUID | None
    status: Literal["pending", "running", "completed", "failed"]
    mapping: dict[str, dict[str, str]]
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None


class CourseTemplateCreate(BaseModel):
    model_config = schema_config
    name: str = Field(min_length=1, max_length=255)
    selection: CourseCopySelection = Field(default_factory=CourseCopySelection)
    date_policy: Literal["clear", "shift"] = "clear"
    date_shift_days: int = Field(default=0, ge=-3650, le=3650)

    @model_validator(mode="after")
    def validate_date_policy(self) -> Self:
        if self.date_policy == "clear" and self.date_shift_days != 0:
            raise ValueError("dateShiftDays must be zero when dates are cleared")
        return self


class CourseTemplateRead(BaseModel):
    model_config = schema_config
    id: UUID
    name: str
    source_course_id: UUID
    selection: CourseCopySelection
    date_policy: str
    date_shift_days: int
    created_at: datetime
