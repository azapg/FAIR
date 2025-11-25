from typing import Optional
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel


class SubmitterBase(BaseModel):
    name: str
    email: Optional[str] = None
    user_id: Optional[UUID] = None
    is_synthetic: bool = False

    class Config:
        from_attributes = True
        alias_generator = lambda field_name: "".join(
            word.capitalize() if i > 0 else word
            for i, word in enumerate(field_name.split("_"))
        )
        populate_by_name = True


class SubmitterCreate(SubmitterBase):
    pass


class SubmitterRead(SubmitterBase):
    id: UUID
    created_at: datetime


__all__ = ["SubmitterBase", "SubmitterCreate", "SubmitterRead"]
