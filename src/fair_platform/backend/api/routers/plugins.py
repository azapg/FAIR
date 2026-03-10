from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.api.schema.plugin import RuntimePlugin
from fair_platform.backend.core.security.permissions import has_capability
from fair_platform.backend.data.models import User
from fair_platform.backend.services.extension_catalog import (
    get_registered_plugin,
    list_registered_plugins,
)
from fair_platform.backend.services.extension_registry import LocalExtensionRegistry
from fair_platform.extension_sdk.contracts.plugin import PluginType

router = APIRouter()


def get_extension_registry(request: Request) -> LocalExtensionRegistry:
    return request.app.state.extension_registry


@router.get("/", response_model=list[RuntimePlugin])
async def list_all_plugins(
    type_filter: Optional[PluginType] = None,
    user: User = Depends(get_current_user),
    registry: LocalExtensionRegistry = Depends(get_extension_registry),
):
    if not has_capability(user, "list_plugins"):
        raise HTTPException(status_code=403, detail="Not authorized to list plugins")
    return await list_registered_plugins(registry, plugin_type=type_filter)


@router.get("/{plugin_id}", response_model=RuntimePlugin)
async def get_plugin(
    plugin_id: str,
    user: User = Depends(get_current_user),
    registry: LocalExtensionRegistry = Depends(get_extension_registry),
):
    if not has_capability(user, "list_plugins"):
        raise HTTPException(status_code=403, detail="Not authorized to get plugin")
    plugin = await get_registered_plugin(registry, plugin_id)
    if plugin is None:
        raise HTTPException(status_code=404, detail="Plugin not found")
    return plugin


__all__ = ["router"]
