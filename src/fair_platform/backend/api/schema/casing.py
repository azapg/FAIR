from __future__ import annotations

import re
from typing import Any

from pydantic.alias_generators import to_camel


_FIRST_CAP_RE = re.compile("(.)([A-Z][a-z]+)")
_ALL_CAP_RE = re.compile("([a-z0-9])([A-Z])")


class KeyConflictError(ValueError):
    def __init__(self, path: str, normalized_key: str) -> None:
        super().__init__(
            f"Conflicting keys normalize to '{normalized_key}' at '{path or '$'}'"
        )
        self.path = path
        self.normalized_key = normalized_key


def _to_snake(name: str) -> str:
    snake = _FIRST_CAP_RE.sub(r"\1_\2", name)
    snake = _ALL_CAP_RE.sub(r"\1_\2", snake)
    return snake.replace("-", "_").lower()


def to_camel_keys(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            (to_camel(key) if isinstance(key, str) else key): to_camel_keys(subvalue)
            for key, subvalue in value.items()
        }
    if isinstance(value, list):
        return [to_camel_keys(item) for item in value]
    return value


def to_snake_keys(value: Any, *, path: str = "") -> Any:
    if isinstance(value, dict):
        normalized: dict[Any, Any] = {}
        seen: dict[str, str] = {}
        for key, subvalue in value.items():
            normalized_key = _to_snake(key) if isinstance(key, str) else key
            if isinstance(normalized_key, str):
                existing = seen.get(normalized_key)
                if existing is not None and existing != key:
                    raise KeyConflictError(path, normalized_key)
                seen[normalized_key] = key
            next_path = (
                f"{path}.{normalized_key}"
                if path and isinstance(normalized_key, str)
                else (str(normalized_key) if isinstance(normalized_key, str) else path)
            )
            normalized[normalized_key] = to_snake_keys(subvalue, path=next_path)
        return normalized
    if isinstance(value, list):
        return [to_snake_keys(item, path=f"{path}[{idx}]") for idx, item in enumerate(value)]
    return value


__all__ = ["KeyConflictError", "to_camel_keys", "to_snake_keys"]
