"""Add the versioned objective quiz engine.

Revision ID: 20260812_0032
Revises: 20260812_0031

There is no legacy quiz data to backfill. Grade items are created when a quiz
is published and grade entries only when a scored attempt is released.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260812_0032"
down_revision: str = "20260812_0031"
branch_labels = None
depends_on = None


def _json_document() -> sa.JSON:
    return sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    op.create_table(
        "question_banks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("course_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("course_id", "name", name="uq_question_banks_course_name"),
        sa.UniqueConstraint("id", "course_id", name="uq_question_banks_id_course"),
    )
    op.create_index(
        "ix_question_banks_course", "question_banks", ["course_id"], unique=False
    )

    op.create_table(
        "questions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("course_id", sa.UUID(), nullable=False),
        sa.Column("bank_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["bank_id", "course_id"],
            ["question_banks.id", "question_banks.course_id"],
            name="fk_questions_bank_course",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "course_id", name="uq_questions_id_course"),
    )
    op.create_index(
        "ix_questions_course_bank",
        "questions",
        ["course_id", "bank_id"],
        unique=False,
    )

    op.create_table(
        "question_versions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("course_id", sa.UUID(), nullable=False),
        sa.Column("question_id", sa.UUID(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("options", _json_document(), nullable=False),
        sa.Column("correct_option_id", sa.String(length=64), nullable=False),
        sa.Column("default_points", sa.Numeric(12, 4), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("authored_by_user_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "default_points > 0", name="ck_question_versions_points_positive"
        ),
        sa.CheckConstraint(
            "kind IN ('single_choice', 'true_false')",
            name="ck_question_versions_kind",
        ),
        sa.CheckConstraint(
            "version_number > 0", name="ck_question_versions_version_positive"
        ),
        sa.ForeignKeyConstraint(
            ["authored_by_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["question_id", "course_id"],
            ["questions.id", "questions.course_id"],
            name="fk_question_versions_question_course",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "course_id", name="uq_question_versions_id_course"),
        sa.UniqueConstraint(
            "question_id",
            "version_number",
            name="uq_question_versions_question_version",
        ),
    )
    op.create_index(
        "ix_question_versions_question",
        "question_versions",
        ["question_id", "version_number"],
        unique=False,
    )

    op.create_table(
        "quizzes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("course_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("release_policy", sa.String(length=32), nullable=False),
        sa.Column("attempt_limit", sa.Integer(), nullable=False),
        sa.Column("opens_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closes_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.UUID(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "attempt_limit > 0", name="ck_quizzes_attempt_limit_positive"
        ),
        sa.CheckConstraint(
            "opens_at IS NULL OR closes_at IS NULL OR opens_at < closes_at",
            name="ck_quizzes_valid_window",
        ),
        sa.CheckConstraint(
            "release_policy IN ('immediate', 'manual')",
            name="ck_quizzes_release_policy",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'published', 'closed')", name="ck_quizzes_status"
        ),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "course_id", name="uq_quizzes_id_course"),
    )
    op.create_index(
        "ix_quizzes_course_status",
        "quizzes",
        ["course_id", "status"],
        unique=False,
    )

    op.create_table(
        "quiz_questions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("course_id", sa.UUID(), nullable=False),
        sa.Column("quiz_id", sa.UUID(), nullable=False),
        sa.Column("question_version_id", sa.UUID(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("points", sa.Numeric(12, 4), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("points > 0", name="ck_quiz_questions_points_positive"),
        sa.CheckConstraint("position >= 0", name="ck_quiz_questions_position"),
        sa.ForeignKeyConstraint(
            ["question_version_id", "course_id"],
            ["question_versions.id", "question_versions.course_id"],
            name="fk_quiz_questions_version_course",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["quiz_id", "course_id"],
            ["quizzes.id", "quizzes.course_id"],
            name="fk_quiz_questions_quiz_course",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("quiz_id", "position", name="uq_quiz_questions_position"),
        sa.UniqueConstraint(
            "quiz_id",
            "question_version_id",
            name="uq_quiz_questions_version",
        ),
    )
    op.create_index(
        "ix_quiz_questions_quiz",
        "quiz_questions",
        ["quiz_id", "position"],
        unique=False,
    )

    op.create_table(
        "quiz_attempts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("course_id", sa.UUID(), nullable=False),
        sa.Column("quiz_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("max_points", sa.Numeric(12, 4), nullable=False),
        sa.Column("earned_points", sa.Numeric(12, 4), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "attempt_number > 0", name="ck_quiz_attempts_number_positive"
        ),
        sa.CheckConstraint(
            "earned_points IS NULL OR earned_points >= 0",
            name="ck_quiz_attempts_earned_non_negative",
        ),
        sa.CheckConstraint(
            "earned_points IS NULL OR earned_points <= max_points",
            name="ck_quiz_attempts_earned_within_maximum",
        ),
        sa.CheckConstraint(
            "max_points > 0", name="ck_quiz_attempts_max_points_positive"
        ),
        sa.CheckConstraint(
            "status IN ('in_progress', 'submitted', 'released')",
            name="ck_quiz_attempts_status",
        ),
        sa.CheckConstraint(
            "(status = 'in_progress' AND earned_points IS NULL AND submitted_at IS NULL "
            "AND released_at IS NULL) OR "
            "(status = 'submitted' AND earned_points IS NOT NULL AND submitted_at IS NOT NULL "
            "AND released_at IS NULL) OR "
            "(status = 'released' AND earned_points IS NOT NULL AND submitted_at IS NOT NULL "
            "AND released_at IS NOT NULL)",
            name="ck_quiz_attempts_status_timestamps",
        ),
        sa.ForeignKeyConstraint(
            ["quiz_id", "course_id"],
            ["quizzes.id", "quizzes.course_id"],
            name="fk_quiz_attempts_quiz_course",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id", "course_id"],
            ["enrollments.user_id", "enrollments.course_id"],
            name="fk_quiz_attempts_enrollment",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "course_id", name="uq_quiz_attempts_id_course"),
        sa.UniqueConstraint(
            "quiz_id",
            "user_id",
            "attempt_number",
            name="uq_quiz_attempts_quiz_user_number",
        ),
    )
    op.create_index(
        "ix_quiz_attempts_course_status",
        "quiz_attempts",
        ["course_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_quiz_attempts_quiz_user",
        "quiz_attempts",
        ["quiz_id", "user_id"],
        unique=False,
    )

    op.create_table(
        "quiz_attempt_questions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("course_id", sa.UUID(), nullable=False),
        sa.Column("attempt_id", sa.UUID(), nullable=False),
        sa.Column("question_version_id", sa.UUID(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("points", sa.Numeric(12, 4), nullable=False),
        sa.CheckConstraint(
            "points > 0", name="ck_quiz_attempt_questions_points_positive"
        ),
        sa.CheckConstraint("position >= 0", name="ck_quiz_attempt_questions_position"),
        sa.ForeignKeyConstraint(
            ["attempt_id", "course_id"],
            ["quiz_attempts.id", "quiz_attempts.course_id"],
            name="fk_quiz_attempt_questions_attempt_course",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["question_version_id", "course_id"],
            ["question_versions.id", "question_versions.course_id"],
            name="fk_quiz_attempt_questions_version_course",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "id", "attempt_id", name="uq_quiz_attempt_questions_id_attempt"
        ),
        sa.UniqueConstraint(
            "attempt_id",
            "position",
            name="uq_quiz_attempt_questions_position",
        ),
        sa.UniqueConstraint(
            "attempt_id",
            "question_version_id",
            name="uq_quiz_attempt_questions_version",
        ),
    )
    op.create_index(
        "ix_quiz_attempt_questions_attempt",
        "quiz_attempt_questions",
        ["attempt_id", "position"],
        unique=False,
    )

    op.create_table(
        "quiz_answers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("attempt_question_id", sa.UUID(), nullable=False),
        sa.Column("selected_option_id", sa.String(length=64), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.Column("points_awarded", sa.Numeric(12, 4), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "points_awarded IS NULL OR points_awarded >= 0",
            name="ck_quiz_answers_points_non_negative",
        ),
        sa.CheckConstraint(
            "(is_correct IS NULL AND points_awarded IS NULL) OR "
            "(is_correct IS NOT NULL AND points_awarded IS NOT NULL)",
            name="ck_quiz_answers_scoring_pair",
        ),
        sa.ForeignKeyConstraint(
            ["attempt_question_id"],
            ["quiz_attempt_questions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "attempt_question_id", name="uq_quiz_answers_attempt_question"
        ),
    )
    op.create_index(
        "ix_quiz_answers_attempt_question",
        "quiz_answers",
        ["attempt_question_id"],
        unique=False,
    )


def downgrade() -> None:
    # Remove only rows whose provenance belongs to this slice before dropping
    # the generic targets they reference. At 0031 neither course-content kinds
    # nor gradebook source types understand quizzes, so leaving these rows
    # behind would produce invalid reads and dangling source identifiers.
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "DELETE FROM grade_entries "
            "WHERE source_type = 'quiz_attempt' "
            "OR grade_item_id IN ("
            "SELECT id FROM grade_items WHERE source_type = 'quiz'"
            ")"
        )
    )
    bind.execute(sa.text("DELETE FROM grade_items WHERE source_type = 'quiz'"))
    bind.execute(sa.text("DELETE FROM course_items WHERE resource_type = 'quiz'"))
    op.drop_index("ix_quiz_answers_attempt_question", table_name="quiz_answers")
    op.drop_table("quiz_answers")
    op.drop_index(
        "ix_quiz_attempt_questions_attempt", table_name="quiz_attempt_questions"
    )
    op.drop_table("quiz_attempt_questions")
    op.drop_index("ix_quiz_attempts_quiz_user", table_name="quiz_attempts")
    op.drop_index("ix_quiz_attempts_course_status", table_name="quiz_attempts")
    op.drop_table("quiz_attempts")
    op.drop_index("ix_quiz_questions_quiz", table_name="quiz_questions")
    op.drop_table("quiz_questions")
    op.drop_index("ix_quizzes_course_status", table_name="quizzes")
    op.drop_table("quizzes")
    op.drop_index("ix_question_versions_question", table_name="question_versions")
    op.drop_table("question_versions")
    op.drop_index("ix_questions_course_bank", table_name="questions")
    op.drop_table("questions")
    op.drop_index("ix_question_banks_course", table_name="question_banks")
    op.drop_table("question_banks")
