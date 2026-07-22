from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from fair_platform.backend.api.schema.flow import FlowDefinition, FlowNodeDefinition
from fair_platform.backend.data.models.execution import (
    Execution,
    ExecutionDispatchOutbox,
    ExecutionKind,
    ExecutionStatus,
    EventVisibility,
)
from fair_platform.backend.data.models.flow import FlowVersion
from fair_platform.backend.services.execution_outbox import enqueue_dispatch
from fair_platform.backend.services.execution_projection import append_and_project_event
from fair_platform.backend.services.execution_store import create_execution
from fair_platform.backend.services.extension_grants import resolve_extension_effects


class FlowRuntimeError(ValueError):
    pass


@dataclass(frozen=True)
class FlowAdvanceResult:
    root: Execution
    step: Execution | None = None
    dispatch: ExecutionDispatchOutbox | None = None


def _value(value: object) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _runtime_event(
    session: Session,
    execution: Execution,
    *,
    event_id: str,
    event_type: str,
    payload: dict,
) -> None:
    append_and_project_event(
        session,
        execution_id=execution.id,
        producer_source="fair.flow-runtime",
        producer_event_id=f"{execution.root_execution_id}:{event_id}",
        event_type=event_type,
        schema_uri=f"urn:fair:event:{event_type}:v1",
        visibility=EventVisibility.user,
        payload=payload,
    )


def _definition(version: FlowVersion) -> FlowDefinition:
    try:
        return FlowDefinition.model_validate(version.definition)
    except ValueError as exc:
        raise FlowRuntimeError(
            "FlowVersion contains an invalid ordered definition"
        ) from exc


def _pin(version: FlowVersion, node_id: str) -> dict:
    pin = next(
        (item for item in version.capability_pins if item.get("nodeId") == node_id),
        None,
    )
    if pin is None:
        raise FlowRuntimeError(f"Flow node {node_id!r} has no capability pin")
    return pin


def validate_flow_runtime(
    session: Session,
    *,
    version: FlowVersion,
    course_id: UUID | None,
    assignment_id: UUID | None,
) -> None:
    definition = _definition(version)
    for node in definition.nodes:
        pin = _pin(version, node.id)
        effects = tuple(pin.get("declaredEffects") or ())
        resolutions = resolve_extension_effects(
            session,
            installation_id=UUID(pin["extensionInstallationId"]),
            capability_definition_id=UUID(pin["capabilityDefinitionId"]),
            effects=effects,
            course_id=course_id,
            assignment_id=assignment_id,
        )
        denied = [
            effect for effect, result in resolutions.items() if not result.allowed
        ]
        if denied:
            raise FlowRuntimeError(
                f"Flow node {node.id!r} is not granted effects: {', '.join(denied)}"
            )


def _step_input(
    root: Execution,
    version: FlowVersion,
    node: FlowNodeDefinition,
    previous_output: dict | None,
) -> dict:
    return {
        "flow": {
            "flowVersionId": str(version.id),
            "definitionHash": version.definition_hash,
            "nodeId": node.id,
        },
        "flowInput": root.input or {},
        "previousOutput": previous_output,
        "nodeInput": node.input,
        "config": {
            "flow": version.config_snapshot or {},
            "node": node.config,
        },
    }


def _create_step(
    session: Session,
    *,
    root: Execution,
    version: FlowVersion,
    node: FlowNodeDefinition,
    previous_output: dict | None,
    retry_of: Execution | None = None,
) -> FlowAdvanceResult:
    pin = _pin(version, node.id)
    step = create_execution(
        session,
        kind=ExecutionKind.flow_step.value,
        parent_execution_id=root.id,
        retry_of_execution_id=retry_of.id if retry_of is not None else None,
        initiated_by_user_id=root.initiated_by_user_id,
        flow_version_id=version.id,
        flow_node_id=node.id,
        capability_id=pin["capabilityId"],
        capability_version=pin["capabilityVersion"],
        capability_definition_id=UUID(pin["capabilityDefinitionId"]),
        extension_installation_id=UUID(pin["extensionInstallationId"]),
        deadline_at=_now() + timedelta(seconds=node.timeout_seconds),
        input=_step_input(root, version, node, previous_output),
    )
    _runtime_event(
        session,
        step,
        event_id=f"step:{node.id}:attempt:{step.attempt}:created",
        event_type="execution.created",
        payload={
            "status": ExecutionStatus.queued.value,
            "flowVersionId": str(version.id),
            "flowNodeId": node.id,
            "attempt": step.attempt,
        },
    )
    dispatch = enqueue_dispatch(
        session,
        execution_id=step.id,
        target=pin["extensionId"],
        # Every dispatch path enqueues the run's input and nothing else; the
        # command envelope already carries execution id and capability pin, so
        # repeating them here only created a second, divergent shape.
        payload=step.input,
        job_id=str(step.id),
    )
    _runtime_event(
        session,
        root,
        event_id=f"step:{node.id}:attempt:{step.attempt}:dispatched",
        event_type="flow.step.dispatched",
        payload={
            "nodeId": node.id,
            "stepExecutionId": str(step.id),
            "attempt": step.attempt,
            "capabilityId": pin["capabilityId"],
            "capabilityVersion": pin["capabilityVersion"],
        },
    )
    return FlowAdvanceResult(root=root, step=step, dispatch=dispatch)


