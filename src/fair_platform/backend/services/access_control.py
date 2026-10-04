from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from fair_platform.backend.core.config import (
    get_admission_mode_override,
    get_ai_controls_enabled_override,
)
from fair_platform.backend.data.models.access_control import (
    AdmissionMode,
    AdmissionRule,
    AdmissionRuleKind,
    AICapabilityClassification,
    AICapabilityPolicy,
    AIEntitlement,
    AIEntitlementState,
    AIUsageCharge,
    PlatformPolicy,
    RegistrationInvite,
)
from fair_platform.backend.data.models.user import normalize_email_address


class AccessPolicyError(RuntimeError):
    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        detail: str,
        extra: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.code = code
        self.detail = detail
        self.extra = extra or {}


@dataclass(frozen=True)
class EffectivePlatformPolicy:
    admission_mode: AdmissionMode
    admission_source: str
    ai_controls_enabled: bool
    ai_controls_source: str


def _value(value: object) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _as_utc(value: datetime) -> datetime:
    return (
        value.replace(tzinfo=timezone.utc)
        if value.tzinfo is None
        else value.astimezone(timezone.utc)
    )


def utc_month_start(now: datetime | None = None) -> date:
    resolved = now or datetime.now(timezone.utc)
    return date(resolved.year, resolved.month, 1)


def next_utc_month_start(period_start: date) -> datetime:
    if period_start.month == 12:
        return datetime(period_start.year + 1, 1, 1, tzinfo=timezone.utc)
    return datetime(period_start.year, period_start.month + 1, 1, tzinfo=timezone.utc)


def read_platform_policy(session: Session) -> PlatformPolicy | None:
    return session.get(PlatformPolicy, 1)


def get_or_create_platform_policy(session: Session) -> PlatformPolicy:
    row = read_platform_policy(session)
    if row is None:
        row = PlatformPolicy(
            id=1,
            admission_mode=AdmissionMode.open,
            ai_controls_enabled=False,
        )
        session.add(row)
        session.flush()
    return row


def resolve_platform_policy(session: Session) -> EffectivePlatformPolicy:
    stored = read_platform_policy(session)
    stored_admission = (
        AdmissionMode(_value(stored.admission_mode)) if stored else AdmissionMode.open
    )
    stored_ai = bool(stored.ai_controls_enabled) if stored else False
    admission_override = get_admission_mode_override()
    ai_override = get_ai_controls_enabled_override()
    return EffectivePlatformPolicy(
        admission_mode=(
            AdmissionMode(admission_override)
            if admission_override is not None
            else stored_admission
        ),
        admission_source="environment"
        if admission_override is not None
        else "database",
        ai_controls_enabled=ai_override if ai_override is not None else stored_ai,
        ai_controls_source="environment" if ai_override is not None else "database",
    )


def normalize_domain(value: str) -> str:
    domain = value.strip().lstrip("@").rstrip(".")
    if not domain or "@" in domain:
        raise ValueError("A valid domain is required")
    try:
        return domain.encode("idna").decode("ascii").casefold()
    except UnicodeError as exc:
        raise ValueError("A valid domain is required") from exc


def normalize_admission_rule(kind: str, value: str) -> str:
    if kind == AdmissionRuleKind.email.value:
        return normalize_email_address(value)
    if kind == AdmissionRuleKind.domain.value:
        return normalize_domain(value)
    raise ValueError("Admission rule kind must be email or domain")


def _invite_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_registration_invite(
    session: Session,
    *,
    email: str,
    created_by_user_id: UUID,
    expires_in_days: int = 7,
) -> tuple[RegistrationInvite, str]:
    if not 1 <= expires_in_days <= 90:
        raise ValueError("Invite expiry must be between 1 and 90 days")
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    row = RegistrationInvite(
        token_hash=_invite_hash(token),
        normalized_email=normalize_email_address(email),
        expires_at=now + timedelta(days=expires_in_days),
        created_by_user_id=created_by_user_id,
    )
    session.add(row)
    session.flush()
    return row, token


def authorize_registration(
    session: Session,
    *,
    normalized_email: str,
    invite_token: str | None,
) -> RegistrationInvite | None:
    mode = resolve_platform_policy(session).admission_mode
    if mode is AdmissionMode.open:
        return None
    if mode is AdmissionMode.allowlist:
        domain = normalized_email.rsplit("@", 1)[1]
        allowed = session.scalar(
            select(AdmissionRule.id).where(
                or_(
                    (
                        (AdmissionRule.kind == AdmissionRuleKind.email)
                        & (AdmissionRule.normalized_value == normalized_email)
                    ),
                    (
                        (AdmissionRule.kind == AdmissionRuleKind.domain)
                        & (AdmissionRule.normalized_value == domain)
                    ),
                )
            )
        )
        if allowed is not None:
            return None
        raise AccessPolicyError(
            status_code=403,
            code="registration_not_permitted",
            detail="Registration is not available for this email address.",
        )

    if not invite_token or len(invite_token) > 512:
        raise AccessPolicyError(
            status_code=403,
            code="registration_not_permitted",
            detail="A valid registration invitation is required.",
        )
    invitation = session.scalar(
        select(RegistrationInvite)
        .where(RegistrationInvite.token_hash == _invite_hash(invite_token))
        .with_for_update()
    )
    now = datetime.now(timezone.utc)
    if (
        invitation is None
        or invitation.normalized_email != normalized_email
        or invitation.redeemed_at is not None
        or invitation.revoked_at is not None
        or _as_utc(invitation.expires_at) <= now
    ):
        raise AccessPolicyError(
            status_code=403,
            code="registration_not_permitted",
            detail="A valid registration invitation is required.",
        )
    return invitation


