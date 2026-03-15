"""add workflow pipeline json fields

Revision ID: 20260305_0014
Revises: 20260228_0013_add_extension_clients_auth
Create Date: 2026-03-05 18:30:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "20260305_0014"
down_revision = "20260228_0013"
branch_labels = None
depends_on = None


def _json_document_type() -> sa.JSON:
    return sa.JSON().with_variant(JSONB, "postgresql")


def upgrade() -> None:
    with op.batch_alter_table("workflows") as batch_op:
        batch_op.add_column(sa.Column("steps", _json_document_type(), nullable=True))

    with op.batch_alter_table("workflow_runs") as batch_op:
        batch_op.add_column(sa.Column("step_states", _json_document_type(), nullable=True))
        batch_op.add_column(
            sa.Column("request_payload", _json_document_type(), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("workflow_runs") as batch_op:
        batch_op.drop_column("request_payload")
        batch_op.drop_column("step_states")

    with op.batch_alter_table("workflows") as batch_op:
        batch_op.drop_column("steps")
