from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from fair_platform.backend.api.schema.assignment import PointsGrade
from fair_platform.backend.api.schema.utils import schema_config


class GradebookAssignment(BaseModel):
    """Legacy assignment column kept for additive response compatibility."""

    model_config = schema_config

    id: UUID
    title: str
    deadline: datetime | None = None
    max_grade: PointsGrade


class GradebookCell(BaseModel):
    """Legacy latest-attempt cell kept for grading-queue compatibility."""

    model_config = schema_config

    assignment_id: UUID
    state: Literal["missing", "submitted", "returned", "excused"]
    submission_id: UUID | None = None
    score: float | None = None
    submitted_at: datetime | None = None
    is_late: bool = False
    attempt_count: int = 0


class GradebookCategoryRead(BaseModel):
    model_config = schema_config

    id: UUID
    name: str
    description: str | None = None
    position: int
    weight: float | None = None
    aggregation_strategy: str
    is_default: bool = False


class GradebookCategoryCreate(BaseModel):
    model_config = schema_config

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    weight: float | None = Field(
        default=None,
        ge=0,
        allow_inf_nan=False,
        description=(
            "Optional percentage weight. If any category is weighted, all "
            "categories should have weights totaling 100; otherwise totals are provisional."
        ),
    )


class GradebookCategoryUpdate(BaseModel):
    model_config = schema_config

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    position: int | None = Field(default=None, ge=0)
    weight: float | None = Field(
        default=None,
        ge=0,
        allow_inf_nan=False,
        description=(
            "Optional percentage weight. Mixed/misaligned weights remain visible "
            "but mark the course total provisional."
        ),
    )


class GradebookItemRead(BaseModel):
    model_config = schema_config

    id: UUID
    category_id: UUID | None = None
    title: str
    description: str | None = None
    position: int
    max_points: float
    source_type: str | None = None
    source_id: UUID | None = None
    is_manual: bool


class GradebookItemCreate(BaseModel):
    model_config = schema_config

    category_id: UUID | None = None
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    max_points: float = Field(gt=0, allow_inf_nan=False)


class GradebookItemUpdate(BaseModel):
    model_config = schema_config

    category_id: UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    max_points: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    position: int | None = Field(default=None, ge=0)


class GradebookEntryUpsert(BaseModel):
    model_config = schema_config

    status: Literal["graded", "excused", "missing"]
    points_earned: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    note: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def validate_status_points(self) -> "GradebookEntryUpsert":
        if self.status == "graded" and self.points_earned is None:
            raise ValueError("A graded entry requires pointsEarned")
        if self.status in {"excused", "missing"} and self.points_earned is not None:
            raise ValueError(f"A {self.status} entry cannot include pointsEarned")
        return self


class GradebookEntryCell(BaseModel):
    model_config = schema_config

    grade_item_id: UUID
    status: Literal["graded", "excused", "missing", "absent"]
    release_state: Literal["released", "unreleased", "absent"]
    points_earned: float | None = None
    source_type: str | None = None
    source_id: UUID | None = None
    released_at: datetime | None = None
    note: str | None = None


class GradebookTotal(BaseModel):
    model_config = schema_config

    points_earned: float
    points_possible: float
    percentage: float | None = None
    provisional: bool
    graded_item_count: int
    excused_item_count: int
    missing_entry_count: int
    reasons: list[str] = Field(default_factory=list)


class GradebookCategoryTotal(GradebookTotal):
    category_id: UUID
    weight: float | None = None


class GradebookCourseTotal(GradebookTotal):
    calculation: Literal["points", "category_weighted"]
    configured_weight_total: float | None = None


class GradebookRow(BaseModel):
    model_config = schema_config

    user_id: UUID
    name: str
    email: str
    cells: list[GradebookCell]
    item_cells: list[GradebookEntryCell] = Field(default_factory=list)
    category_totals: list[GradebookCategoryTotal] = Field(default_factory=list)
    course_total: GradebookCourseTotal | None = None


class CourseGradebook(BaseModel):
    model_config = schema_config

    course_id: UUID
    assignments: list[GradebookAssignment]
    rows: list[GradebookRow]
    categories: list[GradebookCategoryRead] = Field(default_factory=list)
    items: list[GradebookItemRead] = Field(default_factory=list)


__all__ = [
    "CourseGradebook",
    "GradebookAssignment",
    "GradebookCategoryCreate",
    "GradebookCategoryRead",
    "GradebookCategoryTotal",
    "GradebookCategoryUpdate",
    "GradebookCell",
    "GradebookCourseTotal",
    "GradebookEntryCell",
    "GradebookEntryUpsert",
    "GradebookItemCreate",
    "GradebookItemRead",
    "GradebookItemUpdate",
    "GradebookRow",
    "GradebookTotal",
]
