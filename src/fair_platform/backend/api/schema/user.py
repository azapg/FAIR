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
        orm_mode = True


class UserCreate(UserBase):
    password: str  # TODO: This will require proper password hashing implementation


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
