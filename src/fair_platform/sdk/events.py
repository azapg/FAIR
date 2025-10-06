import inspect
from collections import defaultdict


class EventBus:
    def __init__(self):
        self.listeners = defaultdict(list)

    def on(self, event_name: str, callback):
        self.listeners[event_name].append(callback)

    async def emit(self, event_name: str, *args, **kwargs):
        for callback in self.listeners[event_name]:
            if inspect.iscoroutine(callback):
                await callback(*args, **kwargs)
            else:
                callback(*args, **kwargs)