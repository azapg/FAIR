from typing import Optional, Any, Dict

from pydantic import BaseModel

from fair_platform.sdk import PluginType


class PluginBase(BaseModel):
    id: str
    name: str
    author: str
    author_email: Optional[str] = None
    version: str
    hash: str
    source: str
    settings_schema: Optional[Dict[str, Any]] = None
    type: PluginType

    class Config:
        from_attributes = True
        alias_generator = lambda field_name: "".join(
            word.capitalize() if i > 0 else word
            for i, word in enumerate(field_name.split("_"))
        )
        validate_by_name = True

class RuntimePlugin(PluginBase):
    settings: Optional[Dict[str, Any]] = None

__all__ = [
    "PluginBase",
    "RuntimePlugin"
]
