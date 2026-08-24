from uuid import UUID, uuid4
from datetime import datetime
import math
from sqlalchemy import (
    String,
    Text,
    ForeignKey,
    UUID as SAUUID,
    TIMESTAMP,
    Table,
    Column,
    Boolean,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from typing import Any, Optional, List, TYPE_CHECKING
from enum import Enum

from ..database import Base
from .types import json_document_type

if TYPE_CHECKING:
    from .course import Course
    from .submission import Submission
    from .artifact import Artifact
    from .execution import Execution
    from .rubric import Rubric

assignment_artifacts = Table(
    "assignment_artifacts",
    Base.metadata,
    Column("id", SAUUID, primary_key=True, default=uuid4),
    Column(
        "assignment_id",
        SAUUID,
        ForeignKey("assignments.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "artifact_id",
        SAUUID,
        ForeignKey("artifacts.id", ondelete="CASCADE"),
        nullable=False,
    ),
)


class AssignmentStatus(str, Enum):
    draft = "draft"
    published = "published"
    closed = "closed"


class Assignment(Base):
    __tablename__ = "assignments"

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True)
    course_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("courses.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    deadline: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, nullable=True)
    max_grade: Mapped[dict] = mapped_column(json_document_type(), nullable=False)
    status: Mapped[AssignmentStatus] = mapped_column(
        String(32), nullable=False, default=AssignmentStatus.published
    )
    published_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, nullable=True)
    rubric_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID, ForeignKey("rubrics.id", ondelete="RESTRICT"), nullable=True
    )
    allow_resubmissions: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )

    course: Mapped["Course"] = relationship("Course", back_populates="assignments")
    submissions: Mapped[List["Submission"]] = relationship(
        "Submission", back_populates="assignment", cascade="all, delete-orphan"
    )
    executions: Mapped[List["Execution"]] = relationship(
        "Execution", back_populates="assignment"
    )
    rubric: Mapped[Optional["Rubric"]] = relationship("Rubric")

    direct_artifacts: Mapped[List["Artifact"]] = relationship(
        "Artifact", back_populates="assignment"
    )

    artifacts: Mapped[List["Artifact"]] = relationship(
        "Artifact",
        secondary="assignment_artifacts",
        back_populates="assignments",
    )

    @validates("max_grade")
    def validate_max_grade(self, _key: str, value: Any) -> dict[str, float | str]:
        if not isinstance(value, dict):
            raise ValueError("max_grade must be a points grading object")
        if set(value) != {"type", "value"} or value.get("type") != "points":
            raise ValueError(
                'max_grade must have exactly {"type": "points", "value": <positive number>}'
            )
        points = value.get("value")
        if (
            isinstance(points, bool)
            or not isinstance(points, (int, float))
            or not math.isfinite(points)
            or points <= 0
        ):
            raise ValueError("max_grade.value must be a positive number of points")
        return {"type": "points", "value": points}

    def __repr__(self) -> str:
        return (
            f"<Assignment id={self.id} title={self.title!r} course_id={self.course_id}>"
        )
