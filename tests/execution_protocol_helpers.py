from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from fair_platform.backend.data.models import (
    CapabilityDefinition,
    Execution,
    ExtensionInstallation,
)
from fair_platform.backend.services.execution_authorization import issue_execution_token


def add_agent_capability(
    session: Session,
    installation: ExtensionInstallation,
    *,
    capability_id: str = "agent.chat",
    requested_scopes: list[str] | None = None,
    supports_resume: bool = False,
    supports_cancellation: bool = False,
    tool_capabilities: list[str] | None = None,
) -> CapabilityDefinition:
    session.add(installation)
    session.flush()
    capability = CapabilityDefinition(
        id=uuid4(),
        installation_id=installation.id,
        capability_id=capability_id,
        kind="agent",
        version="1.0.0",
        requested_scopes=requested_scopes or [],
        declared_effects=[],
        tool_capabilities=tool_capabilities or [],
        supports_streaming=True,
        supports_resume=supports_resume,
        supports_cancellation=supports_cancellation,
        manifest_snapshot={
            "capabilityId": capability_id,
            "kind": "agent",
            "version": "1.0.0",
            "inputSchema": {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
                "properties": {"content": {"type": "string"}},
                "required": ["content"],
                "additionalProperties": False,
            },
            "outputSchema": {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
            },
            "requestedScopes": requested_scopes or [],
            "declaredEffects": [],
            "toolCapabilities": tool_capabilities or [],
            "supportsStreaming": True,
            "supportsResume": supports_resume,
            "supportsCancellation": supports_cancellation,
        },
    )
    session.add(capability)
    session.flush()
    return capability


def execution_token(test_db, execution_id: UUID | str) -> str:
    with test_db() as session:
        execution = session.get(Execution, UUID(str(execution_id)))
        capability = session.get(
            CapabilityDefinition, execution.capability_definition_id
        )
        installation = session.get(
            ExtensionInstallation, execution.extension_installation_id
        )
        return issue_execution_token(
            execution=execution,
            capability=capability,
            installation=installation,
            scopes={"executions:events", *(capability.requested_scopes or [])},
            submission_ids=[item.id for item in execution.submissions],
        ).token


def execution_headers(test_db, execution_id: UUID | str) -> dict[str, str]:
    return {"Authorization": f"Bearer {execution_token(test_db, execution_id)}"}


__all__ = ["add_agent_capability", "execution_headers", "execution_token"]
