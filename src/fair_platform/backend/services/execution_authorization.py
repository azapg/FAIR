from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from fair_platform.backend.core.config import get_api_base_url, get_secret_key
from fair_platform.backend.data.database import session_dependency
from fair_platform.backend.data.models import (
    CapabilityDefinition,
    Execution,
    ExtensionInstallation,
    ExtensionInstallationStatus,
)


EXECUTION_TOKEN_TYPE = "fair-execution+jwt"
EXECUTION_TOKEN_PURPOSE = "execution_delegation"
EXECUTION_TOKEN_AUDIENCE = "fair-extension-api"
EXECUTION_TOKEN_ALGORITHM = "HS256"
DEFAULT_EXECUTION_TOKEN_MINUTES = 15
TERMINAL_EXECUTION_STATUSES = frozenset({"completed", "failed", "cancelled", "expired"})
execution_bearer = HTTPBearer(auto_error=False)


def _value(value: object) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def execution_token_issuer() -> str:
    return f"{get_api_base_url()}/api/v1"


@dataclass(frozen=True)
class ExecutionAuthorization:
    execution: Execution
    installation: ExtensionInstallation
    capability: CapabilityDefinition
    subject: str
    scopes: frozenset[str]
    token_id: UUID


@dataclass(frozen=True)
class IssuedExecutionToken:
    token: str
    expires_at: datetime
    scopes: tuple[str, ...]


def issue_execution_token(
    *,
    execution: Execution,
    installation: ExtensionInstallation,
    capability: CapabilityDefinition,
    scopes: list[str] | tuple[str, ...] | set[str],
    submission_ids: list[UUID] | tuple[UUID, ...] = (),
    artifact_ids: list[UUID] | tuple[UUID, ...] = (),
    now: datetime | None = None,
    expires_at: datetime | None = None,
) -> IssuedExecutionToken:
    """Issue least-privilege authority for one pinned Execution only."""

    if execution.extension_installation_id != installation.id:
        raise ValueError("execution is not owned by the installation")
    if execution.capability_definition_id != capability.id:
        raise ValueError("execution does not carry the requested capability pin")
    if capability.installation_id != installation.id:
        raise ValueError("capability is not owned by the installation")
    if _value(installation.status) != ExtensionInstallationStatus.enabled.value:
        raise ValueError("installation is not enabled")
    if _value(execution.status) in TERMINAL_EXECUTION_STATUSES:
        raise ValueError("terminal execution authority cannot be issued")

    issued_at = now or _utc_now()
    token_expiry = expires_at or (
        issued_at + timedelta(minutes=DEFAULT_EXECUTION_TOKEN_MINUTES)
    )
    if execution.deadline_at is not None:
        deadline = execution.deadline_at
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        token_expiry = min(token_expiry, deadline)
    if token_expiry <= issued_at:
        raise ValueError("execution authorization must expire after it is issued")

    normalized_scopes = tuple(
        sorted({scope.strip() for scope in scopes if scope.strip()})
    )
    token_id = uuid4()
    subject = str(execution.initiated_by_user_id or f"execution:{execution.id}")
    claims = {
        "iss": execution_token_issuer(),
        "aud": EXECUTION_TOKEN_AUDIENCE,
        "sub": subject,
        "act": {"sub": f"extension-installation:{installation.id}"},
        "purpose": EXECUTION_TOKEN_PURPOSE,
        "jti": str(token_id),
        "iat": issued_at,
        "exp": token_expiry,
        "execution_id": str(execution.id),
        "root_execution_id": str(execution.root_execution_id),
        "installation_id": str(installation.id),
        "capability_definition_id": str(capability.id),
        "scope": " ".join(normalized_scopes),
        "resources": {
            "course_id": str(execution.course_id) if execution.course_id else None,
            "assignment_id": str(execution.assignment_id)
            if execution.assignment_id
            else None,
            "submission_ids": [str(item) for item in submission_ids],
            "artifact_ids": [str(item) for item in artifact_ids],
        },
    }
    token = jwt.encode(
        claims,
        get_secret_key(),
        algorithm=EXECUTION_TOKEN_ALGORITHM,
        headers={"typ": EXECUTION_TOKEN_TYPE},
    )
    return IssuedExecutionToken(
        token=token,
        expires_at=token_expiry,
        scopes=normalized_scopes,
    )


def require_execution_authorization(
    required_scopes: tuple[str, ...] = (),
    *,
    allow_terminal_retry: bool = False,
):
    def _dependency(
        credentials: HTTPAuthorizationCredentials | None = Depends(execution_bearer),
        db: Session = Depends(session_dependency),
    ) -> ExecutionAuthorization:
        if credentials is None or not credentials.credentials.strip():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing execution bearer token",
            )
        token = credentials.credentials.strip()
        try:
            header = jwt.get_unverified_header(token)
            if header.get("typ") != EXECUTION_TOKEN_TYPE:
                raise JWTError("wrong token type")
            payload = jwt.decode(
                token,
                get_secret_key(),
                algorithms=[EXECUTION_TOKEN_ALGORITHM],
                audience=EXECUTION_TOKEN_AUDIENCE,
                issuer=execution_token_issuer(),
            )
            if payload.get("purpose") != EXECUTION_TOKEN_PURPOSE:
                raise JWTError("wrong token purpose")
            execution_id = UUID(payload["execution_id"])
            installation_id = UUID(payload["installation_id"])
            capability_id = UUID(payload["capability_definition_id"])
            token_id = UUID(payload["jti"])
            actor = payload.get("act") or {}
            if actor.get("sub") != f"extension-installation:{installation_id}":
                raise JWTError("wrong token actor")
        except (JWTError, KeyError, TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired execution token",
            ) from exc

        execution = db.get(Execution, execution_id)
        installation = db.get(ExtensionInstallation, installation_id)
        capability = db.get(CapabilityDefinition, capability_id)
        if (
            execution is None
            or installation is None
            or capability is None
            or execution.extension_installation_id != installation.id
            or execution.capability_definition_id != capability.id
            or capability.installation_id != installation.id
            or _value(installation.status) != ExtensionInstallationStatus.enabled.value
            or (
                _value(execution.status) in TERMINAL_EXECUTION_STATUSES
                and not allow_terminal_retry
            )
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Execution authority has been revoked",
            )
        scopes = frozenset((payload.get("scope") or "").split())
        missing = sorted(set(required_scopes) - scopes)
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing execution scopes: {', '.join(missing)}",
            )
        return ExecutionAuthorization(
            execution=execution,
            installation=installation,
            capability=capability,
            subject=str(payload["sub"]),
            scopes=scopes,
            token_id=token_id,
        )

    return _dependency


__all__ = [
    "EXECUTION_TOKEN_AUDIENCE",
    "EXECUTION_TOKEN_PURPOSE",
    "EXECUTION_TOKEN_TYPE",
    "ExecutionAuthorization",
    "IssuedExecutionToken",
    "issue_execution_token",
    "require_execution_authorization",
]
