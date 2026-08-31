from __future__ import annotations

import base64
import hashlib
import re
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat


SIGNATURE_LABEL = "fair"
SIGNATURE_TAG = "fair-execution-command"
SIGNATURE_COMPONENTS = '("@method" "@target-uri" "content-digest" "content-type")'
_SIGNATURE_INPUT_RE = re.compile(
    r'^fair=\("@method" "@target-uri" "content-digest" "content-type"\)'
    r";created=(?P<created>\d+);expires=(?P<expires>\d+)"
    r';nonce="(?P<nonce>[A-Za-z0-9_-]{16,128})"'
    r';keyid="(?P<keyid>[A-Za-z0-9._:-]{1,255})"'
    r';alg="ed25519";tag="fair-execution-command"$'
)
_SIGNATURE_RE = re.compile(r"^fair=:(?P<signature>[A-Za-z0-9+/]+={0,2}):$")
_DIGEST_RE = re.compile(r"^sha-256=:(?P<digest>[A-Za-z0-9+/]+={0,2}):$")


class RequestSignatureError(ValueError):
    """The request does not satisfy FAIR's signed-command profile."""


@dataclass(frozen=True)
class VerifiedRequestSignature:
    key_id: str
    nonce: str
    created: int
    expires: int


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _header(headers: Mapping[str, str], name: str) -> str:
    lowered = name.lower()
    for key, value in headers.items():
        if key.lower() == lowered:
            return value
    raise RequestSignatureError(f"missing required {name} header")


def content_digest(body: bytes) -> str:
    encoded = base64.b64encode(hashlib.sha256(body).digest()).decode("ascii")
    return f"sha-256=:{encoded}:"


def key_id_for_public_key(public_key: Ed25519PublicKey) -> str:
    raw = public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)
    return f"fair-{_base64url_encode(hashlib.sha256(raw).digest()[:12])}"


def public_jwk(
    public_key: Ed25519PublicKey, *, key_id: str | None = None
) -> dict[str, str]:
    raw = public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)
    return {
        "kty": "OKP",
        "crv": "Ed25519",
        "x": _base64url_encode(raw),
        "use": "sig",
        "alg": "EdDSA",
        "kid": key_id or key_id_for_public_key(public_key),
    }


def public_key_from_jwk(jwk: Mapping[str, str]) -> Ed25519PublicKey:
    if (
        jwk.get("kty") != "OKP"
        or jwk.get("crv") != "Ed25519"
        or jwk.get("alg") != "EdDSA"
    ):
        raise RequestSignatureError("unsupported signing key")
    encoded = jwk.get("x")
    if not encoded:
        raise RequestSignatureError("signing key has no public value")
    try:
        raw = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
        return Ed25519PublicKey.from_public_bytes(raw)
    except (TypeError, ValueError) as exc:
        raise RequestSignatureError("invalid Ed25519 public key") from exc


def _signature_params(*, created: int, expires: int, nonce: str, key_id: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]{16,128}", nonce):
        raise ValueError("nonce must be 16-128 URL-safe characters")
    if not re.fullmatch(r"[A-Za-z0-9._:-]{1,255}", key_id):
        raise ValueError("key_id contains unsupported characters")
    return (
        f'{SIGNATURE_COMPONENTS};created={created};expires={expires};nonce="{nonce}";'
        f'keyid="{key_id}";alg="ed25519";tag="{SIGNATURE_TAG}"'
    )


def _signature_base(
    *,
    method: str,
    target_uri: str,
    digest: str,
    content_type: str,
    signature_params: str,
) -> bytes:
    return (
        f'"@method": {method.upper()}\n'
        f'"@target-uri": {target_uri}\n'
        f'"content-digest": {digest}\n'
        f'"content-type": {content_type}\n'
        f'"@signature-params": {signature_params}'
    ).encode("utf-8")


def sign_request(
    *,
    private_key: Ed25519PrivateKey,
    key_id: str,
    method: str,
    target_uri: str,
    body: bytes,
    nonce: str,
    created: int | None = None,
    expires: int | None = None,
    content_type: str = "application/json",
) -> dict[str, str]:
    """Sign a command using FAIR's small RFC 9421 HTTP-signature profile."""

    created = int(time.time()) if created is None else created
    expires = created + 300 if expires is None else expires
    if expires <= created or expires - created > 300:
        raise ValueError("signature lifetime must be between 1 and 300 seconds")
    digest = content_digest(body)
    params = _signature_params(
        created=created,
        expires=expires,
        nonce=nonce,
        key_id=key_id,
    )
    signature = private_key.sign(
        _signature_base(
            method=method,
            target_uri=target_uri,
            digest=digest,
            content_type=content_type,
            signature_params=params,
        )
    )
    return {
        "Content-Type": content_type,
        "Content-Digest": digest,
        "Signature-Input": f"{SIGNATURE_LABEL}={params}",
        "Signature": f"{SIGNATURE_LABEL}=:{base64.b64encode(signature).decode('ascii')}:",
    }


def verify_request_signature(
    *,
    method: str,
    target_uri: str,
    headers: Mapping[str, str],
    body: bytes,
    resolve_key: Callable[[str], Ed25519PublicKey],
    now: int | None = None,
    clock_skew_seconds: int = 60,
) -> VerifiedRequestSignature:
    """Verify body integrity, freshness, target binding, and FAIR's Ed25519 signature."""

    signature_input = _header(headers, "Signature-Input")
    match = _SIGNATURE_INPUT_RE.fullmatch(signature_input)
    if match is None:
        raise RequestSignatureError("unsupported Signature-Input profile")
    values = match.groupdict()
    created = int(values["created"])
    expires = int(values["expires"])
    current = int(time.time()) if now is None else now
    if expires <= created or expires - created > 300:
        raise RequestSignatureError("invalid signature lifetime")
    if created > current + clock_skew_seconds or expires < current - clock_skew_seconds:
        raise RequestSignatureError("request signature is not current")

    digest = _header(headers, "Content-Digest")
    digest_match = _DIGEST_RE.fullmatch(digest)
    if digest_match is None or digest != content_digest(body):
        raise RequestSignatureError("content digest does not match the request body")
    content_type = _header(headers, "Content-Type")
    if content_type != "application/json":
        raise RequestSignatureError(
            "signed command content type must be application/json"
        )

    signature_match = _SIGNATURE_RE.fullmatch(_header(headers, "Signature"))
    if signature_match is None:
        raise RequestSignatureError("invalid Signature header")
    try:
        signature = base64.b64decode(signature_match.group("signature"), validate=True)
        public_key = resolve_key(values["keyid"])
        public_key.verify(
            signature,
            _signature_base(
                method=method,
                target_uri=target_uri,
                digest=digest,
                content_type=content_type,
                signature_params=signature_input.removeprefix(f"{SIGNATURE_LABEL}="),
            ),
        )
    except (InvalidSignature, ValueError, TypeError) as exc:
        raise RequestSignatureError("invalid request signature") from exc
    return VerifiedRequestSignature(
        key_id=values["keyid"],
        nonce=values["nonce"],
        created=created,
        expires=expires,
    )


__all__ = [
    "RequestSignatureError",
    "VerifiedRequestSignature",
    "content_digest",
    "key_id_for_public_key",
    "public_jwk",
    "public_key_from_jwk",
    "sign_request",
    "verify_request_signature",
]
