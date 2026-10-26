import os
from dataclasses import dataclass, field
from typing import Literal
from urllib.parse import urlparse

DeploymentMode = Literal["COMMUNITY", "ENTERPRISE"]
AdmissionModeValue = Literal["open", "allowlist", "invite_only"]
INSECURE_DEFAULT_SECRET_KEY = "fair-insecure-default-key"
DEFAULT_EMAIL_SENDER = "FairGrade Platform <platform@fairgradeproject.org>"


def _parse_bool_env(raw: str | None, *, default: bool = False) -> bool:
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _parse_strict_bool_env(name: str) -> bool | None:
    raw = os.getenv(name)
    if raw is None:
        return None
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise RuntimeError(f"{name} must be a boolean value")


def get_admission_mode_override() -> AdmissionModeValue | None:
    raw = os.getenv("FAIR_ADMISSION_MODE")
    if raw is None:
        return None
    normalized = raw.strip().lower().replace("-", "_")
    if normalized not in {"open", "allowlist", "invite_only"}:
        raise RuntimeError(
            "FAIR_ADMISSION_MODE must be one of: open, allowlist, invite_only"
        )
    return normalized  # type: ignore[return-value]


def get_ai_controls_enabled_override() -> bool | None:
    return _parse_strict_bool_env("FAIR_AI_CONTROLS_ENABLED")


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
    get_admission_mode_override()
    get_ai_controls_enabled_override()
    resolved_secret = secret_key or get_secret_key()
    get_google_login_config()
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


def get_email_sender() -> str:
    raw = os.getenv("FAIR_EMAIL_SENDER") or os.getenv("EMAIL_SENDER")
    if raw is None:
        return DEFAULT_EMAIL_SENDER
    normalized = raw.strip()
    return normalized or DEFAULT_EMAIL_SENDER


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


@dataclass(frozen=True)
class OIDCProviderConfig:
    key: str
    issuer: str
    discovery_url: str
    client_id: str
    client_secret: str = field(repr=False)
    callback_url: str
    frontend_url: str
    secure: bool


def get_google_login_config() -> OIDCProviderConfig | None:
    client_id = os.getenv("FAIR_GOOGLE_CLIENT_ID", "").strip()
    client_secret = os.getenv("FAIR_GOOGLE_CLIENT_SECRET", "").strip()
    if not client_id and not client_secret:
        return None
    if not client_id or not client_secret:
        raise RuntimeError("Set both FAIR_GOOGLE_CLIENT_ID and FAIR_GOOGLE_CLIENT_SECRET")
    if get_secret_key() == INSECURE_DEFAULT_SECRET_KEY or len(get_secret_key()) < 32:
        raise RuntimeError("Google login requires a SECRET_KEY of at least 32 characters")

    frontend_url, api_url = get_base_url(), get_api_base_url()
    for name, value in (("FAIR_BASE_URL", frontend_url), ("FAIR_API_BASE_URL", api_url)):
        parsed = urlparse(value)
        if (
            not parsed.hostname or parsed.username or parsed.password
            or parsed.query or parsed.fragment or parsed.path not in {"", "/"}
            or parsed.scheme not in {"http", "https"}
            or (parsed.scheme != "https" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"})
        ):
            raise RuntimeError(f"{name} must be an HTTPS origin (HTTP is allowed on localhost)")
    return OIDCProviderConfig(
        key="google",
        issuer="https://accounts.google.com",
        discovery_url="https://accounts.google.com/.well-known/openid-configuration",
        client_id=client_id,
        client_secret=client_secret,
        callback_url=f"{api_url}/api/auth/oidc/google/callback",
        frontend_url=frontend_url,
        secure=urlparse(api_url).scheme == "https",
    )
