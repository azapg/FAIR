"""Add typed LMS scope to Executions.

Revision ID: 20260713_0018
Revises: 20260711_0017
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260713_0018"
down_revision: str | None = "20260711_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("executions", sa.Column("course_id", sa.UUID(), nullable=True))
    op.add_column(
        "executions", sa.Column("assignment_id", sa.UUID(), nullable=True)
    )
    with op.batch_alter_table("executions") as batch_op:
        batch_op.create_foreign_key(
            "fk_executions_course_id",
            "courses",
            ["course_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_unique_constraint(
            "uq_executions_flow_node_attempt",
            ["root_execution_id", "flow_node_id", "attempt"],
        )
        batch_op.create_foreign_key(
            "fk_executions_assignment_id",
            "assignments",
            ["assignment_id"],
            ["id"],
            ondelete="RESTRICT",
        )
    op.create_index(
        "ix_executions_course_created",
        "executions",
        ["course_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_executions_assignment_created",
        "executions",
        ["assignment_id", "created_at"],
        unique=False,
    )
    op.create_table(
        "execution_submissions",
        sa.Column("execution_id", sa.UUID(), nullable=False),
        sa.Column("submission_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["execution_id"], ["executions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["submission_id"], ["submissions.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("execution_id", "submission_id"),
    )
    op.create_index(
        "ix_execution_submissions_submission",
        "execution_submissions",
        ["submission_id", "execution_id"],
        unique=False,
    )
    op.add_column(
        "submission_events", sa.Column("execution_id", sa.UUID(), nullable=True)
    )
    with op.batch_alter_table("submission_events") as batch_op:
        batch_op.create_foreign_key(
            "fk_submission_events_execution_id",
            "executions",
            ["execution_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("submission_events") as batch_op:
        batch_op.drop_constraint(
            "fk_submission_events_execution_id", type_="foreignkey"
        )
    op.drop_column("submission_events", "execution_id")
    op.drop_index(
        "ix_execution_submissions_submission", table_name="execution_submissions"
    )
    op.drop_table("execution_submissions")
    op.drop_index("ix_executions_assignment_created", table_name="executions")
    op.drop_index("ix_executions_course_created", table_name="executions")
    with op.batch_alter_table("executions") as batch_op:
        batch_op.drop_constraint(
            "uq_executions_flow_node_attempt", type_="unique"
        )
        batch_op.drop_constraint("fk_executions_assignment_id", type_="foreignkey")
        batch_op.drop_constraint("fk_executions_course_id", type_="foreignkey")
    op.drop_column("executions", "assignment_id")
    op.drop_column("executions", "course_id")
