from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UUID as SAUUID,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from .types import json_document_type


def _now() -> datetime:
    return datetime.now(timezone.utc)


class CourseCopyJob(Base):
    __tablename__ = "course_copy_jobs"
    __table_args__ = (
        UniqueConstraint(
            "requested_by_user_id",
            "idempotency_key",
            name="uq_course_copy_job_request",
        ),
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')",
            name="ck_course_copy_jobs_status",
        ),
        Index("ix_course_copy_jobs_requester_status", "requested_by_user_id", "status"),
    )
    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True, default=uuid4)
    source_course_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("courses.id", ondelete="RESTRICT"), nullable=False
    )
    destination_course_id: Mapped[UUID | None] = mapped_column(
        SAUUID, ForeignKey("courses.id", ondelete="RESTRICT"), nullable=True
    )
    requested_by_user_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    request_fingerprint: Mapped[str] = mapped_column(
        String(64), nullable=False, default=""
    )
    request_snapshot: Mapped[dict[str, Any]] = mapped_column(
        json_document_type(), nullable=False, default=dict
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    mapping: Mapped[dict[str, Any]] = mapped_column(
        json_document_type(), nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )


class CourseTemplate(Base):
    __tablename__ = "course_templates"
    __table_args__ = (
        UniqueConstraint("owner_user_id", "name", name="uq_course_template_owner_name"),
        CheckConstraint(
            "date_policy IN ('clear', 'shift')",
            name="ck_course_templates_date_policy",
        ),
        CheckConstraint(
            "date_shift_days >= -3650 AND date_shift_days <= 3650",
            name="ck_course_templates_date_shift_days",
        ),
    )
    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True, default=uuid4)
    source_course_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("courses.id", ondelete="RESTRICT"), nullable=False
    )
    owner_user_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    selection: Mapped[dict[str, Any]] = mapped_column(
        json_document_type(), nullable=False, default=dict
    )
    date_policy: Mapped[str] = mapped_column(
        String(16), nullable=False, default="clear"
    )
    date_shift_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
