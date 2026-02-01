"""Add draft/published fields to submissions and create submission_events table

Revision ID: 20260131_0004
Revises: 20251101_0003
Create Date: 2026-01-31
"""

from __future__ import annotations

from alembic import op  # type: ignore
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "20260131_0004"
down_revision = "20251101_0003"
branch_labels = None
depends_on = None

submissioneventtype = sa.Enum(
    "AI_GRADED", "MANUAL_EDIT", "RETURNED_TO_STUDENT", name="submissioneventtype"
)


def upgrade() -> None:
    with op.batch_alter_table("submissions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("draft_score", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("draft_feedback", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("published_score", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("published_feedback", sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column("returned_at", sa.TIMESTAMP(timezone=True), nullable=True)
        )

    submissioneventtype.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "submission_events",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column(
            "submission_id",
            sa.UUID(),
            sa.ForeignKey("submissions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", submissioneventtype, nullable=False),
        sa.Column(
            "actor_id",
            sa.UUID(),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column(
            "workflow_run_id",
            sa.UUID(),
            sa.ForeignKey("workflow_runs.id"),
            nullable=True,
        ),
        sa.Column("details", JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("submission_events")

    submissioneventtype.drop(op.get_bind(), checkfirst=True)

    with op.batch_alter_table("submissions", schema=None) as batch_op:
        batch_op.drop_column("returned_at")
        batch_op.drop_column("published_feedback")
        batch_op.drop_column("published_score")
        batch_op.drop_column("draft_feedback")
        batch_op.drop_column("draft_score")
