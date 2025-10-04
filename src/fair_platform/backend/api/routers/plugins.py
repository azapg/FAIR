from typing import Optional, List

from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.data.models import User, UserRole
from fair_platform.sdk import (
    list_plugins,
    PluginMeta,
    PluginType,
)
from fastapi import APIRouter, Depends, HTTPException

router = APIRouter()


@router.get("/", response_model=List[PluginMeta])
def list_all_plugins(
        type_filter: Optional[PluginType] = None, user: User = Depends(get_current_user)
):
    if user.role != UserRole.admin and user.role != UserRole.professor:
        raise HTTPException(status_code=403, detail="Not authorized to list plugins")
    plugins = list_plugins(plugin_type=type_filter)
    return plugins


__all__ = ["router"]
