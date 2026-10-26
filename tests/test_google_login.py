import base64
import hashlib
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse
from uuid import UUID

import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwk, jwt
from sqlalchemy import func, select, update

from fair_platform.backend.core.config import (
    get_google_login_config,
    validate_security_configuration,
)
from fair_platform.backend.data.models import (
    ExternalIdentity,
    OIDCTransaction,
    RegistrationInvite,
    User,
)
from fair_platform.backend.services import oidc
from fair_platform.backend.services.access_control import create_registration_invite

ROOT = "/api/auth/oidc"
ORIGIN = {"Origin": "http://localhost:3000"}
ISSUER = "https://accounts.google.com"


@pytest.fixture(scope="module")
def signing_key():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public = key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    public_jwk = {
        **jwk.construct(public, "RS256").to_dict(),
        "kid": "google-test",
        "use": "sig",
    }
    return private, public_jwk


@pytest.fixture
def google(monkeypatch, signing_key):
    monkeypatch.setenv("FAIR_GOOGLE_CLIENT_ID", "fair-test.apps.googleusercontent.com")
    monkeypatch.setenv("FAIR_GOOGLE_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("SECRET_KEY", "google-test-session-key-at-least-32-characters")
    monkeypatch.setenv("FAIR_BASE_URL", "http://localhost:3000")
    monkeypatch.setenv("FAIR_API_BASE_URL", "http://localhost:8000")
    private, public_jwk = signing_key
    provider = {"claims": {}, "omit": set(), "token_requests": 0}

    def handle(request):
        if provider.get("unavailable") and request.url.path.endswith(
            "openid-configuration"
        ):
            raise httpx.ConnectError("Provider unavailable", request=request)
        if request.url.path.endswith("openid-configuration"):
            return httpx.Response(
                200,
                json={
                    "issuer": ISSUER,
                    "authorization_endpoint": f"{ISSUER}/o/oauth2/v2/auth",
                    "token_endpoint": "https://oauth2.googleapis.com/token",
                    "jwks_uri": "https://www.googleapis.com/oauth2/v3/certs",
                    "id_token_signing_alg_values_supported": ["RS256"],
                },
            )
        if request.url.path == "/oauth2/v3/certs":
            return httpx.Response(200, json={"keys": [public_jwk]})
        if request.url.path == "/token":
            provider["token_requests"] += 1
            if provider.get("token_error"):
                return httpx.Response(400, json={"error": "invalid_grant"})
            body = parse_qs(request.content.decode())
            verifier = body["code_verifier"][0]
            challenge = (
                base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
                .decode()
                .rstrip("=")
            )
            assert challenge == provider["challenge"]
            assert body["redirect_uri"] == [
                provider.get(
                    "callback_url",
                    "http://localhost:8000/api/auth/oidc/google/callback",
                )
            ]
            now = int(time.time())
            claims = {
                "iss": ISSUER,
                "sub": "stable-google-subject",
                "aud": "fair-test.apps.googleusercontent.com",
                "iat": now,
                "exp": now + 3600,
                "nonce": provider["nonce"],
                "email": "new@example.edu",
                "email_verified": True,
                "name": "Google User",
                **provider["claims"],
            }
            for key in provider["omit"]:
                claims.pop(key, None)
            token = jwt.encode(
                claims, private, algorithm="RS256", headers={"kid": "google-test"}
            )
            if provider.get("bad_signature"):
                a, b, c = token.split(".")
                token = f"{a}.{b}.{'A' if c[0] != 'A' else 'B'}{c[1:]}"
            return httpx.Response(
                200,
                json={
                    "id_token": token,
                    "access_token": "discard-me",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                    **provider.get("token_overrides", {}),
                },
            )
        raise AssertionError(f"Unexpected provider URL: {request.url.path}")

    original = oidc.create_client

    def client(config):
        value = original(config)
        value.client_kwargs["transport"] = httpx.MockTransport(handle)
        return value

    monkeypatch.setattr(oidc, "create_client", client)
    return provider


def begin(client, google, payload=None, path="/google/start"):
    response = client.post(f"{ROOT}{path}", json=payload or {}, headers=ORIGIN)
    assert response.status_code == 200, response.text
    params = parse_qs(urlparse(response.json()["authorizationUrl"]).query)
    google["nonce"] = params["nonce"][0]
    google["challenge"] = params["code_challenge"][0]
    assert params["code_challenge_method"] == ["S256"]
    assert set(params["scope"][0].split()) == {"openid", "email", "profile"}
    assert "code_verifier" not in params
    assert "access_type" not in params
    return params["state"][0]


def callback(client, state, **params):
    return client.get(
        f"{ROOT}/google/callback",
        params={"state": state, "code": "one-time-code", **params},
        follow_redirects=False,
    )


def test_disabled_google_does_not_advertise_or_start(test_client, monkeypatch):
    monkeypatch.delenv("FAIR_GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("FAIR_GOOGLE_CLIENT_SECRET", raising=False)
    assert test_client.get("/api/v1/system/config").json()["authentication"] == {
        "providers": []
    }
    assert (
        test_client.post(f"{ROOT}/google/start", json={}, headers=ORIGIN).status_code
        == 404
    )
    assert (
        test_client.post(f"{ROOT}/unknown/start", json={}, headers=ORIGIN).status_code
        == 404
    )


@pytest.mark.parametrize(
    "name,value",
    [
        ("FAIR_GOOGLE_CLIENT_SECRET", ""),
        ("SECRET_KEY", "short"),
        ("FAIR_BASE_URL", "http://fair.example.edu"),
        ("FAIR_API_BASE_URL", "https://api.example.edu/api"),
        ("FAIR_BASE_URL", "https://user:pass@example.edu"),
        ("FAIR_API_BASE_URL", "https://example.edu?redirect=evil"),
    ],
)
def test_configuration_fails_closed(google, monkeypatch, name, value):
    monkeypatch.setenv(name, value)
    with pytest.raises(RuntimeError):
        validate_security_configuration()


@pytest.mark.parametrize("origin", [None, "https://evil.example", "null"])
def test_start_requires_trusted_origin(test_client, google, origin):
    headers = {"Origin": origin} if origin else {}
    assert (
        test_client.post(f"{ROOT}/google/start", json={}, headers=headers).status_code
        == 403
    )


def test_protocol_signup_creates_cookie_session_without_password(
    test_client, test_db, google
):
    config = test_client.get("/api/v1/system/config").json()
    assert config["authentication"] == {"providers": ["google"]}
    assert "test-client-secret" not in str(config)
    state = begin(test_client, google, {"rememberMe": True})
    response = callback(test_client, state)
    assert response.headers["location"] == "http://localhost:3000/"
    session_cookie = next(
        x
        for x in response.headers.get_list("set-cookie")
        if x.startswith("fair_session=")
    )
    assert all(
        x in session_cookie
        for x in ["HttpOnly", "SameSite=lax", "Path=/api", "Max-Age=2678400"]
    )
    me = test_client.get("/api/auth/me").json()
    assert (
        me["email"] == "new@example.edu" and me["role"] == "user" and me["isVerified"]
    )
    with test_db() as db:
        assert db.get(User, UUID(me["id"])).password_hash is None
        assert db.scalar(select(func.count()).select_from(ExternalIdentity)) == 1
        assert db.scalar(select(func.count()).select_from(OIDCTransaction)) == 0
    assert test_client.get(f"{ROOT}/identities").json() == {
        "hasPassword": False,
        "providers": ["google"],
    }
    test_client.post("/api/auth/logout")
    assert test_client.get("/api/auth/me").status_code == 401


@pytest.mark.parametrize(
    "claims,omit,bad_signature",
    [
        ({"iss": "https://attacker.example"}, set(), False),
        (
            {"aud": "another-client", "azp": "fair-test.apps.googleusercontent.com"},
            set(),
            False,
        ),
        ({"azp": "another-client"}, set(), False),
        ({"exp": 1}, set(), False),
        ({"iat": 9999999999}, set(), False),
        ({"nonce": "different"}, set(), False),
        ({}, {"nonce"}, False),
        ({}, {"sub"}, False),
        ({}, {"exp"}, False),
        ({"sub": ""}, set(), False),
        ({"email_verified": False}, set(), False),
        ({"email_verified": "false"}, set(), False),
        ({"email": "invalid"}, set(), False),
        ({}, {"email"}, False),
        ({}, set(), True),
    ],
)
def test_protocol_rejects_untrusted_identity(
    test_client, test_db, google, claims, omit, bad_signature
):
    state = begin(test_client, google)
    google.update(claims=claims, omit=omit, bad_signature=bad_signature)
    response = callback(test_client, state)
    assert response.headers["location"].endswith("google_error=try_again")
    assert test_client.get("/api/auth/me").status_code == 401
    with test_db() as db:
        assert db.scalar(select(func.count()).select_from(User)) == 0
        assert db.scalar(select(func.count()).select_from(OIDCTransaction)) == 0


def test_transaction_wrong_browser_and_state_cannot_consume_then_replay_fails(
    test_client, test_db, google
):
    state = begin(test_client, google)
    browser = test_client.cookies.get(oidc.BINDING_COOKIE)
    test_client.cookies.clear()
    assert callback(test_client, state).headers["location"].endswith("try_again")
    test_client.cookies.set(oidc.BINDING_COOKIE, browser)
    assert (
        callback(test_client, "wrong-state").headers["location"].endswith("try_again")
    )
    assert callback(test_client, state).headers["location"] == "http://localhost:3000/"
    assert callback(test_client, state).headers["location"].endswith("try_again")
    assert google["token_requests"] == 1


def test_transaction_expiry_and_cancellation(test_client, test_db, google):
    state = begin(test_client, google)
    with test_db() as db:
        db.execute(
            update(OIDCTransaction).values(
                expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)
            )
        )
        db.commit()
    assert callback(test_client, state).headers["location"].endswith("try_again")
    state = begin(test_client, google)
    response = callback(
        test_client, state, error="access_denied", error_description="do-not-reflect"
    )
    assert response.headers["location"].endswith("google_error=cancelled")
    assert "do-not-reflect" not in response.headers["location"]
    assert google["token_requests"] == 0


def test_transaction_claim_is_atomic(test_client, test_db, google):
    state = begin(test_client, google)
    browser = test_client.cookies.get(oidc.BINDING_COOKIE)

    def claim(_):
        with test_db() as db:
            try:
                oidc.claim_transaction(
                    db, connection="google", state=state, browser=browser
                )
                return True
            except ValueError:
                return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(claim, range(2))) == [False, True]


