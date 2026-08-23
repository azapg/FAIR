from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi.encoders import jsonable_encoder

from fair_platform.backend.api.schema.casing import to_camel_keys
from fair_platform.backend.core.config import (
    get_base_url,
    get_deployment_mode,
    get_email_enabled,
    get_enforce_email_verification,
)
from fair_platform.backend.core.security.permissions import auth_user_payload
from fair_platform.backend.data.models.user import User


def build_initial_state(user: User | None = None) -> dict[str, Any]:
    auth_user: dict[str, Any] | None = None
    if user is not None:
        auth_user = jsonable_encoder(to_camel_keys(auth_user_payload(user)))

    return {
        "auth": {
            "isAuthenticated": user is not None,
            "user": auth_user,
        },
        "features": {
            "emailEnabled": get_email_enabled(),
            "enforceEmailVerification": get_enforce_email_verification(),
        },
        "platform": {
            "deploymentMode": get_deployment_mode(),
            "baseUrl": get_base_url(),
        },
        "injectedAt": datetime.now(timezone.utc).isoformat(),
    }


__all__ = ["build_initial_state"]
