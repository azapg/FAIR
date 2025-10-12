from uuid import UUID
from datetime import datetime
from sqlalchemy import String, Text, ForeignKey, UUID as SAUUID, TIMESTAMP, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List, TYPE_CHECKING

from ..database import Base

if TYPE_CHECKING:
    from .course import Course
    from .user import User
    from .workflow_run import WorkflowRun


class Workflow(Base):
    __tablename__ = "workflows"

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True)
    course_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("courses.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, nullable=True)
    # TODO: What an ugly schema, needs refactoring.
    transcriber_plugin_id: Mapped[str] = mapped_column(
        Text, ForeignKey("plugins.id"), nullable=True
    )
    transcriber_settings: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    grader_plugin_id: Mapped[str] = mapped_column(
        Text, ForeignKey("plugins.id"), nullable=True
    )
    grader_settings: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    validator_plugin_id: Mapped[str] = mapped_column(
        Text, ForeignKey("plugins.id"), nullable=True
    )
    validator_settings: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    course: Mapped["Course"] = relationship("Course", back_populates="workflows")
    creator: Mapped["User"] = relationship("User", back_populates="created_workflows")
    runs: Mapped[List["WorkflowRun"]] = relationship(
        "WorkflowRun", back_populates="workflow"
    )

    def __repr__(self) -> str:
        return f"<Workflow id={self.id} name={self.name!r} course_id={self.course_id} created_by={self.created_by}>"
