from fair_platform.backend.services.extension_auth import (
    hash_extension_secret,
    verify_extension_secret,
)


def test_verify_extension_secret_returns_false_for_long_input() -> None:
    secret_hash = hash_extension_secret("short-secret")
    overlong_secret = "x" * 80
    assert verify_extension_secret(overlong_secret, secret_hash) is False
