"""Add safe, resumable LMS course copying and assignment rubric pins.

Revision ID: 20260812_0033
Revises: 20260812_0032
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260812_0033"
down_revision: str = "20260812_0032"
branch_labels = None
depends_on = None


def _json_document() -> sa.JSON:
    return sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    with op.batch_alter_table("assignments") as batch_op:
        batch_op.add_column(sa.Column("rubric_id", sa.UUID(), nullable=True))
        batch_op.create_foreign_key(
            "fk_assignments_rubric",
            "rubrics",
            ["rubric_id"],
            ["id"],
            ondelete="RESTRICT",
        )

    with op.batch_alter_table("courses") as batch_op:
        batch_op.add_column(sa.Column("copied_from_id", sa.UUID(), nullable=True))
        batch_op.create_foreign_key(
            "fk_courses_copied_from",
            "courses",
            ["copied_from_id"],
            ["id"],
            ondelete="RESTRICT",
        )

    op.create_table(
        "course_copy_jobs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source_course_id", sa.UUID(), nullable=False),
        sa.Column("destination_course_id", sa.UUID(), nullable=True),
        sa.Column("requested_by_user_id", sa.UUID(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("request_snapshot", _json_document(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("mapping", _json_document(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')",
            name="ck_course_copy_jobs_status",
        ),
        sa.ForeignKeyConstraint(
            ["destination_course_id"], ["courses.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["requested_by_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["source_course_id"], ["courses.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "requested_by_user_id",
            "idempotency_key",
            name="uq_course_copy_job_request",
        ),
    )
    op.create_index(
        "ix_course_copy_jobs_requester_status",
        "course_copy_jobs",
        ["requested_by_user_id", "status"],
        unique=False,
    )

    op.create_table(
        "course_templates",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source_course_id", sa.UUID(), nullable=False),
        sa.Column("owner_user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("selection", _json_document(), nullable=False),
        sa.Column("date_policy", sa.String(length=16), nullable=False),
        sa.Column("date_shift_days", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "date_policy IN ('clear', 'shift')",
            name="ck_course_templates_date_policy",
        ),
        sa.CheckConstraint(
            "date_shift_days >= -3650 AND date_shift_days <= 3650",
            name="ck_course_templates_date_shift_days",
        ),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["source_course_id"], ["courses.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "owner_user_id", "name", name="uq_course_template_owner_name"
        ),
    )


def downgrade() -> None:
    op.drop_table("course_templates")
    op.drop_index("ix_course_copy_jobs_requester_status", table_name="course_copy_jobs")
    op.drop_table("course_copy_jobs")

    with op.batch_alter_table("courses") as batch_op:
        batch_op.drop_constraint("fk_courses_copied_from", type_="foreignkey")
        batch_op.drop_column("copied_from_id")

    with op.batch_alter_table("assignments") as batch_op:
        batch_op.drop_constraint("fk_assignments_rubric", type_="foreignkey")
        batch_op.drop_column("rubric_id")
