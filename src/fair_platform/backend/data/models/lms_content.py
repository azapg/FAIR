from __future__ import annotations

from datetime import datetime, timezone
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
    String,
    Text,
    UUID as SAUUID,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .types import json_document_type

if TYPE_CHECKING:
    from .course import Course


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CourseContentVisibility(str, Enum):
    draft = "draft"
    published = "published"
    hidden = "hidden"


class CourseSection(Base):
    """An ordered, presentational container within one course."""

    __tablename__ = "course_sections"
    __table_args__ = (
        UniqueConstraint(
            "course_id", "position", name="uq_course_sections_course_position"
        ),
        UniqueConstraint("id", "course_id", name="uq_course_sections_id_course"),
        CheckConstraint(
            "position >= 0", name="ck_course_sections_position_non_negative"
        ),
        CheckConstraint(
            "visibility IN ('draft', 'published', 'hidden')",
            name="ck_course_sections_visibility",
        ),
        Index("ix_course_sections_course_visibility", "course_id", "visibility"),
    )

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True, default=uuid4)
    course_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    visibility: Mapped[CourseContentVisibility] = mapped_column(
        String(32), nullable=False, default=CourseContentVisibility.draft
    )
    copied_from_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID, ForeignKey("course_sections.id", ondelete="RESTRICT"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now, onupdate=_utc_now
    )

    course: Mapped["Course"] = relationship("Course", back_populates="sections")
    items: Mapped[list["CourseItem"]] = relationship(
        "CourseItem",
        back_populates="section",
        cascade="all, delete-orphan",
        order_by="CourseItem.position",
    )
    copied_from: Mapped[Optional["CourseSection"]] = relationship(
        "CourseSection", remote_side=[id], foreign_keys=[copied_from_id]
    )


class CourseItem(Base):
    """An ordered course item with an extensible, typed resource link."""

    __tablename__ = "course_items"
    __table_args__ = (
        ForeignKeyConstraint(
            ["section_id", "course_id"],
            ["course_sections.id", "course_sections.course_id"],
            name="fk_course_items_section_course",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "section_id", "position", name="uq_course_items_section_position"
        ),
        UniqueConstraint("id", "course_id", name="uq_course_items_id_course"),
        UniqueConstraint(
            "course_id",
            "resource_type",
            "resource_id",
            name="uq_course_items_course_resource",
        ),
        CheckConstraint("position >= 0", name="ck_course_items_position_non_negative"),
        CheckConstraint(
            "visibility IN ('draft', 'published', 'hidden')",
            name="ck_course_items_visibility",
        ),
        CheckConstraint(
            "(resource_type IS NULL AND resource_id IS NULL) OR "
            "(resource_type IS NOT NULL AND resource_id IS NOT NULL)",
            name="ck_course_items_resource_pair",
        ),
        Index("ix_course_items_course_kind", "course_id", "kind"),
        Index("ix_course_items_resource", "resource_type", "resource_id"),
    )

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True, default=uuid4)
    course_id: Mapped[UUID] = mapped_column(SAUUID, nullable=False)
    section_id: Mapped[UUID] = mapped_column(SAUUID, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    visibility: Mapped[CourseContentVisibility] = mapped_column(
        String(32), nullable=False, default=CourseContentVisibility.draft
    )
    resource_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    resource_id: Mapped[Optional[UUID]] = mapped_column(SAUUID, nullable=True)
    copied_from_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID, ForeignKey("course_items.id", ondelete="RESTRICT"), nullable=True
    )
    payload_schema_uri: Mapped[Optional[str]] = mapped_column(
        String(2048), nullable=True
    )
    payload: Mapped[dict[str, Any]] = mapped_column(
        json_document_type(), nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now, onupdate=_utc_now
    )

    section: Mapped[CourseSection] = relationship(
        "CourseSection", back_populates="items"
    )
    copied_from: Mapped[Optional["CourseItem"]] = relationship(
        "CourseItem", remote_side=[id], foreign_keys=[copied_from_id]
    )


__all__ = ["CourseContentVisibility", "CourseItem", "CourseSection"]
