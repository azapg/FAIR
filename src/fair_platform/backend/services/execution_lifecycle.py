from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from fair_platform.backend.data.models import Execution, ExecutionStatus
from fair_platform.backend.services.execution_projection import append_and_project_event


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def expire_due_executions(
    session: Session,
    *,
    now: datetime | None = None,
    limit: int = 100,
) -> int:
    """Terminate overdue work under a row lock; safe to call from any worker."""

    timestamp = now or _utc_now()
    terminal = tuple(
        status.value
        for status in (
            ExecutionStatus.completed,
            ExecutionStatus.failed,
            ExecutionStatus.cancelled,
            ExecutionStatus.expired,
        )
    )
    due = list(
        session.scalars(
            select(Execution)
            .where(
                Execution.deadline_at.is_not(None),
                Execution.deadline_at <= timestamp,
                Execution.status.not_in(terminal),
            )
            .order_by(Execution.deadline_at, Execution.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
    )
    for execution in due:
        append_and_project_event(
            session,
            execution_id=execution.id,
            producer_source="fair.platform",
            producer_event_id=f"execution:{execution.id}:deadline-expired",
            event_type="execution.expired",
            schema_uri="urn:fair:event:execution.expired:v1",
            occurred_at=timestamp,
            payload={"deadline_at": execution.deadline_at.isoformat()},
        )
    return len(due)


__all__ = ["expire_due_executions"]
