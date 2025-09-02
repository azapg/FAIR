from typing import Optional, Dict, Any

from pydantic import BaseModel


class PluginBase(BaseModel):
    id: str
    name: str
    author: Optional[str] = None
    version: Optional[str] = None
    hash: str
    source: str
    meta: Optional[Dict[str, Any]] = None

    class Config:
        orm_mode = True


class PluginCreate(PluginBase):
    pass


class PluginUpdate(BaseModel):
    name: Optional[str] = None
    author: Optional[str] = None
    version: Optional[str] = None
    source: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None

    class Config:
        orm_mode = True


class PluginRead(PluginBase):
    pass


__all__ = [
    "PluginBase",
    "PluginCreate",
    "PluginUpdate",
    "PluginRead",
]

