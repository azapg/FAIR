from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr

from fair_platform.backend.data.models.user import UserRole
from fair_platform.backend.api.schema.utils import to_camel_case


class UserBase(BaseModel):
    name: str
    email: EmailStr
    role: UserRole = UserRole.professor

    class Config:
        use_enum_values = True
        from_attributes = True
        alias_generator = to_camel_case
        populate_by_name = True


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None

    class Config:
        use_enum_values = True
        from_attributes = True
        alias_generator = to_camel_case
        populate_by_name = True


class UserRead(UserBase):
    id: UUID


__all__ = ["UserRole", "UserBase", "UserCreate", "UserUpdate", "UserRead"]
