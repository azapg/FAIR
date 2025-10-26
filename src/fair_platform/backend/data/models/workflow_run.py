from uuid import UUID
from datetime import datetime
from sqlalchemy import String, ForeignKey, UUID as SAUUID, TIMESTAMP, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from enum import Enum
from typing import Optional, List, TYPE_CHECKING

from ..database import Base

if TYPE_CHECKING:
    from .submission import Submission
    from .submission_result import SubmissionResult


class WorkflowRunStatus(str, Enum):
    pending = "pending"
    running = "running"
    success = "success"
    failure = "failure"
    cancelled = "cancelled"


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True)
    workflow_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("workflows.id"), nullable=False
    )
    run_by: Mapped[UUID] = mapped_column(SAUUID, ForeignKey("users.id"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, nullable=True)
    status: Mapped[WorkflowRunStatus] = mapped_column(String, nullable=False)
    logs: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    workflow = relationship("Workflow", back_populates="runs")
    submissions: Mapped[List["Submission"]] = relationship(
        "Submission",
        secondary="submission_workflow_runs",
        back_populates="runs",
    )
    runner = relationship("User", back_populates="workflow_runs")
    results: Mapped[List["SubmissionResult"]] = relationship(
        "SubmissionResult", back_populates="workflow_run", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<WorkflowRun id={self.id} workflow_id={self.workflow_id} status={self.status}>"
