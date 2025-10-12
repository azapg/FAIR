import asyncio
from datetime import datetime

from fair_platform.sdk.events import EventBus


# TODO: Maybe a Logger interface so you can have a PluginLogger without a session?

class SessionLogger:
    def __init__(self, session_id: str, bus: EventBus, *, index: int = 0):
        self.session_id = session_id
        self.bus = bus
        self.index = index

    def log(self, level: str, message: str):
        self.emit("log", {"message": message}, level=level)

    def info(self, message: str):
        self.log("info", message)

    def warning(self, message: str):
        self.log("warning", message)

    def error(self, message: str):
        self.log("error", message)

    def debug(self, message: str):
        self.log("debug", message)

    def emit(self, event_type: str, payload: dict, *, level: str = "info"):
        coro = self.bus.emit(event_type, data={
            "type": "log",
            "index": self.next(),
            "ts": datetime.now().isoformat(),
            "level": level,
            "payload": payload
        })
        try:
            asyncio.get_event_loop()
            asyncio.create_task(coro)
        except RuntimeError:
            asyncio.run(coro)

    def next(self):
        self.index += 1
        return self.index

    def get_child(self, plugin_id: str):
        """Return a logger for a specific plugin"""
        return PluginLogger(plugin_id, self.session_id, bus=self.bus)


class PluginLogger(SessionLogger):
    def __init__(self, identifier: str, session_id: str, bus: EventBus):
        super().__init__(session_id, bus)
        self.identifier = identifier

    def log(self, level: str, message: str):
        self.emit("log", {"message": message, "plugin": self.identifier}, level=level)
