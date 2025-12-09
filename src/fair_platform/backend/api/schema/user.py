from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr

from fair_platform.backend.data.models.user import UserRole
from fair_platform.backend.api.schema.utils import schema_config_with_enum


class UserBase(BaseModel):
    model_config = schema_config_with_enum
    
    name: str
    email: EmailStr
    role: UserRole = UserRole.professor


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    model_config = schema_config_with_enum
    
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None


class UserRead(UserBase):
    id: UUID


__all__ = ["UserRole", "UserBase", "UserCreate", "UserUpdate", "UserRead"]
