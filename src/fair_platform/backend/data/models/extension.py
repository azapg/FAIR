from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    UUID as SAUUID,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .types import json_document_type


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ExtensionInstallationStatus(str, Enum):
    enabled = "enabled"
    disabled = "disabled"
    revoked = "revoked"


class GrantDecision(str, Enum):
    allow = "allow"
    deny = "deny"


class ExtensionInstallation(Base):
    __tablename__ = "extension_installations"
    __table_args__ = (
        UniqueConstraint(
            "extension_id", name="uq_extension_installations_extension_id"
        ),
    )

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True, default=uuid4)
    extension_id: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    version: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    dispatch_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    health_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    manifest_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[ExtensionInstallationStatus] = mapped_column(
        String(32), nullable=False, default=ExtensionInstallationStatus.enabled
    )
    manifest: Mapped[Optional[dict[str, Any]]] = mapped_column(
        json_document_type(), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now, onupdate=_utc_now
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    capabilities: Mapped[list["CapabilityDefinition"]] = relationship(
        "CapabilityDefinition",
        back_populates="installation",
        cascade="all, delete-orphan",
    )
    grants: Mapped[list["ExtensionGrant"]] = relationship(
        "ExtensionGrant", back_populates="installation", cascade="all, delete-orphan"
    )


class CapabilityDefinition(Base):
    __tablename__ = "capability_definitions"
    __table_args__ = (
        UniqueConstraint(
            "installation_id",
            "capability_id",
            "version",
            name="uq_capability_definitions_installation_identity",
        ),
        Index("ix_capability_definitions_lookup", "capability_id", "version"),
    )

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True, default=uuid4)
    installation_id: Mapped[UUID] = mapped_column(
        SAUUID,
        ForeignKey("extension_installations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    capability_id: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column(String(128), nullable=False)
    input_schema_uri: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    output_schema_uri: Mapped[Optional[str]] = mapped_column(
        String(2048), nullable=True
    )
    config_schema_uri: Mapped[Optional[str]] = mapped_column(
        String(2048), nullable=True
    )
    requested_scopes: Mapped[list[str]] = mapped_column(
        json_document_type(), nullable=False, default=list
    )
    declared_effects: Mapped[list[str]] = mapped_column(
        json_document_type(), nullable=False, default=list
    )
    supports_streaming: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    supports_cancellation: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    supports_resume: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    supports_batch: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    manifest_snapshot: Mapped[Optional[dict[str, Any]]] = mapped_column(
        json_document_type(), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )

    installation: Mapped[ExtensionInstallation] = relationship(
        "ExtensionInstallation", back_populates="capabilities"
    )
    grants: Mapped[list["ExtensionGrant"]] = relationship(
        "ExtensionGrant", back_populates="capability"
    )


class ExtensionGrant(Base):
    __tablename__ = "extension_grants"
    __table_args__ = (
        *(
            Index(
                f"uq_extension_grants_scope_{mask:03b}",
                "installation_id",
                "effect",
                *(
                    column
                    for bit, column in enumerate(
                        ("capability_definition_id", "course_id", "assignment_id")
                    )
                    if mask & (1 << bit)
                ),
                unique=True,
                postgresql_where=text(
                    " AND ".join(
                        f"{column} IS {'NOT ' if mask & (1 << bit) else ''}NULL"
                        for bit, column in enumerate(
                            ("capability_definition_id", "course_id", "assignment_id")
                        )
                    )
                ),
                sqlite_where=text(
                    " AND ".join(
                        f"{column} IS {'NOT ' if mask & (1 << bit) else ''}NULL"
                        for bit, column in enumerate(
                            ("capability_definition_id", "course_id", "assignment_id")
                        )
                    )
                ),
            )
            for mask in range(8)
        ),
        Index(
            "ix_extension_grants_resolution",
            "installation_id",
            "course_id",
            "assignment_id",
            "effect",
        ),
    )

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True, default=uuid4)
    installation_id: Mapped[UUID] = mapped_column(
        SAUUID,
        ForeignKey("extension_installations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    capability_definition_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID,
        ForeignKey("capability_definitions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    course_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID, ForeignKey("courses.id", ondelete="RESTRICT"), nullable=True
    )
    assignment_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID, ForeignKey("assignments.id", ondelete="RESTRICT"), nullable=True
    )
    effect: Mapped[str] = mapped_column(String(128), nullable=False)
    decision: Mapped[GrantDecision] = mapped_column(String(16), nullable=False)
    granted_by_user_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID, ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now, onupdate=_utc_now
    )

    installation: Mapped[ExtensionInstallation] = relationship(
        "ExtensionInstallation", back_populates="grants"
    )
    capability: Mapped[Optional[CapabilityDefinition]] = relationship(
        "CapabilityDefinition", back_populates="grants"
    )


__all__ = [
    "CapabilityDefinition",
    "ExtensionGrant",
    "ExtensionInstallation",
    "ExtensionInstallationStatus",
    "GrantDecision",
]
