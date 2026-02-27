from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Response
from typing_extensions import deprecated

from fair_platform.backend.api.deprecation import (
    LEGACY_SDK_DEPRECATION_MESSAGE,
    apply_legacy_sdk_deprecation_headers,
)
from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.core.security.permissions import has_capability
from fair_platform.backend.data.models import User
from fair_platform.sdk import (
    list_plugins,
    PluginMeta,
    PluginType,
)

router = APIRouter()


@router.get("/", response_model=List[PluginMeta])
@deprecated(LEGACY_SDK_DEPRECATION_MESSAGE)
def list_all_plugins(
        response: Response,
        type_filter: Optional[PluginType] = None, user: User = Depends(get_current_user)
):
    apply_legacy_sdk_deprecation_headers(response)

    if not has_capability(user, "list_plugins"):
        raise HTTPException(status_code=403, detail="Not authorized to list plugins")
    plugins = list_plugins(plugin_type=type_filter)
    return plugins


__all__ = ["router"]
