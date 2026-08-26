from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from fair_platform.backend.core.config import get_email_enabled
from fair_platform.backend.data.database import session_dependency
from fair_platform.backend.services.access_control import resolve_platform_policy
from fair_platform.backend.services.dispatch_signing import get_dispatch_signer

router = APIRouter()


@router.get("/config")
def get_system_config(db: Session = Depends(session_dependency)):
    policy = resolve_platform_policy(db)
    return {
        "features": {
            "email_enabled": get_email_enabled(),
            "ai_controls_enabled": policy.ai_controls_enabled,
        },
        "registration": {
            "mode": policy.admission_mode.value,
            "invite_required": policy.admission_mode.value == "invite_only",
        },
    }


@router.get("/signing-keys")
def get_signing_keys():
    """Public keys used to verify FAIR-signed Extension commands."""
    return get_dispatch_signer().jwks()


__all__ = ["router"]
