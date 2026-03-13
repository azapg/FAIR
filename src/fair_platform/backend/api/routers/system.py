from fastapi import APIRouter

from fair_platform.backend.core.config import get_email_enabled

router = APIRouter()


@router.get("/config")
def get_system_config():
    return {"features": {"email_enabled": get_email_enabled()}}


__all__ = ["router"]
