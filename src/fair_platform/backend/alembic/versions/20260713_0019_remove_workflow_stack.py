"""Remove the legacy Workflow execution stack.

Revision ID: 20260713_0019
Revises: 20260713_0018

There are no production users requiring data preservation. Workflow,
WorkflowRun, and SubmissionResult records are intentionally not projected into
the new Flow/Execution model because their contracts are not equivalent.
"""

from collections.abc import Sequence

from alembic import op


revision: str = "20260713_0019"
down_revision: str | None = "20260713_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("submission_events") as batch_op:
        batch_op.drop_column("workflow_run_id")
    with op.batch_alter_table("submissions") as batch_op:
        batch_op.drop_column("official_run_id")
    op.drop_table("submission_results")
    op.drop_table("submission_workflow_runs")
    op.drop_table("workflow_runs")
    op.drop_table("workflows")


def downgrade() -> None:
    raise RuntimeError(
        "20260713_0019 is an intentional destructive cutover and cannot be downgraded"
    )
