from collections.abc import Callable
from typing import Any
from uuid import UUID

from fair_platform.backend.core.config import get_deployment_mode
from fair_platform.backend.data.models.user import User, UserRole

Capability = str

ADMIN_CAPABILITIES: set[Capability] = {
    "manage_users",
    "create_course",
    "update_any_course",
    "delete_any_course",
    "manage_course_settings_any",
    "manage_enrollments_any",
    "create_workflow",
    "read_workflow",
    "update_workflow",
    "delete_workflow",
    "run_workflow",
    "read_workflow_runs",
    "list_plugins",
    "create_assignment",
    "manage_assignment",
    "create_submission",
    "manage_submission",
    "view_submission_timeline",
    "update_submission_results",
    "create_artifact",
    "manage_artifact",
    "cleanup_orphaned_artifacts",
    "create_rubric",
    "generate_rubric",
    "manage_rubric",
}

INSTRUCTOR_CAPABILITIES: set[Capability] = {
    "create_course",
    "update_own_course",
    "delete_own_course",
    "manage_course_settings_own",
    "manage_enrollments_own",
    "create_workflow",
    "read_workflow",
    "update_workflow",
    "delete_workflow",
    "run_workflow",
    "read_workflow_runs",
    "list_plugins",
    "create_assignment",
    "manage_assignment",
    "create_submission",
    "manage_submission",
    "view_submission_timeline",
    "update_submission_results",
    "create_artifact",
    "manage_artifact",
    "create_rubric",
    "generate_rubric",
    "manage_rubric",
}

USER_ENTERPRISE_CAPABILITIES: set[Capability] = {
    "join_course",
}

USER_COMMUNITY_CAPABILITIES: set[Capability] = (
    USER_ENTERPRISE_CAPABILITIES | INSTRUCTOR_CAPABILITIES
)


def coerce_user_role(role: str | UserRole) -> UserRole:
    if isinstance(role, UserRole):
        return role
    normalized = str(role).strip().lower()
    if normalized == "student":
        return UserRole.user
    if normalized == "professor":
        return UserRole.instructor
    return UserRole(normalized)


def capabilities_for_role(role: str | UserRole) -> set[Capability]:
    normalized_role = coerce_user_role(role)
    mode = get_deployment_mode()
    if normalized_role == UserRole.admin:
        return set(ADMIN_CAPABILITIES)
    if normalized_role == UserRole.instructor:
        return set(INSTRUCTOR_CAPABILITIES)
    if mode == "COMMUNITY":
        return set(USER_COMMUNITY_CAPABILITIES)
    return set(USER_ENTERPRISE_CAPABILITIES)


def has_capability(user: User, capability: Capability) -> bool:
    return capability in capabilities_for_role(user.role)


def has_capability_or_owner(
    user: User,
    capability: Capability,
    owner_id: UUID | None,
) -> bool:
    if has_capability(user, capability):
        return True
    return owner_id is not None and owner_id == user.id


def has_capability_and_owner(
    user: User,
    capability: Capability,
    owner_id: UUID | None,
    *,
    admin_capability: Capability = "manage_users",
) -> bool:
    if has_capability(user, admin_capability):
        return True
    return (
        has_capability(user, capability)
        and owner_id is not None
        and owner_id == user.id
    )


def has_capability_or_resolved_owner(
    user: User,
    capability: Capability,
    owner_resolver: Callable[[], UUID | None],
) -> bool:
    if has_capability(user, capability):
        return True
    owner_id = owner_resolver()
    return owner_id is not None and owner_id == user.id


def auth_user_payload(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": coerce_user_role(user.role),
        "capabilities": sorted(capabilities_for_role(user.role)),
        "preferences": {"interface_mode": "simple"},
    }
