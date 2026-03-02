from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import secrets

import bcrypt
from sqlalchemy.orm import Session

from fair_platform.backend.data.models import ExtensionClient


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def generate_extension_secret() -> str:
    return secrets.token_urlsafe(32)


def hash_extension_secret(secret: str) -> str:
    secret_bytes = secret.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(secret_bytes, salt)
    return hashed.decode("utf-8")


def verify_extension_secret(secret: str, secret_hash: str) -> bool:
    try:
        return bcrypt.checkpw(secret.encode("utf-8"), secret_hash.encode("utf-8"))
    except ValueError:
        # bcrypt rejects inputs longer than 72 bytes; treat as invalid credentials.
        return False


@dataclass
class IssuedExtensionSecret:
    extension_id: str
    secret: str
    scopes: list[str]
    enabled: bool


def issue_extension_secret(
    db: Session,
    *,
    extension_id: str,
    scopes: list[str] | None = None,
    enabled: bool = True,
) -> IssuedExtensionSecret:
    normalized_scopes = sorted({scope.strip() for scope in (scopes or []) if scope.strip()})
    client = db.get(ExtensionClient, extension_id)
    secret = generate_extension_secret()
    now = _utcnow()
    if client is None:
        client = ExtensionClient(
            extension_id=extension_id,
            secret_hash=hash_extension_secret(secret),
            scopes=normalized_scopes,
            enabled=enabled,
            created_at=now,
            updated_at=now,
        )
    else:
        client.secret_hash = hash_extension_secret(secret)
        client.scopes = normalized_scopes
        client.enabled = enabled
        client.updated_at = now
    db.add(client)
    db.commit()
    db.refresh(client)
    return IssuedExtensionSecret(
        extension_id=client.extension_id,
        secret=secret,
        scopes=list(client.scopes or []),
        enabled=bool(client.enabled),
    )


def authenticate_extension_client(
    db: Session,
    *,
    extension_id: str,
    secret: str,
) -> ExtensionClient | None:
    client = db.get(ExtensionClient, extension_id)
    if client is None or not client.enabled:
        return None
    if not verify_extension_secret(secret, client.secret_hash):
        return None
    return client
