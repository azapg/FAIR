from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UUID as SAUUID,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from ..database import Base
from .types import json_document_type

if TYPE_CHECKING:
    from .course import Course
    from .user import User


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _decimal_points(value: Any, *, positive: bool, field_name: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise ValueError(f"{field_name} must be a numeric points value")
    try:
        points = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field_name} must be a finite points value") from exc
    if not points.is_finite() or (points <= 0 if positive else points < 0):
        qualifier = "positive" if positive else "non-negative"
        raise ValueError(f"{field_name} must be a {qualifier} points value")
    return points


class GradeAggregationStrategy(str, Enum):
    sum = "sum"
    weighted_mean = "weighted_mean"
    simple_mean = "simple_mean"
    highest = "highest"


class GradeEntryStatus(str, Enum):
    graded = "graded"
    missing = "missing"
    excused = "excused"


class GradeReleaseState(str, Enum):
    unreleased = "unreleased"
    released = "released"


class GradeCategory(Base):
    __tablename__ = "grade_categories"
    __table_args__ = (
        ForeignKeyConstraint(
            ["parent_category_id", "course_id"],
            ["grade_categories.id", "grade_categories.course_id"],
            name="fk_grade_categories_parent_course",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "course_id", "position", name="uq_grade_categories_course_position"
        ),
        UniqueConstraint("id", "course_id", name="uq_grade_categories_id_course"),
        CheckConstraint(
            "position >= 0", name="ck_grade_categories_position_non_negative"
        ),
        CheckConstraint(
            "weight IS NULL OR weight >= 0", name="ck_grade_categories_weight"
        ),
        CheckConstraint(
            "aggregation_strategy IN "
            "('sum', 'weighted_mean', 'simple_mean', 'highest')",
            name="ck_grade_categories_aggregation_strategy",
        ),
        Index("ix_grade_categories_course_parent", "course_id", "parent_category_id"),
    )

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True, default=uuid4)
    course_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False
    )
    parent_category_id: Mapped[Optional[UUID]] = mapped_column(SAUUID, nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    aggregation_strategy: Mapped[GradeAggregationStrategy] = mapped_column(
        String(32), nullable=False, default=GradeAggregationStrategy.sum
    )
    weight: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 6), nullable=True)
    calculation_policy: Mapped[dict[str, Any]] = mapped_column(
        json_document_type(), nullable=False, default=dict
    )
    copied_from_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID, ForeignKey("grade_categories.id", ondelete="RESTRICT"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now, onupdate=_utc_now
    )

    course: Mapped["Course"] = relationship("Course", back_populates="grade_categories")
    parent: Mapped[Optional["GradeCategory"]] = relationship(
        "GradeCategory",
        remote_side=[id, course_id],
        foreign_keys=[parent_category_id, course_id],
        overlaps="course,grade_categories",
    )
    copied_from: Mapped[Optional["GradeCategory"]] = relationship(
        "GradeCategory", remote_side=[id], foreign_keys=[copied_from_id]
    )
    items: Mapped[list["GradeItem"]] = relationship(
        "GradeItem",
        back_populates="category",
        order_by="GradeItem.position",
        overlaps="grade_items",
    )

    @validates("weight")
    def validate_weight(self, _key: str, value: Any) -> Optional[Decimal]:
        if value is None:
            return None
        return _decimal_points(value, positive=False, field_name="weight")


