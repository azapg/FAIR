from uuid import UUID
from sqlalchemy import String, Text, ForeignKey, UUID as _UUID, Boolean, true
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List, TYPE_CHECKING

from ..database import Base

if TYPE_CHECKING:
    from .user import User
    from .assignment import Assignment
    from .enrollment import Enrollment
    from .flow import Flow
    from .artifact import Artifact
    from .execution import Execution


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    instructor_id: Mapped[UUID] = mapped_column(
        _UUID, ForeignKey("users.id"), nullable=False
    )
    enrollment_code: Mapped[Optional[str]] = mapped_column(
        String(32), unique=True, nullable=True
    )
    is_enrollment_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true(), nullable=False
    )

    instructor: Mapped["User"] = relationship("User", back_populates="courses")
    assignments: Mapped[List["Assignment"]] = relationship(
        "Assignment", back_populates="course"
    )
    flows: Mapped[List["Flow"]] = relationship("Flow", back_populates="course")
    artifacts: Mapped[List["Artifact"]] = relationship(
        "Artifact", back_populates="course"
    )
    enrollments: Mapped[List["Enrollment"]] = relationship(
        "Enrollment", back_populates="course"
    )
    executions: Mapped[List["Execution"]] = relationship(
        "Execution", back_populates="course"
    )

    def __repr__(self) -> str:
        return f"<Course id={self.id} name={self.name!r} instructor_id={self.instructor_id}>"
