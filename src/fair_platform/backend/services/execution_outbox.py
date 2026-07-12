from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from fair_platform.backend.data.models.execution import (
    DispatchCommandKind,
    DispatchStatus,
    Execution,
    ExecutionDispatchOutbox,
)


class DispatchNotFound(ValueError):
    """The requested dispatch does not exist."""


class DispatchStateError(ValueError):
    """The dispatch cannot perform the requested state transition."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def enqueue_dispatch(
    session: Session,
    *,
    execution_id: UUID,
    target: str,
    payload: dict[str, Any],
    command_kind: DispatchCommandKind = DispatchCommandKind.start,
    job_id: Optional[str] = None,
) -> ExecutionDispatchOutbox:
    execution = session.get(Execution, execution_id)
    if execution is None:
        raise DispatchNotFound(f"Execution {execution_id} does not exist")
    if not target or len(target) > 255:
        raise ValueError("target must be 1-255 characters")

    dispatch = ExecutionDispatchOutbox(
        execution_id=execution.id,
        command_kind=command_kind,
        job_id=job_id or str(uuid4()),
        target=target,
        payload=payload,
    )
    session.add(dispatch)
    session.flush()
    return dispatch


def claim_dispatch(
    session: Session,
    *,
    worker_id: str,
    lease_seconds: int = 30,
    now: Optional[datetime] = None,
) -> ExecutionDispatchOutbox | None:
    if not worker_id:
        raise ValueError("worker_id is required")
    if lease_seconds <= 0:
        raise ValueError("lease_seconds must be positive")

    claimed_at = now or _utc_now()
    dispatch = session.scalar(
        select(ExecutionDispatchOutbox)
        .where(
            or_(
                ExecutionDispatchOutbox.status == DispatchStatus.pending,
                (
                    ExecutionDispatchOutbox.status == DispatchStatus.leased
                )
                & (ExecutionDispatchOutbox.lease_expires_at <= claimed_at),
            ),
            ExecutionDispatchOutbox.available_at <= claimed_at,
        )
        .order_by(ExecutionDispatchOutbox.available_at, ExecutionDispatchOutbox.created_at)
        .with_for_update()
    )
    if dispatch is None:
        return None

    dispatch.status = DispatchStatus.leased
    dispatch.attempt_count += 1
    dispatch.claimed_by = worker_id
    dispatch.lease_expires_at = claimed_at + timedelta(seconds=lease_seconds)
    dispatch.updated_at = claimed_at
    session.flush()
    return dispatch


def mark_dispatched(
    session: Session,
    dispatch_id: UUID,
    *,
    dispatched_at: Optional[datetime] = None,
) -> ExecutionDispatchOutbox:
    dispatch = session.get(ExecutionDispatchOutbox, dispatch_id)
    if dispatch is None:
        raise DispatchNotFound(f"Dispatch {dispatch_id} does not exist")
    if dispatch.status not in {DispatchStatus.leased, DispatchStatus.pending}:
        raise DispatchStateError(
            f"dispatch {dispatch_id} is {dispatch.status.value}, not deliverable"
        )
    timestamp = dispatched_at or _utc_now()
    dispatch.status = DispatchStatus.dispatched
    dispatch.dispatched_at = timestamp
    dispatch.lease_expires_at = None
    dispatch.updated_at = timestamp
    session.flush()
    return dispatch


def mark_dispatch_failed(
    session: Session,
    dispatch_id: UUID,
    *,
    error: str,
    retry_at: Optional[datetime] = None,
    dead_letter: bool = False,
) -> ExecutionDispatchOutbox:
    dispatch = session.get(ExecutionDispatchOutbox, dispatch_id)
    if dispatch is None:
        raise DispatchNotFound(f"Dispatch {dispatch_id} does not exist")
    if dispatch.status not in {DispatchStatus.leased, DispatchStatus.pending}:
        raise DispatchStateError(
            f"dispatch {dispatch_id} is {dispatch.status.value}, not retryable"
        )
    timestamp = _utc_now()
    should_retry = retry_at is not None and not dead_letter
    dispatch.status = DispatchStatus.pending if should_retry else (
        DispatchStatus.dead_letter if dead_letter else DispatchStatus.failed
    )
    dispatch.last_error = error
    dispatch.lease_expires_at = None
    dispatch.available_at = retry_at or timestamp
    dispatch.updated_at = timestamp
    session.flush()
    return dispatch


__all__ = [
    "DispatchNotFound",
    "DispatchStateError",
    "claim_dispatch",
    "enqueue_dispatch",
    "mark_dispatch_failed",
    "mark_dispatched",
]
