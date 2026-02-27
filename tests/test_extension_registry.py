import pytest

from fair_platform.backend.services.extension_registry import (
    ExtensionRegistration,
    LocalExtensionRegistry,
)


@pytest.mark.asyncio
async def test_local_extension_registry_register_get_list_unregister():
    registry = LocalExtensionRegistry()

    ext = ExtensionRegistration(
        extension_id="fairgrade.core",
        webhook_url="http://localhost:9000/hooks/jobs",
        intents=["rubrics.generate"],
        capabilities=["rubrics"],
    )
    await registry.register(ext)

    fetched = await registry.get("fairgrade.core")
    assert fetched is not None
    assert fetched.extension_id == "fairgrade.core"

    listed = await registry.list()
    assert len(listed) == 1
    assert listed[0].extension_id == "fairgrade.core"

    await registry.unregister("fairgrade.core")
    assert await registry.get("fairgrade.core") is None
