from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    false,
    ForeignKey,
    func,
    Index,
    Integer,
    SmallInteger,
    String,
    UUID as SAUUID,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AdmissionMode(str, Enum):
    open = "open"
    allowlist = "allowlist"
    invite_only = "invite_only"


class AdmissionRuleKind(str, Enum):
    email = "email"
    domain = "domain"


class AICapabilityClassification(str, Enum):
    unmetered = "unmetered"
    ai = "ai"


class AIEntitlementState(str, Enum):
    disabled = "disabled"
    limited = "limited"
    unlimited = "unlimited"


class PlatformPolicy(Base):
    __tablename__ = "platform_policies"
    __table_args__ = (
        CheckConstraint("id = 1", name="ck_platform_policy_singleton"),
        CheckConstraint(
            "admission_mode IN ('open', 'allowlist', 'invite_only')",
            name="ck_platform_policy_admission_mode",
        ),
    )

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, default=1)
    admission_mode: Mapped[AdmissionMode] = mapped_column(
        String(32),
        nullable=False,
        default=AdmissionMode.open,
        server_default=AdmissionMode.open.value,
    )
    ai_controls_enabled: Mapped[bool] = mapped_column(
        nullable=False, default=False, server_default=false()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
        onupdate=utc_now,
    )
    updated_by_user_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class AdmissionRule(Base):
    __tablename__ = "admission_rules"
    __table_args__ = (
        UniqueConstraint("kind", "normalized_value", name="uq_admission_rule_value"),
        CheckConstraint("kind IN ('email', 'domain')", name="ck_admission_rule_kind"),
        Index("ix_admission_rules_kind_value", "kind", "normalized_value"),
    )

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True, default=uuid4)
    kind: Mapped[AdmissionRuleKind] = mapped_column(String(16), nullable=False)
    normalized_value: Mapped[str] = mapped_column(String(320), nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )


class RegistrationInvite(Base):
    __tablename__ = "registration_invites"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_registration_invites_token_hash"),
        Index("ix_registration_invites_email", "normalized_email", "expires_at"),
    )

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True, default=uuid4)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    normalized_email: Mapped[str] = mapped_column(String(320), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    redeemed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    redeemed_by_user_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by_user_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )


class AICapabilityPolicy(Base):
    __tablename__ = "ai_capability_policies"
    __table_args__ = (
        CheckConstraint("cost_units >= 0", name="ck_ai_capability_cost_nonnegative"),
        CheckConstraint(
            "(classification = 'unmetered' AND cost_units = 0) OR "
            "(classification = 'ai' AND cost_units > 0)",
            name="ck_ai_capability_classification_cost",
        ),
        CheckConstraint(
            "classification IN ('unmetered', 'ai')",
            name="ck_ai_capability_classification",
        ),
    )

    capability_definition_id: Mapped[UUID] = mapped_column(
        SAUUID,
        ForeignKey("capability_definitions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    classification: Mapped[AICapabilityClassification] = mapped_column(
        String(16), nullable=False
    )
    cost_units: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
        onupdate=utc_now,
    )
    updated_by_user_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    capability = relationship("CapabilityDefinition")


class AIEntitlement(Base):
    __tablename__ = "ai_entitlements"
    __table_args__ = (
        CheckConstraint("used_units >= 0", name="ck_ai_entitlement_used_nonnegative"),
        CheckConstraint(
            "monthly_limit_units IS NULL OR monthly_limit_units > 0",
            name="ck_ai_entitlement_limit_positive",
        ),
        CheckConstraint(
            "(state = 'limited' AND monthly_limit_units IS NOT NULL) OR "
            "(state != 'limited' AND monthly_limit_units IS NULL)",
            name="ck_ai_entitlement_state_limit",
        ),
        CheckConstraint(
            "state IN ('disabled', 'limited', 'unlimited')",
            name="ck_ai_entitlement_state",
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    state: Mapped[AIEntitlementState] = mapped_column(
        String(16),
        nullable=False,
        default=AIEntitlementState.disabled,
        server_default=AIEntitlementState.disabled.value,
    )
    monthly_limit_units: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    used_units: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
        onupdate=utc_now,
    )
    updated_by_user_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    user = relationship("User", foreign_keys=[user_id])


class AIUsageCharge(Base):
    __tablename__ = "ai_usage_charges"
    __table_args__ = (
        CheckConstraint("units > 0", name="ck_ai_usage_charge_units_positive"),
        UniqueConstraint("execution_id", name="uq_ai_usage_charges_execution_id"),
        Index("ix_ai_usage_user_period", "user_id", "period_start", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True, default=uuid4)
    execution_id: Mapped[UUID] = mapped_column(
        SAUUID,
        ForeignKey("executions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    capability_definition_id: Mapped[UUID] = mapped_column(
        SAUUID,
        ForeignKey("capability_definitions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    units: Mapped[int] = mapped_column(Integer, nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )

    execution = relationship("Execution")
    user = relationship("User")
    capability = relationship("CapabilityDefinition")


__all__ = [
    "AdmissionMode",
    "AdmissionRule",
    "AdmissionRuleKind",
    "AICapabilityClassification",
    "AICapabilityPolicy",
    "AIEntitlement",
    "AIEntitlementState",
    "AIUsageCharge",
    "PlatformPolicy",
    "RegistrationInvite",
]