def _terminal_root(
    session: Session,
    root: Execution,
    *,
    status: str,
    payload: dict,
) -> FlowAdvanceResult:
    _runtime_event(
        session,
        root,
        event_id=f"root:{status}",
        event_type=f"execution.{status}",
        payload=payload,
    )
    return FlowAdvanceResult(root=root)


def advance_flow_execution(
    session: Session, root_execution_id: UUID
) -> FlowAdvanceResult:
    root = session.get(Execution, root_execution_id)
    if root is None or _value(root.kind) != ExecutionKind.flow.value:
        raise FlowRuntimeError(f"Execution {root_execution_id} is not a Flow root")
    if _value(root.status) in {
        ExecutionStatus.completed.value,
        ExecutionStatus.failed.value,
        ExecutionStatus.cancelled.value,
        ExecutionStatus.expired.value,
    }:
        return FlowAdvanceResult(root=root)
    version = session.get(FlowVersion, root.flow_version_id)
    if version is None:
        raise FlowRuntimeError("Flow root does not reference a FlowVersion")

    definition = _definition(version)
    children = list(
        session.scalars(
            select(Execution)
            .where(
                Execution.parent_execution_id == root.id,
                Execution.kind == ExecutionKind.flow_step,
            )
            .order_by(Execution.created_at, Execution.attempt, Execution.id)
        )
    )
    by_node: dict[str, list[Execution]] = {}
    for child in children:
        by_node.setdefault(child.flow_node_id or "", []).append(child)

    previous_output: dict | None = None
    node_results: list[dict] = []
    for node in definition.nodes:
        attempts = by_node.get(node.id, [])
        if not attempts:
            validate_flow_runtime(
                session,
                version=version,
                course_id=root.course_id,
                assignment_id=root.assignment_id,
            )
            return _create_step(
                session,
                root=root,
                version=version,
                node=node,
                previous_output=previous_output,
            )

        latest = attempts[-1]
        latest_status = _value(latest.status)
        if latest_status in {
            ExecutionStatus.queued.value,
            ExecutionStatus.running.value,
            ExecutionStatus.waiting.value,
        }:
            if latest.deadline_at is not None and latest.deadline_at <= _now():
                _runtime_event(
                    session,
                    latest,
                    event_id=f"step:{node.id}:attempt:{latest.attempt}:expired",
                    event_type="execution.expired",
                    payload={"error": "Flow step deadline expired"},
                )
                latest_status = ExecutionStatus.expired.value
            else:
                dispatch = latest.dispatches[-1] if latest.dispatches else None
                return FlowAdvanceResult(root=root, step=latest, dispatch=dispatch)

        if latest_status == ExecutionStatus.completed.value:
            previous_output = latest.output_summary
            node_results.append(
                {
                    "nodeId": node.id,
                    "executionId": str(latest.id),
                    "status": latest_status,
                    "attempt": latest.attempt,
                    "output": latest.output_summary,
                }
            )
            continue

        if latest.attempt < node.max_attempts:
            validate_flow_runtime(
                session,
                version=version,
                course_id=root.course_id,
                assignment_id=root.assignment_id,
            )
            return _create_step(
                session,
                root=root,
                version=version,
                node=node,
                previous_output=previous_output,
                retry_of=latest,
            )

        node_results.append(
            {
                "nodeId": node.id,
                "executionId": str(latest.id),
                "status": latest_status,
                "attempt": latest.attempt,
                "errorCode": latest.error_code,
                "errorSummary": latest.error_summary,
            }
        )
        if node.on_failure == "continue":
            previous_output = None
            continue
        terminal_status = (
            latest_status
            if latest_status
            in {ExecutionStatus.cancelled.value, ExecutionStatus.expired.value}
            else ExecutionStatus.failed.value
        )
        return _terminal_root(
            session,
            root,
            status=terminal_status,
            payload={
                "errorCode": "flow_step_failed",
                "errorSummary": f"Flow node {node.id!r} ended as {latest_status}",
                "nodeResults": node_results,
            },
        )

    return _terminal_root(
        session,
        root,
        status=ExecutionStatus.completed.value,
        payload={
            "outputSummary": {
                "flowVersionId": str(version.id),
                "definitionHash": version.definition_hash,
                "nodeResults": node_results,
                "output": previous_output,
            }
        },
    )


def fail_flow_execution(
    session: Session, root_execution_id: UUID, error: str
) -> FlowAdvanceResult:
    root = session.get(Execution, root_execution_id)
    if root is None or _value(root.kind) != ExecutionKind.flow.value:
        raise FlowRuntimeError(f"Execution {root_execution_id} is not a Flow root")
    if _value(root.status) in {
        ExecutionStatus.completed.value,
        ExecutionStatus.failed.value,
        ExecutionStatus.cancelled.value,
        ExecutionStatus.expired.value,
    }:
        return FlowAdvanceResult(root=root)
    return _terminal_root(
        session,
        root,
        status=ExecutionStatus.failed.value,
        payload={"errorCode": "flow_runtime_error", "errorSummary": error},
    )


__all__ = [
    "FlowAdvanceResult",
    "FlowRuntimeError",
    "advance_flow_execution",
    "fail_flow_execution",
    "validate_flow_runtime",
]
