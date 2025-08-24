from enum import Enum
from uuid import UUID

from pydantic import EmailStr
from sqlalchemy import String, UUID as SAUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, TYPE_CHECKING

from ..database import Base

if TYPE_CHECKING:
    from .course import Course
    from .workflow import Workflow
    from .workflow_run import WorkflowRun


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

    # Relationship to courses where this user is the instructor
    courses: Mapped[List["Course"]] = relationship("Course", back_populates="instructor")
    created_workflows: Mapped[List["Workflow"]] = relationship("Workflow", back_populates="creator")
    workflow_runs: Mapped[List["WorkflowRun"]] = relationship("WorkflowRun", back_populates="runner")

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} role={self.role}>"
