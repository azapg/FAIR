from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UUID as SAUUID,
    UniqueConstraint,
    event,
)
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship

from ..database import Base
from .types import json_document_type


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CalendarEventVisibility(str, Enum):
    private = "private"
    course = "course"


class NotificationChannel(str, Enum):
    web = "web"
    email = "email"
    push = "push"


class NotificationDeliveryMode(str, Enum):
    immediate = "immediate"
    digest = "digest"
    off = "off"


class CalendarEvent(Base):
    __tablename__ = "calendar_events"
    __table_args__ = (
        CheckConstraint(
            "ends_at IS NULL OR ends_at > starts_at",
            name="ck_calendar_events_time_order",
        ),
        CheckConstraint(
            "visibility IN ('private', 'course')",
            name="ck_calendar_events_visibility",
        ),
        CheckConstraint(
            "visibility != 'course' OR course_id IS NOT NULL",
            name="ck_calendar_events_course_visibility_scope",
        ),
        CheckConstraint(
            "(source_type IS NULL AND source_id IS NULL) OR "
            "(source_type IS NOT NULL AND source_id IS NOT NULL)",
            name="ck_calendar_events_source_pair",
        ),
        Index("ix_calendar_events_course_start", "course_id", "starts_at"),
        Index("ix_calendar_events_owner_start", "owner_user_id", "starts_at"),
        Index("ix_calendar_events_source", "source_type", "source_id"),
    )

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True, default=uuid4)
    course_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID, ForeignKey("courses.id", ondelete="CASCADE"), nullable=True
    )
    owner_user_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    all_day: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    timezone_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    visibility: Mapped[CalendarEventVisibility] = mapped_column(
        String(32), nullable=False, default=CalendarEventVisibility.private
    )
    source_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    source_id: Mapped[Optional[UUID]] = mapped_column(SAUUID, nullable=True)
    copied_from_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID, ForeignKey("calendar_events.id", ondelete="RESTRICT"), nullable=True
    )
    recurrence: Mapped[dict[str, Any]] = mapped_column(
        json_document_type(), nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now, onupdate=_utc_now
    )

    course = relationship("Course", back_populates="calendar_events")
    owner = relationship("User", foreign_keys=[owner_user_id])
    copied_from: Mapped[Optional["CalendarEvent"]] = relationship(
        "CalendarEvent", remote_side=[id], foreign_keys=[copied_from_id]
    )


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "channel",
            "event_type",
            name="uq_notification_preferences_user_channel_event",
        ),
        CheckConstraint(
            "channel IN ('web', 'email', 'push')",
            name="ck_notification_preferences_channel",
        ),
        CheckConstraint(
            "delivery_mode IN ('immediate', 'digest', 'off')",
            name="ck_notification_preferences_delivery_mode",
        ),
        CheckConstraint(
            "(source_type IS NULL AND source_id IS NULL) OR "
            "(source_type IS NOT NULL AND source_id IS NOT NULL)",
            name="ck_notification_preferences_source_pair",
        ),
        Index("ix_notification_preferences_user_mode", "user_id", "delivery_mode"),
        Index("ix_notification_preferences_source", "source_type", "source_id"),
    )

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    channel: Mapped[NotificationChannel] = mapped_column(String(32), nullable=False)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False, default="*")
    delivery_mode: Mapped[NotificationDeliveryMode] = mapped_column(
        String(32), nullable=False, default=NotificationDeliveryMode.immediate
    )
    source_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    source_id: Mapped[Optional[UUID]] = mapped_column(SAUUID, nullable=True)
    config: Mapped[dict[str, Any]] = mapped_column(
        json_document_type(), nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now, onupdate=_utc_now
    )

    user = relationship("User")


class ActivityEvent(Base):
    """An immutable audit/event fact for LMS projections and integrations."""

    __tablename__ = "activity_events"
    __table_args__ = (
        CheckConstraint(
            "(object_type IS NULL AND object_id IS NULL) OR "
            "(object_type IS NOT NULL AND object_id IS NOT NULL)",
            name="ck_activity_events_object_pair",
        ),
        CheckConstraint(
            "(source_type IS NULL AND source_id IS NULL) OR "
            "(source_type IS NOT NULL AND source_id IS NOT NULL)",
            name="ck_activity_events_source_pair",
        ),
        Index("ix_activity_events_course_occurred", "course_id", "occurred_at"),
        Index(
            "ix_activity_events_organization_occurred",
            "organization_id",
            "occurred_at",
        ),
        Index("ix_activity_events_actor_occurred", "actor_user_id", "occurred_at"),
        Index("ix_activity_events_object", "object_type", "object_id"),
        Index("ix_activity_events_source", "source_type", "source_id"),
    )

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True, default=uuid4)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    schema_uri: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    actor_user_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID, ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    course_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID, ForeignKey("courses.id", ondelete="RESTRICT"), nullable=True
    )
    organization_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=True
    )
    object_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    object_id: Mapped[Optional[UUID]] = mapped_column(SAUUID, nullable=True)
    source_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    source_id: Mapped[Optional[UUID]] = mapped_column(SAUUID, nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(
        json_document_type(), nullable=False, default=dict
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )

    actor = relationship("User")
    course = relationship("Course", back_populates="activity_events")
    organization = relationship("Organization")


@event.listens_for(Session, "before_flush")
def _keep_activity_events_append_only(
    session: Session, _flush_context: object, _instances: object
) -> None:
    for activity_event in session.dirty:
        if isinstance(activity_event, ActivityEvent):
            raise ValueError(f"ActivityEvent {activity_event.id} is append-only")
    for activity_event in session.deleted:
        if isinstance(activity_event, ActivityEvent):
            raise ValueError(f"ActivityEvent {activity_event.id} is append-only")


__all__ = [
    "ActivityEvent",
    "CalendarEvent",
    "CalendarEventVisibility",
    "NotificationChannel",
    "NotificationDeliveryMode",
    "NotificationPreference",
]
