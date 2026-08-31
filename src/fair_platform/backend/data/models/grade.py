from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
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
from sqlalchemy import event
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship

from ..database import Base
from .types import json_document_type


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class GradeProposalStatus(str, Enum):
    proposed = "proposed"
    superseded = "superseded"
    accepted = "accepted"
    rejected = "rejected"
    withdrawn = "withdrawn"
    legacy_imported = "legacy_imported"


class GradeDecisionAction(str, Enum):
    accept = "accept"
    edit = "edit"
    reject = "reject"
    manual_replace = "manual_replace"


class GradeProposal(Base):
    __tablename__ = "grade_proposals"
    __table_args__ = (
        UniqueConstraint(
            "submission_id",
            "proposal_ordinal",
            name="uq_grade_proposals_submission_ordinal",
        ),
        Index("ix_grade_proposals_submission_status", "submission_id", "status"),
        Index("ix_grade_proposals_producing_execution", "producing_execution_id"),
        CheckConstraint(
            "proposal_ordinal >= 1", name="ck_grade_proposals_ordinal_positive"
        ),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_grade_proposals_confidence_range",
        ),
        CheckConstraint(
            "created_by_user_id IS NOT NULL OR created_by_extension_installation_id IS NOT NULL",
            name="ck_grade_proposals_actor_present",
        ),
    )

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True, default=uuid4)
    submission_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("submissions.id", ondelete="RESTRICT"), nullable=False
    )
    proposal_ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    rubric_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID, ForeignKey("rubrics.id", ondelete="RESTRICT"), nullable=True
    )
    rubric_version: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rubric_snapshot: Mapped[Optional[dict[str, Any]]] = mapped_column(
        json_document_type(), nullable=True
    )
    score: Mapped[Optional[dict[str, Any]]] = mapped_column(
        json_document_type(), nullable=True
    )
    feedback_artifact_version_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID,
        ForeignKey("artifact_versions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    producing_execution_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID, ForeignKey("executions.id", ondelete="RESTRICT"), nullable=True
    )
    created_by_user_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID, ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    created_by_extension_installation_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID,
        ForeignKey("extension_installations.id", ondelete="RESTRICT"),
        nullable=True,
    )
    confidence: Mapped[Optional[float]] = mapped_column(nullable=True)
    flags: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(
        json_document_type(), nullable=True
    )
    status: Mapped[GradeProposalStatus] = mapped_column(
        String(32), nullable=False, default=GradeProposalStatus.proposed
    )
    supersedes_proposal_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID, ForeignKey("grade_proposals.id", ondelete="RESTRICT"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
    superseded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    submission = relationship("Submission")
    rubric = relationship("Rubric")
    feedback_artifact_version = relationship("ArtifactVersion")
    producing_execution = relationship("Execution")
    supersedes = relationship(
        "GradeProposal", foreign_keys=[supersedes_proposal_id], remote_side=[id]
    )
    decisions: Mapped[list["GradeDecision"]] = relationship(
        "GradeDecision", back_populates="proposal"
    )


class GradeDecision(Base):
    __tablename__ = "grade_decisions"
    __table_args__ = (
        Index("ix_grade_decisions_submission_created", "submission_id", "created_at"),
        Index("ix_grade_decisions_proposal", "proposal_id"),
        CheckConstraint(
            "action != 'manual_replace' OR (selected_score IS NOT NULL OR selected_feedback_artifact_version_id IS NOT NULL)",
            name="ck_grade_decisions_manual_replacement_content",
        ),
    )

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True, default=uuid4)
    submission_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("submissions.id", ondelete="RESTRICT"), nullable=False
    )
    proposal_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID, ForeignKey("grade_proposals.id", ondelete="RESTRICT"), nullable=True
    )
    action: Mapped[GradeDecisionAction] = mapped_column(String(32), nullable=False)
    decided_by_user_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    selected_score: Mapped[Optional[dict[str, Any]]] = mapped_column(
        json_document_type(), nullable=True
    )
    selected_feedback_artifact_version_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID,
        ForeignKey("artifact_versions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )

    submission = relationship("Submission")
    proposal: Mapped[Optional[GradeProposal]] = relationship(
        "GradeProposal", back_populates="decisions"
    )
    decided_by = relationship("User", foreign_keys=[decided_by_user_id])
    selected_feedback_artifact_version = relationship("ArtifactVersion")


@event.listens_for(Session, "before_flush")
def _keep_grade_decisions_append_only(
    session: Session, _flush_context: object, _instances: object
) -> None:
    for decision in session.dirty:
        if isinstance(decision, GradeDecision):
            raise ValueError(f"GradeDecision {decision.id} is append-only")
    for decision in session.deleted:
        if isinstance(decision, GradeDecision):
            raise ValueError(f"GradeDecision {decision.id} is append-only")


__all__ = [
    "GradeDecision",
    "GradeDecisionAction",
    "GradeProposal",
    "GradeProposalStatus",
]
