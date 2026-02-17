from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status

from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.core.security.permissions import has_capability
from fair_platform.backend.data.models.user import User


def require_capability(action: str) -> Callable[[Annotated[User, Depends(get_current_user)]], User]:
    def _checker(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if not has_capability(current_user, action):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing capability: {action}",
            )
        return current_user

    return _checker

