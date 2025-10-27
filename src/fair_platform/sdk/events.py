import inspect
import uuid
from collections import defaultdict
from datetime import date, datetime


class EventBus:
    def __init__(self):
        self.listeners = defaultdict(list)

    def on(self, event_name: str, callback):
        self.listeners[event_name].append(callback)

    def off(self, event_name: str, callback):
        if callback in self.listeners[event_name]:
            self.listeners[event_name].remove(callback)
            if not self.listeners[event_name]:
                del self.listeners[event_name]

    async def emit(self, event_name: str, data):
        def _to_jsonable(obj):
            if isinstance(obj, uuid.UUID):
                return str(obj)
            if isinstance(obj, (datetime, date)):
                return obj.isoformat()
            if isinstance(obj, dict):
                return {k: _to_jsonable(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple, set)):
                return [_to_jsonable(v) for v in obj]
            return obj

        payload = _to_jsonable(data)
        if isinstance(payload, dict):
            if "type" not in payload:
                payload["type"] = event_name

        for callback in list(self.listeners.get(event_name, [])):
            try:
                result = callback(payload)
            except TypeError:
                result = callback(data=payload)
            if inspect.isawaitable(result):
                await result


class IndexedEventBus(EventBus):
    def __init__(self):
        super().__init__()
        self._index = 0

    async def emit(self, event_name: str, data):
        current_index = self._index
        self._index += 1
        if isinstance(data, dict):
            payload = dict(data)
            payload["index"] = current_index
        else:
            payload = data
        await super().emit(event_name, payload)


class DebugEventBus(EventBus):
    async def emit(self, event_name: str, data):
        print(f"[DEBUG] [{event_name}]: {data}")
