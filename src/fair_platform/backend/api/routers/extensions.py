from fastapi import APIRouter, Depends, Request, status

from fair_platform.backend.api.schema.extension import (
    ExtensionRead,
    ExtensionRegisterRequest,
)
from fair_platform.backend.services.extension_registry import (
    ExtensionRegistration,
    LocalExtensionRegistry,
)

router = APIRouter()


def get_extension_registry(request: Request) -> LocalExtensionRegistry:
    registry = getattr(request.app.state, "extension_registry", None)
    if registry is None:
        registry = LocalExtensionRegistry()
        request.app.state.extension_registry = registry
    return registry


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=ExtensionRead)
async def register_extension(
    payload: ExtensionRegisterRequest,
    registry: LocalExtensionRegistry = Depends(get_extension_registry),
):
    # TODO(auth): require extension credentials/signature for registration.
    registration = await registry.register(
        ExtensionRegistration(
            extension_id=payload.extension_id,
            webhook_url=payload.webhook_url,
            intents=payload.intents,
            capabilities=payload.capabilities,
            metadata=payload.metadata,
        )
    )
    return ExtensionRead(
        extension_id=registration.extension_id,
        webhook_url=registration.webhook_url,
        intents=registration.intents,
        capabilities=registration.capabilities,
        metadata=registration.metadata,
        enabled=registration.enabled,
    )


@router.get("/", response_model=list[ExtensionRead])
async def list_extensions(
    registry: LocalExtensionRegistry = Depends(get_extension_registry),
):
    records = await registry.list()
    return [
        ExtensionRead(
            extension_id=record.extension_id,
            webhook_url=record.webhook_url,
            intents=record.intents,
            capabilities=record.capabilities,
            metadata=record.metadata,
            enabled=record.enabled,
        )
        for record in records
    ]


__all__ = ["router", "get_extension_registry"]
