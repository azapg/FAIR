from fastapi import APIRouter

from fair_platform.backend.core.config import get_email_enabled
from fair_platform.backend.services.dispatch_signing import get_dispatch_signer

router = APIRouter()


@router.get("/config")
def get_system_config():
    return {"features": {"email_enabled": get_email_enabled()}}


@router.get("/signing-keys")
def get_signing_keys():
    """Public keys used to verify FAIR-signed Extension commands."""
    return get_dispatch_signer().jwks()


__all__ = ["router"]
