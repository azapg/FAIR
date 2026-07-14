from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional
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
from sqlalchemy import event, inspect
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship

from ..database import Base
from .types import json_document_type

if TYPE_CHECKING:
    from .course import Course
    from .execution import Execution


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class FlowVersionState(str, Enum):
    draft = "draft"
    published = "published"
    archived = "archived"


class Flow(Base):
    __tablename__ = "flows"
    __table_args__ = (Index("ix_flows_owner_archived", "owner_user_id", "archived_at"),)

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True, default=uuid4)
    owner_user_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    course_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID, ForeignKey("courses.id", ondelete="RESTRICT"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    archived_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now, onupdate=_utc_now
    )

    versions: Mapped[list["FlowVersion"]] = relationship(
        "FlowVersion",
        back_populates="flow",
        cascade="all, delete-orphan",
        order_by="FlowVersion.ordinal",
    )
    course: Mapped[Optional["Course"]] = relationship("Course", back_populates="flows")


class FlowVersion(Base):
    __tablename__ = "flow_versions"
    __table_args__ = (
        UniqueConstraint("flow_id", "ordinal", name="uq_flow_versions_flow_ordinal"),
        CheckConstraint("ordinal >= 1", name="ck_flow_versions_ordinal_positive"),
        Index("ix_flow_versions_published", "flow_id", "state", "published_at"),
    )

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True, default=uuid4)
    flow_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("flows.id", ondelete="RESTRICT"), nullable=False
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[FlowVersionState] = mapped_column(
        String(32), nullable=False, default=FlowVersionState.draft
    )
    definition: Mapped[dict[str, Any]] = mapped_column(
        json_document_type(), nullable=False, default=dict
    )
    capability_pins: Mapped[list[dict[str, Any]]] = mapped_column(
        json_document_type(), nullable=False, default=list
    )
    config_snapshot: Mapped[dict[str, Any]] = mapped_column(
        json_document_type(), nullable=False, default=dict
    )
    definition_hash: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_by_user_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    archived_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    flow: Mapped[Flow] = relationship("Flow", back_populates="versions")
    executions: Mapped[list["Execution"]] = relationship(
        "Execution", back_populates="flow_version"
    )


@event.listens_for(Session, "before_flush")
def _reject_published_flow_version_mutations(
    session: Session, _flush_context: object, _instances: object
) -> None:
    for version in session.dirty:
        if not isinstance(version, FlowVersion):
            continue
        history = inspect(version).attrs.state.history
        original = history.deleted[0] if history.deleted else version.state
        original_value = (
            original.value if isinstance(original, FlowVersionState) else str(original)
        )
        if original_value in {
            FlowVersionState.published.value,
            FlowVersionState.archived.value,
        }:
            raise ValueError(f"FlowVersion {version.id} is immutable once published")
    for version in session.deleted:
        if isinstance(version, FlowVersion) and version.state in {
            FlowVersionState.published,
            FlowVersionState.archived,
            FlowVersionState.published.value,
            FlowVersionState.archived.value,
        }:
            raise ValueError(f"FlowVersion {version.id} is immutable once published")


__all__ = ["Flow", "FlowVersion", "FlowVersionState"]
