from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Column, ForeignKey, String, Table, Text, TIMESTAMP, UUID as SAUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

if TYPE_CHECKING:
    from .course import Course
    from .legacy_artifact import Artifact
    from .submission import Submission
    from .user import User


course_post_artifacts = Table(
    "course_post_artifacts",
    Base.metadata,
    Column("post_id", SAUUID, ForeignKey("course_posts.id", ondelete="CASCADE"), primary_key=True),
    Column("artifact_id", SAUUID, ForeignKey("artifacts.id", ondelete="CASCADE"), primary_key=True),
)


class CoursePostKind(str, Enum):
    announcement = "announcement"
    material = "material"


class CoursePost(Base):
    __tablename__ = "course_posts"

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True)
    course_id: Mapped[UUID] = mapped_column(SAUUID, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    author_id: Mapped[UUID] = mapped_column(SAUUID, ForeignKey("users.id"), nullable=False)
    kind: Mapped[CoursePostKind] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    course: Mapped["Course"] = relationship("Course")
    author: Mapped["User"] = relationship("User")
    artifacts: Mapped[list["Artifact"]] = relationship("Artifact", secondary=course_post_artifacts)
    comments: Mapped[list["CourseComment"]] = relationship(
        "CourseComment", back_populates="post", cascade="all, delete-orphan"
    )


class CourseComment(Base):
    __tablename__ = "course_comments"

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True)
    post_id: Mapped[UUID] = mapped_column(SAUUID, ForeignKey("course_posts.id", ondelete="CASCADE"), nullable=False)
    author_id: Mapped[UUID] = mapped_column(SAUUID, ForeignKey("users.id"), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    post: Mapped[CoursePost] = relationship("CoursePost", back_populates="comments")
    author: Mapped["User"] = relationship("User")


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(SAUUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    link: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    read_at: Mapped[datetime | None] = mapped_column(TIMESTAMP, nullable=True)


class SubmissionComment(Base):
    __tablename__ = "submission_comments"

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True)
    submission_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False
    )
    author_id: Mapped[UUID] = mapped_column(SAUUID, ForeignKey("users.id"), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    submission: Mapped["Submission"] = relationship("Submission")
    author: Mapped["User"] = relationship("User")


__all__ = [
    "CourseComment",
    "CoursePost",
    "CoursePostKind",
    "Notification",
    "SubmissionComment",
    "course_post_artifacts",
]
