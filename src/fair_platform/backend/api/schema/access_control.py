from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, model_validator

from fair_platform.backend.api.schema.utils import schema_config


AdmissionModeValue = Literal["open", "allowlist", "invite_only"]


class PlatformPolicyRead(BaseModel):
    model_config = schema_config
    stored_admission_mode: AdmissionModeValue
    effective_admission_mode: AdmissionModeValue
    admission_source: Literal["database", "environment"]
    admission_locked: bool
    stored_ai_controls_enabled: bool
    effective_ai_controls_enabled: bool
    ai_controls_source: Literal["database", "environment"]
    ai_controls_locked: bool
    updated_at: datetime | None


class PlatformPolicyUpdate(BaseModel):
    model_config = schema_config
    admission_mode: AdmissionModeValue | None = None
    ai_controls_enabled: bool | None = None


class AdmissionRuleCreate(BaseModel):
    model_config = schema_config
    kind: Literal["email", "domain"]
    value: str = Field(min_length=1, max_length=320)


class AdmissionRuleRead(BaseModel):
    model_config = schema_config
    id: UUID
    kind: Literal["email", "domain"]
    value: str
    created_at: datetime


class InviteCreate(BaseModel):
    model_config = schema_config
    email: EmailStr
    expires_in_days: int = Field(default=7, ge=1, le=90)
    send_email: bool = False


class InviteRead(BaseModel):
    model_config = schema_config
    id: UUID
    email: EmailStr
    expires_at: datetime
    redeemed_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime
    active: bool


class InviteSecretRead(InviteRead):
    token: str
    registration_url: str


class CapabilityCostPolicyUpdate(BaseModel):
    model_config = schema_config
    classification: Literal["unmetered", "ai"]
    cost_units: int = Field(ge=0, le=1_000_000)

    @model_validator(mode="after")
    def validate_weight(self):
        if self.classification == "unmetered" and self.cost_units != 0:
            raise ValueError("Unmetered capabilities must cost 0 units")
        if self.classification == "ai" and self.cost_units <= 0:
            raise ValueError("AI capabilities must cost at least 1 unit")
        return self


class CapabilityCostPolicyRead(BaseModel):
    model_config = schema_config
    capability_definition_id: UUID
    capability_id: str
    display_name: str | None
    version: str
    surface: str
    extension_id: str
    classification: Literal["unclassified", "unmetered", "ai"]
    cost_units: int | None
    updated_at: datetime | None


class AIEntitlementUpdate(BaseModel):
    model_config = schema_config
    state: Literal["disabled", "limited", "unlimited"]
    monthly_limit_units: int | None = Field(default=None, ge=1, le=1_000_000_000)

    @model_validator(mode="after")
    def validate_limit(self):
        if self.state == "limited" and self.monthly_limit_units is None:
            raise ValueError("Limited entitlements require a monthly limit")
        if self.state != "limited" and self.monthly_limit_units is not None:
            raise ValueError("Only limited entitlements have a monthly limit")
        return self


class AIEntitlementRead(BaseModel):
    model_config = schema_config
    user_id: UUID
    user_name: str
    user_email: EmailStr
    state: Literal["disabled", "limited", "unlimited"]
    monthly_limit_units: int | None
    used_units: int
    remaining_units: int | None
    period_start: date
    next_reset_at: datetime
    controls_enabled: bool


class SelfAIEntitlementRead(BaseModel):
    model_config = schema_config
    state: Literal["disabled", "limited", "unlimited"]
    monthly_limit_units: int | None
    used_units: int
    remaining_units: int | None
    period_start: date
    next_reset_at: datetime
    controls_enabled: bool


class AIUsageChargeRead(BaseModel):
    model_config = schema_config
    id: UUID
    execution_id: UUID
    user_id: UUID
    user_email: EmailStr
    capability_definition_id: UUID
    capability_id: str
    units: int
    period_start: date
    created_at: datetime


class AIUsageRead(BaseModel):
    model_config = schema_config
    period_start: date
    total_units: int
    charges: list[AIUsageChargeRead]


__all__ = [name for name in globals() if not name.startswith("_")]
