from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from fair_platform.backend.api.schema.gradebook import (
    GradebookCategoryRead,
    GradebookCategoryTotal,
    GradebookCourseTotal,
)
from fair_platform.backend.api.schema.utils import schema_config


class StudentGradeItem(BaseModel):
    model_config = schema_config

    grade_item_id: UUID
    category_id: UUID | None = None
    title: str | None = None
    max_points: float | None = None
    status: Literal["graded", "excused", "missing", "unreleased"]
    points_earned: float | None = None
    released_at: datetime | None = None
    note: str | None = None
    assignment_id: UUID | None = None
    submission_id: UUID | None = None
    contribution_percentage_points: float | None = None


class StudentCourseGrades(BaseModel):
    model_config = schema_config

    course_id: UUID
    course_name: str
    term: str | None = None
    total: GradebookCourseTotal
    current_grade_label: str = "Current grade"
    final_grade_available: bool = False
    categories: list[GradebookCategoryRead] = Field(default_factory=list)
    category_totals: list[GradebookCategoryTotal] = Field(default_factory=list)
    items: list[StudentGradeItem] = Field(default_factory=list)


class StudentDashboardWorkItem(BaseModel):
    model_config = schema_config

    assignment_id: UUID
    course_id: UUID
    course_name: str
    title: str
    deadline: datetime | None = None
    timezone_name: str = "UTC"
    state: Literal["upcoming", "overdue", "submitted"]
    submission_id: UUID | None = None


class StudentReturnedFeedback(BaseModel):
    model_config = schema_config

    assignment_id: UUID
    submission_id: UUID
    course_id: UUID
    course_name: str
    assignment_title: str
    points_earned: float | None = None
    max_points: float | None = None
    feedback_available: bool
    returned_at: datetime
    link: str


class StudentCourseActivity(BaseModel):
    model_config = schema_config

    id: UUID
    course_id: UUID
    course_name: str
    kind: Literal["announcement", "material", "assignment"]
    title: str
    occurred_at: datetime
    link: str


class StudentCourseProgress(BaseModel):
    model_config = schema_config

    course_id: UUID
    course_name: str
    term: str | None = None
    completed_items: int
    tracked_items: int
    completion_percentage: float | None = None
    current_grade: float | None = None
    points_earned: float
    points_possible: float
    grade_is_provisional: bool


class StudentDashboardSourceStatus(BaseModel):
    model_config = schema_config

    source: Literal["work", "feedback", "activity", "progress"]
    available: bool
    message: str | None = None


class StudentDashboard(BaseModel):
    model_config = schema_config

    generated_at: datetime
    upcoming_work: list[StudentDashboardWorkItem] = Field(default_factory=list)
    overdue_work: list[StudentDashboardWorkItem] = Field(default_factory=list)
    returned_feedback: list[StudentReturnedFeedback] = Field(default_factory=list)
    recent_activity: list[StudentCourseActivity] = Field(default_factory=list)
    course_progress: list[StudentCourseProgress] = Field(default_factory=list)
    sources: list[StudentDashboardSourceStatus] = Field(default_factory=list)


__all__ = [
    "StudentCourseActivity",
    "StudentCourseGrades",
    "StudentCourseProgress",
    "StudentDashboard",
    "StudentDashboardSourceStatus",
    "StudentDashboardWorkItem",
    "StudentGradeItem",
    "StudentReturnedFeedback",
]
