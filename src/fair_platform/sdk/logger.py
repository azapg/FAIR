import asyncio
from datetime import datetime
from typing import Optional

from fair_platform.backend.data.models.submission_result import TYPE_CHECKING
from fair_platform.sdk.events import EventBus

# TODO: Maybe a Logger interface so you can have a PluginLogger without a session?
# TODO: Bro what? Why the base logger is a session logger?
if TYPE_CHECKING:
    from fair_platform.backend.data.models.plugin import Plugin


class SessionLogger:
    def __init__(self, session_id: str, bus: EventBus):
        self.session_id = session_id
        self.bus = bus

    def log(self, level: str, message: str):
        return self.emit("log", {"message": message}, level=level)

    def info(self, message: str):
        return self.log("info", message)

    def warning(self, message: str):
        return self.log("warning", message)

    def error(self, message: str):
        return self.log("error", message)

    def debug(self, message: str):
        return self.log("debug", message)

    async def _emit_async(self, event_type: str, payload: dict, *, level: str = "info"):
        await self.bus.emit(
            event_type,
            data={
                "type": "log",
                "ts": datetime.now().isoformat(),
                "level": level,
                "payload": payload,
            },
        )

    def emit(self, event_type: str, payload: dict, *, level: str = "info"):
        coro = self._emit_async(event_type, payload, level=level)

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)

        task = asyncio.create_task(coro)
        return task

    def get_child(self, plugin: Optional["Plugin"] = None):
        """Return a logger for a specific plugin"""
        return PluginLogger(session_id=self.session_id, bus=self.bus, plugin=plugin)


class PluginLogger(SessionLogger):
    def __init__(
        self, session_id: str, bus: EventBus, plugin: Optional["Plugin"] = None
    ):
        super().__init__(session_id, bus)
        self.plugin = plugin

    def log(self, level: str, message: str):
        payload = {"message": message}
        if self.plugin is not None:
            payload["plugin"] = {
                "id": self.plugin.id,
                "name": self.plugin.name,
                "hash": self.plugin.hash,
                "author": self.plugin.author,
                "version": self.plugin.version,
                "source": self.plugin.source,
                "type": self.plugin.type,
            }
        return self.emit("log", payload, level=level)
