"""Add LMS assignment publication and submission attempts.

Revision ID: 20260714_0022
Revises: 20260714_0021
Create Date: 2026-07-13
"""

from alembic import op  # type: ignore
import sqlalchemy as sa


revision = "20260714_0022"
down_revision = "20260714_0021"
branch_labels = None
depends_on = None


def _column_names(table_name: str) -> set[str]:
    return {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)
    }


def upgrade() -> None:
    expected_assignment_columns = {"status", "published_at", "allow_resubmissions"}
    expected_submission_columns = {"attempt_number", "is_late"}
    assignment_columns = _column_names("assignments")
    submission_columns = _column_names("submissions")
    present = (expected_assignment_columns & assignment_columns) | (
        expected_submission_columns & submission_columns
    )
    if expected_assignment_columns <= assignment_columns and expected_submission_columns <= submission_columns:
        return
    if present:
        raise RuntimeError("LMS assignment/submission migration is only partially applied")

    with op.batch_alter_table("assignments") as batch_op:
        batch_op.add_column(
            sa.Column("status", sa.String(length=32), server_default="published", nullable=False)
        )
        batch_op.add_column(sa.Column("published_at", sa.TIMESTAMP(), nullable=True))
        batch_op.add_column(
            sa.Column("allow_resubmissions", sa.Boolean(), server_default=sa.true(), nullable=False)
        )
        batch_op.create_index("ix_assignments_course_status", ["course_id", "status"])

    with op.batch_alter_table("submissions") as batch_op:
        batch_op.add_column(
            sa.Column("attempt_number", sa.Integer(), server_default="1", nullable=False)
        )
        batch_op.add_column(
            sa.Column("is_late", sa.Boolean(), server_default=sa.false(), nullable=False)
        )
        batch_op.create_index(
            "ix_submissions_assignment_submitter_attempt",
            ["assignment_id", "submitter_id", "attempt_number"],
            unique=True,
        )


def downgrade() -> None:
    with op.batch_alter_table("submissions") as batch_op:
        batch_op.drop_index("ix_submissions_assignment_submitter_attempt")
        batch_op.drop_column("is_late")
        batch_op.drop_column("attempt_number")

    with op.batch_alter_table("assignments") as batch_op:
        batch_op.drop_index("ix_assignments_course_status")
        batch_op.drop_column("allow_resubmissions")
        batch_op.drop_column("published_at")
        batch_op.drop_column("status")