def test_email_collision_requires_explicit_link_even_if_locally_verified(
    test_client, google, student_user
):
    google["claims"]["email"] = student_user.email
    response = callback(test_client, begin(test_client, google))
    assert response.headers["location"].endswith("google_error=account_link_required")
    assert test_client.get("/api/auth/me").status_code == 401


def test_explicit_link_keeps_existing_user_and_subject_survives_email_change(
    test_client, test_db, google, student_user, monkeypatch
):
    google["claims"]["email"] = student_user.email
    test_client.post(
        "/api/auth/login",
        data={"username": student_user.email, "password": "test_password_123"},
    )
    state = begin(
        test_client, google, {"currentPassword": "test_password_123"}, "/google/link"
    )
    assert callback(test_client, state).headers["location"] == "http://localhost:3000/"
    assert test_client.get("/api/auth/me").json()["id"] == str(student_user.id)
    test_client.post("/api/auth/logout")
    google["claims"]["email"] = "changed@example.edu"
    monkeypatch.setenv("FAIR_ADMISSION_MODE", "invite_only")
    assert (
        callback(test_client, begin(test_client, google)).headers["location"]
        == "http://localhost:3000/"
    )
    assert test_client.get("/api/auth/me").json()["email"] == student_user.email
    with test_db() as db:
        assert db.scalar(select(func.count()).select_from(User)) == 1


