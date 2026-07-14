"""Add private LMS submission comments.

Revision ID: 20260714_0024
Revises: 20260714_0023
Create Date: 2026-07-13
"""

from alembic import op  # type: ignore
import sqlalchemy as sa


revision = "20260714_0024"
down_revision = "20260714_0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "submission_comments" in sa.inspect(op.get_bind()).get_table_names():
        return

    op.create_table(
        "submission_comments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("submission_id", sa.UUID(), nullable=False),
        sa.Column("author_id", sa.UUID(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["submission_id"], ["submissions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_submission_comments_submission_created",
        "submission_comments",
        ["submission_id", "created_at"],
    )


def downgrade() -> None:
    raise RuntimeError(
        "20260714_0024 follows an intentional destructive cutover and cannot be downgraded"
    )
