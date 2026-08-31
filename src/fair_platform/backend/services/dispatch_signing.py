from __future__ import annotations

import base64
import hashlib
import os
import secrets

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from fair_platform.backend.core.config import get_deployment_mode, get_secret_key
from fair_platform.extension_sdk.signatures import (
    key_id_for_public_key,
    public_jwk,
    sign_request,
)


def _decode_private_key(value: str) -> bytes:
    try:
        raw = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except (ValueError, TypeError) as exc:
        raise RuntimeError(
            "FAIR_DISPATCH_SIGNING_PRIVATE_KEY must be base64url encoded"
        ) from exc
    if len(raw) != 32:
        raise RuntimeError("FAIR_DISPATCH_SIGNING_PRIVATE_KEY must contain 32 bytes")
    return raw


def _private_key_bytes() -> bytes:
    configured = os.getenv("FAIR_DISPATCH_SIGNING_PRIVATE_KEY", "").strip()
    if configured:
        return _decode_private_key(configured)
    if get_deployment_mode() == "ENTERPRISE":
        raise RuntimeError(
            "FAIR_DISPATCH_SIGNING_PRIVATE_KEY must be configured in ENTERPRISE mode"
        )
    # A deterministic development key survives local process restarts. Production
    # deployments must provide an independently generated key above.
    return hashlib.sha256(
        b"fair-community-dispatch-signing-key\0" + get_secret_key().encode("utf-8")
    ).digest()


class DispatchSigner:
    def __init__(self, private_key: Ed25519PrivateKey | None = None):
        self._private_key = private_key or Ed25519PrivateKey.from_private_bytes(
            _private_key_bytes()
        )
        self.public_key = self._private_key.public_key()
        self.key_id = key_id_for_public_key(self.public_key)

    def jwks(self) -> dict[str, list[dict[str, str]]]:
        return {"keys": [public_jwk(self.public_key, key_id=self.key_id)]}

    def sign(
        self,
        *,
        method: str,
        target_uri: str,
        body: bytes,
        expires: int,
        created: int | None = None,
    ) -> dict[str, str]:
        return sign_request(
            private_key=self._private_key,
            key_id=self.key_id,
            method=method,
            target_uri=target_uri,
            body=body,
            nonce=secrets.token_urlsafe(24),
            created=created,
            expires=expires,
        )


_dispatch_signer: DispatchSigner | None = None


def get_dispatch_signer() -> DispatchSigner:
    global _dispatch_signer
    if _dispatch_signer is None:
        _dispatch_signer = DispatchSigner()
    return _dispatch_signer


__all__ = ["DispatchSigner", "get_dispatch_signer"]