@pytest.mark.parametrize("change", ["wrong_email", "logout", "switched_user"])
def test_link_cannot_change_account_ownership(
    test_client, test_db, google, student_user, admin_user, change
):
    google["claims"]["email"] = student_user.email
    test_client.post(
        "/api/auth/login",
        data={"username": student_user.email, "password": "test_password_123"},
    )
    state = begin(
        test_client, google, {"currentPassword": "test_password_123"}, "/google/link"
    )
    if change == "wrong_email":
        google["claims"]["email"] = "different@example.edu"
    elif change == "logout":
        test_client.post("/api/auth/logout")
    else:
        test_client.post(
            "/api/auth/login",
            data={"username": admin_user.email, "password": "test_password_123"},
        )
    response = callback(test_client, state)
    assert "google_error=" in response.headers["location"]
    with test_db() as db:
        assert db.scalar(select(func.count()).select_from(ExternalIdentity)) == 0


def test_link_requires_password_and_origin(test_client, google, student_user):
    assert (
        test_client.post(
            f"{ROOT}/google/link", json={"currentPassword": "wrong"}, headers=ORIGIN
        ).status_code
        == 401
    )
    test_client.post(
        "/api/auth/login",
        data={"username": student_user.email, "password": "test_password_123"},
    )
    assert (
        test_client.post(
            f"{ROOT}/google/link", json={"currentPassword": "wrong"}, headers=ORIGIN
        ).status_code
        == 400
    )
    assert (
        test_client.post(
            f"{ROOT}/google/link", json={"currentPassword": "test_password_123"}
        ).status_code
        == 403
    )


