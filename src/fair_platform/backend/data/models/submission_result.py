from uuid import UUID, uuid4
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import UUID as SAUUID, ForeignKey, JSON, TIMESTAMP, Float, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

if TYPE_CHECKING:
    from .submission import Submission
    from .workflow_run import WorkflowRun


class SubmissionResult(Base):
    __tablename__ = "submission_results"

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True, default=uuid4)
    submission_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False
    )
    workflow_run_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False
    )

    # Transcription
    transcription: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    transcription_confidence: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )
    transcribed_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP, nullable=True
    )

    # Grading
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    grading_meta: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    graded_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, nullable=True)

    # Relationships
    submission: Mapped["Submission"] = relationship("Submission", back_populates="results")
    workflow_run: Mapped["WorkflowRun"] = relationship(
        "WorkflowRun", back_populates="results"
    )

    def __repr__(self) -> str:
        return (
            f"<SubmissionResult id={self.id} submission_id={self.submission_id} "
            f"run_id={self.workflow_run_id}>"
        )
