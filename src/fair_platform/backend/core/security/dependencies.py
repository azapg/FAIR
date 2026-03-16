from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from fair_platform.backend.api.routers.auth import (
    get_current_user,
    SECRET_KEY,
    ALGORITHM,
    TOKEN_PURPOSE_EXT_JOB,
    oauth2_scheme,
)
from fair_platform.backend.core.security.permissions import has_capability
from fair_platform.backend.data.database import session_dependency
from fair_platform.backend.data.models import ExtensionClient
from fair_platform.backend.data.models.user import User
from fair_platform.backend.services.extension_auth import authenticate_extension_client

extension_bearer = HTTPBearer(auto_error=False)


def require_capability(action: str) -> Callable[[Annotated[User, Depends(get_current_user)]], User]:
    def _checker(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if not has_capability(current_user, action):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing capability: {action}",
            )
        return current_user

    return _checker


def require_extension_client(
    required_scopes: tuple[str, ...] = (),
) -> Callable[..., ExtensionClient]:
    def _dependency(
        extension_id: Annotated[str | None, Header(alias="X-FAIR-Extension-Id")] = None,
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(extension_bearer)] = None,
        db: Session = Depends(session_dependency),
    ) -> ExtensionClient:
        resolved_extension_id = extension_id.strip() if extension_id else ""
        resolved_secret = ""
        if credentials is not None and credentials.credentials.strip():
            resolved_secret = credentials.credentials.strip()

        if not resolved_extension_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing extension id",
            )
        if not resolved_secret:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing extension bearer token",
            )
        client = authenticate_extension_client(
            db,
            extension_id=resolved_extension_id,
            secret=resolved_secret,
        )
        if client is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid extension credentials",
            )
        if required_scopes:
            granted_scopes = set(client.scopes or [])
            missing_scopes = [scope for scope in required_scopes if scope not in granted_scopes]
            if missing_scopes:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing extension scopes: {', '.join(missing_scopes)}",
                )
        return client

    return _dependency


def get_artifact_download_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(session_dependency),
) -> User:
    """Auth dependency for the artifact download endpoint.

    Accepts two token types:
    1. Regular user session JWT (no 'purpose' claim) — standard login token.
    2. Extension job delegation token ('purpose': 'ext_job') — issued at job
       creation, encodes the user on whose behalf the extension is acting.

    Rejects any other purpose-bearing tokens (e.g. password_reset, verify_email).
    The resolved User is the real user; can_view() will enforce their permissions.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise credentials_exception

    user_id: str | None = payload.get("sub")
    if not user_id:
        raise credentials_exception

    purpose: str | None = payload.get("purpose")
    if purpose is not None and purpose != TOKEN_PURPOSE_EXT_JOB:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token purpose is not permitted for artifact access",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if purpose == TOKEN_PURPOSE_EXT_JOB and (not payload.get("job_id") or not payload.get("ext")):
        raise credentials_exception

    try:
        user = db.get(User, UUID(user_id))
    except Exception:
        raise credentials_exception

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
