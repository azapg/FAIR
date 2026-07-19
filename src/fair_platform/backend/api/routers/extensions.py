from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.api.schema.extension import (
    CapabilityRead,
    ExtensionClientIssueRequest,
    ExtensionClientRead,
    ExtensionClientSecretRead,
    ExtensionClientUpdateRequest,
    GrantCreate,
    GrantRead,
    InstallationCreate,
    InstallationRead,
    InstallationStatusUpdate,
)
from fair_platform.backend.core.security.permissions import has_capability
from fair_platform.backend.data.database import session_dependency
from fair_platform.backend.data.models import (
    CapabilityDefinition,
    Execution,
    ExecutionDispatchOutbox,
    ExtensionClient,
    ExtensionGrant,
    ExtensionInstallation,
    ExtensionInstallationStatus,
    GrantDecision,
    User,
)
from fair_platform.backend.services.extension_auth import issue_extension_secret
from fair_platform.backend.core.security.dependencies import require_extension_client
from fair_platform.backend.services.execution_outbox import (
    DispatchStateError,
    acknowledge_dispatch,
    claim_dispatch,
    mark_dispatch_failed,
)
from fair_platform.backend.services.execution_protocol import (
    ExecutionProtocolError,
    build_execution_command,
)
from fair_platform.backend.services.execution_lifecycle import expire_due_executions
from fair_platform.extension_sdk.contracts.extension import (
    CapabilityManifest,
    ExtensionManifest,
)
from fair_platform.extension_sdk.contracts.protocol import (
    RunnerClaimRequest,
    RunnerCommandAck,
    RunnerCommandLease,
)


router = APIRouter()


def _runner_installation(db: Session, client: ExtensionClient) -> ExtensionInstallation:
    installation = db.scalar(
        select(ExtensionInstallation).where(
            ExtensionInstallation.extension_id == client.extension_id
        )
    )
    if (
        installation is None
        or _value(installation.status) != ExtensionInstallationStatus.enabled.value
        or _value(installation.delivery_mode) != "runner"
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Extension has no enabled runner installation",
        )
    return installation


def _value(value: object) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _require_admin(user: User) -> None:
    if not has_capability(user, "admin"):
        raise HTTPException(status_code=403, detail="Admin access required")


def _require_discovery(user: User) -> None:
    if not has_capability(user, "discover_extension_capabilities"):
        raise HTTPException(
            status_code=403, detail="Extension capability discovery required"
        )


def _schema_uri(schema: dict, fallback: str) -> str:
    return str(schema.get("$id") or fallback)


def _capability_read(row: CapabilityDefinition) -> CapabilityRead:
    snapshot = CapabilityManifest.model_validate(row.manifest_snapshot or {})
    return CapabilityRead(
        **snapshot.model_dump(),
        id=row.id,
        installation_id=row.installation_id,
        created_at=row.created_at,
    )


