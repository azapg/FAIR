from uuid import UUID, uuid4
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, ForeignKey, UUID as SAUUID, TIMESTAMP, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

if TYPE_CHECKING:
    from .user import User


class Rubric(Base):
    __tablename__ = "rubrics"

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_by_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("users.id"), nullable=False
    )
    content: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, nullable=False, default=datetime.utcnow
    )

    creator: Mapped["User"] = relationship("User", back_populates="rubrics")

    def __repr__(self) -> str:
        return f"<Rubric id={self.id} name={self.name!r}>"
