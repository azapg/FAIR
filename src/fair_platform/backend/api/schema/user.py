from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from fair_platform.backend.data.models.user import UserRole
from fair_platform.backend.api.schema.utils import schema_config, schema_config_with_enum


class UserBase(BaseModel):
    model_config = schema_config_with_enum
    
    name: str
    email: EmailStr
    role: UserRole = UserRole.user
    is_verified: bool = False

    @field_validator("role", mode="before")
    @classmethod
    def _normalize_legacy_role(cls, value):
        if value == "student":
            return UserRole.user
        if value == "professor":
            return UserRole.instructor
        return value


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    model_config = schema_config_with_enum
    
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None


class UserRead(UserBase):
    id: UUID


class AuthUserRead(UserRead):
    capabilities: list[str] = Field(default_factory=list)
    settings: dict[str, Any] = Field(default_factory=dict)


class UserSettingsRead(BaseModel):
    model_config = schema_config

    settings: dict[str, Any] = Field(default_factory=dict)


class UserSettingsUpdate(BaseModel):
    model_config = schema_config

    settings: dict[str, Any]


__all__ = [
    "UserRole",
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserRead",
    "AuthUserRead",
    "UserSettingsRead",
    "UserSettingsUpdate",
]
