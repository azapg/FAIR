from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.api.schema.extension import (
    CapabilityRead,
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
    ExtensionGrant,
    ExtensionInstallation,
    ExtensionInstallationStatus,
    GrantDecision,
    User,
)
from fair_platform.extension_sdk.contracts.extension import CapabilityManifest, ExtensionManifest


router = APIRouter()


def _value(value: object) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _require_admin(user: User) -> None:
    if not has_capability(user, "admin"):
        raise HTTPException(status_code=403, detail="Admin access required")


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


@router.post("/installations", response_model=InstallationRead, status_code=status.HTTP_201_CREATED)
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
        dispatch_url=str(manifest.dispatch_url),
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
        db.add(CapabilityDefinition(
            installation_id=row.id,
            capability_id=capability.capability_id,
            kind=capability.kind,
            version=capability.version,
            input_schema_uri=_schema_uri(raw["inputSchema"], f"{base}:input"),
            output_schema_uri=_schema_uri(raw["outputSchema"], f"{base}:output"),
            config_schema_uri=(
                _schema_uri(raw["configSchema"], f"{base}:config")
                if raw.get("configSchema") else None
            ),
            requested_scopes=capability.requested_scopes,
            declared_effects=capability.declared_effects,
            supports_streaming=capability.supports_streaming,
            supports_cancellation=capability.supports_cancellation,
            supports_resume=capability.supports_resume,
            supports_batch=capability.supports_batch,
            manifest_snapshot=raw,
        ))
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Extension installation already exists") from exc
    return _installation_read(db.scalar(
        select(ExtensionInstallation)
        .options(selectinload(ExtensionInstallation.capabilities))
        .where(ExtensionInstallation.id == row.id)
    ))


@router.get("/installations", response_model=list[InstallationRead])
def list_installations(
    include_disabled: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
) -> list[InstallationRead]:
    statement = select(ExtensionInstallation).options(
        selectinload(ExtensionInstallation.capabilities)
    ).order_by(ExtensionInstallation.extension_id)
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
    row = db.scalar(select(ExtensionInstallation).options(
        selectinload(ExtensionInstallation.capabilities)
    ).where(ExtensionInstallation.id == installation_id))
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
    statement = select(CapabilityDefinition).join(ExtensionInstallation).where(
        ExtensionInstallation.status == ExtensionInstallationStatus.enabled
    ).order_by(CapabilityDefinition.capability_id, CapabilityDefinition.version)
    if installation_id:
        statement = statement.where(CapabilityDefinition.installation_id == installation_id)
    return [_capability_read(row) for row in db.scalars(statement)]


@router.get("/capabilities/{capability_id}", response_model=CapabilityRead)
def get_capability(
    capability_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
) -> CapabilityRead:
    row = db.scalar(select(CapabilityDefinition).join(ExtensionInstallation).where(
        CapabilityDefinition.id == capability_id,
        ExtensionInstallation.status == ExtensionInstallationStatus.enabled,
    ))
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
            raise HTTPException(status_code=422, detail="Capability does not belong to installation")
        if payload.effect not in (capability.declared_effects or []):
            raise HTTPException(status_code=422, detail="Effect is not declared by capability")
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
        raise HTTPException(status_code=409, detail="Grant already exists for this scope") from exc
    db.refresh(row)
    return _grant_read(row)


@router.get("/grants", response_model=list[GrantRead])
def list_grants(
    installation_id: UUID | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
) -> list[GrantRead]:
    _require_admin(current_user)
    statement = select(ExtensionGrant).order_by(ExtensionGrant.created_at, ExtensionGrant.id)
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


__all__ = ["router"]
