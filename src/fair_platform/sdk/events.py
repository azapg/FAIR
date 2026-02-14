import inspect
import uuid
from collections import defaultdict
from datetime import date, datetime


def normalize_event_message(event_name: str, data):
    event_type = event_name
    level = "info"
    index = None
    ts = datetime.now().isoformat()
    payload = {}

    if isinstance(data, dict):
        raw_type = data.get("type")
        if isinstance(raw_type, str) and raw_type:
            event_type = raw_type

        if isinstance(data.get("level"), str) and data.get("level"):
            level = data.get("level")
        if isinstance(data.get("ts"), str) and data.get("ts"):
            ts = data.get("ts")
        if isinstance(data.get("index"), int):
            index = data.get("index")

        source_payload = data.get("payload")
        if isinstance(source_payload, dict):
            payload.update(source_payload)
            if not isinstance(data.get("ts"), str):
                payload_ts = payload.get("ts")
                if isinstance(payload_ts, str) and payload_ts:
                    ts = payload_ts
            payload.pop("ts", None)
        elif source_payload is not None:
            payload["value"] = source_payload

        for key, value in data.items():
            if key in {"index", "type", "level", "ts", "payload"}:
                continue
            payload[key] = value
    else:
        payload = {"value": data}

    if event_type == "log" and not isinstance(payload.get("plugin"), dict):
        event_type = "system"

    message = {"type": event_type, "level": level, "ts": ts, "payload": payload}
    if index is not None:
        message["index"] = index
    return message


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

        payload = normalize_event_message(event_name, _to_jsonable(data))

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
            payload = {"index": current_index, "payload": data}
        await super().emit(event_name, payload)


class DebugEventBus(EventBus):
    async def emit(self, event_name: str, data):
        print(f"[DEBUG] [{event_name}]: {data}")
