from authlib.integrations.base_client.errors import OAuthError
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from httpx import HTTPError
from joserfc.errors import JoseError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from fair_platform.backend.api.routers.auth import (
    _set_session_cookie,
    create_access_token,
    get_current_user,
    verify_password,
)
from fair_platform.backend.api.schema.external_identity import (
    GoogleLinkStart,
    GoogleLoginStart,
)
from fair_platform.backend.core.config import get_base_url, get_google_login_config
from fair_platform.backend.data.database import session_dependency
from fair_platform.backend.data.models import ExternalIdentity, User
from fair_platform.backend.services import oidc
from fair_platform.backend.services.access_control import AccessPolicyError
from fair_platform.backend.services.external_identity import (
    IdentityConflict,
    resolve_identity,
)

router = APIRouter()


def _config():
    config = get_google_login_config()
    if config is None:
        raise HTTPException(status_code=404, detail="Google sign-in is not enabled")
    return config


async def _start(
    request: Request, response: Response, db: Session, *, payload=None, user_id=None
):
    config = _config()
    if request.headers.get("origin") != config.frontend_url:
        raise HTTPException(status_code=403, detail="Invalid sign-in origin")
    try:
        url, browser = await oidc.start_transaction(
            db,
            config,
            remember_me=payload.remember_me if payload else False,
            invite_token=payload.invite_token if payload else None,
            user_id=user_id,
        )
    except (OAuthError, HTTPError, JoseError, ValueError):
        db.rollback()
        raise HTTPException(
            status_code=503, detail="Google sign-in is unavailable. Try again."
        ) from None
    response.set_cookie(
        oidc.BINDING_COOKIE,
        browser,
        max_age=oidc.TRANSACTION_SECONDS,
        httponly=True,
        secure=config.secure,
        samesite="lax",
        path=oidc.COOKIE_PATH,
    )
    response.headers["Cache-Control"] = "no-store"
    return {"authorizationUrl": url}


@router.post("/google/start")
async def google_start(
    payload: GoogleLoginStart,
    request: Request,
    response: Response,
    db: Session = Depends(session_dependency),
):
    return await _start(request, response, db, payload=payload)


@router.get("/identities")
def identities(
    user: User = Depends(get_current_user), db: Session = Depends(session_dependency)
):
    keys = db.scalars(
        select(ExternalIdentity.connection_key).where(
            ExternalIdentity.user_id == user.id
        )
    ).all()
    return {"hasPassword": bool(user.password_hash), "providers": keys}


@router.post("/google/link")
async def google_link(
    payload: GoogleLinkStart,
    request: Request,
    response: Response,
    user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
):
    try:
        valid_password = bool(user.password_hash) and verify_password(
            payload.current_password, user.password_hash
        )
    except ValueError:
        # bcrypt rejects oversized UTF-8 passwords; treat them as bad credentials.
        valid_password = False
    if not valid_password:
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    return await _start(request, response, db, user_id=user.id)


@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(session_dependency)):
    config = _config()
    error = None
    claimed = False
    try:
        transaction = oidc.claim_transaction(
            db,
            connection=config.key,
            state=request.query_params.get("state", ""),
            browser=request.cookies.get(oidc.BINDING_COOKIE, ""),
        )
        claimed = True
        if request.query_params.get("error"):
            error = "cancelled"
        else:
            claims = await oidc.exchange_identity(
                config, transaction, request.query_params.get("code", "")
            )
            linking_user = None
            if transaction.purpose == "link":
                linking_user = get_current_user(request, token=None, db=db)
            user = resolve_identity(db, claims, transaction, linking_user=linking_user)
            db.commit()
            response = RedirectResponse(f"{config.frontend_url}/", status_code=303)
            _set_session_cookie(
                response,
                create_access_token(
                    {"sub": str(user.id), "role": user.role},
                    remember_me=transaction.remember_me,
                ),
                remember_me=transaction.remember_me,
            )
    except IdentityConflict:
        error = "account_link_required"
    except AccessPolicyError:
        error = "registration_not_permitted"
    except (
        OAuthError,
        HTTPError,
        JoseError,
        ValueError,
        HTTPException,
        IntegrityError,
    ):
        error = "try_again"
    if error:
        db.rollback()
        response = RedirectResponse(
            f"{get_base_url()}/login?google_error={error}", status_code=303
        )
    if claimed:
        response.delete_cookie(
            oidc.BINDING_COOKIE,
            path=oidc.COOKIE_PATH,
            httponly=True,
            secure=config.secure,
            samesite="lax",
        )
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response
