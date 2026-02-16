"""remove enrollment code prefix

Revision ID: 20260215_0008
Revises: 20260215_0007
Create Date: 2026-02-15
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260215_0008"
down_revision = "20260215_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    
    courses = sa.table(
        "courses",
        sa.column("id", sa.UUID()),
        sa.column("enrollment_code", sa.String()),
    )

    result = bind.execute(
        sa.select(courses.c.id, courses.c.enrollment_code)
    )
    rows = result.fetchall()

    for row in rows:
        if row.enrollment_code and row.enrollment_code.startswith("FAIR-"):
            new_code = row.enrollment_code.replace("FAIR-", "", 1)
            # We don't strictly enforce 4 digits here to avoid collisions 
            # and preserve the existing random part, just removing the prefix as requested.
            bind.execute(
                sa.update(courses)
                .where(courses.c.id == row.id)
                .values(enrollment_code=new_code)
            )


def downgrade() -> None:
    bind = op.get_bind()
    
    courses = sa.table(
        "courses",
        sa.column("id", sa.UUID()),
        sa.column("enrollment_code", sa.String()),
    )

    result = bind.execute(
        sa.select(courses.c.id, courses.c.enrollment_code)
    )
    rows = result.fetchall()

    for row in rows:
        if row.enrollment_code and not row.enrollment_code.startswith("FAIR-"):
            new_code = f"FAIR-{row.enrollment_code}"
            bind.execute(
                sa.update(courses)
                .where(courses.c.id == row.id)
                .values(enrollment_code=new_code)
            )
