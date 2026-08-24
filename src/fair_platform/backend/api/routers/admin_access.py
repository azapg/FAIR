from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.api.schema.access_control import (
    AdmissionRuleCreate,
    AdmissionRuleRead,
    AIEntitlementRead,
    AIEntitlementUpdate,
    AIUsageChargeRead,
    AIUsageRead,
    CapabilityCostPolicyRead,
    CapabilityCostPolicyUpdate,
    InviteCreate,
    InviteRead,
    InviteSecretRead,
    PlatformPolicyRead,
    PlatformPolicyUpdate,
    SelfAIEntitlementRead,
)
from fair_platform.backend.core.config import (
    get_admission_mode_override,
    get_ai_controls_enabled_override,
    get_base_url,
)
from fair_platform.backend.core.security.permissions import has_capability
from fair_platform.backend.data.database import session_dependency
from fair_platform.backend.data.models import (
    AdmissionMode,
    AdmissionRule,
    AdmissionRuleKind,
    AICapabilityPolicy,
    AIEntitlement,
    AIEntitlementState,
    AIUsageCharge,
    CapabilityDefinition,
    ExtensionInstallation,
    RegistrationInvite,
    User,
)
from fair_platform.backend.data.models.access_control import AICapabilityClassification
from fair_platform.backend.services.access_control import (
    create_registration_invite,
    entitlement_payload,
    get_or_create_platform_policy,
    normalize_admission_rule,
    read_platform_policy,
    resolve_platform_policy,
    usage_total_for_period,
    utc_month_start,
)


router = APIRouter()
self_router = APIRouter()


def _value(value: object) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _require_admin(user: User) -> None:
    if not has_capability(user, "admin"):
        raise HTTPException(status_code=403, detail="Admin access required")


def _policy_read(db: Session) -> PlatformPolicyRead:
    stored = read_platform_policy(db)
    effective = resolve_platform_policy(db)
    return PlatformPolicyRead(
        stored_admission_mode=(
            _value(stored.admission_mode) if stored else AdmissionMode.open.value
        ),
        effective_admission_mode=effective.admission_mode.value,
        admission_source=effective.admission_source,
        admission_locked=effective.admission_source == "environment",
        stored_ai_controls_enabled=(
            bool(stored.ai_controls_enabled) if stored else False
        ),
        effective_ai_controls_enabled=effective.ai_controls_enabled,
        ai_controls_source=effective.ai_controls_source,
        ai_controls_locked=effective.ai_controls_source == "environment",
        updated_at=stored.updated_at if stored else None,
    )


@router.get("/platform-policy", response_model=PlatformPolicyRead)
def read_policy(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
) -> PlatformPolicyRead:
    _require_admin(current_user)
    return _policy_read(db)


@router.patch("/platform-policy", response_model=PlatformPolicyRead)
def update_policy(
    payload: PlatformPolicyUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
) -> PlatformPolicyRead:
    _require_admin(current_user)
    if payload.admission_mode is not None and get_admission_mode_override() is not None:
        raise HTTPException(
            status_code=409, detail="Admission mode is locked by the environment"
        )
    if (
        payload.ai_controls_enabled is not None
        and get_ai_controls_enabled_override() is not None
    ):
        raise HTTPException(
            status_code=409, detail="AI controls are locked by the environment"
        )
    if payload.ai_controls_enabled is True:
        unclassified = int(
            db.scalar(
                select(func.count())
                .select_from(CapabilityDefinition)
                .outerjoin(
                    AICapabilityPolicy,
                    AICapabilityPolicy.capability_definition_id
                    == CapabilityDefinition.id,
                )
                .where(AICapabilityPolicy.capability_definition_id.is_(None))
            )
            or 0
        )
        if unclassified:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Classify all capabilities before enabling AI controls "
                    f"({unclassified} unclassified)"
                ),
            )
    row = get_or_create_platform_policy(db)
    if payload.admission_mode is not None:
        row.admission_mode = AdmissionMode(payload.admission_mode)
    if payload.ai_controls_enabled is not None:
        row.ai_controls_enabled = payload.ai_controls_enabled
    row.updated_by_user_id = current_user.id
    db.commit()
    db.refresh(row)
    return _policy_read(db)


