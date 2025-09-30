from enum import Enum
from uuid import UUID
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import Text, JSON, UUID as SAUUID, String, TIMESTAMP, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

if TYPE_CHECKING:
    from .assignment import Assignment
    from .submission import Submission
    from .user import User
    from .course import Course


class ArtifactStatus(str, Enum):
    pending = "pending"          # Uploaded but not attached
    attached = "attached"        # Linked to assignment/submission
    orphaned = "orphaned"        # Parent deleted but artifact remains
    archived = "archived"        # Soft deleted


class AccessLevel(str, Enum):
    private = "private"
    course = "course"
    assignment = "assignment"
    public = "public"


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    artifact_type: Mapped[str] = mapped_column("type", Text, nullable=False)
    mime: Mapped[str] = mapped_column(Text, nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    storage_type: Mapped[str] = mapped_column(Text, nullable=False)
    meta: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, default=datetime.now, onupdate=datetime.now)
    creator_id: Mapped[UUID] = mapped_column(SAUUID, ForeignKey("users.id"), nullable=False)
    status: Mapped[ArtifactStatus] = mapped_column(String, nullable=False, default=ArtifactStatus.pending)
    access_level: Mapped[AccessLevel] = mapped_column(String, nullable=False, default=AccessLevel.private)
    
    course_id: Mapped[Optional[UUID]] = mapped_column(SAUUID, ForeignKey("courses.id"), nullable=True)
    assignment_id: Mapped[Optional[UUID]] = mapped_column(SAUUID, ForeignKey("assignments.id"), nullable=True)

    creator: Mapped["User"] = relationship("User", back_populates="created_artifacts")
    course: Mapped[Optional["Course"]] = relationship("Course", back_populates="artifacts")
    assignment: Mapped[Optional["Assignment"]] = relationship("Assignment", back_populates="direct_artifacts")

    assignments: Mapped[List["Assignment"]] = relationship(
        "Assignment",
        secondary="assignment_artifacts",
        back_populates="artifacts",
        viewonly=False,
    )

    submissions: Mapped[List["Submission"]] = relationship(
        "Submission",
        secondary="submission_artifacts",
        back_populates="artifacts",
        viewonly=False,
    )

    def __repr__(self) -> str:
        return (
            f"<Artifact id={self.id} title={self.title!r} "
            f"type={self.artifact_type!r} mime={self.mime!r}>"
        )


__all__ = ["Artifact", "ArtifactStatus", "AccessLevel"]
