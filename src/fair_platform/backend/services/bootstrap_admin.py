from __future__ import annotations

import logging
import os
import secrets
from collections.abc import Callable
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fair_platform.backend.data.models.user import (
    User,
    UserRole,
    normalize_email_address,
)

logger = logging.getLogger(__name__)


def bootstrap_admin_from_environment(
    session_factory: Callable[[], Session],
) -> bool:
    """Create the first administrator for unattended deployments.

    The bootstrap is deliberately constrained to an empty user table. It never
    promotes an existing account or creates another administrator after any
    account exists. The generated password is intentionally not returned or
    logged; the administrator establishes a password through the normal reset
    email flow.
    """

    raw_email = os.getenv("FAIR_BOOTSTRAP_ADMIN_EMAIL", "").strip()
    if not raw_email:
        return False

    name = os.getenv("FAIR_BOOTSTRAP_ADMIN_NAME", "FAIR Administrator").strip()
    if not name:
        raise RuntimeError(
            "FAIR_BOOTSTRAP_ADMIN_NAME must not be empty when "
            "FAIR_BOOTSTRAP_ADMIN_EMAIL is configured"
        )

    try:
        normalized_email = normalize_email_address(raw_email)
    except ValueError as exc:
        raise RuntimeError("FAIR_BOOTSTRAP_ADMIN_EMAIL is invalid") from exc

    with session_factory() as session:
        existing = session.scalar(
            select(User).where(User.normalized_email == normalized_email)
        )
        if existing is not None:
            if existing.role != UserRole.admin.value:
                logger.warning(
                    "Bootstrap administrator email belongs to a non-admin account; "
                    "refusing to change its role"
                )
            return False

        user_count = session.scalar(select(func.count()).select_from(User)) or 0
        if user_count:
            logger.warning(
                "FAIR_BOOTSTRAP_ADMIN_EMAIL is configured but users already exist; "
                "refusing to create an additional administrator"
            )
            return False

        # Import lazily to avoid coupling application module import order to the
        # deployment-only bootstrap path.
        from fair_platform.backend.api.routers.auth import hash_password

        admin = User(
            id=uuid4(),
            name=name,
            email=raw_email,
            normalized_email=normalized_email,
            role=UserRole.admin.value,
            password_hash=hash_password(secrets.token_urlsafe(48)),
            is_verified=True,
        )
        session.add(admin)
        session.commit()

    logger.info(
        "Created the initial FAIR administrator. Use the password-reset flow "
        "to establish its password."
    )
    return True
