"""Clear obsolete released assignment grades after an ungraded resubmission.

Revision ID: 20261025_0037
Revises: 20260830_0036
"""

import sqlalchemy as sa
from alembic import op


revision: str = "20261025_0037"
down_revision: str = "20260830_0036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    entries = sa.table(
        "grade_entries",
        sa.column("id", sa.UUID()),
        sa.column("grade_item_id", sa.UUID()),
        sa.column("course_id", sa.UUID()),
        sa.column("user_id", sa.UUID()),
        sa.column("source_type", sa.String()),
        sa.column("source_id", sa.UUID()),
        sa.column("release_state", sa.String()),
    )
    items = sa.table(
        "grade_items",
        sa.column("id", sa.UUID()),
        sa.column("course_id", sa.UUID()),
        sa.column("source_type", sa.String()),
        sa.column("source_id", sa.UUID()),
    )
    submissions = sa.table(
        "submissions",
        sa.column("id", sa.UUID()),
        sa.column("assignment_id", sa.UUID()),
        sa.column("submitter_id", sa.UUID()),
        sa.column("attempt_number", sa.Integer()),
        sa.column("submitted_at", sa.DateTime()),
        sa.column("status", sa.String()),
        sa.column("published_score", sa.Float()),
    )
    submitters = sa.table(
        "submitters",
        sa.column("id", sa.UUID()),
        sa.column("user_id", sa.UUID()),
        sa.column("is_synthetic", sa.Boolean()),
    )
    enrollments = sa.table(
        "enrollments",
        sa.column("course_id", sa.UUID()),
        sa.column("user_id", sa.UUID()),
        sa.column("role", sa.String()),
        sa.column("status", sa.String()),
    )
    # Match runtime ranking, including tied attempts and duplicate real submitters.
    ranked = (
        sa.select(
            submissions.c.id,
            submissions.c.assignment_id,
            submitters.c.user_id,
            submissions.c.status,
            submissions.c.published_score,
            sa.func.row_number()
            .over(
                partition_by=(submissions.c.assignment_id, submitters.c.user_id),
                order_by=(
                    submissions.c.attempt_number.desc().nulls_last(),
                    submissions.c.submitted_at.desc().nulls_last(),
                    submissions.c.id.desc(),
                ),
            )
            .label("recency"),
        )
        .select_from(
            submissions.join(submitters, submissions.c.submitter_id == submitters.c.id)
        )
        .where(submitters.c.is_synthetic.is_(False), submitters.c.user_id.is_not(None))
        .subquery()
    )
    stale_ids = (
        sa.select(entries.c.id)
        .select_from(
            entries.join(items, items.c.id == entries.c.grade_item_id)
            .join(
                ranked,
                sa.and_(
                    ranked.c.assignment_id == items.c.source_id,
                    ranked.c.user_id == entries.c.user_id,
                    ranked.c.recency == 1,
                ),
            )
            .join(
                submissions,
                sa.and_(
                    submissions.c.id == entries.c.source_id,
                    submissions.c.assignment_id == items.c.source_id,
                ),
            )
            .join(
                submitters,
                sa.and_(
                    submitters.c.id == submissions.c.submitter_id,
                    submitters.c.user_id == entries.c.user_id,
                    submitters.c.is_synthetic.is_(False),
                ),
            )
            .join(
                enrollments,
                sa.and_(
                    enrollments.c.course_id == entries.c.course_id,
                    enrollments.c.user_id == entries.c.user_id,
                    enrollments.c.role == "student",
                    enrollments.c.status == "active",
                ),
            )
        )
        .where(
            items.c.source_type == "assignment",
            items.c.course_id == entries.c.course_id,
            entries.c.source_type == "submission",
            entries.c.release_state == "released",
            entries.c.source_id != ranked.c.id,
            ranked.c.status != "excused",
            sa.or_(ranked.c.status != "returned", ranked.c.published_score.is_(None)),
        )
    )
    op.get_bind().execute(entries.delete().where(entries.c.id.in_(stale_ids)))


def downgrade() -> None:
    # Derived entries are not restored: that would reintroduce obsolete grades.
    # All original submissions, published scores, and feedback remain intact.
    pass