class GradeItem(Base):
    __tablename__ = "grade_items"
    __table_args__ = (
        ForeignKeyConstraint(
            ["category_id", "course_id"],
            ["grade_categories.id", "grade_categories.course_id"],
            name="fk_grade_items_category_course",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "course_id", "position", name="uq_grade_items_course_position"
        ),
        UniqueConstraint("id", "course_id", name="uq_grade_items_id_course"),
        UniqueConstraint(
            "course_id",
            "source_type",
            "source_id",
            name="uq_grade_items_course_source",
        ),
        CheckConstraint("position >= 0", name="ck_grade_items_position_non_negative"),
        CheckConstraint("max_points > 0", name="ck_grade_items_max_points_positive"),
        CheckConstraint("weight IS NULL OR weight >= 0", name="ck_grade_items_weight"),
        CheckConstraint(
            "(source_type IS NULL AND source_id IS NULL) OR "
            "(source_type IS NOT NULL AND source_id IS NOT NULL)",
            name="ck_grade_items_source_pair",
        ),
        Index("ix_grade_items_course_category", "course_id", "category_id"),
        Index("ix_grade_items_source", "source_type", "source_id"),
    )

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True, default=uuid4)
    course_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False
    )
    category_id: Mapped[Optional[UUID]] = mapped_column(SAUUID, nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    max_points: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    weight: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 6), nullable=True)
    calculation_policy: Mapped[dict[str, Any]] = mapped_column(
        json_document_type(), nullable=False, default=dict
    )
    release_policy: Mapped[dict[str, Any]] = mapped_column(
        json_document_type(), nullable=False, default=dict
    )
    source_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    source_id: Mapped[Optional[UUID]] = mapped_column(SAUUID, nullable=True)
    copied_from_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID, ForeignKey("grade_items.id", ondelete="RESTRICT"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now, onupdate=_utc_now
    )

    course: Mapped["Course"] = relationship(
        "Course", back_populates="grade_items", overlaps="items"
    )
    category: Mapped[Optional[GradeCategory]] = relationship(
        "GradeCategory",
        back_populates="items",
        foreign_keys=[category_id, course_id],
        overlaps="course,grade_items",
    )
    copied_from: Mapped[Optional["GradeItem"]] = relationship(
        "GradeItem", remote_side=[id], foreign_keys=[copied_from_id]
    )
    entries: Mapped[list["GradeEntry"]] = relationship(
        "GradeEntry", back_populates="grade_item", cascade="all, delete-orphan"
    )

    @validates("max_points")
    def validate_max_points(self, _key: str, value: Any) -> Decimal:
        return _decimal_points(value, positive=True, field_name="max_points")

    @validates("weight")
    def validate_weight(self, _key: str, value: Any) -> Optional[Decimal]:
        if value is None:
            return None
        return _decimal_points(value, positive=False, field_name="weight")


class GradeEntry(Base):
    """The current release-aware points projection for one learner and item.

    Draft scores never belong here. Assignment grading writes an entry only
    when points are returned, and records the published submission as source.
    """

    __tablename__ = "grade_entries"
    __table_args__ = (
        ForeignKeyConstraint(
            ["grade_item_id", "course_id"],
            ["grade_items.id", "grade_items.course_id"],
            name="fk_grade_entries_item_course",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["user_id", "course_id"],
            ["enrollments.user_id", "enrollments.course_id"],
            name="fk_grade_entries_enrollment",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("grade_item_id", "user_id", name="uq_grade_entries_item_user"),
        CheckConstraint(
            "(status = 'graded' AND points_earned IS NOT NULL) OR "
            "(status IN ('missing', 'excused') AND points_earned IS NULL)",
            name="ck_grade_entries_status_points",
        ),
        CheckConstraint(
            "points_earned IS NULL OR points_earned >= 0",
            name="ck_grade_entries_points_non_negative",
        ),
        CheckConstraint(
            "release_state IN ('unreleased', 'released')",
            name="ck_grade_entries_release_state",
        ),
        CheckConstraint(
            "(release_state = 'unreleased' AND released_at IS NULL) OR "
            "(release_state = 'released' AND released_at IS NOT NULL)",
            name="ck_grade_entries_release_timestamp",
        ),
        CheckConstraint(
            "(source_type IS NULL AND source_id IS NULL) OR "
            "(source_type IS NOT NULL AND source_id IS NOT NULL)",
            name="ck_grade_entries_source_pair",
        ),
        Index("ix_grade_entries_course_user", "course_id", "user_id"),
        Index("ix_grade_entries_release", "course_id", "release_state"),
        Index("ix_grade_entries_source", "source_type", "source_id"),
    )

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True, default=uuid4)
    course_id: Mapped[UUID] = mapped_column(SAUUID, nullable=False)
    grade_item_id: Mapped[UUID] = mapped_column(SAUUID, nullable=False)
    user_id: Mapped[UUID] = mapped_column(SAUUID, nullable=False)
    status: Mapped[GradeEntryStatus] = mapped_column(String(32), nullable=False)
    points_earned: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 4), nullable=True
    )
    release_state: Mapped[GradeReleaseState] = mapped_column(
        String(32), nullable=False, default=GradeReleaseState.unreleased
    )
    released_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    graded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    source_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    source_id: Mapped[Optional[UUID]] = mapped_column(SAUUID, nullable=True)
    source_version: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    recorded_by_user_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID, ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now, onupdate=_utc_now
    )

    grade_item: Mapped[GradeItem] = relationship("GradeItem", back_populates="entries")
    recorded_by: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[recorded_by_user_id]
    )

    @validates("points_earned")
    def validate_points_earned(self, _key: str, value: Any) -> Optional[Decimal]:
        if value is None:
            return None
        return _decimal_points(value, positive=False, field_name="points_earned")


__all__ = [
    "GradeAggregationStrategy",
    "GradeCategory",
    "GradeEntry",
    "GradeEntryStatus",
    "GradeItem",
    "GradeReleaseState",
]
