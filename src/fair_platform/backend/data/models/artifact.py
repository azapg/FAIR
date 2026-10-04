from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UUID as SAUUID,
    UniqueConstraint,
    event,
    inspect,
)
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship

from ..database import Base
from .types import json_document_type
def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ArtifactStatus(str, Enum):
    pending = "pending"
    attached = "attached"
    orphaned = "orphaned"
    archived = "archived"


class AccessLevel(str, Enum):
    private = "private"
    course = "course"
    assignment = "assignment"
    public = "public"


class Artifact(Base):
    """A logical FAIR artifact with immutable versions and optional LMS scope."""

    __tablename__ = "artifacts"

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    artifact_type: Mapped[str] = mapped_column("type", Text, nullable=False)
    meta: Mapped[Optional[dict[str, Any]]] = mapped_column(
        json_document_type(), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now, onupdate=_utc_now
    )
    creator_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("users.id"), nullable=False
    )
    status: Mapped[ArtifactStatus] = mapped_column(
        String, nullable=False, default=ArtifactStatus.pending
    )
    access_level: Mapped[AccessLevel] = mapped_column(
        String, nullable=False, default=AccessLevel.private
    )
    course_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID, ForeignKey("courses.id"), nullable=True
    )
    assignment_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID, ForeignKey("assignments.id"), nullable=True
    )
    kind_uri: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    owner_user_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID, ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    sensitivity: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    access_policy: Mapped[Optional[dict[str, Any]]] = mapped_column(
        json_document_type(), nullable=True
    )
    current_version_id: Mapped[Optional[UUID]] = mapped_column(SAUUID, nullable=True)

    creator = relationship(
        "User", back_populates="created_artifacts", foreign_keys=[creator_id]
    )
    course = relationship("Course", back_populates="artifacts")
    assignment = relationship("Assignment", back_populates="direct_artifacts")
    owner = relationship("User", foreign_keys=[owner_user_id])
    versions: Mapped[list["ArtifactVersion"]] = relationship(
        "ArtifactVersion",
        foreign_keys="ArtifactVersion.artifact_id",
        back_populates="artifact",
        cascade="all, delete-orphan",
        order_by="ArtifactVersion.ordinal",
    )
    assignments = relationship(
        "Assignment", secondary="assignment_artifacts", back_populates="artifacts"
    )
    submissions = relationship(
        "Submission", secondary="submission_artifacts", back_populates="artifacts"
    )
    derivatives: Mapped[list["ArtifactDerivative"]] = relationship(
        "ArtifactDerivative",
        back_populates="artifact",
        cascade="all, delete-orphan",
        order_by="ArtifactDerivative.created_at",
    )

    def __init__(self, **kwargs: Any):
        mime = kwargs.pop("mime", None)
        storage_path = kwargs.pop("storage_path", None)
        storage_type = kwargs.pop("storage_type", None)
        super().__init__(**kwargs)
        if storage_path:
            self.derivatives.append(
                ArtifactDerivative(
                    id=uuid4(),
                    derivative_type="original",
                    storage_uri=f"{storage_type or 'local'}://{storage_path.lstrip('/')}",
                    mime_type=mime or "application/octet-stream",
                )
            )

    @property
    def original_derivative(self) -> Optional["ArtifactDerivative"]:
        return next(
            (item for item in self.derivatives if item.derivative_type == "original"),
            self.derivatives[0] if self.derivatives else None,
        )

    @property
    def mime(self) -> str:
        derivative = self.original_derivative
        return derivative.mime_type if derivative else "application/octet-stream"

    @property
    def storage_path(self) -> Optional[str]:
        derivative = self.original_derivative
        return derivative.storage_path if derivative else None

    @property
    def storage_type(self) -> Optional[str]:
        derivative = self.original_derivative
        return derivative.storage_type if derivative else None


class ArtifactDerivative(Base):
    __tablename__ = "artifact_derivatives"

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True)
    artifact_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("artifacts.id", ondelete="CASCADE"), nullable=False
    )
    derivative_type: Mapped[str] = mapped_column(String, nullable=False)
    storage_uri: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now, onupdate=_utc_now
    )

    artifact: Mapped[Artifact] = relationship("Artifact", back_populates="derivatives")

    @property
    def storage_type(self) -> str:
        return self.storage_uri.split("://", 1)[0]

    @property
    def storage_path(self) -> str:
        return self.storage_uri.partition("://")[2]


class ArtifactVersionState(str, Enum):
    draft = "draft"
    finalized = "finalized"
    abandoned = "abandoned"


class ArtifactVersionMutationError(RuntimeError):
    """Raised when finalized semantic content is edited or deleted."""


class ArtifactLinkRelationship(str, Enum):
    input = "input"
    output = "output"
    evidence = "evidence"
    derived_from = "derived_from"
    attached_to = "attached_to"
    citation = "citation"
    preview = "preview"