def _entitlement_payload(row: AIEntitlement | None) -> dict[str, Any]:
    if row is None:
        period = utc_month_start()
        return {
            "state": AIEntitlementState.disabled.value,
            "monthlyLimitUnits": None,
            "usedUnits": 0,
            "remainingUnits": 0,
            "periodStart": period,
            "nextResetAt": next_utc_month_start(period),
        }
    period = row.period_start
    used = row.used_units if period == utc_month_start() else 0
    limit = row.monthly_limit_units
    remaining = None if limit is None else max(limit - used, 0)
    return {
        "state": _value(row.state),
        "monthlyLimitUnits": limit,
        "usedUnits": used,
        "remainingUnits": remaining,
        "periodStart": utc_month_start() if period != utc_month_start() else period,
        "nextResetAt": next_utc_month_start(
            utc_month_start() if period != utc_month_start() else period
        ),
    }


def entitlement_payload(session: Session, user_id: UUID) -> dict[str, Any]:
    effective = resolve_platform_policy(session)
    payload = _entitlement_payload(session.get(AIEntitlement, user_id))
    payload["controlsEnabled"] = effective.ai_controls_enabled
    return payload


def capability_cost_control(
    session: Session,
    *,
    capability_definition_id: UUID,
    user_id: UUID | None,
) -> dict[str, Any]:
    effective = resolve_platform_policy(session)
    policy = session.get(AICapabilityPolicy, capability_definition_id)
    classification = _value(policy.classification) if policy else "unclassified"
    units = policy.cost_units if policy else None
    executable = True
    reason = None
    if effective.ai_controls_enabled:
        if policy is None:
            executable = False
            reason = "ai_policy_unconfigured"
        elif classification == AICapabilityClassification.ai.value:
            if user_id is None:
                executable = False
                reason = "ai_not_entitled"
            else:
                entitlement = session.get(AIEntitlement, user_id)
                state = _value(entitlement.state) if entitlement else "disabled"
                if state == AIEntitlementState.disabled.value:
                    executable = False
                    reason = "ai_not_entitled"
                elif state == AIEntitlementState.limited.value:
                    used = (
                        entitlement.used_units
                        if entitlement.period_start == utc_month_start()
                        else 0
                    )
                    if used + policy.cost_units > int(
                        entitlement.monthly_limit_units or 0
                    ):
                        executable = False
                        reason = "ai_quota_exhausted"
    return {
        "controlsEnabled": effective.ai_controls_enabled,
        "classification": classification,
        "costUnits": units,
        "executable": executable,
        "reason": reason,
    }


def reserve_execution_credits(
    session: Session,
    *,
    execution_id: UUID,
    user_id: UUID | None,
    capability_definition_id: UUID | None,
) -> AIUsageCharge | None:
    effective = resolve_platform_policy(session)
    if not effective.ai_controls_enabled or capability_definition_id is None:
        return None
    policy = session.get(AICapabilityPolicy, capability_definition_id)
    if policy is None:
        raise AccessPolicyError(
            status_code=503,
            code="ai_policy_unconfigured",
            detail="This capability has not been classified by an administrator.",
        )
    if _value(policy.classification) == AICapabilityClassification.unmetered.value:
        return None
    if user_id is None:
        raise AccessPolicyError(
            status_code=403,
            code="ai_not_entitled",
            detail="Metered capabilities require a user entitlement.",
        )

    period = utc_month_start()
    session.execute(
        update(AIEntitlement)
        .where(
            AIEntitlement.user_id == user_id,
            AIEntitlement.period_start != period,
        )
        .values(period_start=period, used_units=0)
    )
    entitlement = session.get(AIEntitlement, user_id)
    if (
        entitlement is None
        or _value(entitlement.state) == AIEntitlementState.disabled.value
    ):
        raise AccessPolicyError(
            status_code=403,
            code="ai_not_entitled",
            detail="AI access has not been enabled for this account.",
        )

    state = _value(entitlement.state)
    conditions = [
        AIEntitlement.user_id == user_id,
        AIEntitlement.period_start == period,
        AIEntitlement.state == entitlement.state,
    ]
    if state == AIEntitlementState.limited.value:
        conditions.append(
            AIEntitlement.used_units + policy.cost_units
            <= AIEntitlement.monthly_limit_units
        )
    result = session.execute(
        update(AIEntitlement)
        .where(*conditions)
        .values(used_units=AIEntitlement.used_units + policy.cost_units)
    )
    if result.rowcount != 1:
        raise AccessPolicyError(
            status_code=429,
            code="ai_quota_exhausted",
            detail="This account has reached its monthly AI credit limit.",
            extra={"nextResetAt": next_utc_month_start(period).isoformat()},
        )

    charge = AIUsageCharge(
        execution_id=execution_id,
        user_id=user_id,
        capability_definition_id=capability_definition_id,
        units=policy.cost_units,
        period_start=period,
    )
    session.add(charge)
    session.flush()
    return charge


def usage_total_for_period(session: Session, period_start: date | None = None) -> int:
    period = period_start or utc_month_start()
    return int(
        session.scalar(
            select(func.coalesce(func.sum(AIUsageCharge.units), 0)).where(
                AIUsageCharge.period_start == period
            )
        )
        or 0
    )


__all__ = [
    "AccessPolicyError",
    "EffectivePlatformPolicy",
    "authorize_registration",
    "capability_cost_control",
    "create_registration_invite",
    "entitlement_payload",
    "get_or_create_platform_policy",
    "next_utc_month_start",
    "normalize_admission_rule",
    "read_platform_policy",
    "reserve_execution_credits",
    "resolve_platform_policy",
    "usage_total_for_period",
    "utc_month_start",
]
