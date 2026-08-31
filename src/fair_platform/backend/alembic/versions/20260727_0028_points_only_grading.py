"""Canonicalize assignment grading as points.

Revision ID: 20260727_0028
Revises: 20260719_0027
"""

from __future__ import annotations

import json
import math
from typing import Any

import sqlalchemy as sa
from alembic import op


revision: str = "20260727_0028"
down_revision: str = "20260719_0027"
branch_labels = None
depends_on = None


def _positive_number(value: Any) -> int | float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not math.isfinite(value) or value <= 0:
        return None
    return value


def _canonical_points(raw: Any) -> dict[str, int | float | str] | None:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return None
    if not isinstance(raw, dict):
        return None

    grade_type = raw.get("type")
    if grade_type in (None, "points"):
        value = raw.get("value", raw.get("points"))
    elif grade_type == "percentage":
        # The former UI stored the numeric scale in `value`; points use the
        # same scale and only remove the alternate storage type.
        value = raw.get("value")
    else:
        return None

    points = _positive_number(value)
    if points is None:
        return None
    return {"type": "points", "value": points}


def upgrade() -> None:
    connection = op.get_bind()
    assignments = sa.table(
        "assignments",
        sa.column("id", sa.UUID()),
        sa.column("max_grade", sa.JSON()),
    )

    invalid_ids: list[str] = []
    updates: list[tuple[Any, dict[str, int | float | str]]] = []
    for row in connection.execute(
        sa.select(assignments.c.id, assignments.c.max_grade)
    ).mappings():
        canonical = _canonical_points(row["max_grade"])
        if canonical is None:
            invalid_ids.append(str(row["id"]))
        elif canonical != row["max_grade"]:
            updates.append((row["id"], canonical))

    if invalid_ids:
        preview = ", ".join(invalid_ids[:10])
        suffix = "" if len(invalid_ids) <= 10 else f" (+{len(invalid_ids) - 10} more)"
        raise RuntimeError(
            "Cannot convert assignments with non-numeric grading to points. "
            f"Choose a positive point maximum for assignment IDs: {preview}{suffix}"
        )

    for assignment_id, canonical in updates:
        connection.execute(
            assignments.update()
            .where(assignments.c.id == assignment_id)
            .values(max_grade=canonical)
        )


def downgrade() -> None:
    raise RuntimeError(
        "Points-only grading is an intentional destructive cutover: the "
        "discarded grading types cannot be reconstructed."
    )
