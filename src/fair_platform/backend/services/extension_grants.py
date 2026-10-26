from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from fair_platform.backend.data.models.extension import (
    CapabilityDefinition,
    ExtensionGrant,
    ExtensionInstallation,
    ExtensionInstallationStatus,
    GrantDecision,
)


@dataclass(frozen=True)
class GrantResolution:
    """Explainable result for one extension effect."""

    effect: str
    allowed: bool
    reason: str
    matched_grant_ids: tuple[UUID, ...] = ()
    allowing_grant_ids: tuple[UUID, ...] = ()
    denying_grant_ids: tuple[UUID, ...] = ()


def _grant_applies(
    grant: ExtensionGrant,
    *,
    capability_definition_id: UUID | None,
    course_id: UUID | None,
    assignment_id: UUID | None,
) -> bool:
    """Return whether a grant's nullable scope matches the requested scope."""

    if (
        grant.capability_definition_id is not None
        and grant.capability_definition_id != capability_definition_id
    ):
        return False
    if grant.course_id is not None and grant.course_id != course_id:
        return False
    if grant.assignment_id is not None and grant.assignment_id != assignment_id:
        return False
    return True


def resolve_extension_effects(
    session: Session,
    *,
    installation_id: UUID,
    effects: list[str] | tuple[str, ...] | set[str],
    capability_definition_id: UUID | None = None,
    course_id: UUID | None = None,
    assignment_id: UUID | None = None,
) -> dict[str, GrantResolution]:
    """Resolve effects using global and scoped grants.

    This is the authorization policy for extension side effects, not a
    replacement for the caller's user/resource permission check. Callers
    should require both their normal user capability and an allowed result
    here. Missing grants are deny-by-default; disabled or revoked
    installations deny every effect.
    """

    requested = tuple(dict.fromkeys(effect.strip() for effect in effects if effect.strip()))
    installation = session.get(ExtensionInstallation, installation_id)
    capability_scope_valid = True
    if capability_definition_id is not None:
        capability = session.get(CapabilityDefinition, capability_definition_id)
        capability_scope_valid = (
            capability is not None and capability.installation_id == installation_id
        )
    grants = list(
        session.scalars(
            select(ExtensionGrant).where(
                ExtensionGrant.installation_id == installation_id,
                ExtensionGrant.effect.in_(requested or ("",)),
            )
        )
    )
    installation_enabled = (
        installation is not None
        and _enum_value(installation.status) == ExtensionInstallationStatus.enabled.value
    )

    results: dict[str, GrantResolution] = {}
    for effect in requested:
        applicable = [
            grant
            for grant in grants
            if grant.effect == effect
            and _grant_applies(
                grant,
                capability_definition_id=capability_definition_id,
                course_id=course_id,
                assignment_id=assignment_id,
            )
        ]
        allowing = [
            grant
            for grant in applicable
            if _enum_value(grant.decision) == GrantDecision.allow.value
        ]
        denying = [
            grant
            for grant in applicable
            if _enum_value(grant.decision) == GrantDecision.deny.value
        ]
        matched_ids = tuple(grant.id for grant in applicable)
        if not installation_enabled:
            reason = "extension installation is missing or not enabled"
            allowed = False
        elif not capability_scope_valid:
            reason = "capability definition is not owned by this installation"
            allowed = False
        elif denying:
            reason = "an applicable deny grant overrides all allows"
            allowed = False
        elif allowing:
            reason = "an applicable allow grant exists"
            allowed = True
        else:
            reason = "no applicable allow grant exists"
            allowed = False
        results[effect] = GrantResolution(
            effect=effect,
            allowed=allowed,
            reason=reason,
            matched_grant_ids=matched_ids,
            allowing_grant_ids=tuple(grant.id for grant in allowing),
            denying_grant_ids=tuple(grant.id for grant in denying),
        )
    return results


def is_extension_effect_allowed(
    session: Session,
    *,
    installation_id: UUID,
    effect: str,
    capability_definition_id: UUID | None = None,
    course_id: UUID | None = None,
    assignment_id: UUID | None = None,
) -> bool:
    """Small predicate for service call sites that only need the decision."""

    return resolve_extension_effects(
        session,
        installation_id=installation_id,
        effects=(effect,),
        capability_definition_id=capability_definition_id,
        course_id=course_id,
        assignment_id=assignment_id,
    )[effect].allowed


def _enum_value(value: object) -> str:
    return value.value if hasattr(value, "value") else str(value)


__all__ = [
    "GrantResolution",
    "is_extension_effect_allowed",
    "resolve_extension_effects",
]
