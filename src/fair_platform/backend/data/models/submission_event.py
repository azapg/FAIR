from uuid import UUID, uuid4
from datetime import datetime
from enum import Enum
from typing import Optional, TYPE_CHECKING

from sqlalchemy import (
    UUID as SAUUID,
    ForeignKey,
    TIMESTAMP,
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from ..database import Base

if TYPE_CHECKING:
    from .submission import Submission
    from .user import User
    from .workflow_run import WorkflowRun


class SubmissionEventType(str, Enum):
    AI_GRADED = "AI_GRADED"
    MANUAL_EDIT = "MANUAL_EDIT"
    RETURNED_TO_STUDENT = "RETURNED_TO_STUDENT"


class SubmissionEvent(Base):
    __tablename__ = "submission_events"

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True, default=uuid4)
    submission_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[SubmissionEventType] = mapped_column(
        SAEnum(SubmissionEventType, name="submissioneventtype"), nullable=False
    )
    actor_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID, ForeignKey("users.id"), nullable=True
    )
    workflow_run_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID, ForeignKey("workflow_runs.id"), nullable=True
    )
    details: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    submission: Mapped["Submission"] = relationship(
        "Submission", back_populates="events"
    )
    actor: Mapped[Optional["User"]] = relationship("User")
    workflow_run: Mapped[Optional["WorkflowRun"]] = relationship("WorkflowRun")
