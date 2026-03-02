from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from fair_platform.backend.api.routers.auth import get_current_user
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
