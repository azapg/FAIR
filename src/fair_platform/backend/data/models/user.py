from enum import Enum
from uuid import UUID
from typing import Optional

from pydantic import EmailStr
from sqlalchemy import String, UUID as SAUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, TYPE_CHECKING

from ..database import Base

if TYPE_CHECKING:
    from .course import Course
    from .workflow import Workflow
    from .workflow_run import WorkflowRun
    from .artifact import Artifact
    from .submitter import Submitter
    from .submission import Submission


class UserRole(str, Enum):
    professor = "professor"
    student = "student"
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[EmailStr] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    password_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Relationship to courses where this user is the instructor
    courses: Mapped[List["Course"]] = relationship(
        "Course", back_populates="instructor"
    )
    created_workflows: Mapped[List["Workflow"]] = relationship(
        "Workflow", back_populates="creator"
    )
    workflow_runs: Mapped[List["WorkflowRun"]] = relationship(
        "WorkflowRun", back_populates="runner"
    )
    created_artifacts: Mapped[List["Artifact"]] = relationship(
        "Artifact", back_populates="creator"
    )
    # Relationship to submitters that link to this user account
    submitters: Mapped[List["Submitter"]] = relationship(
        "Submitter", back_populates="user"
    )
    # Relationship to submissions created by this user (professor/admin)
    created_submissions: Mapped[List["Submission"]] = relationship(
        "Submission", back_populates="created_by", foreign_keys="Submission.created_by_id"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} role={self.role}>"
