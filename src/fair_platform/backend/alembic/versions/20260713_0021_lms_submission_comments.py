"""Add private LMS submission comments.

Revision ID: 20260713_0021
Revises: 20260713_0020
Create Date: 2026-07-13
"""

from alembic import op  # type: ignore
import sqlalchemy as sa


revision = "20260713_0021"
down_revision = "20260713_0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
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
    op.drop_index(
        "ix_submission_comments_submission_created", table_name="submission_comments"
    )
    op.drop_table("submission_comments")
