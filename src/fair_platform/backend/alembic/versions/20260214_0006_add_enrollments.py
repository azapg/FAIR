"""add enrollments table

Revision ID: 20260214_0006
Revises: 20260211_0005_rename_submission_event_types
Create Date: 2026-02-14
"""

from __future__ import annotations

from alembic import op  # type: ignore
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260214_0006"
down_revision = "20260211_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "enrollments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("course_id", sa.UUID(), nullable=False),
        sa.Column("enrolled_at", sa.TIMESTAMP(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "course_id", name="uq_enrollment_user_course"),
    )


def downgrade() -> None:
    op.drop_table("enrollments")