@router.get("/admission-rules", response_model=list[AdmissionRuleRead])
def list_admission_rules(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
):
    _require_admin(current_user)
    rows = db.scalars(
        select(AdmissionRule).order_by(
            AdmissionRule.kind, AdmissionRule.normalized_value
        )
    )
    return [
        AdmissionRuleRead(
            id=row.id,
            kind=_value(row.kind),
            value=row.normalized_value,
            created_at=row.created_at,
        )
        for row in rows
    ]


@router.post("/admission-rules", response_model=AdmissionRuleRead, status_code=201)
def create_admission_rule(
    payload: AdmissionRuleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
):
    _require_admin(current_user)
    try:
        normalized = normalize_admission_rule(payload.kind, payload.value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    row = AdmissionRule(
        kind=AdmissionRuleKind(payload.kind),
        normalized_value=normalized,
        created_by_user_id=current_user.id,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Admission rule already exists"
        ) from exc
    db.refresh(row)
    return AdmissionRuleRead(
        id=row.id, kind=payload.kind, value=normalized, created_at=row.created_at
    )


@router.delete("/admission-rules/{rule_id}", status_code=204)
def delete_admission_rule(
    rule_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
):
    _require_admin(current_user)
    row = db.get(AdmissionRule, rule_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Admission rule not found")
    db.delete(row)
    db.commit()


def _invite_read(row, *, token: str | None = None):
    now = datetime.now(timezone.utc)
    expires_at = (
        row.expires_at.replace(tzinfo=timezone.utc)
        if row.expires_at.tzinfo is None
        else row.expires_at
    )
    values = dict(
        id=row.id,
        email=row.normalized_email,
        expires_at=row.expires_at,
        redeemed_at=row.redeemed_at,
        revoked_at=row.revoked_at,
        created_at=row.created_at,
        active=(
            row.redeemed_at is None and row.revoked_at is None and expires_at > now
        ),
    )
    if token is None:
        return InviteRead(**values)
    return InviteSecretRead(
        **values,
        token=token,
        registration_url=f"{get_base_url()}/register#invite={token}",
    )


@router.get("/invites", response_model=list[InviteRead])
def list_invites(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
):
    _require_admin(current_user)
    rows = db.scalars(
        select(RegistrationInvite).order_by(RegistrationInvite.created_at.desc())
    )
    return [_invite_read(row) for row in rows]


@router.post("/invites", response_model=InviteSecretRead, status_code=201)
def create_invite(
    payload: InviteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
):
    _require_admin(current_user)
    row, token = create_registration_invite(
        db,
        email=str(payload.email),
        created_by_user_id=current_user.id,
        expires_in_days=payload.expires_in_days,
    )
    db.commit()
    db.refresh(row)
    return _invite_read(row, token=token)


@router.post("/invites/{invite_id}/revoke", response_model=InviteRead)
def revoke_invite(
    invite_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
):
    _require_admin(current_user)
    row = db.get(RegistrationInvite, invite_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Invitation not found")
    if row.redeemed_at is not None:
        raise HTTPException(
            status_code=409, detail="A redeemed invitation cannot be revoked"
        )
    if row.revoked_at is None:
        row.revoked_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(row)
    return _invite_read(row)


def _capability_policy_read(capability, installation, policy):
    return CapabilityCostPolicyRead(
        capability_definition_id=capability.id,
        capability_id=capability.capability_id,
        display_name=capability.display_name,
        version=capability.version,
        surface=capability.surface,
        extension_id=installation.extension_id,
        classification=_value(policy.classification) if policy else "unclassified",
        cost_units=policy.cost_units if policy else None,
        updated_at=policy.updated_at if policy else None,
    )


@router.get("/capability-cost-policies", response_model=list[CapabilityCostPolicyRead])
def list_capability_cost_policies(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
):
    _require_admin(current_user)
    rows = db.execute(
        select(CapabilityDefinition, ExtensionInstallation, AICapabilityPolicy)
        .join(
            ExtensionInstallation,
            CapabilityDefinition.installation_id == ExtensionInstallation.id,
        )
        .outerjoin(
            AICapabilityPolicy,
            AICapabilityPolicy.capability_definition_id == CapabilityDefinition.id,
        )
        .order_by(
            ExtensionInstallation.extension_id,
            CapabilityDefinition.capability_id,
            CapabilityDefinition.version,
        )
    )
    return [_capability_policy_read(*row) for row in rows]


@router.put(
    "/capability-cost-policies/{capability_id}", response_model=CapabilityCostPolicyRead
)
def put_capability_cost_policy(
    capability_id: UUID,
    payload: CapabilityCostPolicyUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
):
    _require_admin(current_user)
    capability = db.get(CapabilityDefinition, capability_id)
    if capability is None:
        raise HTTPException(status_code=404, detail="Capability definition not found")
    installation = db.get(ExtensionInstallation, capability.installation_id)
    row = db.get(AICapabilityPolicy, capability_id)
    if row is None:
        row = AICapabilityPolicy(capability_definition_id=capability_id)
        db.add(row)
    row.classification = AICapabilityClassification(payload.classification)
    row.cost_units = payload.cost_units
    row.updated_by_user_id = current_user.id
    db.commit()
    db.refresh(row)
    return _capability_policy_read(capability, installation, row)


def _entitlement_read(db: Session, user: User) -> AIEntitlementRead:
    payload = entitlement_payload(db, user.id)
    return AIEntitlementRead(
        user_id=user.id, user_name=user.name, user_email=user.email, **payload
    )


@router.get("/ai-entitlements", response_model=list[AIEntitlementRead])
def list_ai_entitlements(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
):
    _require_admin(current_user)
    users = db.scalars(select(User).order_by(User.name, User.normalized_email))
    return [_entitlement_read(db, user) for user in users]


@router.put("/users/{user_id}/ai-entitlement", response_model=AIEntitlementRead)
def put_ai_entitlement(
    user_id: UUID,
    payload: AIEntitlementUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
):
    _require_admin(current_user)
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    period = utc_month_start()
    row = db.get(AIEntitlement, user_id)
    if row is None:
        row = AIEntitlement(user_id=user_id, used_units=0, period_start=period)
        db.add(row)
    elif row.period_start != period:
        row.period_start = period
        row.used_units = 0
    row.state = AIEntitlementState(payload.state)
    row.monthly_limit_units = payload.monthly_limit_units
    row.updated_by_user_id = current_user.id
    db.commit()
    db.refresh(row)
    return _entitlement_read(db, user)


@router.get("/ai-usage", response_model=AIUsageRead)
def read_ai_usage(
    user_id: UUID | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
):
    _require_admin(current_user)
    period = utc_month_start()
    statement = (
        select(AIUsageCharge, User, CapabilityDefinition)
        .join(User, AIUsageCharge.user_id == User.id)
        .join(
            CapabilityDefinition,
            AIUsageCharge.capability_definition_id == CapabilityDefinition.id,
        )
        .where(AIUsageCharge.period_start == period)
        .order_by(AIUsageCharge.created_at.desc())
        .limit(limit)
    )
    if user_id is not None:
        statement = statement.where(AIUsageCharge.user_id == user_id)
    rows = db.execute(statement)
    charges = [
        AIUsageChargeRead(
            id=charge.id,
            execution_id=charge.execution_id,
            user_id=charge.user_id,
            user_email=user.email,
            capability_definition_id=charge.capability_definition_id,
            capability_id=capability.capability_id,
            units=charge.units,
            period_start=charge.period_start,
            created_at=charge.created_at,
        )
        for charge, user, capability in rows
    ]
    total = usage_total_for_period(db, period)
    if user_id is not None:
        total = int(
            db.scalar(
                select(func.coalesce(func.sum(AIUsageCharge.units), 0)).where(
                    AIUsageCharge.period_start == period,
                    AIUsageCharge.user_id == user_id,
                )
            )
            or 0
        )
    return AIUsageRead(period_start=period, total_units=total, charges=charges)


@self_router.get("/entitlement", response_model=SelfAIEntitlementRead)
def read_my_ai_entitlement(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
):
    return SelfAIEntitlementRead(**entitlement_payload(db, current_user.id))


__all__ = ["router", "self_router"]
