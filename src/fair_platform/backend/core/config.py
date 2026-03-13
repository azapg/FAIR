import os
from typing import Literal

DeploymentMode = Literal["COMMUNITY", "ENTERPRISE"]


def _parse_bool_env(raw: str | None, *, default: bool = False) -> bool:
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def get_deployment_mode() -> DeploymentMode:
    raw_mode = (
        os.getenv("FAIR_DEPLOYMENT_MODE")
        or os.getenv("DEPLOYMENT_MODE")
        or "COMMUNITY"
    )
    mode = raw_mode.strip().upper()
    if mode not in {"COMMUNITY", "ENTERPRISE"}:
        return "COMMUNITY"
    return mode  # type: ignore[return-value]


EMAIL_ENABLED = _parse_bool_env(
    os.getenv("FAIR_EMAIL_ENABLED", os.getenv("EMAIL_ENABLED")),
    default=False,
)


def get_email_enabled() -> bool:
    return _parse_bool_env(
        os.getenv("FAIR_EMAIL_ENABLED", os.getenv("EMAIL_ENABLED")),
        default=EMAIL_ENABLED,
    )

