"""Backfill Gradebook 2 projections for existing LMS data.

Revision ID: 20260812_0031
Revises: 20260812_0030
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4

import sqlalchemy as sa
from alembic import op


revision: str = "20260812_0031"
down_revision: str = "20260812_0030"
branch_labels = None
depends_on = None


DEFAULT_CATEGORY_POLICY_KEY = "fairDefaultCategory"
DEFAULT_CATEGORY_POLICY_VALUE = "assignments"
CREATED_BY_BACKFILL_KEY = "fairGradebookBackfillCreated"
CATEGORY_ASSIGNED_BY_BACKFILL_KEY = "fairGradebookBackfillCategoryAssigned"
BACKFILL_MARKER_VALUE = revision
ENTRY_SOURCE_VERSION_PREFIX = f"fair-gradebook-backfill-{revision}:"


def _policy(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, str):
        value = json.loads(value)
    if isinstance(value, Mapping):
        return dict(value)
    raise ValueError("Expected a JSON object for gradebook calculation policy")


def _max_points(value: Any) -> Decimal:
    if isinstance(value, str):
        value = json.loads(value)
    if not isinstance(value, Mapping) or value.get("type") != "points":
        raise ValueError("Assignment max_grade must use the canonical points contract")
    points = Decimal(str(value["value"]))
    if not points.is_finite() or points <= 0:
        raise ValueError("Assignment max_grade points must be positive and finite")
    return points


def _published_points(submission: Mapping[str, Any]) -> Decimal | None:
    value = submission["published_score"]
    if value is None:
        return None
    points = Decimal(str(value))
    if not points.is_finite() or points < 0:
        raise ValueError(
            f"Submission {submission['id']} has an invalid published_score"
        )
    return points


def _aware(value: datetime | None, fallback: datetime) -> datetime:
    result = value or fallback
    if result.tzinfo is None:
        return result.replace(tzinfo=timezone.utc)
    return result.astimezone(timezone.utc)


def _submission_rank(row: Mapping[str, Any], now: datetime) -> tuple[int, float, str]:
    released_at = _aware(row["returned_at"] or row["submitted_at"], now)
    return (
        int(row["attempt_number"] or 0),
        released_at.timestamp(),
        str(row["id"]),
    )


def _tables() -> dict[str, sa.TableClause]:
    return {
        "courses": sa.table("courses", sa.column("id", sa.UUID())),
        "assignments": sa.table(
            "assignments",
            sa.column("id", sa.UUID()),
            sa.column("course_id", sa.UUID()),
            sa.column("title", sa.String()),
            sa.column("description", sa.Text()),
            sa.column("max_grade", sa.JSON()),
        ),
        "enrollments": sa.table(
            "enrollments",
            sa.column("course_id", sa.UUID()),
            sa.column("user_id", sa.UUID()),
            sa.column("role", sa.String()),
            sa.column("status", sa.String()),
        ),
        "submitters": sa.table(
            "submitters",
            sa.column("id", sa.UUID()),
            sa.column("user_id", sa.UUID()),
            sa.column("is_synthetic", sa.Boolean()),
        ),
        "submissions": sa.table(
            "submissions",
            sa.column("id", sa.UUID()),
            sa.column("assignment_id", sa.UUID()),
            sa.column("submitter_id", sa.UUID()),
            sa.column("status", sa.String()),
            sa.column("published_score", sa.Float()),
            sa.column("returned_at", sa.DateTime(timezone=True)),
            sa.column("submitted_at", sa.DateTime(timezone=True)),
            sa.column("attempt_number", sa.Integer()),
        ),
        "categories": sa.table(
            "grade_categories",
            sa.column("id", sa.UUID()),
            sa.column("course_id", sa.UUID()),
            sa.column("parent_category_id", sa.UUID()),
            sa.column("name", sa.String()),
            sa.column("description", sa.Text()),
            sa.column("position", sa.Integer()),
            sa.column("aggregation_strategy", sa.String()),
            sa.column("weight", sa.Numeric(12, 6)),
            sa.column("calculation_policy", sa.JSON()),
            sa.column("copied_from_id", sa.UUID()),
            sa.column("created_at", sa.DateTime(timezone=True)),
            sa.column("updated_at", sa.DateTime(timezone=True)),
        ),
        "items": sa.table(
            "grade_items",
            sa.column("id", sa.UUID()),
            sa.column("course_id", sa.UUID()),
            sa.column("category_id", sa.UUID()),
            sa.column("title", sa.String()),
            sa.column("description", sa.Text()),
            sa.column("position", sa.Integer()),
            sa.column("max_points", sa.Numeric(12, 4)),
            sa.column("weight", sa.Numeric(12, 6)),
            sa.column("calculation_policy", sa.JSON()),
            sa.column("release_policy", sa.JSON()),
            sa.column("source_type", sa.String()),
            sa.column("source_id", sa.UUID()),
            sa.column("copied_from_id", sa.UUID()),
            sa.column("created_at", sa.DateTime(timezone=True)),
            sa.column("updated_at", sa.DateTime(timezone=True)),
        ),
        "entries": sa.table(
            "grade_entries",
            sa.column("id", sa.UUID()),
            sa.column("course_id", sa.UUID()),
            sa.column("grade_item_id", sa.UUID()),
            sa.column("user_id", sa.UUID()),
            sa.column("status", sa.String()),
            sa.column("points_earned", sa.Numeric(12, 4)),
            sa.column("release_state", sa.String()),
            sa.column("released_at", sa.DateTime(timezone=True)),
            sa.column("graded_at", sa.DateTime(timezone=True)),
            sa.column("source_type", sa.String()),
            sa.column("source_id", sa.UUID()),
            sa.column("source_version", sa.String()),
            sa.column("recorded_by_user_id", sa.UUID()),
            sa.column("note", sa.Text()),
            sa.column("created_at", sa.DateTime(timezone=True)),
            sa.column("updated_at", sa.DateTime(timezone=True)),
        ),
    }


def upgrade() -> None:
    connection = op.get_bind()
    tables = _tables()
    courses = tables["courses"]
    assignments = tables["assignments"]
    enrollments = tables["enrollments"]
    submitters = tables["submitters"]
    submissions = tables["submissions"]
    categories = tables["categories"]
    items = tables["items"]
    entries = tables["entries"]
    now = datetime.now(timezone.utc)
    submission_rows = list(connection.execute(sa.select(submissions)).mappings())
    invalid_submission_ids: list[str] = []
    for submission in submission_rows:
        try:
            _published_points(submission)
        except (ValueError, ArithmeticError):
            invalid_submission_ids.append(str(submission["id"]))
    if invalid_submission_ids:
        raise ValueError(
            "Invalid non-negative finite published_score for submission(s): "
            + ", ".join(sorted(invalid_submission_ids))
        )

    category_rows = list(connection.execute(sa.select(categories)).mappings())
    categories_by_course: dict[Any, list[Mapping[str, Any]]] = {}
    for category in category_rows:
        categories_by_course.setdefault(category["course_id"], []).append(category)

    default_category_by_course: dict[Any, Any] = {}
    for course_id in connection.execute(
        sa.select(courses.c.id).order_by(courses.c.id)
    ).scalars():
        course_categories = categories_by_course.get(course_id, [])
        default = next(
            (
                category
                for category in course_categories
                if _policy(category["calculation_policy"]).get(
                    DEFAULT_CATEGORY_POLICY_KEY
                )
                == DEFAULT_CATEGORY_POLICY_VALUE
            ),
            None,
        )
        if default is not None:
            default_category_by_course[course_id] = default["id"]
            continue
        category_id = uuid4()
        position = (
            max(
                (int(category["position"]) for category in course_categories),
                default=-1,
            )
            + 1
        )
        connection.execute(
            categories.insert().values(
                id=category_id,
                course_id=course_id,
                parent_category_id=None,
                name="Assignments",
                description="Automatically linked assignment grades.",
                position=position,
                aggregation_strategy="sum",
                weight=None,
                calculation_policy={
                    DEFAULT_CATEGORY_POLICY_KEY: DEFAULT_CATEGORY_POLICY_VALUE,
                    CREATED_BY_BACKFILL_KEY: BACKFILL_MARKER_VALUE,
                },
                copied_from_id=None,
                created_at=now,
                updated_at=now,
            )
        )
        default_category_by_course[course_id] = category_id

    item_rows = list(connection.execute(sa.select(items)).mappings())
    item_by_assignment = {
        (item["course_id"], item["source_id"]): item
        for item in item_rows
        if item["source_type"] == "assignment"
    }
    next_item_position: dict[Any, int] = {}
    for item in item_rows:
        next_item_position[item["course_id"]] = max(
            next_item_position.get(item["course_id"], 0), int(item["position"]) + 1
        )

    assignment_rows = list(
        connection.execute(
            sa.select(assignments).order_by(
                assignments.c.course_id,
                assignments.c.title,
                assignments.c.id,
            )
        ).mappings()
    )
    grade_item_id_by_assignment: dict[Any, Any] = {}
    item_course_by_id = {item["id"]: item["course_id"] for item in item_rows}
    for assignment in assignment_rows:
        course_id = assignment["course_id"]
        existing = item_by_assignment.get((course_id, assignment["id"]))
        if existing is not None:
            grade_item_id_by_assignment[assignment["id"]] = existing["id"]
            if existing["category_id"] is None:
                policy = _policy(existing["calculation_policy"])
                policy[CATEGORY_ASSIGNED_BY_BACKFILL_KEY] = BACKFILL_MARKER_VALUE
                connection.execute(
                    items.update()
                    .where(items.c.id == existing["id"])
                    .values(
                        category_id=default_category_by_course[course_id],
                        calculation_policy=policy,
                        updated_at=now,
                    )
                )
            continue
        item_id = uuid4()
        position = next_item_position.get(course_id, 0)
        next_item_position[course_id] = position + 1
        connection.execute(
            items.insert().values(
                id=item_id,
                course_id=course_id,
                category_id=default_category_by_course[course_id],
                title=assignment["title"],
                description=assignment["description"],
                position=position,
                max_points=_max_points(assignment["max_grade"]),
                weight=None,
                calculation_policy={
                    CREATED_BY_BACKFILL_KEY: BACKFILL_MARKER_VALUE,
                },
                release_policy={},
                source_type="assignment",
                source_id=assignment["id"],
                copied_from_id=None,
                created_at=now,
                updated_at=now,
            )
        )
        grade_item_id_by_assignment[assignment["id"]] = item_id
        item_course_by_id[item_id] = course_id

    user_by_submitter = {
        row["id"]: row["user_id"]
        for row in connection.execute(sa.select(submitters)).mappings()
        if row["user_id"] is not None and not row["is_synthetic"]
    }
    student_enrollments = {
        (row["course_id"], row["user_id"])
        for row in connection.execute(sa.select(enrollments)).mappings()
        if row["role"] == "student" and row["status"] == "active"
    }
    course_by_assignment = {
        assignment["id"]: assignment["course_id"] for assignment in assignment_rows
    }

    latest_by_assignment_user: dict[tuple[Any, Any], Mapping[str, Any]] = {}
    for submission in submission_rows:
        user_id = user_by_submitter.get(submission["submitter_id"])
        course_id = course_by_assignment.get(submission["assignment_id"])
        if (
            user_id is None
            or course_id is None
            or (course_id, user_id) not in student_enrollments
        ):
            continue
        key = (submission["assignment_id"], user_id)
        current = latest_by_assignment_user.get(key)
        if current is None or _submission_rank(submission, now) > _submission_rank(
            current, now
        ):
            latest_by_assignment_user[key] = submission

    existing_entries = {
        (row["grade_item_id"], row["user_id"]): row
        for row in connection.execute(sa.select(entries)).mappings()
    }
    processed_existing_keys: set[tuple[Any, Any]] = set()
    for (assignment_id, user_id), submission in latest_by_assignment_user.items():
        item_id = grade_item_id_by_assignment[assignment_id]
        entry_key = (item_id, user_id)
        existing_entry = existing_entries.get(entry_key)
        is_released = submission["status"] in {"returned", "excused"}
        is_excused = submission["status"] == "excused"
        points = None if is_excused else _published_points(submission)
        has_canonical_entry = is_released and (is_excused or points is not None)
        if existing_entry is not None:
            processed_existing_keys.add(entry_key)
            parity = (
                has_canonical_entry
                and existing_entry["status"] == ("excused" if is_excused else "graded")
                and existing_entry["points_earned"] == points
                and existing_entry["release_state"] == "released"
                and existing_entry["source_type"] == "submission"
                and existing_entry["source_id"] == submission["id"]
            )
            if not parity:
                raise ValueError(
                    "Existing GradeEntry does not match canonical latest submission: "
                    f"{existing_entry['id']}"
                )
            continue
        if not has_canonical_entry:
            continue
        released_at = _aware(
            submission["returned_at"] or submission["submitted_at"], now
        )
        connection.execute(
            entries.insert().values(
                id=uuid4(),
                course_id=course_by_assignment[assignment_id],
                grade_item_id=item_id,
                user_id=user_id,
                status="excused" if is_excused else "graded",
                points_earned=points,
                release_state="released",
                released_at=released_at,
                graded_at=released_at,
                source_type="submission",
                source_id=submission["id"],
                source_version=(
                    f"{ENTRY_SOURCE_VERSION_PREFIX}"
                    f"{int(submission['attempt_number'] or 0)}"
                ),
                recorded_by_user_id=None,
                note=None,
                created_at=now,
                updated_at=now,
            )
        )

    assignment_by_item = {
        item_id: assignment_id
        for assignment_id, item_id in grade_item_id_by_assignment.items()
    }
    for entry_key, existing_entry in existing_entries.items():
        item_id, user_id = entry_key
        assignment_id = assignment_by_item.get(item_id)
        course_id = item_course_by_id.get(item_id)
        if (
            assignment_id is not None
            and course_id is not None
            and (course_id, user_id) in student_enrollments
            and entry_key not in processed_existing_keys
        ):
            raise ValueError(
                "Existing GradeEntry has no canonical latest submission: "
                f"{existing_entry['id']}"
            )


def downgrade() -> None:
    connection = op.get_bind()
    tables = _tables()
    categories = tables["categories"]
    items = tables["items"]
    entries = tables["entries"]

    connection.execute(
        entries.delete().where(
            entries.c.source_version.like(f"{ENTRY_SOURCE_VERSION_PREFIX}%")
        )
    )
    remaining_entry_item_ids = set(
        connection.execute(sa.select(entries.c.grade_item_id)).scalars()
    )
    for item in connection.execute(sa.select(items)).mappings():
        policy = _policy(item["calculation_policy"])
        created = policy.get(CREATED_BY_BACKFILL_KEY) == BACKFILL_MARKER_VALUE
        assigned = (
            policy.get(CATEGORY_ASSIGNED_BY_BACKFILL_KEY) == BACKFILL_MARKER_VALUE
        )
        if created and item["id"] not in remaining_entry_item_ids:
            connection.execute(items.delete().where(items.c.id == item["id"]))
            continue
        if created or assigned:
            policy.pop(CREATED_BY_BACKFILL_KEY, None)
            policy.pop(CATEGORY_ASSIGNED_BY_BACKFILL_KEY, None)
            values: dict[str, Any] = {"calculation_policy": policy}
            if assigned:
                values["category_id"] = None
            connection.execute(
                items.update().where(items.c.id == item["id"]).values(**values)
            )

    referenced_category_ids = set(
        connection.execute(
            sa.select(items.c.category_id).where(items.c.category_id.is_not(None))
        ).scalars()
    )
    for category in connection.execute(sa.select(categories)).mappings():
        policy = _policy(category["calculation_policy"])
        if policy.get(CREATED_BY_BACKFILL_KEY) != BACKFILL_MARKER_VALUE:
            continue
        if category["id"] not in referenced_category_ids:
            connection.execute(
                categories.delete().where(categories.c.id == category["id"])
            )
            continue
        policy.pop(CREATED_BY_BACKFILL_KEY, None)
        connection.execute(
            categories.update()
            .where(categories.c.id == category["id"])
            .values(calculation_policy=policy)
        )
