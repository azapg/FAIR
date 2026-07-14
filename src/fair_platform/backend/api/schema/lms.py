from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel

from fair_platform.backend.api.schema.utils import schema_config


class GradebookAssignment(BaseModel):
    model_config = schema_config

    id: UUID
    title: str
    deadline: datetime | None = None
    max_grade: dict[str, Any] | None = None


class GradebookCell(BaseModel):
    model_config = schema_config

    assignment_id: UUID
    state: Literal["missing", "submitted", "returned", "excused"]
    submission_id: UUID | None = None
    score: float | None = None
    submitted_at: datetime | None = None
    is_late: bool = False
    attempt_count: int = 0


class GradebookRow(BaseModel):
    model_config = schema_config

    user_id: UUID
    name: str
    email: str
    cells: list[GradebookCell]


class CourseGradebook(BaseModel):
    model_config = schema_config

    course_id: UUID
    assignments: list[GradebookAssignment]
    rows: list[GradebookRow]


class GradingQueueItem(BaseModel):
    model_config = schema_config

    submission_id: UUID
    assignment_id: UUID
    assignment_title: str
    user_id: UUID
    student_name: str
    submitted_at: datetime | None = None
    is_late: bool
    attempt_number: int
    status: str


class StudentTodoItem(BaseModel):
    model_config = schema_config

    assignment_id: UUID
    assignment_title: str
    course_id: UUID
    course_name: str
    deadline: datetime | None = None
    state: Literal["missing", "submitted"]
    submission_id: UUID | None = None
    attempt_count: int = 0
    is_late: bool = False


__all__ = [
    "CourseGradebook",
    "GradebookAssignment",
    "GradebookCell",
    "GradebookRow",
    "GradingQueueItem",
    "StudentTodoItem",
]
