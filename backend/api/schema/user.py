from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr

from data.models.user import UserRole

class UserBase(BaseModel):
    name: str
    email: EmailStr
    role: UserRole

    class Config:
        use_enum_values = True
        orm_mode = True


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None

    class Config:
        use_enum_values = True
        orm_mode = True


class UserRead(UserBase):
    id: UUID


__all__ = ["UserRole", "UserBase", "UserCreate", "UserUpdate", "UserRead"]
