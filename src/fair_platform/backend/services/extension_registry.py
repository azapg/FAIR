from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExtensionRegistration:
    """Represents one registered extension instance.

    This is intentionally generic so future SDK clients can register additional
    metadata without breaking dispatcher behavior.
    """

    extension_id: str
    webhook_url: str
    intents: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True


class LocalExtensionRegistry:
    """In-memory extension registry.

    This is the first minimal implementation used by the dispatcher.
    It can later be replaced with a DB-backed registry while keeping
    the same public async methods.
    """

    def __init__(self):
        self._extensions: dict[str, ExtensionRegistration] = {}

    async def register(
        self,
        registration: ExtensionRegistration,
    ) -> ExtensionRegistration:
        self._extensions[registration.extension_id] = registration
        return registration

    async def get(self, extension_id: str) -> ExtensionRegistration | None:
        extension = self._extensions.get(extension_id)
        if extension is None or not extension.enabled:
            return None
        return extension

    async def list(self) -> list[ExtensionRegistration]:
        return [e for e in self._extensions.values() if e.enabled]

    async def unregister(self, extension_id: str) -> None:
        self._extensions.pop(extension_id, None)


__all__ = ["ExtensionRegistration", "LocalExtensionRegistry"]
