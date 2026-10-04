from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import sqlalchemy as sa
from alembic import command
from sqlalchemy import create_engine

from fair_platform.backend.data.migrations import (
    build_alembic_config,
    run_migrations_to_head,
    run_migrations_to_revision,
)


P0_REVISION = "20260812_0029"


def _seed_pre_content_data(database_url: str) -> dict[str, object]:
    engine = create_engine(database_url)
    users = sa.table(
        "users",
        sa.column("id", sa.UUID()),
        sa.column("name", sa.String()),
        sa.column("email", sa.String()),
        sa.column("role", sa.String()),
        sa.column("password_hash", sa.String()),
        sa.column("settings", sa.JSON()),
        sa.column("is_verified", sa.Boolean()),
    )
    courses = sa.table(
        "courses",
        sa.column("id", sa.UUID()),
        sa.column("name", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("instructor_id", sa.UUID()),
        sa.column("organization_id", sa.UUID()),
        sa.column("enrollment_code", sa.String()),
        sa.column("is_enrollment_enabled", sa.Boolean()),
        sa.column("section", sa.String()),
        sa.column("term", sa.String()),
        sa.column("is_archived", sa.Boolean()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    assignments = sa.table(
        "assignments",
        sa.column("id", sa.UUID()),
        sa.column("course_id", sa.UUID()),
        sa.column("title", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("deadline", sa.DateTime(timezone=True)),
        sa.column("max_grade", sa.JSON()),
        sa.column("status", sa.String()),
        sa.column("published_at", sa.DateTime(timezone=True)),
        sa.column("allow_resubmissions", sa.Boolean()),
    )
    sections = sa.table(
        "course_sections",
        sa.column("id", sa.UUID()),
        sa.column("course_id", sa.UUID()),
        sa.column("title", sa.String()),
        sa.column("summary", sa.Text()),
        sa.column("position", sa.Integer()),
        sa.column("visibility", sa.String()),
        sa.column("copied_from_id", sa.UUID()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    items = sa.table(
        "course_items",
        sa.column("id", sa.UUID()),
        sa.column("course_id", sa.UUID()),
        sa.column("section_id", sa.UUID()),
        sa.column("title", sa.String()),
        sa.column("position", sa.Integer()),
        sa.column("kind", sa.String()),
        sa.column("visibility", sa.String()),
        sa.column("resource_type", sa.String()),
        sa.column("resource_id", sa.UUID()),
        sa.column("copied_from_id", sa.UUID()),
        sa.column("payload_schema_uri", sa.String()),
        sa.column("payload", sa.JSON()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    owner_id = uuid4()
    populated_course_id = uuid4()
    empty_course_id = uuid4()
    teacher_section_id = uuid4()
    same_title_section_id = uuid4()
    linked_assignment_id = uuid4()
    missing_assignment_id = uuid4()
    linked_item_id = uuid4()
    now = datetime.now(timezone.utc)
    with engine.begin() as connection:
        connection.execute(
            users.insert().values(
                id=owner_id,
                name="Backfill Owner",
                email=f"backfill-{uuid4()}@example.test",
                role="instructor",
                password_hash=None,
                is_verified=True,
                settings={},
            )
        )
        for course_id, name in (
            (populated_course_id, "Existing assignments"),
            (empty_course_id, "No assignments"),
        ):
            connection.execute(
                courses.insert().values(
                    id=course_id,
                    name=name,
                    description=None,
                    instructor_id=owner_id,
                    organization_id=None,
                    enrollment_code=None,
                    is_enrollment_enabled=True,
                    section=None,
                    term=None,
                    is_archived=False,
                    created_at=now,
                    updated_at=now,
                )
            )
        for assignment_id, title, assignment_status in (
            (linked_assignment_id, "Already placed", "published"),
            (missing_assignment_id, "Needs placement", "draft"),
        ):
            connection.execute(
                assignments.insert().values(
                    id=assignment_id,
                    course_id=populated_course_id,
                    title=title,
                    description=None,
                    deadline=None,
                    max_grade={"type": "points", "value": 100},
                    status=assignment_status,
                    published_at=None,
                    allow_resubmissions=True,
                )
            )
        connection.execute(
            sections.insert(),
            [
                {
                    "id": teacher_section_id,
                    "course_id": populated_course_id,
                    "title": "Existing outline",
                    "summary": "Teacher-authored content",
                    "position": 0,
                    "visibility": "published",
                    "copied_from_id": None,
                    "created_at": now,
                    "updated_at": now,
                },
                {
                    "id": same_title_section_id,
                    "course_id": empty_course_id,
                    "title": "Course content",
                    "summary": "Assignments already available in this course.",
                    "position": 0,
                    "visibility": "published",
                    "copied_from_id": None,
                    "created_at": now,
                    "updated_at": now,
                },
            ],
        )
        connection.execute(
            items.insert().values(
                id=linked_item_id,
                course_id=populated_course_id,
                section_id=teacher_section_id,
                title="Already placed",
                position=0,
                kind="assignment",
                visibility="published",
                resource_type="assignment",
                resource_id=linked_assignment_id,
                copied_from_id=None,
                payload_schema_uri="urn:test:existing-assignment:v1",
                payload={},
                created_at=now,
                updated_at=now,
            )
        )
    engine.dispose()
    return {
        "populated_course_id": populated_course_id,
        "empty_course_id": empty_course_id,
        "teacher_section_id": teacher_section_id,
        "same_title_section_id": same_title_section_id,
        "linked_assignment_id": linked_assignment_id,
        "missing_assignment_id": missing_assignment_id,
        "linked_item_id": linked_item_id,
    }


def _content_rows(database_url: str) -> tuple[list[dict], list[dict]]:
    engine = create_engine(database_url)
    # SQLite reflects UUID columns as NUMERIC, which applies a Decimal result
    # processor to the stored UUID text. Keep the rehearsal dialect-neutral by
    # declaring only the columns whose values the assertions inspect.
    sections = sa.table(
        "course_sections",
        sa.column("id", sa.UUID()),
        sa.column("course_id", sa.UUID()),
        sa.column("position", sa.Integer()),
    )
    items = sa.table(
        "course_items",
        sa.column("id", sa.UUID()),
        sa.column("course_id", sa.UUID()),
        sa.column("title", sa.String()),
        sa.column("position", sa.Integer()),
        sa.column("kind", sa.String()),
        sa.column("visibility", sa.String()),
        sa.column("resource_type", sa.String()),
        sa.column("resource_id", sa.UUID()),
        sa.column("payload_schema_uri", sa.String()),
    )
    with engine.connect() as connection:
        section_rows = list(
            connection.execute(
                sa.select(sections).order_by(sections.c.course_id)
            ).mappings()
        )
        item_rows = list(
            connection.execute(sa.select(items).order_by(items.c.title)).mappings()
        )
    engine.dispose()
    return section_rows, item_rows


def test_backfill_upgrade_downgrade_and_reupgrade(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'content-backfill.sqlite').as_posix()}"
    run_migrations_to_revision(P0_REVISION, database_url)
    seeded = _seed_pre_content_data(database_url)

    run_migrations_to_head(database_url)
    sections, items = _content_rows(database_url)
    assert len(sections) == 3
    populated_sections = [
        row for row in sections if row["course_id"] == seeded["populated_course_id"]
    ]
    assert {row["position"] for row in populated_sections} == {0, 1}
    assert any(row["id"] == seeded["teacher_section_id"] for row in sections)
    assert any(row["id"] == seeded["same_title_section_id"] for row in sections)
    assert len(items) == 2
    assert {row["resource_id"] for row in items} == {
        seeded["linked_assignment_id"],
        seeded["missing_assignment_id"],
    }
    existing = next(row for row in items if row["id"] == seeded["linked_item_id"])
    assert existing["payload_schema_uri"] == "urn:test:existing-assignment:v1"
    backfilled = next(
        row for row in items if row["resource_id"] == seeded["missing_assignment_id"]
    )
    assert backfilled["visibility"] == "draft"
    assert all(row["resource_type"] == "assignment" for row in items)

    command.downgrade(build_alembic_config(database_url), P0_REVISION)
    sections, items = _content_rows(database_url)
    assert {row["id"] for row in sections} == {
        seeded["teacher_section_id"],
        seeded["same_title_section_id"],
    }
    assert [row["id"] for row in items] == [seeded["linked_item_id"]]

    run_migrations_to_head(database_url)
    sections, items = _content_rows(database_url)
    assert len(sections) == 3
    assert len(items) == 2
