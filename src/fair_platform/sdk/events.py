import inspect
from collections import defaultdict


class EventBus:
    def __init__(self):
        self.listeners = defaultdict(list)

    def on(self, event_name: str, callback):
        self.listeners[event_name].append(callback)

    async def emit(self, event_name: str, data):
        for callback in self.listeners[event_name]:
            if inspect.iscoroutine(callback):
                await callback(data=data)
            else:
                callback(data=data)

class DebugEventBus(EventBus):
    async def emit(self, event_name: str, data):
        print(f"[DEBUG] [{event_name}]: {data}")