class ArtifactLinkTargetType(str, Enum):
    artifact_version = "artifact_version"
    execution = "execution"
    thread = "thread"
    turn = "turn"
    message = "message"
    submission = "submission"
    assignment = "assignment"
    course = "course"
    grade_proposal = "grade_proposal"
    rubric = "rubric"
    flow_version = "flow_version"


class ArtifactVersion(Base):
    __tablename__ = "artifact_versions"
    __table_args__ = (
        UniqueConstraint(
            "artifact_id", "ordinal", name="uq_artifact_versions_artifact_ordinal"
        ),
        UniqueConstraint("artifact_id", "id", name="uq_artifact_versions_artifact_id"),
        Index("ix_artifact_versions_artifact_state", "artifact_id", "state"),
        Index("ix_artifact_versions_producer", "producing_execution_id"),
        CheckConstraint("ordinal >= 1", name="ck_artifact_versions_ordinal_positive"),
        CheckConstraint(
            "size_bytes IS NULL OR size_bytes >= 0",
            name="ck_artifact_versions_size_nonnegative",
        ),
        CheckConstraint(
            "state != 'finalized' OR (hash_algorithm IS NOT NULL AND content_hash IS NOT NULL AND size_bytes IS NOT NULL)",
            name="ck_artifact_versions_terminal_integrity",
        ),
    )

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True, default=uuid4)
    artifact_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("artifacts.id", ondelete="RESTRICT"), nullable=False
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[ArtifactVersionState] = mapped_column(
        String(32), nullable=False, default=ArtifactVersionState.draft
    )
    media_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    schema_uri: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", json_document_type(), nullable=False, default=dict
    )
    created_by_user_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID, ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    created_by_extension_installation_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID,
        ForeignKey("extension_installations.id", ondelete="RESTRICT"),
        nullable=True,
    )
    producing_execution_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID, ForeignKey("executions.id", ondelete="RESTRICT"), nullable=True
    )
    hash_algorithm: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    content_hash: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    provenance: Mapped[dict[str, Any]] = mapped_column(
        json_document_type(), nullable=False, default=dict
    )
    supersedes_version_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID, ForeignKey("artifact_versions.id", ondelete="RESTRICT"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
    finalized_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    abandoned_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    artifact = relationship(
        "Artifact", foreign_keys=[artifact_id], back_populates="versions"
    )
    producing_execution = relationship(
        "Execution", foreign_keys=[producing_execution_id]
    )
    supersedes = relationship(
        "ArtifactVersion", foreign_keys=[supersedes_version_id], remote_side=[id]
    )
    parts: Mapped[list["ArtifactPart"]] = relationship(
        "ArtifactPart",
        back_populates="version",
        cascade="all, delete-orphan",
        order_by="ArtifactPart.ordinal",
    )
    links: Mapped[list["ArtifactLink"]] = relationship(
        "ArtifactLink", back_populates="source_version", cascade="all, delete-orphan"
    )


class ArtifactPart(Base):
    __tablename__ = "artifact_parts"
    __table_args__ = (
        UniqueConstraint(
            "artifact_version_id", "ordinal", name="uq_artifact_parts_version_ordinal"
        ),
        UniqueConstraint(
            "artifact_version_id", "name", name="uq_artifact_parts_version_name"
        ),
        CheckConstraint("ordinal >= 1", name="ck_artifact_parts_ordinal_positive"),
        CheckConstraint(
            "size_bytes IS NULL OR size_bytes >= 0",
            name="ck_artifact_parts_size_nonnegative",
        ),
        CheckConstraint(
            "(storage_uri IS NOT NULL AND inline_json IS NULL) OR (storage_uri IS NULL AND inline_json IS NOT NULL)",
            name="ck_artifact_parts_exactly_one_source",
        ),
        Index("ix_artifact_parts_version_ordinal", "artifact_version_id", "ordinal"),
    )

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True, default=uuid4)
    artifact_version_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("artifact_versions.id", ondelete="RESTRICT"), nullable=False
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(64), nullable=False)
    media_type: Mapped[str] = mapped_column(String(255), nullable=False)
    schema_uri: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    storage_uri: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    inline_json: Mapped[Optional[dict[str, Any]]] = mapped_column(
        json_document_type(), nullable=True
    )
    hash_algorithm: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    content_hash: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    annotations: Mapped[Optional[dict[str, Any]]] = mapped_column(
        json_document_type(), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )

    version: Mapped[ArtifactVersion] = relationship(
        "ArtifactVersion", back_populates="parts"
    )