@pytest.mark.parametrize(
    "mode,allowed", [("open", True), ("allowlist", False), ("invite_only", False)]
)
def test_google_registration_obeys_admission(
    test_client, test_db, google, monkeypatch, mode, allowed
):
    monkeypatch.setenv("FAIR_ADMISSION_MODE", mode)
    response = callback(test_client, begin(test_client, google))
    assert response.headers["location"].endswith(
        "/" if allowed else "google_error=registration_not_permitted"
    )
    with test_db() as db:
        assert db.scalar(select(func.count()).select_from(ExternalIdentity)) == int(
            allowed
        )


@pytest.mark.parametrize("failure", [None, "revoked", "expired", "wrong_email", "used"])
def test_google_invite_is_bound_rechecked_and_redeemed(
    test_client, test_db, google, monkeypatch, admin_user, failure
):
    monkeypatch.setenv("FAIR_ADMISSION_MODE", "invite_only")
    with test_db() as db:
        invitation, token = create_registration_invite(
            db, email="new@example.edu", created_by_user_id=admin_user.id
        )
        invitation_id = invitation.id
        db.commit()
    state = begin(test_client, google, {"inviteToken": token})
    with test_db() as db:
        row = db.scalar(select(OIDCTransaction))
        assert row.invite_hash == oidc.digest(token) and token not in str(row.__dict__)
        invitation = db.get(RegistrationInvite, invitation_id)
        if failure == "revoked":
            invitation.revoked_at = datetime.now(timezone.utc)
        elif failure == "expired":
            invitation.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        elif failure == "used":
            invitation.redeemed_at = datetime.now(timezone.utc)
        db.commit()
    if failure == "wrong_email":
        google["claims"]["email"] = "other@example.edu"
    response = callback(test_client, state)
    assert response.headers["location"].endswith(
        "google_error=registration_not_permitted" if failure else "/"
    )
    with test_db() as db:
        assert db.scalar(select(func.count()).select_from(ExternalIdentity)) == (
            0 if failure else 1
        )
        invitation = db.get(RegistrationInvite, invitation_id)
        if not failure:
            assert invitation.redeemed_by_user_id is not None


