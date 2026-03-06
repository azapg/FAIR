"""add workflow pipeline json fields

Revision ID: 20260305_0014
Revises: 20260228_0013_add_extension_clients_auth
Create Date: 2026-03-05 18:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260305_0014"
down_revision = "20260228_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("workflows") as batch_op:
        batch_op.add_column(sa.Column("steps", sa.JSON(), nullable=True))

    with op.batch_alter_table("workflow_runs") as batch_op:
        batch_op.add_column(sa.Column("step_states", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("request_payload", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("workflow_runs") as batch_op:
        batch_op.drop_column("request_payload")
        batch_op.drop_column("step_states")

    with op.batch_alter_table("workflows") as batch_op:
        batch_op.drop_column("steps")
