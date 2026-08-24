from datetime import datetime
from uuid import UUID
from sqlalchemy import (
    Boolean,
    ForeignKey,
    String,
    Text,
    TIMESTAMP,
    UUID as _UUID,
    UniqueConstraint,
    false,
    true,
)
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
    from .lms_content import CourseSection
    from .lms_events import ActivityEvent, CalendarEvent
    from .lms_gradebook import GradeCategory, GradeItem
    from .lms_organization import CourseGroup, Organization


class Course(Base):
    __tablename__ = "courses"
    __table_args__ = (
        UniqueConstraint("id", "organization_id", name="uq_courses_id_organization"),
    )

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    instructor_id: Mapped[UUID] = mapped_column(
        _UUID, ForeignKey("users.id"), nullable=False
    )
    organization_id: Mapped[Optional[UUID]] = mapped_column(
        _UUID,
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
    )
    enrollment_code: Mapped[Optional[str]] = mapped_column(
        String(32), unique=True, nullable=True
    )
    is_enrollment_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true(), nullable=False
    )
    section: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    term: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    is_archived: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), nullable=False
    )
    copied_from_id: Mapped[Optional[UUID]] = mapped_column(
        _UUID, ForeignKey("courses.id", ondelete="RESTRICT"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
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
    organization: Mapped[Optional["Organization"]] = relationship(
        "Organization", back_populates="courses"
    )
    sections: Mapped[List["CourseSection"]] = relationship(
        "CourseSection",
        back_populates="course",
        cascade="all, delete-orphan",
        order_by="CourseSection.position",
    )
    grade_categories: Mapped[List["GradeCategory"]] = relationship(
        "GradeCategory",
        back_populates="course",
        cascade="all, delete-orphan",
        order_by="GradeCategory.position",
    )
    grade_items: Mapped[List["GradeItem"]] = relationship(
        "GradeItem",
        back_populates="course",
        cascade="all, delete-orphan",
        order_by="GradeItem.position",
    )
    groups: Mapped[List["CourseGroup"]] = relationship(
        "CourseGroup", back_populates="course", cascade="all, delete-orphan"
    )
    calendar_events: Mapped[List["CalendarEvent"]] = relationship(
        "CalendarEvent", back_populates="course", cascade="all, delete-orphan"
    )
    activity_events: Mapped[List["ActivityEvent"]] = relationship(
        "ActivityEvent", back_populates="course"
    )

    def __repr__(self) -> str:
        return f"<Course id={self.id} name={self.name!r} instructor_id={self.instructor_id}>"
