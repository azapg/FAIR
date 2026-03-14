import os
from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe
from uuid import UUID, uuid4

from fair_platform.backend.api.schema.user import AuthUserRead, UserCreate
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt, JWTError
import bcrypt
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from fair_platform.backend.data.database import session_dependency
from fair_platform.backend.data.models import User
from fair_platform.backend.data.models.user import UserRole
from fair_platform.backend.core.config import (
    get_base_url,
    get_email_enabled,
    get_enforce_email_verification,
)
from fair_platform.backend.core.security.permissions import auth_user_payload
from fair_platform.backend.api.schema.casing import to_camel_keys
from fair_platform.backend.services.mailer import Mailer, get_mailer
from dotenv import load_dotenv
load_dotenv()

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

SECRET_KEY = os.getenv("SECRET_KEY") or "fair-insecure-default-key"
if SECRET_KEY == "fair-insecure-default-key":
    print("WARNING: Using insecure default SECRET_KEY. Set SECRET_KEY environment variable for better security.")
ALGORITHM = "HS256"
DEFAULT_TOKEN_EXPIRE_HOURS = 24
REMEMBER_ME_TOKEN_EXPIRE_DAYS = 31
EMAIL_DISABLED_MESSAGE = "Email services are disabled on this instance"
EMAIL_VERIFICATION_REQUIRED_MESSAGE = "Please verify your email before signing in"
RESEND_VERIFICATION_REQUEST_SENT_MESSAGE = (
    "If an account exists and requires verification, a verification email has been sent"
)
TOKEN_PURPOSE_PASSWORD_RESET = "password_reset"
TOKEN_PURPOSE_VERIFY_EMAIL = "verify_email"
PASSWORD_RESET_TOKEN_EXPIRE_MINUTES = 60
VERIFY_EMAIL_TOKEN_EXPIRE_MINUTES = 30


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class TokenConfirmRequest(BaseModel):
    token: str


class ResetPasswordConfirmRequest(TokenConfirmRequest):
    password: str


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    password_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)


def create_access_token(data: dict, remember_me: bool = False):
    """Create a JWT access token with variable expiry"""
    to_encode = data.copy()
    if remember_me:
        expires_delta = timedelta(days=REMEMBER_ME_TOKEN_EXPIRE_DAYS)
    else:
        expires_delta = timedelta(hours=DEFAULT_TOKEN_EXPIRE_HOURS)
    
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def _create_action_token(
    *,
    user: User,
    purpose: str,
    expires_delta: timedelta,
) -> str:
    payload = {
        "sub": str(user.id),
        "email": str(user.email),
        "purpose": purpose,
        "exp": datetime.now(timezone.utc) + expires_delta,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def _decode_action_token(token: str, *, expected_purpose: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired token",
        ) from exc

    if payload.get("purpose") != expected_purpose:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired token",
        )
    if not payload.get("sub") or not payload.get("email"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired token",
        )
    return payload


def _build_reset_url(token: str) -> str:
    return f"{get_base_url()}/reset-password?token={token}"


def _build_verify_url(token: str) -> str:
    return f"{get_base_url()}/verify-email?token={token}"


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(session_dependency)
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.get(User, UUID(user_id))
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserCreate,
    db: Session = Depends(session_dependency),
    mailer: Mailer = Depends(get_mailer),
):
    """Register a new user with password hashing"""
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    password_hash = hash_password(user_in.password)
    
    user = User(
        id=uuid4(),
        name=user_in.name,
        email=user_in.email,
        role=UserRole.user.value,
        password_hash=password_hash,
        is_verified=not get_email_enabled(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    if get_email_enabled() and not user.is_verified:
        verification_token = _create_action_token(
            user=user,
            purpose=TOKEN_PURPOSE_VERIFY_EMAIL,
            expires_delta=timedelta(minutes=VERIFY_EMAIL_TOKEN_EXPIRE_MINUTES),
        )
        await mailer.send_verification(
            user=user,
            verification_url=_build_verify_url(verification_token),
        )
        if get_enforce_email_verification():
            return {
                "detail": "Verification email sent. Please verify your email before continuing.",
                "verification_required": True,
            }

    access_token = create_access_token(
        {"sub": str(user.id), "role": user.role},
        remember_me=False
    )
    auth_user = auth_user_payload(user)
    auth_user["settings"] = to_camel_keys(auth_user.get("settings", {}))
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": AuthUserRead.model_validate(auth_user),
    }


@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(session_dependency),
):
    """Login endpoint with proper password verification"""
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.password_hash or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if get_enforce_email_verification() and not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=EMAIL_VERIFICATION_REQUIRED_MESSAGE,
        )

    remember_me = "remember_me" in form_data.scopes

    access_token = create_access_token(
        {"sub": str(user.id), "role": user.role},
        remember_me=remember_me
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=AuthUserRead)
def read_me(current_user: User = Depends(get_current_user)):
    """
    Return the currently authenticated user's public information.
    """
    auth_user = auth_user_payload(current_user)
    auth_user["settings"] = to_camel_keys(auth_user.get("settings", {}))
    return auth_user


