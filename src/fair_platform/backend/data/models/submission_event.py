from uuid import UUID, uuid4
from datetime import datetime
from enum import Enum
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, ForeignKey, UUID as SAUUID, TIMESTAMP, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

if TYPE_CHECKING:
    from .submission import Submission
    from .user import User
    from .workflow_run import WorkflowRun


class SubmissionEventType(str, Enum):
    ai_graded = "ai_graded"
    manual_edit = "manual_edit"
    returned = "returned"
    status_changed = "status_changed"


class SubmissionEvent(Base):
    __tablename__ = "submission_events"

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True, default=uuid4)
    submission_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[SubmissionEventType] = mapped_column(String, nullable=False)
    actor_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID, ForeignKey("users.id"), nullable=True
    )
    workflow_run_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID, ForeignKey("workflow_runs.id"), nullable=True
    )
    details: Mapped[Optional[dict]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, nullable=False, default=datetime.utcnow
    )

    submission: Mapped["Submission"] = relationship(
        "Submission", back_populates="events"
    )
    actor: Mapped[Optional["User"]] = relationship("User")
    workflow_run: Mapped[Optional["WorkflowRun"]] = relationship("WorkflowRun")

    def __repr__(self) -> str:
        return (
            f"<SubmissionEvent id={self.id} submission_id={self.submission_id} "
            f"type={self.event_type}>"
        )
