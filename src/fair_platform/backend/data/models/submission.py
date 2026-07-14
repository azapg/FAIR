from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy import String, ForeignKey, UUID as SAUUID, TIMESTAMP, Table, Column, Float, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from enum import Enum
from typing import Optional, List, TYPE_CHECKING

from ..database import Base

if TYPE_CHECKING:
    from .assignment import Assignment
    from .artifact import Artifact
    from .submission_event import SubmissionEvent
    from .submitter import Submitter
    from .user import User
    from .execution import Execution

submission_artifacts = Table(
    "submission_artifacts",
    Base.metadata,
    Column("id", SAUUID, primary_key=True, default=uuid4),
    Column(
        "submission_id",
        SAUUID,
        ForeignKey("submissions.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "artifact_id",
        SAUUID,
        ForeignKey("artifacts.id", ondelete="CASCADE"),
        nullable=False,
    ),
)


class SubmissionStatus(str, Enum):
    pending = "pending"
    submitted = "submitted"
    transcribing = "transcribing"
    transcribed = "transcribed"
    grading = "grading"
    graded = "graded"
    needs_review = "needs_review"
    returned = "returned"
    excused = "excused"
    failure = "failure"
    processing = "processing"


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True)
    assignment_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("assignments.id"), nullable=False
    )
    submitter_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("submitters.id"), nullable=False
    )
    created_by_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("users.id"), nullable=False
    )
    submitted_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, nullable=True)
    status: Mapped[SubmissionStatus] = mapped_column(
        String, nullable=False, default=SubmissionStatus.submitted
    )
    # DRAFT STATE (What the professor/AI works on)
    draft_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    draft_feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # PUBLISHED STATE (What the student sees)
    published_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    published_feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    returned_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, nullable=True)
    attempt_number: Mapped[int] = mapped_column(nullable=False, default=1)
    is_late: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    assignment: Mapped["Assignment"] = relationship(
        "Assignment", back_populates="submissions"
    )
    submitter: Mapped["Submitter"] = relationship("Submitter")
    created_by: Mapped["User"] = relationship(
        "User", back_populates="created_submissions", foreign_keys=[created_by_id]
    )
    artifacts: Mapped[List["Artifact"]] = relationship(
        "Artifact",
        secondary="submission_artifacts",
        back_populates="submissions",
    )

    events: Mapped[List["SubmissionEvent"]] = relationship(
        "SubmissionEvent",
        back_populates="submission",
        cascade="all, delete-orphan",
    )
    executions: Mapped[List["Execution"]] = relationship(
        "Execution",
        secondary="execution_submissions",
        back_populates="submissions",
    )
