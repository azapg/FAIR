"""Local browser E2E fixture with a simulated Google provider and real signed tokens.

Build frontend-dev first, then: uv run python tests/google_login_browser_fixture.py
Open http://localhost:8010/login. POST /__test__/scenario with a named scenario
to select failures/admission. No real credentials, users, email, or external APIs
are used. Temporary data is removed on exit. This module is never loaded by FAIR.
"""

import base64
import hashlib
import html
import os
import secrets
import tempfile
import time
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit
from uuid import uuid4

import httpx
import uvicorn
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from jose import jwk, jwt
from sqlalchemy import func, select

ORIGIN = "http://localhost:8010"
PROVIDER = "http://127.0.0.1:8010"
ISSUER = "https://accounts.google.com"
PASSWORD = "fixture-password-123"
CLIENT_ID = "browser-fixture.apps.googleusercontent.com"
FRONTEND = Path(__file__).resolve().parents[1] / "frontend-dev/dist"


def run():
    if not (FRONTEND / "index.html").is_file():
        raise SystemExit("Build frontend-dev before running this fixture")
    with tempfile.TemporaryDirectory(prefix="fair-google-browser-") as data_dir:
        os.environ.update(
            {
                "PYTHON_DOTENV_DISABLED": "1",
                "FAIR_DATA_DIR": data_dir,
                "DATABASE_URL": f"sqlite:///{data_dir}/fair.db",
                "SECRET_KEY": secrets.token_urlsafe(48),
                "FAIR_BASE_URL": ORIGIN,
                "FAIR_API_BASE_URL": ORIGIN,
                "FAIR_GOOGLE_CLIENT_ID": CLIENT_ID,
                "FAIR_GOOGLE_CLIENT_SECRET": "fixture-not-a-real-secret",
                "FAIR_CORS_ORIGINS": ORIGIN,
                "FAIR_DEPLOYMENT_MODE": "COMMUNITY",
                "FAIR_ENABLE_EXECUTION_DISPATCHER": "0",
                "FAIR_STORAGE_BACKEND": "local",
                "FAIR_STORAGE_BACKENDS": "local",
                "FAIR_BOOTSTRAP_ADMIN_EMAIL": "",
                "FAIR_EMAIL_ENABLED": "0",
                "FAIR_ENFORCE_EMAIL_VERIFICATION": "0",
                "FAIR_RESEND_API_KEY": "",
                "RESEND_API_KEY": "",
                "EMAIL_ENABLED": "0",
                "FAIR_AUTO_MIGRATE": "1",
                "FAIR_SESSION_COOKIE_SECURE": "0",
                "FAIR_AI_CONTROLS_ENABLED": "0",
                "FAIR_ADMISSION_MODE": "open",
            }
        )
        # Import only after the temporary runtime environment is in place.
        from fair_platform.backend.main import app
        from fair_platform.backend.api.routers.auth import hash_password
        from fair_platform.backend.data.database import SessionLocal
        from fair_platform.backend.data.migrations import run_migrations_to_head
        from fair_platform.backend.data.models import Course, ExternalIdentity, User
        from fair_platform.backend.services import oidc
        from fair_platform.backend.services.access_control import (
            create_registration_invite,
        )

        run_migrations_to_head()
        with SessionLocal() as db:
            existing = User(
                id=uuid4(),
                name="Existing Professor",
                email="existing@example.edu",
                role="instructor",
                password_hash=hash_password(PASSWORD),
                is_verified=True,
            )
            db.add(existing)
            db.flush()
            db.add(
                Course(id=uuid4(), name="Preserved course", instructor_id=existing.id)
            )
            _, invitation = create_registration_invite(
                db, email="invited@example.edu", created_by_user_id=existing.id
            )
            existing_id = str(existing.id)
            db.commit()

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
            "kid": "fixture",
            "use": "sig",
        }
        settings = {"scenario": "new", "tokens": 0}
        codes = {}

        def provider_response(request):
            if request.url.path.endswith("openid-configuration"):
                if settings["scenario"] == "outage":
                    raise httpx.ConnectError(
                        "Simulated provider outage", request=request
                    )
                return httpx.Response(
                    200,
                    json={
                        "issuer": ISSUER,
                        "authorization_endpoint": f"{ISSUER}/authorize",
                        "token_endpoint": "https://oauth2.googleapis.com/token",
                        "jwks_uri": "https://www.googleapis.com/certs",
                        "id_token_signing_alg_values_supported": ["RS256"],
                    },
                )
            if request.url.path == "/certs":
                return httpx.Response(200, json={"keys": [public_jwk]})
            if request.url.path == "/token":
                body = parse_qs(request.content.decode())
                saved = codes.pop(body.get("code", [""])[0], None)
                if not saved:
                    return httpx.Response(400, json={"error": "invalid_grant"})
                challenge = (
                    base64.urlsafe_b64encode(
                        hashlib.sha256(body["code_verifier"][0].encode()).digest()
                    )
                    .decode()
                    .rstrip("=")
                )
                assert challenge == saved["code_challenge"]
                assert body["redirect_uri"] == [
                    f"{ORIGIN}/api/auth/oidc/google/callback"
                ]
                settings["tokens"] += 1
                scenario = saved["scenario"]
                email = {
                    "existing": "existing@example.edu",
                    "collision": "existing@example.edu",
                    "wrong_email": "other@example.edu",
                    "invited": "invited@example.edu",
                }.get(scenario, "new@example.edu")
                now = int(time.time())
                token = jwt.encode(
                    {
                        "iss": ISSUER,
                        "aud": CLIENT_ID,
                        "sub": email,
                        "nonce": "wrong" if scenario == "bad_nonce" else saved["nonce"],
                        "iat": now,
                        "exp": now + 3600,
                        "email": email,
                        "email_verified": True,
                        "name": "Browser fixture",
                    },
                    private,
                    algorithm="RS256",
                    headers={"kid": "fixture"},
                )
                return httpx.Response(
                    200,
                    json={
                        "access_token": "discard-fixture-token",
                        "token_type": "Bearer",
                        "id_token": token,
                    },
                )
            raise AssertionError("Unexpected provider request")

        actual_client = oidc.create_client

        def fixture_client(config):
            client = actual_client(config)
            client.client_kwargs["transport"] = httpx.MockTransport(provider_response)
            authorize = client.create_authorization_url

            async def local_authorization(*args, **kwargs):
                value = await authorize(*args, **kwargs)
                value["url"] = (
                    f"{PROVIDER}/__test__/authorize?{urlsplit(value['url']).query}"
                )
                return value

            client.create_authorization_url = local_authorization
            return client

        oidc.create_client = fixture_client

        @app.post("/__test__/scenario")
        async def scenario(request: Request):
            name = (await request.json())["name"]
            if name not in {
                "new",
                "existing",
                "collision",
                "wrong_email",
                "invited",
                "restricted",
                "cancel",
                "bad_nonce",
                "outage",
                "disabled",
            }:
                raise HTTPException(400)
            settings["scenario"] = name
            os.environ["FAIR_ADMISSION_MODE"] = (
                "invite_only" if name in {"invited", "restricted"} else "open"
            )
            os.environ["FAIR_GOOGLE_CLIENT_ID"] = (
                "" if name == "disabled" else CLIENT_ID
            )
            os.environ["FAIR_GOOGLE_CLIENT_SECRET"] = (
                "" if name == "disabled" else "fixture-not-a-real-secret"
            )
            return {"scenario": name}

        @app.get("/__test__/authorize")
        def authorize(request: Request):
            query = dict(request.query_params)
            code = secrets.token_urlsafe(24)
            codes[code] = {**query, "scenario": settings["scenario"]}
            params = {"state": query["state"]}
            params.update(
                {"error": "access_denied"}
                if settings["scenario"] == "cancel"
                else {"code": code}
            )
            callback = f"{ORIGIN}/api/auth/oidc/google/callback?{urlencode(params)}"
            return HTMLResponse(
                "<h1>Simulated Google consent</h1><p>Test identities only</p>"
                f'<a href="{html.escape(callback)}">Return to FAIR</a>'
            )

        @app.get("/__test__/invitation")
        def invitation_link():
            return RedirectResponse(f"{ORIGIN}/register#invite={invitation}")

        @app.get("/__test__/summary")
        def summary():
            with SessionLocal() as db:
                return {
                    "users": db.scalar(select(func.count()).select_from(User)),
                    "identities": db.scalar(
                        select(func.count()).select_from(ExternalIdentity)
                    ),
                    "existingUserId": existing_id,
                    "tokenExchanges": settings["tokens"],
                }

        for folder in ("assets", "fonts", "data"):
            app.mount(
                f"/{folder}",
                StaticFiles(directory=FRONTEND / folder),
                name=f"fixture-{folder}",
            )

        @app.middleware("http")
        async def frontend(request, call_next):
            response = await call_next(request)
            if response.status_code == 404 and not request.url.path.startswith(
                ("/api/", "/__test__/")
            ):
                return FileResponse(FRONTEND / "index.html")
            return response

        print(
            f"Browser fixture ready at {ORIGIN}; only temporary test data is used.",
            flush=True,
        )
        uvicorn.run(app, host="127.0.0.1", port=8010, access_log=False)


if __name__ == "__main__":
    run()
