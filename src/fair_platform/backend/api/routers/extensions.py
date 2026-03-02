from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.api.schema.extension import (
    ExtensionClientIssueRequest,
    ExtensionClientRead,
    ExtensionClientSecretRead,
    ExtensionClientUpdateRequest,
    ExtensionRead,
    ExtensionRegisterRequest,
)
from fair_platform.backend.core.security.permissions import has_capability
from fair_platform.backend.core.security.dependencies import require_extension_client
from fair_platform.backend.data.database import session_dependency
from fair_platform.backend.data.models import ExtensionClient
from fair_platform.backend.data.models.user import User
from fair_platform.backend.services.extension_auth import issue_extension_secret
from fair_platform.backend.services.extension_registry import (
    ExtensionRegistration,
    LocalExtensionRegistry,
)

router = APIRouter()


def get_extension_registry(request: Request) -> LocalExtensionRegistry:
    registry = getattr(request.app.state, "extension_registry", None)
    if registry is None:
        registry = LocalExtensionRegistry()
        request.app.state.extension_registry = registry
    return registry


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=ExtensionRead)
@router.post("/connect", status_code=status.HTTP_201_CREATED, response_model=ExtensionRead)
async def register_extension(
    payload: ExtensionRegisterRequest,
    extension_client: ExtensionClient = Depends(require_extension_client),
    registry: LocalExtensionRegistry = Depends(get_extension_registry),
):
    if extension_client.extension_id != payload.extension_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Extension id does not match authenticated extension",
        )
    requested_scopes = sorted(
        {
            scope.strip()
            for scope in (payload.requested_scopes or payload.capabilities)
            if scope.strip()
        }
    )
    approved_scopes = sorted(set(extension_client.scopes or []))
    effective_scopes = [scope for scope in requested_scopes if scope in approved_scopes]
    metadata = dict(payload.metadata)
    metadata["approved_scopes"] = approved_scopes
    metadata["effective_scopes"] = effective_scopes

    registration = await registry.register(
        ExtensionRegistration(
            extension_id=payload.extension_id,
            webhook_url=payload.webhook_url,
            intents=payload.intents,
            capabilities=payload.capabilities,
            metadata=metadata,
        )
    )
    return ExtensionRead(
        extension_id=registration.extension_id,
        webhook_url=registration.webhook_url,
        intents=registration.intents,
        capabilities=registration.capabilities,
        requested_scopes=requested_scopes,
        metadata=registration.metadata,
        enabled=registration.enabled,
    )


@router.get("/", response_model=list[ExtensionRead])
async def list_extensions(
    registry: LocalExtensionRegistry = Depends(get_extension_registry),
):
    records = await registry.list()
    return [
        ExtensionRead(
            extension_id=record.extension_id,
            webhook_url=record.webhook_url,
            intents=record.intents,
            capabilities=record.capabilities,
            requested_scopes=list(record.metadata.get("effective_scopes", []))
            if isinstance(record.metadata, dict)
            else [],
            metadata=record.metadata,
            enabled=record.enabled,
        )
        for record in records
    ]


@router.get("/admin/clients", response_model=list[ExtensionClientRead])
def list_extension_clients(
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    if not has_capability(current_user, "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can manage extension clients",
        )
    rows = db.query(ExtensionClient).order_by(ExtensionClient.extension_id.asc()).all()
    return [
        ExtensionClientRead(
            extension_id=row.extension_id,
            scopes=list(row.scopes or []),
            enabled=bool(row.enabled),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
        for row in rows
    ]


@router.get("/admin/clients/{extension_id}", response_model=ExtensionClientRead)
def get_extension_client(
    extension_id: str,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    if not has_capability(current_user, "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can manage extension clients",
        )
    row = db.get(ExtensionClient, extension_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Extension client not found",
        )
    return ExtensionClientRead(
        extension_id=row.extension_id,
        scopes=list(row.scopes or []),
        enabled=bool(row.enabled),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.patch("/admin/clients/{extension_id}", response_model=ExtensionClientRead)
def update_extension_client(
    extension_id: str,
    payload: ExtensionClientUpdateRequest,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    if not has_capability(current_user, "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can manage extension clients",
        )
    row = db.get(ExtensionClient, extension_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Extension client not found",
        )

    normalized_scopes = sorted({scope.strip() for scope in payload.scopes if scope.strip()})
    row.scopes = normalized_scopes
    row.enabled = payload.enabled
    row.updated_at = datetime.now(timezone.utc)
    db.add(row)
    db.commit()
    db.refresh(row)
    return ExtensionClientRead(
        extension_id=row.extension_id,
        scopes=list(row.scopes or []),
        enabled=bool(row.enabled),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.post(
    "/admin/clients",
    status_code=status.HTTP_201_CREATED,
    response_model=ExtensionClientSecretRead,
)
def issue_extension_client_secret(
    payload: ExtensionClientIssueRequest,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    if not has_capability(current_user, "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can manage extension clients",
        )
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


@router.post(
    "/admin/clients/{extension_id}/rotate",
    response_model=ExtensionClientSecretRead,
)
def rotate_extension_client_secret(
    extension_id: str,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    if not has_capability(current_user, "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can manage extension clients",
        )
    existing = db.get(ExtensionClient, extension_id)
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Extension client not found",
        )
    issued = issue_extension_secret(
        db,
        extension_id=extension_id,
        scopes=list(existing.scopes or []),
        enabled=bool(existing.enabled),
    )
    return ExtensionClientSecretRead(
        extension_id=issued.extension_id,
        extension_secret=issued.secret,
        scopes=issued.scopes,
        enabled=issued.enabled,
    )


__all__ = ["router", "get_extension_registry"]
