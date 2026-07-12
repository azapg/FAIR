from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, selectinload

from fair_platform.backend.data.models.execution import ExecutionKind
from fair_platform.backend.data.models.flow import Flow, FlowVersion, FlowVersionState
from fair_platform.backend.services.execution_outbox import enqueue_dispatch
from fair_platform.backend.services.execution_store import create_execution


class FlowNotFound(ValueError):
    pass


class FlowStateError(ValueError):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _state(value: object) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _version_hash(
    definition: dict, capability_pins: list[dict], config_snapshot: dict
) -> str:
    encoded = json.dumps(
        {
            "definition": definition,
            "capabilityPins": capability_pins,
            "configSnapshot": config_snapshot,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _flow_allocation_lock_statement(flow_id: UUID):
    return select(Flow.id).where(Flow.id == flow_id).with_for_update()


def get_owned_flow(session: Session, flow_id: UUID, owner_user_id: UUID) -> Flow:
    flow = session.scalar(
        select(Flow)
        .where(Flow.id == flow_id, Flow.owner_user_id == owner_user_id)
        .options(selectinload(Flow.versions))
    )
    if flow is None:
        raise FlowNotFound(f"Flow {flow_id} does not exist")
    return flow


def create_flow(
    session: Session,
    *,
    owner_user_id: UUID,
    name: str,
    description: str | None,
    course_id: UUID | None,
) -> Flow:
    flow = Flow(
        owner_user_id=owner_user_id,
        name=name,
        description=description,
        course_id=course_id,
    )
    session.add(flow)
    session.flush()
    return flow


def create_flow_version(
    session: Session,
    *,
    flow: Flow,
    created_by_user_id: UUID,
    definition: dict,
    capability_pins: list[dict],
    config_snapshot: dict,
) -> FlowVersion:
    if flow.archived_at is not None:
        raise FlowStateError("Archived Flows cannot receive new versions")
    # Serialize ordinal allocation per Flow. PostgreSQL emits SELECT ... FOR
    # UPDATE; SQLite safely ignores the unsupported locking clause.
    if session.scalar(_flow_allocation_lock_statement(flow.id)) is None:
        raise FlowNotFound(f"Flow {flow.id} does not exist")
    next_ordinal = (
        session.scalar(
            select(func.max(FlowVersion.ordinal)).where(FlowVersion.flow_id == flow.id)
        )
        or 0
    ) + 1
    version = FlowVersion(
        flow_id=flow.id,
        ordinal=next_ordinal,
        definition=definition,
        capability_pins=capability_pins,
        config_snapshot=config_snapshot,
        definition_hash=_version_hash(
            definition, capability_pins, config_snapshot
        ),
        created_by_user_id=created_by_user_id,
    )
    session.add(version)
    session.flush()
    return version


def publish_flow_version(session: Session, version: FlowVersion) -> FlowVersion:
    if _state(version.state) != FlowVersionState.draft.value:
        raise FlowStateError("Only a draft FlowVersion can be published")
    version.state = FlowVersionState.published
    version.published_at = _now()
    session.flush()
    return version


def archive_flow_version(session: Session, version: FlowVersion) -> FlowVersion:
    if _state(version.state) != FlowVersionState.published.value:
        raise FlowStateError("Only a published FlowVersion can be archived")
    archived_at = _now()
    # Published versions are otherwise immutable. A direct transition updates only
    # the lifecycle columns and deliberately bypasses ordinary ORM mutation.
    session.execute(
        update(FlowVersion)
        .where(FlowVersion.id == version.id)
        .values(state=FlowVersionState.archived, archived_at=archived_at)
    )
    session.expire(version)
    return version


def start_flow_execution(
    session: Session,
    *,
    flow: Flow,
    initiated_by_user_id: UUID,
    input_payload: dict,
    flow_version_id: UUID | None,
):
    query = select(FlowVersion).where(
        FlowVersion.flow_id == flow.id,
        FlowVersion.state == FlowVersionState.published,
    )
    if flow_version_id is not None:
        query = query.where(FlowVersion.id == flow_version_id)
    else:
        query = query.order_by(FlowVersion.ordinal.desc())
    version = session.scalar(query)
    if version is None:
        raise FlowStateError("A published FlowVersion is required to start a Flow")

    execution = create_execution(
        session,
        kind=ExecutionKind.flow.value,
        initiated_by_user_id=initiated_by_user_id,
        flow_version_id=version.id,
        input=input_payload,
    )
    dispatch = enqueue_dispatch(
        session,
        execution_id=execution.id,
        target="flow.executor",
        payload={
            "executionId": str(execution.id),
            "flowId": str(flow.id),
            "flowVersionId": str(version.id),
            "definitionHash": version.definition_hash,
            "input": input_payload,
        },
    )
    return execution, version, dispatch


__all__ = [
    "FlowNotFound",
    "FlowStateError",
    "archive_flow_version",
    "create_flow",
    "create_flow_version",
    "get_owned_flow",
    "publish_flow_version",
    "start_flow_execution",
]
