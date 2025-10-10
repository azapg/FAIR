from sqlalchemy import String, Text, JSON, PrimaryKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional, Dict, Any

from ..database import Base


class Plugin(Base):
    __tablename__ = "plugins"
    __table_args__ = (PrimaryKeyConstraint("id", "hash"),)

    id: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    author: Mapped[Optional[str]] = mapped_column(String, nullable=False)
    author_email: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    version: Mapped[Optional[str]] = mapped_column(String, nullable=False)
    hash: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    meta: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    type: Mapped[str] = mapped_column(String, nullable=False)
    settings_schema: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    def __repr__(self) -> str:
        return f"<Plugin id={self.id} hash={self.hash} name={self.name} source={self.source}>"
