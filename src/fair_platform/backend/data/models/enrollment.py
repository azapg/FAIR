from uuid import UUID
from datetime import datetime

from sqlalchemy import ForeignKey, UUID as SAUUID, TIMESTAMP, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

from ..database import Base

if TYPE_CHECKING:
    from .user import User
    from .course import Course


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (
        UniqueConstraint("user_id", "course_id", name="uq_enrollment_user_course"),
    )

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("users.id"), nullable=False
    )
    course_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("courses.id"), nullable=False
    )
    enrolled_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, nullable=False, default=datetime.utcnow
    )

    user: Mapped["User"] = relationship("User", back_populates="enrollments")
    course: Mapped["Course"] = relationship("Course", back_populates="enrollments")

    def __repr__(self) -> str:
        return f"<Enrollment id={self.id} user_id={self.user_id} course_id={self.course_id}>"
