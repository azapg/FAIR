from typing import Optional, Any, Dict

from pydantic import BaseModel

from fair_platform.sdk import PluginType
from fair_platform.backend.api.schema.utils import to_camel_case


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
        alias_generator = to_camel_case
        populate_by_name = True

class RuntimePlugin(PluginBase):
    settings: Optional[Dict[str, Any]] = None

__all__ = [
    "PluginBase",
    "RuntimePlugin"
]