def test_configuration_cookie_is_secure_and_host_headers_cannot_change_callback(
    test_client, google, monkeypatch
):
    monkeypatch.setenv("FAIR_API_BASE_URL", "https://api.example.edu")
    monkeypatch.setenv("FAIR_BASE_URL", "https://fair.example.edu")
    response = test_client.post(
        f"{ROOT}/google/start",
        json={},
        headers={
            "Origin": "https://fair.example.edu",
            "Host": "attacker.example",
            "X-Forwarded-Host": "attacker.example",
            "X-Forwarded-Proto": "http",
        },
    )
    assert response.status_code == 200
    assert (
        "Secure" in response.headers["set-cookie"]
        and "HttpOnly" in response.headers["set-cookie"]
    )
    params = parse_qs(urlparse(response.json()["authorizationUrl"]).query)
    assert params["redirect_uri"] == [
        "https://api.example.edu/api/auth/oidc/google/callback"
    ]
    assert get_google_login_config().frontend_url == "https://fair.example.edu"


@pytest.mark.parametrize("phase", ["discovery", "exchange", "missing_token"])
def test_provider_failure_is_recoverable_without_creating_accounts(
    test_client, test_db, google, phase
):
    if phase == "discovery":
        google["unavailable"] = True
        response = test_client.post(f"{ROOT}/google/start", json={}, headers=ORIGIN)
        assert response.status_code == 503
        assert oidc.BINDING_COOKIE not in test_client.cookies
    else:
        state = begin(test_client, google)
        if phase == "exchange":
            google["token_error"] = True
        else:
            google["token_overrides"] = {"id_token": ""}
        assert (
            callback(test_client, state)
            .headers["location"]
            .endswith("google_error=try_again")
        )
        assert oidc.BINDING_COOKIE not in test_client.cookies
    with test_db() as db:
        assert db.scalar(select(func.count()).select_from(User)) == 0
        assert db.scalar(select(func.count()).select_from(OIDCTransaction)) == 0
    google.update(unavailable=False, token_error=False, token_overrides={})
    assert (
        callback(test_client, begin(test_client, google)).headers["location"]
        == "http://localhost:3000/"
    )


def test_second_tab_replaces_first_without_losing_the_new_login(test_client, google):
    old_state = begin(test_client, google)
    current_state = begin(test_client, google)
    assert callback(test_client, old_state).headers["location"].endswith("try_again")
    assert (
        callback(test_client, current_state).headers["location"]
        == "http://localhost:3000/"
    )


def test_allowlist_accepts_case_insensitive_email_but_not_subdomains(
    test_client, test_db, google, admin_user, monkeypatch
):
    from fair_platform.backend.data.models import AdmissionRule

    monkeypatch.setenv("FAIR_ADMISSION_MODE", "allowlist")
    with test_db() as db:
        db.add(
            AdmissionRule(
                kind="domain",
                normalized_value="example.edu",
                created_by_user_id=admin_user.id,
            )
        )
        db.commit()
    google["claims"]["email"] = "New@sub.example.edu"
    assert (
        callback(test_client, begin(test_client, google))
        .headers["location"]
        .endswith("registration_not_permitted")
    )
    google["claims"]["email"] = "New@EXAMPLE.edu"
    assert (
        callback(test_client, begin(test_client, google)).headers["location"]
        == "http://localhost:3000/"
    )


