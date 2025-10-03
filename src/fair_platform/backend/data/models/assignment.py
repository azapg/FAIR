from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy import (
    String,
    Text,
    ForeignKey,
    UUID as SAUUID,
    TIMESTAMP,
    JSON,
    Table,
    Column,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List, TYPE_CHECKING

from ..database import Base

if TYPE_CHECKING:
    from .course import Course
    from .submission import Submission
    from .artifact import Artifact

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


class Assignment(Base):
    __tablename__ = "assignments"

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True)
    course_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("courses.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    deadline: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, nullable=True)
    max_grade: Mapped[dict] = mapped_column(JSON, nullable=False)

    course: Mapped["Course"] = relationship("Course", back_populates="assignments")
    submissions: Mapped[List["Submission"]] = relationship(
        "Submission", back_populates="assignment"
    )

    direct_artifacts: Mapped[List["Artifact"]] = relationship(
        "Artifact", back_populates="assignment"
    )

    artifacts: Mapped[List["Artifact"]] = relationship(
        "Artifact",
        secondary="assignment_artifacts",
        back_populates="assignments",
    )

    def __repr__(self) -> str:
        return (
            f"<Assignment id={self.id} title={self.title!r} course_id={self.course_id}>"
        )