def _installation_read(row: ExtensionInstallation) -> InstallationRead:
    manifest = ExtensionManifest.model_validate(row.manifest) if row.manifest else None
    return InstallationRead(
        id=row.id,
        extension_id=row.extension_id,
        display_name=row.display_name,
        version=row.version,
        delivery_mode=_value(row.delivery_mode),
        dispatch_url=row.dispatch_url,
        health_url=row.health_url,
        manifest_version=row.manifest_version,
        status=_value(row.status),
        manifest=manifest,
        capabilities=[_capability_read(item) for item in row.capabilities],
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _grant_read(row: ExtensionGrant) -> GrantRead:
    return GrantRead(
        id=row.id,
        installation_id=row.installation_id,
        capability_definition_id=row.capability_definition_id,
        course_id=row.course_id,
        assignment_id=row.assignment_id,
        effect=row.effect,
        decision=_value(row.decision),
        reason=row.reason,
        granted_by_user_id=row.granted_by_user_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _client_read(row: ExtensionClient) -> ExtensionClientRead:
    return ExtensionClientRead(
        extension_id=row.extension_id,
        scopes=list(row.scopes or []),
        enabled=bool(row.enabled),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.post(
    "/installations",
    response_model=InstallationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_installation(
    payload: InstallationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
) -> InstallationRead:
    _require_admin(current_user)
    manifest = payload.manifest
    row = ExtensionInstallation(
        extension_id=manifest.extension_id,
        display_name=manifest.display_name,
        version=manifest.version,
        delivery_mode=manifest.delivery_mode,
        dispatch_url=str(manifest.dispatch_url) if manifest.dispatch_url else None,
        health_url=str(manifest.health_url) if manifest.health_url else None,
        manifest_version=manifest.manifest_version,
        manifest=manifest.model_dump(by_alias=True, mode="json"),
        status=ExtensionInstallationStatus.enabled,
    )
    db.add(row)
    db.flush()
    for capability in manifest.capabilities:
        raw = capability.model_dump(by_alias=True, mode="json")
        base = f"urn:fair:extension:{manifest.extension_id}:capability:{capability.capability_id}:{capability.version}"
        db.add(
            CapabilityDefinition(
                installation_id=row.id,
                capability_id=capability.capability_id,
                kind=capability.kind,
                version=capability.version,
                input_schema_uri=_schema_uri(raw["inputSchema"], f"{base}:input"),
                output_schema_uri=_schema_uri(raw["outputSchema"], f"{base}:output"),
                config_schema_uri=(
                    _schema_uri(raw["configSchema"], f"{base}:config")
                    if raw.get("configSchema")
                    else None
                ),
                requested_scopes=capability.requested_scopes,
                declared_effects=capability.declared_effects,
                tool_capabilities=capability.tool_capabilities,
                supports_streaming=capability.supports_streaming,
                supports_cancellation=capability.supports_cancellation,
                supports_resume=capability.supports_resume,
                supports_batch=capability.supports_batch,
                manifest_snapshot=raw,
            )
        )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Extension installation already exists"
        ) from exc
    return _installation_read(
        db.scalar(
            select(ExtensionInstallation)
            .options(selectinload(ExtensionInstallation.capabilities))
            .where(ExtensionInstallation.id == row.id)
        )
    )


@router.post("/runner/commands/claim", response_model=None)
async def claim_runner_command(
    payload: RunnerClaimRequest,
    extension_client: ExtensionClient = Depends(
        require_extension_client(("runner:commands",))
    ),
    db: Session = Depends(session_dependency),
) -> RunnerCommandLease | Response:
    """Long-poll one durable command for a runner behind NAT."""

    installation = _runner_installation(db, extension_client)
    stop_at = datetime.now(timezone.utc) + timedelta(seconds=payload.wait_seconds)
    while True:
        expired_count = expire_due_executions(db)
        dispatch = claim_dispatch(
            db,
            worker_id=f"runner:{installation.id}:{payload.runner_id}",
            lease_seconds=payload.lease_seconds,
            delivery_mode="runner",
            installation_id=installation.id,
        )
        if dispatch is not None:
            try:
                command = build_execution_command(db, dispatch)
            except ExecutionProtocolError as exc:
                mark_dispatch_failed(
                    db,
                    dispatch.id,
                    lease_id=dispatch.lease_id,
                    error=str(exc),
                    dead_letter=True,
                )
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=str(exc),
                ) from exc
            lease = RunnerCommandLease(
                lease_id=dispatch.lease_id,
                lease_expires_at=dispatch.lease_expires_at,
                command=command,
            )
            db.commit()
            return lease
        if expired_count:
            db.commit()
        else:
            db.rollback()
        remaining = (stop_at - datetime.now(timezone.utc)).total_seconds()
        if remaining <= 0:
            return Response(status_code=status.HTTP_204_NO_CONTENT)
        await asyncio.sleep(min(0.25, remaining))


@router.post(
    "/runner/commands/{dispatch_id}/ack",
    status_code=status.HTTP_204_NO_CONTENT,
)
def acknowledge_runner_command(
    dispatch_id: UUID,
    payload: RunnerCommandAck,
    extension_client: ExtensionClient = Depends(
        require_extension_client(("runner:commands",))
    ),
    db: Session = Depends(session_dependency),
) -> Response:
    """Acknowledge only the exact lease a runner durably accepted."""

    installation = _runner_installation(db, extension_client)
    dispatch = db.get(ExecutionDispatchOutbox, dispatch_id)
    execution = (
        db.get(Execution, dispatch.execution_id) if dispatch is not None else None
    )
    if dispatch is None or execution is None:
        raise HTTPException(status_code=404, detail="Runner command not found")
    if execution.extension_installation_id != installation.id:
        raise HTTPException(
            status_code=403, detail="Runner command is owned by another installation"
        )
    try:
        acknowledge_dispatch(db, dispatch.id, lease_id=payload.lease_id)
        db.commit()
    except DispatchStateError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/installations", response_model=list[InstallationRead])
def list_installations(
    include_disabled: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
) -> list[InstallationRead]:
    _require_discovery(current_user)
    statement = (
        select(ExtensionInstallation)
        .options(selectinload(ExtensionInstallation.capabilities))
        .order_by(ExtensionInstallation.extension_id)
    )
    if include_disabled:
        _require_admin(current_user)
    else:
        statement = statement.where(
            ExtensionInstallation.status == ExtensionInstallationStatus.enabled
        )
    return [_installation_read(row) for row in db.scalars(statement).unique()]


@router.get("/installations/{installation_id}", response_model=InstallationRead)
def get_installation(
    installation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
) -> InstallationRead:
    _require_discovery(current_user)
    row = db.scalar(
        select(ExtensionInstallation)
        .options(selectinload(ExtensionInstallation.capabilities))
        .where(ExtensionInstallation.id == installation_id)
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Extension installation not found")
    if _value(row.status) != "enabled":
        _require_admin(current_user)
    return _installation_read(row)


@router.patch("/installations/{installation_id}", response_model=InstallationRead)
def update_installation_status(
    installation_id: UUID,
    payload: InstallationStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
) -> InstallationRead:
    _require_admin(current_user)
    row = db.get(ExtensionInstallation, installation_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Extension installation not found")
    row.status = ExtensionInstallationStatus(payload.status)
    row.revoked_at = datetime.now(timezone.utc) if payload.status == "revoked" else None
    db.commit()
    db.refresh(row)
    return _installation_read(row)


@router.get("/capabilities", response_model=list[CapabilityRead])
def list_capabilities(
    installation_id: UUID | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
) -> list[CapabilityRead]:
    _require_discovery(current_user)
    statement = (
        select(CapabilityDefinition)
        .join(ExtensionInstallation)
        .where(ExtensionInstallation.status == ExtensionInstallationStatus.enabled)
        .order_by(CapabilityDefinition.capability_id, CapabilityDefinition.version)
    )
    if installation_id:
        statement = statement.where(
            CapabilityDefinition.installation_id == installation_id
        )
    return [_capability_read(row) for row in db.scalars(statement)]


@router.get("/capabilities/{capability_id}", response_model=CapabilityRead)
def get_capability(
    capability_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
) -> CapabilityRead:
    _require_discovery(current_user)
    row = db.scalar(
        select(CapabilityDefinition)
        .join(ExtensionInstallation)
        .where(
            CapabilityDefinition.id == capability_id,
            ExtensionInstallation.status == ExtensionInstallationStatus.enabled,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Capability not found")
    return _capability_read(row)


@router.post("/grants", response_model=GrantRead, status_code=status.HTTP_201_CREATED)
def create_grant(
    payload: GrantCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
) -> GrantRead:
    _require_admin(current_user)
    installation = db.get(ExtensionInstallation, payload.installation_id)
    if installation is None:
        raise HTTPException(status_code=404, detail="Extension installation not found")
    if payload.capability_definition_id:
        capability = db.get(CapabilityDefinition, payload.capability_definition_id)
        if capability is None or capability.installation_id != installation.id:
            raise HTTPException(
                status_code=422, detail="Capability does not belong to installation"
            )
        if payload.effect not in (capability.declared_effects or []):
            raise HTTPException(
                status_code=422, detail="Effect is not declared by capability"
            )
    values = payload.model_dump()
    values["decision"] = GrantDecision(payload.decision)
    row = ExtensionGrant(
        **values,
        granted_by_user_id=current_user.id,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Grant already exists for this scope"
        ) from exc
    db.refresh(row)
    return _grant_read(row)


@router.get("/grants", response_model=list[GrantRead])
def list_grants(
    installation_id: UUID | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
) -> list[GrantRead]:
    _require_admin(current_user)
    statement = select(ExtensionGrant).order_by(
        ExtensionGrant.created_at, ExtensionGrant.id
    )
    if installation_id:
        statement = statement.where(ExtensionGrant.installation_id == installation_id)
    return [_grant_read(row) for row in db.scalars(statement)]


@router.delete("/grants/{grant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_grant(
    grant_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
) -> None:
    _require_admin(current_user)
    row = db.get(ExtensionGrant, grant_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Grant not found")
    db.delete(row)
    db.commit()


@router.get("/clients", response_model=list[ExtensionClientRead])
def list_extension_clients(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
) -> list[ExtensionClientRead]:
    _require_admin(current_user)
    return [
        _client_read(row)
        for row in db.scalars(
            select(ExtensionClient).order_by(ExtensionClient.extension_id)
        )
    ]


@router.post(
    "/clients",
    response_model=ExtensionClientSecretRead,
    status_code=status.HTTP_201_CREATED,
)
def create_extension_client(
    payload: ExtensionClientIssueRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
) -> ExtensionClientSecretRead:
    _require_admin(current_user)
    issued = issue_extension_secret(
        db,
        extension_id=payload.extension_id,
        scopes=payload.scopes,
        enabled=payload.enabled,
    )
    return ExtensionClientSecretRead(
        extension_id=issued.extension_id,
        extension_secret=issued.secret,
        scopes=issued.scopes,
        enabled=issued.enabled,
    )


@router.get("/clients/{extension_id}", response_model=ExtensionClientRead)
def get_extension_client(
    extension_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
) -> ExtensionClientRead:
    _require_admin(current_user)
    row = db.get(ExtensionClient, extension_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Extension client not found")
    return _client_read(row)


@router.patch("/clients/{extension_id}", response_model=ExtensionClientRead)
def update_extension_client(
    extension_id: str,
    payload: ExtensionClientUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
) -> ExtensionClientRead:
    _require_admin(current_user)
    row = db.get(ExtensionClient, extension_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Extension client not found")
    row.scopes = sorted({scope.strip() for scope in payload.scopes if scope.strip()})
    row.enabled = payload.enabled
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return _client_read(row)


@router.post(
    "/clients/{extension_id}/rotate",
    response_model=ExtensionClientSecretRead,
)
def rotate_extension_client(
    extension_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
) -> ExtensionClientSecretRead:
    _require_admin(current_user)
    row = db.get(ExtensionClient, extension_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Extension client not found")
    issued = issue_extension_secret(
        db,
        extension_id=extension_id,
        scopes=list(row.scopes or []),
        enabled=bool(row.enabled),
    )
    return ExtensionClientSecretRead(
        extension_id=issued.extension_id,
        extension_secret=issued.secret,
        scopes=issued.scopes,
        enabled=issued.enabled,
    )


__all__ = ["router"]
