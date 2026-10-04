from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import pytest

from fair_platform.backend.services.dispatch_signing import DispatchSigner
from fair_platform.extension_sdk.signatures import (
    RequestSignatureError,
    public_key_from_jwk,
    verify_request_signature,
)


def test_signed_command_round_trip_binds_body_method_and_target():
    signer = DispatchSigner(Ed25519PrivateKey.generate())
    body = b'{"protocolVersion":"1"}'
    headers = signer.sign(
        method="POST",
        target_uri="https://agent.example/commands",
        body=body,
        created=1_700_000_000,
        expires=1_700_000_120,
    )
    jwk = signer.jwks()["keys"][0]

    verified = verify_request_signature(
        method="POST",
        target_uri="https://agent.example/commands",
        headers=headers,
        body=body,
        resolve_key=lambda key_id: (
            public_key_from_jwk(jwk)
            if key_id == jwk["kid"]
            else (_ for _ in ()).throw(KeyError(key_id))
        ),
        now=1_700_000_000,
    )

    assert verified.key_id == jwk["kid"]
    assert verified.expires == 1_700_000_120


@pytest.mark.parametrize(
    ("method", "target_uri", "body"),
    [
        ("GET", "https://agent.example/commands", b'{"protocolVersion":"1"}'),
        ("POST", "https://agent.example/other", b'{"protocolVersion":"1"}'),
        ("POST", "https://agent.example/commands", b'{"protocolVersion":"2"}'),
    ],
)
def test_signed_command_rejects_tampering(method: str, target_uri: str, body: bytes):
    signer = DispatchSigner(Ed25519PrivateKey.generate())
    headers = signer.sign(
        method="POST",
        target_uri="https://agent.example/commands",
        body=b'{"protocolVersion":"1"}',
        created=1_700_000_000,
        expires=1_700_000_120,
    )
    public_key = signer.public_key

    with pytest.raises(RequestSignatureError):
        verify_request_signature(
            method=method,
            target_uri=target_uri,
            headers=headers,
            body=body,
            resolve_key=lambda _key_id: public_key,
            now=1_700_000_000,
        )


def test_signed_command_rejects_expired_signature():
    signer = DispatchSigner(Ed25519PrivateKey.generate())
    body = b"{}"
    headers = signer.sign(
        method="POST",
        target_uri="https://agent.example/commands",
        body=body,
        created=1_700_000_000,
        expires=1_700_000_120,
    )

    with pytest.raises(RequestSignatureError, match="not current"):
        verify_request_signature(
            method="POST",
            target_uri="https://agent.example/commands",
            headers=headers,
            body=body,
            resolve_key=lambda _key_id: signer.public_key,
            now=1_700_000_181,
            clock_skew_seconds=60,
        )
