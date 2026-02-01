"""Add submission draft/published fields and submission events table

Revision ID: 20251110_0004
Revises: 20251101_0003
Create Date: 2025-11-10
"""

from __future__ import annotations

from alembic import op  # type: ignore
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20251110_0004"
down_revision = "20251101_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("submissions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("draft_score", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("draft_feedback", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("published_score", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("published_feedback", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("returned_at", sa.TIMESTAMP(), nullable=True))

    json_type = sa.JSON().with_variant(postgresql.JSONB, "postgresql")

    op.create_table(
        "submission_events",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column(
            "submission_id",
            sa.UUID(),
            sa.ForeignKey("submissions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("actor_id", sa.UUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column(
            "workflow_run_id",
            sa.UUID(),
            sa.ForeignKey("workflow_runs.id"),
            nullable=True,
        ),
        sa.Column("details", json_type, nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_submission_events_submission_id",
        "submission_events",
        ["submission_id"],
        unique=False,
    )
    op.create_index(
        "ix_submission_events_actor_id",
        "submission_events",
        ["actor_id"],
        unique=False,
    )
    op.create_index(
        "ix_submission_events_workflow_run_id",
        "submission_events",
        ["workflow_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_submission_events_created_at",
        "submission_events",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_submission_events_created_at", table_name="submission_events")
    op.drop_index("ix_submission_events_workflow_run_id", table_name="submission_events")
    op.drop_index("ix_submission_events_actor_id", table_name="submission_events")
    op.drop_index("ix_submission_events_submission_id", table_name="submission_events")
    op.drop_table("submission_events")

    with op.batch_alter_table("submissions", schema=None) as batch_op:
        batch_op.drop_column("returned_at")
        batch_op.drop_column("published_feedback")
        batch_op.drop_column("published_score")
        batch_op.drop_column("draft_feedback")
        batch_op.drop_column("draft_score")
