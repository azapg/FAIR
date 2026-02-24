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

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 6

def _generate_code(existing: set[str]) -> str:
"""Generate a unique enrollment code avoiding ambiguous characters."""
while True:
  code = ''.join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
  if code not in existing:
  return code


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {col["name"] for col in inspector.get_columns("courses")}
    existing_indexes = {idx["name"] for idx in inspector.get_indexes("courses")}
    existing_uniques = {
        uq["name"] for uq in inspector.get_unique_constraints("courses") if uq.get("name")
    }

    # Make migration idempotent across divergent branch histories.
    if "enrollment_code" not in existing_columns:
        op.add_column(
            "courses",
            sa.Column("enrollment_code", sa.String(length=32), nullable=True),
        )

    if "is_enrollment_enabled" not in existing_columns:
        op.add_column(
            "courses",
            sa.Column(
                "is_enrollment_enabled",
                sa.Boolean(),
                server_default=sa.true(),
                nullable=False,
            ),
        )

    courses = sa.table(
        "courses",
        sa.column("id", sa.UUID()),
        sa.column("enrollment_code", sa.String()),
        sa.column("is_enrollment_enabled", sa.Boolean()),
    )

    result = bind.execute(
        sa.select(courses.c.id, courses.c.enrollment_code, courses.c.is_enrollment_enabled)
    )
    rows = result.fetchall()

    existing_codes: set[str] = {row.enrollment_code for row in rows if row.enrollment_code}

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

    # SQLite cannot ALTER TABLE ADD CONSTRAINT, so enforce uniqueness with a unique index there.
    if bind.dialect.name == "sqlite":
        if "uq_courses_enrollment_code" not in existing_indexes:
            op.create_index(
                "uq_courses_enrollment_code",
                "courses",
                ["enrollment_code"],
                unique=True,
            )
    else:
        if "uq_courses_enrollment_code" not in existing_uniques:
            op.create_unique_constraint(
                "uq_courses_enrollment_code",
                "courses",
                ["enrollment_code"],
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {col["name"] for col in inspector.get_columns("courses")}
    existing_indexes = {idx["name"] for idx in inspector.get_indexes("courses")}
    existing_uniques = {
        uq["name"] for uq in inspector.get_unique_constraints("courses") if uq.get("name")
    }

    # Keep downgrade safe if schema drift exists.
    if bind.dialect.name == "sqlite":
        if "uq_courses_enrollment_code" in existing_indexes:
            op.drop_index("uq_courses_enrollment_code", table_name="courses")
    else:
        if "uq_courses_enrollment_code" in existing_uniques:
            op.drop_constraint("uq_courses_enrollment_code", "courses", type_="unique")

    if "is_enrollment_enabled" in existing_columns:
        op.drop_column("courses", "is_enrollment_enabled")
    if "enrollment_code" in existing_columns:
        op.drop_column("courses", "enrollment_code")