def test_policy_is_rechecked_when_it_changes_during_google_redirect(
    test_client, test_db, google, monkeypatch
):
    state = begin(test_client, google)
    monkeypatch.setenv("FAIR_ADMISSION_MODE", "invite_only")
    assert (
        callback(test_client, state)
        .headers["location"]
        .endswith("registration_not_permitted")
    )
    with test_db() as db:
        assert db.scalar(select(func.count()).select_from(User)) == 0


def test_disabled_google_keeps_existing_sessions_and_password_fallback(
    test_client, test_db, google, student_user, monkeypatch
):
    google["claims"]["email"] = student_user.email
    test_client.post(
        "/api/auth/login",
        data={"username": student_user.email, "password": "test_password_123"},
    )
    state = begin(
        test_client, google, {"currentPassword": "test_password_123"}, "/google/link"
    )
    assert callback(test_client, state).headers["location"] == "http://localhost:3000/"
    monkeypatch.delenv("FAIR_GOOGLE_CLIENT_ID")
    monkeypatch.delenv("FAIR_GOOGLE_CLIENT_SECRET")
    assert (
        test_client.get("/api/v1/system/config").json()["authentication"]["providers"]
        == []
    )
    assert test_client.get("/api/auth/me").json()["id"] == str(student_user.id)
    test_client.post("/api/auth/logout")
    assert (
        test_client.post(
            "/api/auth/login",
            data={"username": student_user.email, "password": "test_password_123"},
        ).status_code
        == 200
    )
    with test_db() as db:
        assert db.scalar(select(func.count()).select_from(ExternalIdentity)) == 1


def test_google_only_user_can_recover_a_password_without_losing_google(
    test_client, test_db, google, monkeypatch
):
    from fair_platform.backend.services.mailer import Mailer

    assert (
        callback(test_client, begin(test_client, google)).headers["location"]
        == "http://localhost:3000/"
    )
    user_id = test_client.get("/api/auth/me").json()["id"]
    test_client.post("/api/auth/logout")
    assert (
        test_client.post(
            "/api/auth/login",
            data={"username": "new@example.edu", "password": "anything"},
        ).status_code
        == 401
    )
    assert (
        test_client.post(
            "/api/auth/forgot-password", json={"email": "new@example.edu"}
        ).status_code
        == 400
    )
    monkeypatch.setenv("FAIR_EMAIL_ENABLED", "1")
    messages = []

    async def capture(self, user, reset_url):
        messages.append(reset_url)

    monkeypatch.setattr(Mailer, "send_password_reset", capture)
    assert (
        test_client.post(
            "/api/auth/forgot-password", json={"email": "new@example.edu"}
        ).status_code
        == 200
    )
    token = parse_qs(urlparse(messages[0]).query)["token"][0]
    assert (
        test_client.post(
            "/api/auth/reset-password/confirm",
            json={"token": token, "password": "recovered-password-123"},
        ).status_code
        == 200
    )
    assert (
        test_client.post(
            "/api/auth/login",
            data={"username": "new@example.edu", "password": "recovered-password-123"},
        ).status_code
        == 200
    )
    assert test_client.get("/api/auth/me").json()["id"] == user_id
    assert test_client.get(f"{ROOT}/identities").json() == {
        "hasPassword": True,
        "providers": ["google"],
    }
    test_client.post("/api/auth/logout")
    assert (
        callback(test_client, begin(test_client, google)).headers["location"]
        == "http://localhost:3000/"
    )
    assert test_client.get("/api/auth/me").json()["id"] == user_id


