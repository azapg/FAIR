from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from fair_platform.backend.data.models.user import UserRole
from fair_platform.backend.api.schema.utils import schema_config, schema_config_with_enum


class UserBase(BaseModel):
    model_config = schema_config_with_enum
    
    name: str
    email: EmailStr
    role: UserRole = UserRole.user

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


class UserPreferences(BaseModel):
    model_config = schema_config

    interface_mode: Literal["simple", "expert"] = "simple"


class AuthUserRead(UserRead):
    capabilities: list[str] = Field(default_factory=list)
    preferences: UserPreferences = Field(default_factory=UserPreferences)


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
    "UserPreferences",
    "AuthUserRead",
    "UserSettingsRead",
    "UserSettingsUpdate",
]
