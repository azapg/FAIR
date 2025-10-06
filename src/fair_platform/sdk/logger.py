import asyncio
from typing import Optional

from fair_platform.sdk.events import EventBus


class ExtensionLogger:
    def __init__(self, identifier: str, *, bus: Optional[EventBus], _mode = "debug"):
        self._identifier = identifier
        self._mode = _mode

        if _mode == "bus" and bus is None:
            raise ValueError("EventBus must be provided when mode is 'bus'")

        self._bus = bus

    def log(self, message: str):
        self._emit("log", message=message)

    def _emit(self, name: str, *args, **kwargs):
        if self._mode == "debug":
            print(f"[{self._identifier}] {name}: ", *args, **kwargs)
        elif self._mode == "bus" and self._bus is not None:
            event_name = f"extension:{self._identifier}:{name}"
            coro = self._bus.emit(event_name, *args, **kwargs)
            try:
                loop = asyncio.get_event_loop()
                asyncio.create_task(coro)
            except RuntimeError:
                asyncio.run(coro)
        else:
            raise ValueError(f"Unknown mode: {self._mode}")