@pytest.mark.parametrize("password", ["x" * 100, "é" * 40])
def test_link_handles_passwords_exceeding_bcrypt_byte_limit(
    test_client, google, student_user, password
):
    test_client.post(
        "/api/auth/login",
        data={"username": student_user.email, "password": "test_password_123"},
    )
    response = test_client.post(
        f"{ROOT}/google/link", json={"currentPassword": password}, headers=ORIGIN
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Current password is incorrect"


def test_https_google_rollout_rejects_insecure_session_override(google, monkeypatch):
    monkeypatch.setenv("FAIR_BASE_URL", "https://fair.example.edu")
    monkeypatch.setenv("FAIR_API_BASE_URL", "https://api.fair.example.edu")
    monkeypatch.setenv("FAIR_SESSION_COOKIE_SECURE", "0")
    with pytest.raises(RuntimeError, match="FAIR_SESSION_COOKIE_SECURE"):
        validate_security_configuration()


def test_google_does_not_grant_roles_and_link_preserves_course_ownership(
    test_client, test_db, google, professor_user
):
    from uuid import uuid4
    from fair_platform.backend.data.models import Course

    google["claims"].update(email=professor_user.email, role="admin", groups=["admin"])
    with test_db() as db:
        course = Course(
            id=uuid4(), name="Existing course", instructor_id=professor_user.id
        )
        db.add(course)
        db.commit()
        course_id = course.id
    test_client.post(
        "/api/auth/login",
        data={"username": professor_user.email, "password": "test_password_123"},
    )
    state = begin(
        test_client, google, {"currentPassword": "test_password_123"}, "/google/link"
    )
    assert callback(test_client, state).headers["location"] == "http://localhost:3000/"
    me = test_client.get("/api/auth/me").json()
    assert me["id"] == str(professor_user.id) and me["role"] == "instructor"
    courses = test_client.get("/api/courses/").json()
    assert any(
        c["id"] == str(course_id) and c["membershipRole"] == "owner" for c in courses
    )
    test_client.post("/api/auth/logout")
    google["claims"].update(sub="unrelated-subject", email="brand-new@example.edu")
    assert (
        callback(test_client, begin(test_client, google)).headers["location"]
        == "http://localhost:3000/"
    )
    assert test_client.get("/api/auth/me").json()["role"] == "user"


def test_link_cannot_replace_another_users_google_identity(
    test_client, test_db, google, student_user
):
    assert (
        callback(test_client, begin(test_client, google)).headers["location"]
        == "http://localhost:3000/"
    )
    original_user_id = test_client.get("/api/auth/me").json()["id"]
    test_client.post("/api/auth/logout")
    test_client.post(
        "/api/auth/login",
        data={"username": student_user.email, "password": "test_password_123"},
    )
    google["claims"]["email"] = student_user.email
    state = begin(
        test_client, google, {"currentPassword": "test_password_123"}, "/google/link"
    )
    assert (
        callback(test_client, state)
        .headers["location"]
        .endswith("account_link_required")
    )
    assert test_client.get("/api/auth/me").json()["id"] == str(student_user.id)
    with test_db() as db:
        assert str(db.scalar(select(ExternalIdentity)).user_id) == original_user_id
        assert db.scalar(select(func.count()).select_from(ExternalIdentity)) == 1


def test_session_cookie_is_secure_and_expires_after_one_day_on_https(
    test_client, google, monkeypatch
):
    monkeypatch.setenv("FAIR_BASE_URL", "https://fair.example.edu")
    monkeypatch.setenv("FAIR_API_BASE_URL", "https://api.example.edu")
    google["callback_url"] = "https://api.example.edu/api/auth/oidc/google/callback"
    test_client.base_url = httpx.URL("https://api.example.edu")
    response = test_client.post(
        f"{ROOT}/google/start", json={}, headers={"Origin": "https://fair.example.edu"}
    )
    params = parse_qs(urlparse(response.json()["authorizationUrl"]).query)
    google["nonce"] = params["nonce"][0]
    google["challenge"] = params["code_challenge"][0]
    response = callback(test_client, params["state"][0])
    assert response.headers["location"] == "https://fair.example.edu/"
    session_cookie = next(
        c
        for c in response.headers.get_list("set-cookie")
        if c.startswith("fair_session=")
    )
    assert all(
        flag in session_cookie
        for flag in ("Secure", "HttpOnly", "SameSite=lax", "Max-Age=86400")
    )
