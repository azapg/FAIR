"""OIDC mechanics shared by sign-in providers; no course permissions or tokens stored."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from authlib.integrations.starlette_client import OAuth
from pydantic import EmailStr, TypeAdapter
from sqlalchemy import delete
from sqlalchemy.orm import Session

from fair_platform.backend.core.config import OIDCProviderConfig
from fair_platform.backend.data.models.external_identity import OIDCTransaction

BINDING_COOKIE = "fair_oidc"
COOKIE_PATH = "/api/auth/oidc"
TRANSACTION_SECONDS = 600


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def create_client(config: OIDCProviderConfig):
    return OAuth().register(
        name=config.key,
        client_id=config.client_id,
        client_secret=config.client_secret,
        server_metadata_url=config.discovery_url,
        client_kwargs={
            "scope": "openid email profile",
            "code_challenge_method": "S256",
            "timeout": 10,
        },
    )


async def start_transaction(
    db: Session,
    config: OIDCProviderConfig,
    *,
    remember_me: bool = False,
    invite_token: str | None = None,
    user_id=None,
) -> tuple[str, str]:
    state, browser, nonce, verifier = (secrets.token_urlsafe(32) for _ in range(4))
    # Release a linking request's read transaction before provider network I/O.
    db.commit()
    authorization = await create_client(config).create_authorization_url(
        config.callback_url,
        state=state,
        nonce=nonce,
        code_verifier=verifier,
        prompt="select_account",
    )
    now = datetime.now(timezone.utc)
    db.execute(delete(OIDCTransaction).where(OIDCTransaction.expires_at <= now))
    db.add(
        OIDCTransaction(
            state_hash=digest(state),
            browser_hash=digest(browser),
            connection_key=config.key,
            purpose="link" if user_id else "login",
            user_id=user_id,
            nonce=nonce,
            code_verifier=verifier,
            remember_me=remember_me,
            invite_hash=digest(invite_token) if invite_token else None,
            expires_at=now + timedelta(seconds=TRANSACTION_SECONDS),
        )
    )
    db.commit()
    return authorization["url"], browser


def claim_transaction(
    db: Session, *, connection: str, state: str, browser: str
) -> OIDCTransaction:
    if not state or not browser or len(state) > 256 or len(browser) > 256:
        raise ValueError("Invalid sign-in transaction")
    # DELETE RETURNING is an atomic, single-use claim on SQLite and PostgreSQL.
    # Only this browser can claim it; no proof material remains on disk afterward.
    transaction = db.execute(
        delete(OIDCTransaction)
        .where(
            OIDCTransaction.state_hash == digest(state),
            OIDCTransaction.browser_hash == digest(browser),
            OIDCTransaction.connection_key == connection,
            OIDCTransaction.expires_at > datetime.now(timezone.utc),
        )
        .returning(OIDCTransaction)
    ).scalar_one_or_none()
    db.commit()
    if transaction is None:
        raise ValueError("Invalid sign-in transaction")
    return transaction


async def exchange_identity(
    config: OIDCProviderConfig, transaction: OIDCTransaction, code: str
) -> dict:
    if not code or len(code) > 4096:
        raise ValueError("Missing authorization code")
    client = create_client(config)
    token = await client.fetch_access_token(
        redirect_uri=config.callback_url,
        code=code,
        code_verifier=transaction.code_verifier,
    )
    claims = await client.parse_id_token(
        token,
        nonce=transaction.nonce,
        leeway=30,
        claims_options={
            "iss": {"essential": True, "value": config.issuer},
            "aud": {"essential": True, "value": config.client_id},
        },
    )
    if not claims:
        raise ValueError("Missing identity token")
    subject = claims.get("sub")
    if (
        not isinstance(subject, str)
        or not 1 <= len(subject) <= 255
        or not subject.isascii()
    ):
        raise ValueError("Invalid subject")
    if (
        claims.get("email_verified") is not True
        and claims.get("email_verified") != "true"
    ):
        raise ValueError("Verified email required")
    email = str(TypeAdapter(EmailStr).validate_python(claims.get("email")))
    return {
        "issuer": config.issuer,
        "subject": subject,
        "email": email,
        "name": str(claims.get("name") or email)[:255],
    }
