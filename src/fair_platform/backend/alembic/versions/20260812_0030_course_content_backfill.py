"""Backfill a default content outline for existing courses.

Revision ID: 20260812_0030
Revises: 20260812_0029
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4, uuid5

import sqlalchemy as sa
from alembic import op


revision: str = "20260812_0030"
down_revision: str = "20260812_0029"
branch_labels = None
depends_on = None


BACKFILL_SCHEMA_URI = "urn:fair:lms:course-item:assignment-backfill:v1"
DEFAULT_SECTION_TITLE = "Course content"
DEFAULT_SECTION_SUMMARY = "Assignments already available in this course."
BACKFILL_SECTION_NAMESPACE = UUID("5d3412f8-9294-5de9-9b8f-87f4b1218e4a")


def _backfill_section_id(course_id: object) -> UUID:
    canonical_course_id = (
        course_id if isinstance(course_id, UUID) else UUID(str(course_id))
    )
    return uuid5(BACKFILL_SECTION_NAMESPACE, canonical_course_id.hex)


def upgrade() -> None:
    connection = op.get_bind()
    now = datetime.now(timezone.utc)
    courses = sa.table("courses", sa.column("id", sa.UUID()))
    assignments = sa.table(
        "assignments",
        sa.column("id", sa.UUID()),
        sa.column("course_id", sa.UUID()),
        sa.column("title", sa.String()),
        sa.column("status", sa.String()),
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

    for course_id in connection.execute(
        sa.select(courses.c.id).order_by(courses.c.id)
    ).scalars():
        existing_resource_ids = set(
            connection.execute(
                sa.select(items.c.resource_id).where(
                    items.c.course_id == course_id,
                    items.c.resource_type == "assignment",
                    items.c.resource_id.is_not(None),
                )
            ).scalars()
        )
        course_assignments = list(
            connection.execute(
                sa.select(
                    assignments.c.id,
                    assignments.c.title,
                    assignments.c.status,
                )
                .where(assignments.c.course_id == course_id)
                .order_by(assignments.c.title, assignments.c.id)
            ).mappings()
        )
        missing_assignments = [
            assignment
            for assignment in course_assignments
            if assignment["id"] not in existing_resource_ids
        ]
        if not missing_assignments:
            continue

        section_id = _backfill_section_id(course_id)
        existing_sections = list(
            connection.execute(
                sa.select(sections.c.id, sections.c.position).where(
                    sections.c.course_id == course_id
                )
            ).mappings()
        )
        if not any(section["id"] == section_id for section in existing_sections):
            section_position = (
                max(
                    (int(section["position"]) for section in existing_sections),
                    default=-1,
                )
                + 1
            )
            connection.execute(
                sections.insert().values(
                    id=section_id,
                    course_id=course_id,
                    title=DEFAULT_SECTION_TITLE,
                    summary=DEFAULT_SECTION_SUMMARY,
                    position=section_position,
                    visibility="published",
                    copied_from_id=None,
                    created_at=now,
                    updated_at=now,
                )
            )
        maximum_item_position = connection.execute(
            sa.select(sa.func.max(items.c.position)).where(
                items.c.section_id == section_id
            )
        ).scalar()
        next_item_position = (
            int(maximum_item_position) + 1 if maximum_item_position is not None else 0
        )
        for offset, assignment in enumerate(missing_assignments):
            connection.execute(
                items.insert().values(
                    id=uuid4(),
                    course_id=course_id,
                    section_id=section_id,
                    title=assignment["title"],
                    position=next_item_position + offset,
                    kind="assignment",
                    visibility=(
                        "published" if assignment["status"] == "published" else "draft"
                    ),
                    resource_type="assignment",
                    resource_id=assignment["id"],
                    copied_from_id=None,
                    payload_schema_uri=BACKFILL_SCHEMA_URI,
                    payload={},
                    created_at=now,
                    updated_at=now,
                )
            )


def downgrade() -> None:
    connection = op.get_bind()
    courses = sa.table("courses", sa.column("id", sa.UUID()))
    items = sa.table(
        "course_items",
        sa.column("id", sa.UUID()),
        sa.column("section_id", sa.UUID()),
        sa.column("payload_schema_uri", sa.String()),
    )
    sections = sa.table(
        "course_sections",
        sa.column("id", sa.UUID()),
    )
    backfill_section_ids = set(
        connection.execute(
            sa.select(items.c.section_id).where(
                items.c.payload_schema_uri == BACKFILL_SCHEMA_URI
            )
        ).scalars()
    )
    backfill_section_ids.update(
        _backfill_section_id(course_id)
        for course_id in connection.execute(sa.select(courses.c.id)).scalars()
    )
    connection.execute(
        items.delete().where(items.c.payload_schema_uri == BACKFILL_SCHEMA_URI)
    )
    for section_id in backfill_section_ids:
        has_remaining_items = connection.execute(
            sa.select(items.c.id).where(items.c.section_id == section_id).limit(1)
        ).first()
        if has_remaining_items is not None:
            continue
        connection.execute(sections.delete().where(sections.c.id == section_id))