class ArtifactLink(Base):
    __tablename__ = "artifact_links"
    __table_args__ = (
        UniqueConstraint(
            "artifact_version_id",
            "relationship",
            "target_type",
            "target_id",
            name="uq_artifact_links_edge",
        ),
        Index("ix_artifact_links_target", "target_type", "target_id"),
        Index("ix_artifact_links_relationship", "relationship", "target_type"),
    )

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True, default=uuid4)
    artifact_version_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("artifact_versions.id", ondelete="RESTRICT"), nullable=False
    )
    link_relationship: Mapped[ArtifactLinkRelationship] = mapped_column(
        "relationship", String(32), nullable=False
    )
    target_type: Mapped[ArtifactLinkTargetType] = mapped_column(
        String(64), nullable=False
    )
    target_id: Mapped[UUID] = mapped_column(SAUUID, nullable=False)
    metadata_json: Mapped[Optional[dict[str, Any]]] = mapped_column(
        "metadata", json_document_type(), nullable=True
    )
    created_by_execution_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID, ForeignKey("executions.id", ondelete="RESTRICT"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
    retracted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    source_version: Mapped[ArtifactVersion] = relationship(
        "ArtifactVersion", back_populates="links"
    )
    created_by_execution = relationship(
        "Execution", foreign_keys=[created_by_execution_id]
    )


def _state_value(value: object) -> str:
    return value.value if isinstance(value, Enum) else str(value)


def _version_state_history(version: ArtifactVersion) -> tuple[str | None, str]:
    history = inspect(version).attrs.state.history
    old_state = _state_value(history.deleted[0]) if history.deleted else None
    return old_state, _state_value(version.state)


def _version_is_being_finalized(version: ArtifactVersion) -> bool:
    old_state, new_state = _version_state_history(version)
    return (
        old_state == ArtifactVersionState.draft.value
        and new_state == ArtifactVersionState.finalized.value
    )


@event.listens_for(Session, "before_flush")
def _reject_finalized_artifact_mutations(
    session: Session, _flush_context: object, _instances: object
) -> None:
    for obj in session.new.union(session.dirty):
        if not isinstance(obj, Artifact) or obj.current_version_id is None:
            continue
        current = session.get(ArtifactVersion, obj.current_version_id)
        if current is None or current.artifact_id != obj.id:
            raise ArtifactVersionMutationError(
                "current ArtifactVersion must belong to the same Artifact"
            )

    for obj in session.new.union(session.dirty):
        if not isinstance(obj, ArtifactVersion) or obj.supersedes_version_id is None:
            continue
        prior = session.get(ArtifactVersion, obj.supersedes_version_id)
        if (
            prior is None
            or prior.artifact_id != obj.artifact_id
            or prior.ordinal >= obj.ordinal
        ):
            raise ArtifactVersionMutationError(
                "superseded ArtifactVersion must be an earlier version of the same Artifact"
            )

    for obj in session.dirty:
        if isinstance(obj, ArtifactVersion):
            old_state, new_state = _version_state_history(obj)
            if old_state in {
                ArtifactVersionState.finalized.value,
                ArtifactVersionState.abandoned.value,
            }:
                raise ArtifactVersionMutationError(
                    f"ArtifactVersion {obj.id} is {old_state} and immutable"
                )
            if (
                new_state
                in {
                    ArtifactVersionState.finalized.value,
                    ArtifactVersionState.abandoned.value,
                }
                and old_state is None
            ):
                # A loaded version with no state history is already terminal.
                raise ArtifactVersionMutationError(
                    f"ArtifactVersion {obj.id} is {new_state} and immutable"
                )
        elif isinstance(obj, ArtifactPart):
            version = session.get(ArtifactVersion, obj.artifact_version_id)
            if version is None:
                continue
            old_state, new_state = _version_state_history(version)
            if new_state in {
                ArtifactVersionState.finalized.value,
                ArtifactVersionState.abandoned.value,
            } and not _version_is_being_finalized(version):
                raise ArtifactVersionMutationError(
                    f"parts of ArtifactVersion {version.id} are immutable"
                )

    for obj in session.deleted:
        if isinstance(obj, ArtifactVersion):
            state = _state_value(obj.state)
            if state in {
                ArtifactVersionState.finalized.value,
                ArtifactVersionState.abandoned.value,
            }:
                raise ArtifactVersionMutationError(
                    f"ArtifactVersion {obj.id} is {state} and immutable"
                )
        elif isinstance(obj, ArtifactPart):
            version = session.get(ArtifactVersion, obj.artifact_version_id)
            if version is not None and _state_value(version.state) in {
                ArtifactVersionState.finalized.value,
                ArtifactVersionState.abandoned.value,
            }:
                raise ArtifactVersionMutationError(
                    f"parts of ArtifactVersion {version.id} are immutable"
                )


__all__ = [
    "AccessLevel",
    "Artifact",
    "ArtifactDerivative",
    "ArtifactLink",
    "ArtifactLinkRelationship",
    "ArtifactLinkTargetType",
    "ArtifactPart",
    "ArtifactVersionMutationError",
    "ArtifactVersion",
    "ArtifactVersionState",
    "ArtifactStatus",
]
