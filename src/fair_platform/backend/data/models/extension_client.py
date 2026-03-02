from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from .types import json_document_type


class ExtensionClient(Base):
    __tablename__ = "extension_clients"

    extension_id: Mapped[str] = mapped_column(String, primary_key=True)
    secret_hash: Mapped[str] = mapped_column(String, nullable=False)
    scopes: Mapped[list[str]] = mapped_column(
        json_document_type(),
        nullable=False,
        default=list,
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    def __repr__(self) -> str:
        return f"<ExtensionClient extension_id={self.extension_id!r} enabled={self.enabled}>"
