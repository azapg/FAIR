from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr

from fair_platform.backend.data.models.user import UserRole


class UserBase(BaseModel):
    name: str
    email: EmailStr
    role: UserRole = UserRole.professor

    class Config:
        use_enum_values = True
        from_attributes = True
        alias_generator = lambda field_name: "".join(
            word.capitalize() if i > 0 else word
            for i, word in enumerate(field_name.split("_"))
        )
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
        alias_generator = lambda field_name: "".join(
            word.capitalize() if i > 0 else word
            for i, word in enumerate(field_name.split("_"))
        )
        populate_by_name = True


class UserRead(UserBase):
    id: UUID


__all__ = ["UserRole", "UserBase", "UserCreate", "UserUpdate", "UserRead"]
