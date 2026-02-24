"""Drop legacy plugins.id uniqueness after hash-based references.

Revision ID: 20260224_0012
Revises: 20260224_0011
Create Date: 2026-02-24
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260224_0012"
down_revision = "20260224_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    inspector = sa.inspect(bind)
    unique_constraints = inspector.get_unique_constraints("plugins")
    has_uq_plugins_id = any((uc.get("name") == "uq_plugins_id") for uc in unique_constraints)
    if has_uq_plugins_id:
        op.drop_constraint("uq_plugins_id", "plugins", type_="unique")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    inspector = sa.inspect(bind)
    unique_constraints = inspector.get_unique_constraints("plugins")
    has_uq_plugins_id = any((uc.get("name") == "uq_plugins_id") for uc in unique_constraints)
    if not has_uq_plugins_id:
        op.create_unique_constraint("uq_plugins_id", "plugins", ["id"])

