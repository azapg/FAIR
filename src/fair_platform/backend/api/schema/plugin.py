from typing import Optional

from pydantic import BaseModel


class PluginBase(BaseModel):
    id: str
    name: str
    author: str = None
    author_email: Optional[str] = None
    version: str = None
    hash: str
    source: str

    class Config:
        from_attributes = True
        alias_generator = lambda field_name: "".join(
            word.capitalize() if i > 0 else word
            for i, word in enumerate(field_name.split("_"))
        )
        validate_by_name = True


__all__ = [
    "PluginBase",
]