@router.post("/forgot-password")
async def forgot_password(
    payload: ForgotPasswordRequest,
    db: Session = Depends(session_dependency),
    mailer: Mailer = Depends(get_mailer),
):
    if not get_email_enabled():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=EMAIL_DISABLED_MESSAGE,
        )

    user = db.query(User).filter(User.email == payload.email).first()
    if user:
        reset_token = _create_action_token(
            user=user,
            purpose=TOKEN_PURPOSE_PASSWORD_RESET,
            expires_delta=timedelta(minutes=PASSWORD_RESET_TOKEN_EXPIRE_MINUTES),
        )
        await mailer.send_password_reset(
            user=user,
            reset_url=_build_reset_url(reset_token),
        )

    return {"detail": "If an account exists for this email, a reset message has been sent"}


@router.post("/resend-verification")
async def resend_verification_email(
    current_user: User = Depends(get_current_user),
    mailer: Mailer = Depends(get_mailer),
):
    if not get_email_enabled():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=EMAIL_DISABLED_MESSAGE,
        )

    if current_user.is_verified:
        return {"detail": "Account is already verified"}

    verification_token = _create_action_token(
        user=current_user,
        purpose=TOKEN_PURPOSE_VERIFY_EMAIL,
        expires_delta=timedelta(minutes=VERIFY_EMAIL_TOKEN_EXPIRE_MINUTES),
    )
    await mailer.send_verification(
        user=current_user,
        verification_url=_build_verify_url(verification_token),
    )
    return {"detail": "Verification email sent"}


@router.post("/resend-verification-request")
async def resend_verification_request(
    payload: ResendVerificationRequest,
    db: Session = Depends(session_dependency),
    mailer: Mailer = Depends(get_mailer),
):
    if not get_email_enabled():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=EMAIL_DISABLED_MESSAGE,
        )

    user = db.query(User).filter(User.email == payload.email).first()
    if user and not user.is_verified:
        verification_token = _create_action_token(
            user=user,
            purpose=TOKEN_PURPOSE_VERIFY_EMAIL,
            expires_delta=timedelta(minutes=VERIFY_EMAIL_TOKEN_EXPIRE_MINUTES),
        )
        await mailer.send_verification(
            user=user,
            verification_url=_build_verify_url(verification_token),
        )
    return {"detail": RESEND_VERIFICATION_REQUEST_SENT_MESSAGE}


@router.post("/verify-email/confirm")
async def verify_email_confirm(
    payload: TokenConfirmRequest,
    db: Session = Depends(session_dependency),
):
    token_data = _decode_action_token(
        payload.token,
        expected_purpose=TOKEN_PURPOSE_VERIFY_EMAIL,
    )
    user = db.get(User, UUID(token_data["sub"]))
    if user is None or str(user.email) != token_data["email"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired token",
        )

    if user.is_verified:
        detail = "Email already verified"
    else:
        user.is_verified = True
        db.add(user)
        db.commit()
        detail = "Email verified successfully"

    access_token = create_access_token(
        {"sub": str(user.id), "role": user.role},
        remember_me=False
    )
    auth_user = auth_user_payload(user)
    auth_user["settings"] = to_camel_keys(auth_user.get("settings", {}))

    return {
        "detail": detail,
        "access_token": access_token,
        "token_type": "bearer",
        "user": auth_user,
    }


@router.post("/reset-password/confirm")
async def reset_password_confirm(
    payload: ResetPasswordConfirmRequest,
    db: Session = Depends(session_dependency),
):
    token_data = _decode_action_token(
        payload.token,
        expected_purpose=TOKEN_PURPOSE_PASSWORD_RESET,
    )
    user = db.get(User, UUID(token_data["sub"]))
    if user is None or str(user.email) != token_data["email"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired token",
        )

    user.password_hash = hash_password(payload.password)
    db.add(user)
    db.commit()
    return {"detail": "Password reset successful"}
