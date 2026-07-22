"""Replace capability kind with Surface, drop platform-linked tools.

A Capability's `kind` only ever labelled the shape of the author's code, which
told FAIR nothing actionable. `surface` says where the capability plugs into the
product and whose schema governs its I/O, which is what dispatch and the UI
actually need. Platform-linked tools (extension-to-extension calls) and the
unused `supports_batch` flag are removed with it.

Revision ID: 20260719_0027
Revises: 20260714_0026
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision: str = "20260719_0027"
down_revision: str = "20260714_0026"
branch_labels = None
depends_on = None


# Historical kinds map onto the three Surfaces of Protocol 1.
_KIND_TO_SURFACE = {
    "agent": "chat.agent",
    "grader": "flow.step",
    "transformer": "flow.step",
    "integration": "function",
    "tool": "function",
}


def upgrade() -> None:
    with op.batch_alter_table("capability_definitions") as batch:
        batch.add_column(sa.Column("surface", sa.String(64), nullable=True))
        batch.add_column(sa.Column("contract", sa.String(255), nullable=True))
        batch.add_column(sa.Column("display_name", sa.String(255), nullable=True))
        batch.add_column(sa.Column("description", sa.Text(), nullable=True))

    for kind, surface in _KIND_TO_SURFACE.items():
        op.execute(
            sa.text(
                "UPDATE capability_definitions SET surface = :surface "
                "WHERE kind = :kind"
            ).bindparams(surface=surface, kind=kind)
        )
    # Anything unrecognised is still callable as a plain function.
    op.execute("UPDATE capability_definitions SET surface = 'function' "
               "WHERE surface IS NULL")

    with op.batch_alter_table("capability_definitions") as batch:
        batch.alter_column("surface", existing_type=sa.String(64), nullable=False)
        batch.drop_column("kind")
        batch.drop_column("tool_capabilities")
        batch.drop_column("supports_batch")


def downgrade() -> None:
    # Follows the 20260713_0019 cutover lineage: restoring `kind` would have to
    # invent a capability shape that Surfaces deliberately no longer record, and
    # platform-linked tool grants cannot be reconstructed once dropped.
    raise RuntimeError(
        "20260719_0027 follows an intentional destructive cutover and cannot "
        "be downgraded"
    )
