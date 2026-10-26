"""Login identities are separate from organization-scoped LMS identifiers."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy import UUID as SAUUID
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ExternalIdentity(Base):
    __tablename__ = "external_identities"
    __table_args__ = (
        UniqueConstraint("issuer", "subject", name="uq_external_identity_subject"),
        UniqueConstraint(
            "user_id", "connection_key", name="uq_external_identity_user_connection"
        ),
    )

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    connection_key: Mapped[str] = mapped_column(String(128), nullable=False)
    issuer: Mapped[str] = mapped_column(String(512), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    last_login_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )


class OIDCTransaction(Base):
    __tablename__ = "oidc_transactions"
    __table_args__ = (
        CheckConstraint(
            "purpose IN ('login', 'link')", name="ck_oidc_transaction_purpose"
        ),
        CheckConstraint(
            "(purpose = 'login' AND user_id IS NULL) OR (purpose = 'link' AND user_id IS NOT NULL)",
            name="ck_oidc_transaction_user",
        ),
    )

    state_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    browser_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    connection_key: Mapped[str] = mapped_column(String(128), nullable=False)
    purpose: Mapped[str] = mapped_column(String(16), nullable=False)
    nonce: Mapped[str] = mapped_column(String(128), nullable=False)
    code_verifier: Mapped[str] = mapped_column(String(128), nullable=False)
    remember_me: Mapped[bool] = mapped_column(nullable=False, default=False)
    user_id: Mapped[UUID | None] = mapped_column(
        SAUUID, ForeignKey("users.id", ondelete="CASCADE")
    )
    invite_hash: Mapped[str | None] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
