from enum import Enum
from uuid import UUID, uuid4
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import Text, UUID as SAUUID, String, TIMESTAMP, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .types import json_document_type

if TYPE_CHECKING:
    from .assignment import Assignment
    from .submission import Submission
    from .user import User
    from .course import Course


class ArtifactStatus(str, Enum):
    pending = "pending"          # Uploaded but not attached
    attached = "attached"        # Linked to assignment/submission
    orphaned = "orphaned"        # Parent deleted but artifact remains
    archived = "archived"        # Soft deleted


class AccessLevel(str, Enum):
    private = "private"
    course = "course"
    assignment = "assignment"
    public = "public"


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    artifact_type: Mapped[str] = mapped_column("type", Text, nullable=False)
    meta: Mapped[Optional[dict]] = mapped_column(json_document_type(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    creator_id: Mapped[UUID] = mapped_column(SAUUID, ForeignKey("users.id"), nullable=False)
    status: Mapped[ArtifactStatus] = mapped_column(String, nullable=False, default=ArtifactStatus.pending)
    access_level: Mapped[AccessLevel] = mapped_column(String, nullable=False, default=AccessLevel.private)
    
    course_id: Mapped[Optional[UUID]] = mapped_column(SAUUID, ForeignKey("courses.id"), nullable=True)
    assignment_id: Mapped[Optional[UUID]] = mapped_column(SAUUID, ForeignKey("assignments.id"), nullable=True)

    creator: Mapped["User"] = relationship("User", back_populates="created_artifacts")
    course: Mapped[Optional["Course"]] = relationship("Course", back_populates="artifacts")
    assignment: Mapped[Optional["Assignment"]] = relationship("Assignment", back_populates="direct_artifacts")

    assignments: Mapped[List["Assignment"]] = relationship(
        "Assignment",
        secondary="assignment_artifacts",
        back_populates="artifacts",
        viewonly=False,
    )

    submissions: Mapped[List["Submission"]] = relationship(
        "Submission",
        secondary="submission_artifacts",
        back_populates="artifacts",
        viewonly=False,
    )
    derivatives: Mapped[List["ArtifactDerivative"]] = relationship(
        "ArtifactDerivative",
        back_populates="artifact",
        cascade="all, delete-orphan",
        order_by="ArtifactDerivative.created_at",
    )

    def __init__(self, **kwargs):
        legacy_mime = kwargs.pop("mime", None)
        legacy_storage_path = kwargs.pop("storage_path", None)
        legacy_storage_type = kwargs.pop("storage_type", None)
        super().__init__(**kwargs)
        if legacy_storage_path:
            storage_scheme = legacy_storage_type or "local"
            self.derivatives.append(
                ArtifactDerivative(
                    id=uuid4(),
                    derivative_type="original",
                    storage_uri=f"{storage_scheme}://{legacy_storage_path.lstrip('/')}",
                    mime_type=legacy_mime or "application/octet-stream",
                )
            )

    @property
    def original_derivative(self) -> Optional["ArtifactDerivative"]:
        for derivative in self.derivatives:
            if derivative.derivative_type == "original":
                return derivative
        return self.derivatives[0] if self.derivatives else None

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

    def __repr__(self) -> str:
        return (
            f"<Artifact id={self.id} title={self.title!r} "
            f"type={self.artifact_type!r} mime={self.mime!r}>"
        )


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
        TIMESTAMP, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    artifact: Mapped["Artifact"] = relationship("Artifact", back_populates="derivatives")

    @property
    def storage_type(self) -> str:
        return self.storage_uri.split("://", 1)[0]

    @property
    def storage_path(self) -> str:
        _, _, path = self.storage_uri.partition("://")
        return path


__all__ = ["Artifact", "ArtifactDerivative", "ArtifactStatus", "AccessLevel"]
