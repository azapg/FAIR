"""add course enrollment code defaults

Revision ID: 20260215_0007
Revises: 20260213_0006_add_workflow_plugin_hash_indexes, 20260214_0006_add_enrollments
Create Date: 2026-02-15
"""

from __future__ import annotations

import secrets

from alembic import op  # type: ignore
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260215_0007"
down_revision = ("20260213_0006", "20260214_0006")
branch_labels = None
depends_on = None

CODE_PREFIX = "FAIR-"
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 6


def _generate_code(existing: set[str]) -> str:
    """Generate a unique enrollment code avoiding ambiguous characters."""
    while True:
        code = f"{CODE_PREFIX}{''.join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))}"
        if code not in existing:
            return code


def upgrade() -> None:
    op.add_column(
        "courses",
        sa.Column("enrollment_code", sa.String(length=32), nullable=True, unique=True),
    )
    op.add_column(
        "courses",
        sa.Column(
            "is_enrollment_enabled",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
    )

    bind = op.get_bind()
    courses = sa.table(
        "courses",
        sa.column("id", sa.UUID()),
        sa.column("enrollment_code", sa.String()),
        sa.column("is_enrollment_enabled", sa.Boolean()),
    )

    result = bind.execute(sa.select(courses.c.id, courses.c.enrollment_code, courses.c.is_enrollment_enabled))
    rows = result.fetchall()

    existing_codes: set[str] = {
        row.enrollment_code for row in rows if row.enrollment_code
    }

    for row in rows:
        if row.enrollment_code:
            # Ensure enabled courses keep their code; leave as-is.
            continue

        # Create codes for any course missing one, and keep self-enrollment enabled.
        code = _generate_code(existing_codes)
        existing_codes.add(code)
        bind.execute(
            sa.update(courses)
            .where(courses.c.id == row.id)
            .values(
                enrollment_code=code,
                is_enrollment_enabled=True,
            )
        )


def downgrade() -> None:
    op.drop_column("courses", "is_enrollment_enabled")
    op.drop_column("courses", "enrollment_code")
