from datetime import datetime
from uuid import UUID
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Boolean, UUID as SAUUID, TIMESTAMP, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

if TYPE_CHECKING:
    from .user import User


class Submitter(Base):
    """
    Represents someone who submitted work - can be either:
    - A real student with a User account (user_id is set)
    - A synthetic/research-generated identity (user_id is None, is_synthetic=True)
    """
    __tablename__ = "submitters"

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    user_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID, ForeignKey("users.id"), nullable=True
    )
    is_synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, nullable=False, default=datetime.utcnow
    )

    # Relationship to the user account (if this is a real student)
    user: Mapped[Optional["User"]] = relationship("User", back_populates="submitters")

    def __repr__(self) -> str:
        return f"<Submitter id={self.id} name={self.name!r} is_synthetic={self.is_synthetic}>"
