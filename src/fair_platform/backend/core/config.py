import os
from typing import Literal
from urllib.parse import urlparse

DeploymentMode = Literal["COMMUNITY", "ENTERPRISE"]
INSECURE_DEFAULT_SECRET_KEY = "fair-insecure-default-key"


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
        os.getenv("FAIR_DEPLOYMENT_MODE") or os.getenv("DEPLOYMENT_MODE") or "COMMUNITY"
    )
    mode = raw_mode.strip().upper()
    if mode not in {"COMMUNITY", "ENTERPRISE"}:
        return "COMMUNITY"
    return mode  # type: ignore[return-value]


def get_secret_key() -> str:
    return os.getenv("SECRET_KEY") or INSECURE_DEFAULT_SECRET_KEY


def validate_security_configuration(secret_key: str | None = None) -> None:
    """Reject development-only authentication defaults in institutional mode."""
    resolved_secret = secret_key or get_secret_key()
    if get_deployment_mode() != "ENTERPRISE":
        return
    if resolved_secret == INSECURE_DEFAULT_SECRET_KEY:
        raise RuntimeError(
            "SECRET_KEY must be configured when FAIR_DEPLOYMENT_MODE=ENTERPRISE"
        )
    if not (os.getenv("FAIR_DISPATCH_SIGNING_PRIVATE_KEY") or "").strip():
        raise RuntimeError(
            "FAIR_DISPATCH_SIGNING_PRIVATE_KEY must be configured when "
            "FAIR_DEPLOYMENT_MODE=ENTERPRISE"
        )
    if urlparse(get_api_base_url()).scheme != "https":
        raise RuntimeError(
            "FAIR_API_BASE_URL must use HTTPS when FAIR_DEPLOYMENT_MODE=ENTERPRISE"
        )


EMAIL_ENABLED = _parse_bool_env(
    os.getenv("FAIR_EMAIL_ENABLED", os.getenv("EMAIL_ENABLED")),
    default=False,
)
ENFORCE_EMAIL_VERIFICATION = _parse_bool_env(
    os.getenv(
        "FAIR_ENFORCE_EMAIL_VERIFICATION",
        os.getenv("ENFORCE_EMAIL_VERIFICATION"),
    ),
    default=False,
)
RESEND_API_KEY = os.getenv("FAIR_RESEND_API_KEY") or os.getenv("RESEND_API_KEY") or None
if RESEND_API_KEY:
    EMAIL_ENABLED = True


def get_email_enabled() -> bool:
    if get_resend_api_key():
        return True
    return _parse_bool_env(
        os.getenv("FAIR_EMAIL_ENABLED", os.getenv("EMAIL_ENABLED")),
        default=EMAIL_ENABLED,
    )


def get_enforce_email_verification() -> bool:
    if not get_email_enabled():
        return False
    return _parse_bool_env(
        os.getenv(
            "FAIR_ENFORCE_EMAIL_VERIFICATION",
            os.getenv("ENFORCE_EMAIL_VERIFICATION"),
        ),
        default=ENFORCE_EMAIL_VERIFICATION,
    )


def get_resend_api_key() -> str | None:
    raw = (
        os.getenv("FAIR_RESEND_API_KEY")
        or os.getenv("RESEND_API_KEY")
        or RESEND_API_KEY
    )
    if raw is None:
        return None
    normalized = raw.strip()
    return normalized or None


BASE_URL = (
    (os.getenv("FAIR_BASE_URL") or os.getenv("BASE_URL") or "http://localhost:3000")
    .strip()
    .rstrip("/")
)


def get_base_url() -> str:
    raw = os.getenv("FAIR_BASE_URL") or os.getenv("BASE_URL") or BASE_URL
    return raw.strip().rstrip("/")


API_BASE_URL = (
    (os.getenv("FAIR_API_BASE_URL") or "http://localhost:8000").strip().rstrip("/")
)


def get_api_base_url() -> str:
    raw = os.getenv("FAIR_API_BASE_URL") or API_BASE_URL
    return raw.strip().rstrip("/")
