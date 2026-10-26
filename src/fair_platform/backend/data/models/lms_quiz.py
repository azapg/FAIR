from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
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
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from .types import json_document_type


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class QuestionKind(str, Enum):
    single_choice = "single_choice"
    true_false = "true_false"


class QuizStatus(str, Enum):
    draft = "draft"
    published = "published"
    closed = "closed"


class QuizReleasePolicy(str, Enum):
    immediate = "immediate"
    manual = "manual"


class QuizAttemptStatus(str, Enum):
    in_progress = "in_progress"
    submitted = "submitted"
    released = "released"


class QuestionBank(Base):
    """A course-scoped container for reusable, versioned questions."""

    __tablename__ = "question_banks"
    __table_args__ = (
        UniqueConstraint("id", "course_id", name="uq_question_banks_id_course"),
        UniqueConstraint("course_id", "name", name="uq_question_banks_course_name"),
        Index("ix_question_banks_course", "course_id"),
    )

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True, default=uuid4)
    course_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now, onupdate=_utc_now
    )


class Question(Base):
    """Logical identity for a question; authored content lives in versions."""

    __tablename__ = "questions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["bank_id", "course_id"],
            ["question_banks.id", "question_banks.course_id"],
            name="fk_questions_bank_course",
            ondelete="CASCADE",
        ),
        UniqueConstraint("id", "course_id", name="uq_questions_id_course"),
        Index("ix_questions_course_bank", "course_id", "bank_id"),
    )

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True, default=uuid4)
    course_id: Mapped[UUID] = mapped_column(SAUUID, nullable=False)
    bank_id: Mapped[UUID] = mapped_column(SAUUID, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now, onupdate=_utc_now
    )


