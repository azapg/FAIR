from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UUID as SAUUID,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .types import json_document_type


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ItemCompletionStatus(str, Enum):
    not_started = "not_started"
    in_progress = "in_progress"
    completed = "completed"


class CompletionRule(Base):
    """One ordered condition that contributes to a course item's completion."""

    __tablename__ = "completion_rules"
    __table_args__ = (
        ForeignKeyConstraint(
            ["course_item_id", "course_id"],
            ["course_items.id", "course_items.course_id"],
            name="fk_completion_rules_item_course",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "course_item_id", "position", name="uq_completion_rules_item_position"
        ),
        CheckConstraint(
            "position >= 0", name="ck_completion_rules_position_non_negative"
        ),
        Index("ix_completion_rules_course_type", "course_id", "rule_type"),
    )

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True, default=uuid4)
    course_id: Mapped[UUID] = mapped_column(SAUUID, nullable=False)
    course_item_id: Mapped[UUID] = mapped_column(SAUUID, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    rule_type: Mapped[str] = mapped_column(String(64), nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(
        json_document_type(), nullable=False, default=dict
    )
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now, onupdate=_utc_now
    )

    course_item = relationship("CourseItem")


class UserItemCompletion(Base):
    """The current completion projection for an enrolled learner."""

    __tablename__ = "user_item_completions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["course_item_id", "course_id"],
            ["course_items.id", "course_items.course_id"],
            name="fk_user_item_completions_item_course",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["user_id", "course_id"],
            ["enrollments.user_id", "enrollments.course_id"],
            name="fk_user_item_completions_enrollment",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "course_item_id",
            "user_id",
            name="uq_user_item_completions_item_user",
        ),
        CheckConstraint(
            "status IN ('not_started', 'in_progress', 'completed')",
            name="ck_user_item_completions_status",
        ),
        CheckConstraint(
            "(status = 'completed' AND completed_at IS NOT NULL) OR "
            "(status != 'completed' AND completed_at IS NULL)",
            name="ck_user_item_completions_timestamp",
        ),
        CheckConstraint(
            "(source_type IS NULL AND source_id IS NULL) OR "
            "(source_type IS NOT NULL AND source_id IS NOT NULL)",
            name="ck_user_item_completions_source_pair",
        ),
        Index("ix_user_item_completions_course_user", "course_id", "user_id"),
        Index("ix_user_item_completions_course_status", "course_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True, default=uuid4)
    course_id: Mapped[UUID] = mapped_column(SAUUID, nullable=False)
    course_item_id: Mapped[UUID] = mapped_column(SAUUID, nullable=False)
    user_id: Mapped[UUID] = mapped_column(SAUUID, nullable=False)
    status: Mapped[ItemCompletionStatus] = mapped_column(
        String(32), nullable=False, default=ItemCompletionStatus.not_started
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    source_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    source_id: Mapped[Optional[UUID]] = mapped_column(SAUUID, nullable=True)
    evidence: Mapped[dict[str, Any]] = mapped_column(
        json_document_type(), nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now, onupdate=_utc_now
    )

    course_item = relationship("CourseItem")


class AvailabilityRule(Base):
    """One ordered prerequisite/availability predicate for a course item."""

    __tablename__ = "availability_rules"
    __table_args__ = (
        ForeignKeyConstraint(
            ["course_item_id", "course_id"],
            ["course_items.id", "course_items.course_id"],
            name="fk_availability_rules_item_course",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "course_item_id", "position", name="uq_availability_rules_item_position"
        ),
        CheckConstraint(
            "position >= 0", name="ck_availability_rules_position_non_negative"
        ),
        Index("ix_availability_rules_course_type", "course_id", "rule_type"),
    )

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True, default=uuid4)
    course_id: Mapped[UUID] = mapped_column(SAUUID, nullable=False)
    course_item_id: Mapped[UUID] = mapped_column(SAUUID, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    rule_type: Mapped[str] = mapped_column(String(64), nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(
        json_document_type(), nullable=False, default=dict
    )
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now, onupdate=_utc_now
    )

    course_item = relationship("CourseItem")


__all__ = [
    "AvailabilityRule",
    "CompletionRule",
    "ItemCompletionStatus",
    "UserItemCompletion",
]
