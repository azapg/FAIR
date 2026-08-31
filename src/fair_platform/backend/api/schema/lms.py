from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from fair_platform.backend.api.schema.utils import schema_config
from fair_platform.backend.api.schema.gradebook import (
    CourseGradebook,
    GradebookAssignment,
    GradebookCell,
    GradebookRow,
)


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
