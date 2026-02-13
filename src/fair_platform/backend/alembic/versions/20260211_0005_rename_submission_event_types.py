"""rename_submission_event_types

Revision ID: 20260211_0005
Revises: 20260210_0004
Create Date: 2026-02-11
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260211_0005"
down_revision = "20260210_0004"
branch_labels = None
depends_on = None


def _rename(mapping: dict[str, str]) -> None:
    for old_value, new_value in mapping.items():
        op.execute(
            sa.text(
                "UPDATE submission_events SET event_type = :new_value WHERE event_type = :old_value"
            ).bindparams(old_value=old_value, new_value=new_value)
        )


def upgrade() -> None:
    _rename(
        {
            "initial_result": "ai_initial_result_recorded",
            "ai_graded": "ai_regrade_result_recorded",
            "manual_edit": "draft_manually_edited",
            "returned": "returned_to_student",
            "status_changed": "status_transitioned",
        }
    )


def downgrade() -> None:
    _rename(
        {
            "ai_initial_result_recorded": "initial_result",
            "ai_regrade_result_recorded": "ai_graded",
            "draft_manually_edited": "manual_edit",
            "returned_to_student": "returned",
            "status_transitioned": "status_changed",
        }
    )
