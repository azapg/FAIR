from typing import Optional, Dict, Any

from pydantic import BaseModel


class PluginBase(BaseModel):
    id: str
    name: str
    author: str = None
    author_email: Optional[str] = None
    version: str = None
    hash: str
    source: str
    settings: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True
        alias_generator = lambda field_name: ''.join(word.capitalize() if i > 0 else word for i, word in enumerate(field_name.split('_')))
        validate_by_name = True

class PluginCreate(PluginBase):
    pass


class PluginUpdate(BaseModel):
    name: Optional[str] = None
    author: Optional[str] = None
    version: Optional[str] = None
    source: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True
        alias_generator = lambda field_name: ''.join(word.capitalize() if i > 0 else word for i, word in enumerate(field_name.split('_')))
        validate_by_name = True


class PluginRead(PluginBase):
    pass


__all__ = [
    "PluginBase",
    "PluginCreate",
    "PluginUpdate",
    "PluginRead",
]

