from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy import String, ForeignKey, UUID as SAUUID, TIMESTAMP, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from enum import Enum
from typing import Optional, List, TYPE_CHECKING

from ..database import Base

if TYPE_CHECKING:
    from .assignment import Assignment
    from .workflow_run import WorkflowRun
    from .artifact import Artifact
    from .submission_result import SubmissionResult
    from .submitter import Submitter
    from .user import User

submission_workflow_runs = Table(
    "submission_workflow_runs",
    Base.metadata,
    Column(
        "submission_id",
        SAUUID,
        ForeignKey("submissions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "workflow_run_id",
        SAUUID,
        ForeignKey("workflow_runs.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

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
        String, nullable=False, default=SubmissionStatus.pending
    )
    official_run_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID, ForeignKey("workflow_runs.id"), nullable=True
    )

    assignment: Mapped["Assignment"] = relationship(
        "Assignment", back_populates="submissions"
    )
    submitter: Mapped["Submitter"] = relationship("Submitter")
    created_by: Mapped["User"] = relationship(
        "User", back_populates="created_submissions", foreign_keys=[created_by_id]
    )
    # Many-to-many: a submission can have multiple runs linked
    runs: Mapped[List["WorkflowRun"]] = relationship(
        "WorkflowRun",
        secondary="submission_workflow_runs",
        back_populates="submissions",
    )
    # The official workflow run for this submission (must be one of `runs` at the app level)
    official_run: Mapped[Optional["WorkflowRun"]] = relationship(
        "WorkflowRun",
        primaryjoin="Submission.official_run_id == WorkflowRun.id",
        foreign_keys="Submission.official_run_id",
        uselist=False,
        post_update=True,
    )
    artifacts: Mapped[List["Artifact"]] = relationship(
        "Artifact",
        secondary="submission_artifacts",
        back_populates="submissions",
    )

    # Processing results (per workflow run)
    results: Mapped[List["SubmissionResult"]] = relationship(
        "SubmissionResult",
        back_populates="submission",
        cascade="all, delete-orphan",
    )
