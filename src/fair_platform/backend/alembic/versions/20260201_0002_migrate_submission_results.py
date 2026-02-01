"""Migrate legacy submission_results into submission_events and draft fields.

Revision ID: 20260201_0002
Revises: 11fc834d5d46
Create Date: 2026-02-01
"""

from __future__ import annotations

from datetime import datetime
import uuid

from alembic import op  # type: ignore
import sqlalchemy as sa
from sqlalchemy import func


# revision identifiers, used by Alembic.
revision = "20260201_0002"
down_revision = "11fc834d5d46"
branch_labels = None
depends_on = None


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def upgrade() -> None:
    bind = op.get_bind()

    submission_results = sa.table(
        "submission_results",
        sa.column("id", sa.UUID()),
        sa.column("submission_id", sa.UUID()),
        sa.column("workflow_run_id", sa.UUID()),
        sa.column("transcription", sa.Text()),
        sa.column("transcription_confidence", sa.Float()),
        sa.column("transcribed_at", sa.TIMESTAMP()),
        sa.column("score", sa.Float()),
        sa.column("feedback", sa.Text()),
        sa.column("grading_meta", sa.JSON()),
        sa.column("graded_at", sa.TIMESTAMP()),
    )

    submissions = sa.table(
        "submissions",
        sa.column("id", sa.UUID()),
        sa.column("draft_score", sa.Float()),
        sa.column("draft_feedback", sa.Text()),
    )

    submission_events = sa.table(
        "submission_events",
        sa.column("id", sa.UUID()),
        sa.column("submission_id", sa.UUID()),
        sa.column("event_type", sa.String()),
        sa.column("actor_id", sa.UUID()),
        sa.column("workflow_run_id", sa.UUID()),
        sa.column("details", sa.JSON()),
        sa.column("created_at", sa.TIMESTAMP()),
    )

    order_key = func.coalesce(
        submission_results.c.graded_at,
        submission_results.c.transcribed_at,
    )

    rows = bind.execute(
        sa.select(submission_results).order_by(
            submission_results.c.submission_id,
            order_key,
            submission_results.c.id,
        )
    ).mappings()

    seen_first: set[uuid.UUID] = set()
    latest_by_submission: dict[uuid.UUID, dict] = {}

    for row in rows:
        submission_id = row["submission_id"]
        event_type = (
            "initial_result" if submission_id not in seen_first else "ai_graded"
        )
        seen_first.add(submission_id)

        created_at = (
            row["graded_at"]
            or row["transcribed_at"]
            or datetime.utcnow()
        )

        details = {
            "source": "submission_results",
            "legacy_result_id": str(row["id"]),
            "score": row["score"],
            "feedback": row["feedback"],
            "grading_meta": row["grading_meta"],
            "graded_at": _iso(row["graded_at"]),
            "transcription": row["transcription"],
            "transcription_confidence": row["transcription_confidence"],
            "transcribed_at": _iso(row["transcribed_at"]),
        }

        bind.execute(
            submission_events.insert().values(
                id=uuid.uuid4(),
                submission_id=row["submission_id"],
                event_type=event_type,
                actor_id=None,
                workflow_run_id=row["workflow_run_id"],
                details=details,
                created_at=created_at,
            )
        )

        latest_by_submission[submission_id] = {
            "score": row["score"],
            "feedback": row["feedback"],
        }

    for submission_id, latest in latest_by_submission.items():
        bind.execute(
            submissions.update()
            .where(submissions.c.id == submission_id)
            .values(
                draft_score=latest["score"],
                draft_feedback=latest["feedback"],
            )
        )


def downgrade() -> None:
    # Irreversible data migration. Intentionally left as a no-op.
    pass