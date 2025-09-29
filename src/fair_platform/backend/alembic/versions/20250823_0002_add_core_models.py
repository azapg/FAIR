"""Add core models and align users schema

Revision ID: 20250823_0002
Revises: 20250818_0001
Create Date: 2025-08-23
"""

from __future__ import annotations

from alembic import op  # type: ignore
import sqlalchemy as sa
import uuid


# revision identifiers, used by Alembic.
revision = "20250823_0002"
down_revision = "20250818_0001"
branch_labels = None
depends_on = None


def _drop_user_role_enum_if_exists(conn) -> None:
    # Best effort: drop the old enum type if on a dialect that supports it
    try:
        if conn.dialect.name != "sqlite":
            sa.Enum(name="user_role").drop(conn, checkfirst=True)
    except Exception:
        # Ignore if not present or unsupported
        pass


def _migrate_users_table_to_uuid_and_string_role() -> None:
    conn = op.get_bind()

    # Create a new users table with the desired schema
    op.create_table(
        "users_new",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "role", sa.String(length=50), nullable=False, server_default="student"
        ),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    # Copy data from old users table if it exists
    inspector = sa.inspect(conn)
    if "users" in inspector.get_table_names():
        try:
            rows = conn.execute(
                sa.text("SELECT email, name, role FROM users")
            ).fetchall()
        except Exception:
            rows = []
        if rows:
            for r in rows:
                # r.role might be an enum or string; coerce to string
                role_str = str(r.role)
                conn.execute(
                    sa.text(
                        "INSERT INTO users_new (id, email, name, role) VALUES (:id, :email, :name, :role)"
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "email": r.email,
                        "name": r.name,
                        "role": role_str,
                    },
                )

        # Drop the old users table and replace it with the new one
        op.drop_table("users")

    # Rename the new table to users
    op.rename_table("users_new", "users")

    # Recreate indexes that existed in the initial migration
    op.create_index("ix_users_email", "users", ["email"], unique=False)
    op.create_index("ix_users_id", "users", ["id"], unique=False)

    # Best-effort cleanup of old enum type if present (non-sqlite)
    _drop_user_role_enum_if_exists(conn)


def upgrade() -> None:
    # 1) Align users table with current model (UUID id, string role)
    _migrate_users_table_to_uuid_and_string_role()

    # 2) Create core domain tables
    op.create_table(
        "courses",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "instructor_id", sa.UUID(), sa.ForeignKey("users.id"), nullable=False
        ),
    )
    op.create_index(
        "ix_courses_instructor_id", "courses", ["instructor_id"], unique=False
    )

    op.create_table(
        "assignments",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column("course_id", sa.UUID(), sa.ForeignKey("courses.id"), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("deadline", sa.TIMESTAMP(), nullable=True),
        sa.Column("max_grade", sa.JSON(), nullable=False),
    )
    op.create_index(
        "ix_assignments_course_id", "assignments", ["course_id"], unique=False
    )

    op.create_table(
        "workflows",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column("course_id", sa.UUID(), sa.ForeignKey("courses.id"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False),
    )
    op.create_index("ix_workflows_course_id", "workflows", ["course_id"], unique=False)
    op.create_index(
        "ix_workflows_created_by", "workflows", ["created_by"], unique=False
    )

    op.create_table(
        "workflow_runs",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column(
            "workflow_id", sa.UUID(), sa.ForeignKey("workflows.id"), nullable=False
        ),
        sa.Column("run_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("started_at", sa.TIMESTAMP(), nullable=False),
        sa.Column("finished_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("logs", sa.JSON(), nullable=True),
    )
    op.create_index(
        "ix_workflow_runs_workflow_id", "workflow_runs", ["workflow_id"], unique=False
    )
    op.create_index(
        "ix_workflow_runs_run_by", "workflow_runs", ["run_by"], unique=False
    )

    op.create_table(
        "submissions",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column(
            "assignment_id", sa.UUID(), sa.ForeignKey("assignments.id"), nullable=False
        ),
        sa.Column("submitter_id", sa.UUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("submitted_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column(
            "official_run_id",
            sa.UUID(),
            sa.ForeignKey("workflow_runs.id"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_submissions_assignment_id", "submissions", ["assignment_id"], unique=False
    )
    op.create_index(
        "ix_submissions_submitter_id", "submissions", ["submitter_id"], unique=False
    )
    op.create_index(
        "ix_submissions_official_run_id",
        "submissions",
        ["official_run_id"],
        unique=False,
    )

    op.create_table(
        "submission_workflow_runs",
        sa.Column(
            "submission_id",
            sa.UUID(),
            sa.ForeignKey("submissions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "workflow_run_id",
            sa.UUID(),
            sa.ForeignKey("workflow_runs.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )

    op.create_table(
        "plugins",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("author", sa.String(), nullable=True),
        sa.Column("version", sa.String(), nullable=True),
        sa.Column("hash", sa.String(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id", "hash"),
    )


def downgrade() -> None:
    # Drop newly added tables in reverse dependency order
    op.drop_table("plugins")
    op.drop_table("submission_workflow_runs")
    op.drop_index("ix_submissions_official_run_id", table_name="submissions")
    op.drop_index("ix_submissions_submitter_id", table_name="submissions")
    op.drop_index("ix_submissions_assignment_id", table_name="submissions")
    op.drop_table("submissions")
    op.drop_index("ix_workflow_runs_run_by", table_name="workflow_runs")
    op.drop_index("ix_workflow_runs_workflow_id", table_name="workflow_runs")
    op.drop_table("workflow_runs")
    op.drop_index("ix_workflows_created_by", table_name="workflows")
    op.drop_index("ix_workflows_course_id", table_name="workflows")
    op.drop_table("workflows")
    op.drop_index("ix_assignments_course_id", table_name="assignments")
    op.drop_table("assignments")
    op.drop_index("ix_courses_instructor_id", table_name="courses")
    op.drop_table("courses")

    # Best-effort: revert users table to the original schema (Integer id, Enum role)
    conn = op.get_bind()

    # Rename current users to a temp table
    op.rename_table("users", "users_uuid")

    # Recreate enum type for role (skip for sqlite)
    if conn.dialect.name != "sqlite":
        user_role_enum = sa.Enum("professor", "student", "admin", name="user_role")
        user_role_enum.create(conn, checkfirst=True)
        role_col_type = user_role_enum
    else:
        role_col_type = sa.String(length=50)

    # Recreate the old users table
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("role", role_col_type, nullable=False, server_default="student"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    # Copy data back with fresh integer ids (as downgrade is best-effort)
    try:
        rows = conn.execute(
            sa.text("SELECT email, name, role FROM users_uuid")
        ).fetchall()
    except Exception:
        rows = []
    if rows:
        new_id = 1
        for r in rows:
            conn.execute(
                sa.text(
                    "INSERT INTO users (id, email, name, role) VALUES (:id, :email, :name, :role)"
                ),
                {"id": new_id, "email": r.email, "name": r.name, "role": str(r.role)},
            )
            new_id += 1

    # Drop temp table and recreate indexes
    op.drop_table("users_uuid")
    op.create_index("ix_users_email", "users", ["email"], unique=False)
    op.create_index("ix_users_id", "users", ["id"], unique=False)