class QuestionVersion(Base):
    """Immutable objective-question content and answer key."""

    __tablename__ = "question_versions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["question_id", "course_id"],
            ["questions.id", "questions.course_id"],
            name="fk_question_versions_question_course",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "question_id",
            "version_number",
            name="uq_question_versions_question_version",
        ),
        UniqueConstraint("id", "course_id", name="uq_question_versions_id_course"),
        CheckConstraint(
            "version_number > 0", name="ck_question_versions_version_positive"
        ),
        CheckConstraint(
            "kind IN ('single_choice', 'true_false')",
            name="ck_question_versions_kind",
        ),
        CheckConstraint(
            "default_points > 0", name="ck_question_versions_points_positive"
        ),
        Index("ix_question_versions_question", "question_id", "version_number"),
    )

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True, default=uuid4)
    course_id: Mapped[UUID] = mapped_column(SAUUID, nullable=False)
    question_id: Mapped[UUID] = mapped_column(SAUUID, nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[QuestionKind] = mapped_column(String(32), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[list[dict[str, Any]]] = mapped_column(
        json_document_type(), nullable=False
    )
    correct_option_id: Mapped[str] = mapped_column(String(64), nullable=False)
    default_points: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    authored_by_user_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )


class Quiz(Base):
    __tablename__ = "quizzes"
    __table_args__ = (
        UniqueConstraint("id", "course_id", name="uq_quizzes_id_course"),
        CheckConstraint(
            "status IN ('draft', 'published', 'closed')", name="ck_quizzes_status"
        ),
        CheckConstraint(
            "release_policy IN ('immediate', 'manual')",
            name="ck_quizzes_release_policy",
        ),
        CheckConstraint("attempt_limit > 0", name="ck_quizzes_attempt_limit_positive"),
        CheckConstraint(
            "opens_at IS NULL OR closes_at IS NULL OR opens_at < closes_at",
            name="ck_quizzes_valid_window",
        ),
        Index("ix_quizzes_course_status", "course_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True, default=uuid4)
    course_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[QuizStatus] = mapped_column(
        String(32), nullable=False, default=QuizStatus.draft
    )
    release_policy: Mapped[QuizReleasePolicy] = mapped_column(
        String(32), nullable=False, default=QuizReleasePolicy.manual
    )
    attempt_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    opens_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    closes_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by_user_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now, onupdate=_utc_now
    )


class QuizQuestion(Base):
    """An ordered pin to one immutable question version."""

    __tablename__ = "quiz_questions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["quiz_id", "course_id"],
            ["quizzes.id", "quizzes.course_id"],
            name="fk_quiz_questions_quiz_course",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["question_version_id", "course_id"],
            ["question_versions.id", "question_versions.course_id"],
            name="fk_quiz_questions_version_course",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("quiz_id", "position", name="uq_quiz_questions_position"),
        UniqueConstraint(
            "quiz_id",
            "question_version_id",
            name="uq_quiz_questions_version",
        ),
        CheckConstraint("position >= 0", name="ck_quiz_questions_position"),
        CheckConstraint("points > 0", name="ck_quiz_questions_points_positive"),
        Index("ix_quiz_questions_quiz", "quiz_id", "position"),
    )

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True, default=uuid4)
    course_id: Mapped[UUID] = mapped_column(SAUUID, nullable=False)
    quiz_id: Mapped[UUID] = mapped_column(SAUUID, nullable=False)
    question_version_id: Mapped[UUID] = mapped_column(SAUUID, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    points: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"
    __table_args__ = (
        ForeignKeyConstraint(
            ["quiz_id", "course_id"],
            ["quizzes.id", "quizzes.course_id"],
            name="fk_quiz_attempts_quiz_course",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["user_id", "course_id"],
            ["enrollments.user_id", "enrollments.course_id"],
            name="fk_quiz_attempts_enrollment",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "quiz_id",
            "user_id",
            "attempt_number",
            name="uq_quiz_attempts_quiz_user_number",
        ),
        UniqueConstraint("id", "course_id", name="uq_quiz_attempts_id_course"),
        CheckConstraint(
            "status IN ('in_progress', 'submitted', 'released')",
            name="ck_quiz_attempts_status",
        ),
        CheckConstraint("attempt_number > 0", name="ck_quiz_attempts_number_positive"),
        CheckConstraint("max_points > 0", name="ck_quiz_attempts_max_points_positive"),
        CheckConstraint(
            "earned_points IS NULL OR earned_points >= 0",
            name="ck_quiz_attempts_earned_non_negative",
        ),
        CheckConstraint(
            "earned_points IS NULL OR earned_points <= max_points",
            name="ck_quiz_attempts_earned_within_maximum",
        ),
        CheckConstraint(
            "(status = 'in_progress' AND earned_points IS NULL AND submitted_at IS NULL "
            "AND released_at IS NULL) OR "
            "(status = 'submitted' AND earned_points IS NOT NULL AND submitted_at IS NOT NULL "
            "AND released_at IS NULL) OR "
            "(status = 'released' AND earned_points IS NOT NULL AND submitted_at IS NOT NULL "
            "AND released_at IS NOT NULL)",
            name="ck_quiz_attempts_status_timestamps",
        ),
        Index("ix_quiz_attempts_quiz_user", "quiz_id", "user_id"),
        Index("ix_quiz_attempts_course_status", "course_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True, default=uuid4)
    course_id: Mapped[UUID] = mapped_column(SAUUID, nullable=False)
    quiz_id: Mapped[UUID] = mapped_column(SAUUID, nullable=False)
    user_id: Mapped[UUID] = mapped_column(SAUUID, nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[QuizAttemptStatus] = mapped_column(
        String(32), nullable=False, default=QuizAttemptStatus.in_progress
    )
    max_points: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    earned_points: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 4), nullable=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
    submitted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    released_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class QuizAttemptQuestion(Base):
    """Exact ordered question-version selection captured when an attempt starts."""

    __tablename__ = "quiz_attempt_questions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["attempt_id", "course_id"],
            ["quiz_attempts.id", "quiz_attempts.course_id"],
            name="fk_quiz_attempt_questions_attempt_course",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["question_version_id", "course_id"],
            ["question_versions.id", "question_versions.course_id"],
            name="fk_quiz_attempt_questions_version_course",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "attempt_id", "position", name="uq_quiz_attempt_questions_position"
        ),
        UniqueConstraint(
            "attempt_id",
            "question_version_id",
            name="uq_quiz_attempt_questions_version",
        ),
        UniqueConstraint(
            "id", "attempt_id", name="uq_quiz_attempt_questions_id_attempt"
        ),
        CheckConstraint("position >= 0", name="ck_quiz_attempt_questions_position"),
        CheckConstraint("points > 0", name="ck_quiz_attempt_questions_points_positive"),
        Index("ix_quiz_attempt_questions_attempt", "attempt_id", "position"),
    )

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True, default=uuid4)
    course_id: Mapped[UUID] = mapped_column(SAUUID, nullable=False)
    attempt_id: Mapped[UUID] = mapped_column(SAUUID, nullable=False)
    question_version_id: Mapped[UUID] = mapped_column(SAUUID, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    points: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)


class QuizAnswer(Base):
    __tablename__ = "quiz_answers"
    __table_args__ = (
        UniqueConstraint(
            "attempt_question_id", name="uq_quiz_answers_attempt_question"
        ),
        CheckConstraint(
            "points_awarded IS NULL OR points_awarded >= 0",
            name="ck_quiz_answers_points_non_negative",
        ),
        CheckConstraint(
            "(is_correct IS NULL AND points_awarded IS NULL) OR "
            "(is_correct IS NOT NULL AND points_awarded IS NOT NULL)",
            name="ck_quiz_answers_scoring_pair",
        ),
        Index("ix_quiz_answers_attempt_question", "attempt_question_id"),
    )

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True, default=uuid4)
    attempt_question_id: Mapped[UUID] = mapped_column(
        SAUUID,
        ForeignKey("quiz_attempt_questions.id", ondelete="CASCADE"),
        nullable=False,
    )
    selected_option_id: Mapped[str] = mapped_column(String(64), nullable=False)
    is_correct: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    points_awarded: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 4), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now, onupdate=_utc_now
    )


__all__ = [
    "Question",
    "QuestionBank",
    "QuestionKind",
    "QuestionVersion",
    "Quiz",
    "QuizAnswer",
    "QuizAttempt",
    "QuizAttemptQuestion",
    "QuizAttemptStatus",
    "QuizQuestion",
    "QuizReleasePolicy",
    "QuizStatus",
]
