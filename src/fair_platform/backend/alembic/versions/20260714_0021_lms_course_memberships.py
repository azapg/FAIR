"""Add LMS course memberships and archival metadata.

Revision ID: 20260714_0021
Revises: 20260713_0020
Create Date: 2026-07-13
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from alembic import op  # type: ignore
import sqlalchemy as sa


revision = "20260714_0021"
down_revision = "20260713_0020"
branch_labels = None
depends_on = None


def _column_names(table_name: str) -> set[str]:
    return {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)
    }


def upgrade() -> None:
    expected_course_columns = {
        "section",
        "term",
        "is_archived",
        "created_at",
        "updated_at",
    }
    expected_enrollment_columns = {"role", "status", "updated_at"}
    course_columns = _column_names("courses")
    enrollment_columns = _column_names("enrollments")
    present = (expected_course_columns & course_columns) | (
        expected_enrollment_columns & enrollment_columns
    )
    if expected_course_columns <= course_columns and expected_enrollment_columns <= enrollment_columns:
        return
    if present:
        raise RuntimeError("LMS course-membership migration is only partially applied")

    with op.batch_alter_table("courses") as batch_op:
        batch_op.add_column(sa.Column("section", sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column("term", sa.String(length=128), nullable=True))
        batch_op.add_column(
            sa.Column("is_archived", sa.Boolean(), server_default=sa.false(), nullable=False)
        )
        batch_op.add_column(
            sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False)
        )
        batch_op.add_column(
            sa.Column("updated_at", sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False)
        )

    with op.batch_alter_table("enrollments") as batch_op:
        batch_op.add_column(
            sa.Column("role", sa.String(length=32), server_default="student", nullable=False)
        )
        batch_op.add_column(
            sa.Column("status", sa.String(length=32), server_default="active", nullable=False)
        )
        batch_op.add_column(
            sa.Column("updated_at", sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False)
        )
        batch_op.create_index("ix_enrollments_course_status", ["course_id", "status"])
        batch_op.create_index("ix_enrollments_course_role", ["course_id", "role"])

    bind = op.get_bind()
    courses = bind.execute(sa.text("SELECT id, instructor_id FROM courses")).mappings()
    for course in courses:
        existing = bind.execute(
            sa.text(
                "SELECT id FROM enrollments WHERE course_id = :course_id AND user_id = :user_id"
            ),
            {"course_id": course["id"], "user_id": course["instructor_id"]},
        ).first()
        if existing:
            bind.execute(
                sa.text(
                    "UPDATE enrollments SET role = 'owner', status = 'active', updated_at = :now "
                    "WHERE id = :id"
                ),
                {"id": existing[0], "now": datetime.utcnow()},
            )
        else:
            bind.execute(
                sa.text(
                    "INSERT INTO enrollments "
                    "(id, user_id, course_id, enrolled_at, role, status, updated_at) "
                    "VALUES (:id, :user_id, :course_id, :now, 'owner', 'active', :now)"
                ),
                {
                    "id": str(uuid4()),
                    "user_id": course["instructor_id"],
                    "course_id": course["id"],
                    "now": datetime.utcnow(),
                },
            )


def downgrade() -> None:
    with op.batch_alter_table("enrollments") as batch_op:
        batch_op.drop_index("ix_enrollments_course_role")
        batch_op.drop_index("ix_enrollments_course_status")
        batch_op.drop_column("updated_at")
        batch_op.drop_column("status")
        batch_op.drop_column("role")

    with op.batch_alter_table("courses") as batch_op:
        batch_op.drop_column("updated_at")
        batch_op.drop_column("created_at")
        batch_op.drop_column("is_archived")
        batch_op.drop_column("term")
        batch_op.drop_column("section")
