from uuid import UUID
from sqlalchemy import String, Text, ForeignKey, UUID as _UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List, TYPE_CHECKING

from ..database import Base

if TYPE_CHECKING:
    from .user import User
    from .assignment import Assignment
    from .workflow import Workflow
    from .artifact import Artifact


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    instructor_id: Mapped[UUID] = mapped_column(
        _UUID, ForeignKey("users.id"), nullable=False
    )

    instructor: Mapped["User"] = relationship("User", back_populates="courses")
    assignments: Mapped[List["Assignment"]] = relationship(
        "Assignment", back_populates="course"
    )
    workflows: Mapped[List["Workflow"]] = relationship(
        "Workflow", back_populates="course"
    )
    artifacts: Mapped[List["Artifact"]] = relationship(
        "Artifact", back_populates="course"
    )

    def __repr__(self) -> str:
        return f"<Course id={self.id} name={self.name!r} instructor_id={self.instructor_id}>"
