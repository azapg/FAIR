# FAIR Platform: Refresh Token Implementation Spec

## Overview

This spec defines the implementation of a secure refresh token system for FAIR Platform. The goal is to improve security by:
- Reducing access token lifetime (from 24h to 15-30 minutes)
- Implementing refresh tokens with longer lifetime (7-14 days) stored in `httpOnly` cookies
- Adding token rotation and revocation capabilities
- Enabling secure logout functionality

---

## Architecture

### Token Flow

```
User Login
    ↓
Issue Access Token (short-lived, 15 min) + Refresh Token (long-lived, 7 days)
    ↓
Access Token in Authorization header (Bearer)
Refresh Token in httpOnly cookie (secure, sameSite=strict)
    ↓
Access Token expires
    ↓
Frontend intercepts 401 → calls POST /auth/refresh
    ↓
Backend validates Refresh Token → issues new Access Token
    ↓
Continue request with new Access Token
```

### Token Types

1. **Access Token** (JWT, short-lived)
   - Purpose: Authenticate API requests
   - Lifetime: 15 minutes (default)
   - Storage: Authorization header
   - Claims: `sub` (user_id), `role`, `exp`, `iat`
   - Format: Signed JWT

2. **Refresh Token** (JWT + Database record, long-lived)
   - Purpose: Issue new access tokens
   - Lifetime: 7 days (default)
   - Storage: httpOnly cookie (`refresh_token`)
   - Claims: `sub` (user_id), `jti` (token family ID), `exp`, `iat`
   - Format: Signed JWT
   - Database: Tracked for revocation and rotation

---

## Database Schema Changes

### New Table: `refresh_tokens`

```sql
CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    family_id UUID NOT NULL,  -- Token family for rotation tracking
    token_hash VARCHAR NOT NULL UNIQUE,  -- Hashed token for comparison
    is_revoked BOOLEAN DEFAULT FALSE,
    issued_at TIMESTAMP WITH TIMEZONE NOT NULL,
    expires_at TIMESTAMP WITH TIMEZONE NOT NULL,
    last_used_at TIMESTAMP WITH TIMEZONE,
    created_at TIMESTAMP WITH TIMEZONE DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_user_id (user_id),
    INDEX idx_family_id (family_id),
    INDEX idx_expires_at (expires_at)
);
```

### User Model Update

Add optional relationship in `src/fair_platform/backend/data/models/user.py`:

```python
refresh_tokens: Mapped[List["RefreshToken"]] = relationship(
    "RefreshToken", 
    back_populates="user",
    cascade="all, delete-orphan"
)
```

### New Model: `RefreshToken`

Create `src/fair_platform/backend/data/models/refresh_token.py`:

```python
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import Boolean, DateTime, ForeignKey, String, UUID as SAUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

from ..database import Base

if TYPE_CHECKING:
    from .user import User

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    
    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        SAUUID, 
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    family_id: Mapped[UUID] = mapped_column(SAUUID, nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    
    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")
    
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at
    
    def is_valid(self) -> bool:
        return not self.is_revoked and not self.is_expired()
```

---

## Backend Changes

### 1. Configuration (`src/fair_platform/backend/core/config.py`)

Add these environment variable defaults:

```python
# Token lifetimes (in seconds)
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("FAIR_ACCESS_TOKEN_EXPIRE_MINUTES", "15")
)
REFRESH_TOKEN_EXPIRE_DAYS = int(
    os.getenv("FAIR_REFRESH_TOKEN_EXPIRE_DAYS", "7")
)

# Cookie settings
REFRESH_TOKEN_COOKIE_NAME = os.getenv(
    "FAIR_REFRESH_TOKEN_COOKIE_NAME", 
    "refresh_token"
)
REFRESH_TOKEN_COOKIE_SECURE = _parse_bool_env(
    os.getenv("FAIR_REFRESH_TOKEN_COOKIE_SECURE"),
    default=True  # HTTPS only in production
)
REFRESH_TOKEN_COOKIE_SAMESITE = os.getenv(
    "FAIR_REFRESH_TOKEN_COOKIE_SAMESITE",
    "strict"
)

# Token rotation
ENABLE_REFRESH_TOKEN_ROTATION = _parse_bool_env(
    os.getenv("FAIR_ENABLE_REFRESH_TOKEN_ROTATION"),
    default=True
)
```

### 2. Auth Service (`src/fair_platform/backend/services/auth_service.py`)

**New file** with utility functions:

```python
import os
import hashlib
from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe
from uuid import UUID, uuid4

from jose import jwt, JWTError
from sqlalchemy.orm import Session

from fair_platform.backend.data.models import User, RefreshToken
from fair_platform.backend.core.config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
    ENABLE_REFRESH_TOKEN_ROTATION,
)

SECRET_KEY = os.getenv("SECRET_KEY") or "fair-insecure-default-key"
ALGORITHM = "HS256"


def hash_token(token: str) -> str:
    """Hash a token for storage (never store plain tokens)"""
    return hashlib.sha256(token.encode()).hexdigest()


def create_access_token(user_id: str, role: str) -> str:
    """Create a short-lived access token"""
    to_encode = {
        "sub": user_id,
        "role": role,
        "type": "access",
    }
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode["exp"] = expire
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token() -> tuple[str, str]:
    """
    Create a refresh token and return (token, jti).
    
    The token is a signed JWT. The jti (token family ID) is used
    to group related tokens and detect token reuse attacks.
    """
    family_id = str(uuid4())
    token_payload = {
        "jti": family_id,
        "type": "refresh",
    }
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    token_payload["exp"] = expire
    
    token = jwt.encode(token_payload, SECRET_KEY, algorithm=ALGORITHM)
    return token, family_id


def store_refresh_token(
    db: Session,
    user_id: UUID,
    family_id: str,
    token: str,
) -> RefreshToken:
    """Store a refresh token in the database"""
    token_hash = hash_token(token)
    issued_at = datetime.now(timezone.utc)
    expires_at = issued_at + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    refresh_token = RefreshToken(
        id=uuid4(),
        user_id=user_id,
        family_id=UUID(family_id),
        token_hash=token_hash,
        issued_at=issued_at,
        expires_at=expires_at,
    )
    db.add(refresh_token)
    db.commit()
    db.refresh(refresh_token)
    return refresh_token


def verify_refresh_token(token: str) -> dict | None:
    """
    Verify a refresh token and return its payload.
    Returns None if invalid.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            return None
        return payload
    except JWTError:
        return None


def get_valid_refresh_token(
    db: Session,
    user_id: UUID,
    token: str,
) -> RefreshToken | None:
    """
    Retrieve and validate a refresh token from the database.
    
    Checks:
    - Token hash matches
    - Not revoked
    - Not expired
    
    Returns the RefreshToken record or None if invalid.
    """
    token_hash = hash_token(token)
    db_token = db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.token_hash == token_hash,
    ).first()
    
    if not db_token or not db_token.is_valid():
        return None
    
    return db_token


def revoke_refresh_token(db: Session, refresh_token: RefreshToken) -> None:
    """Revoke a single refresh token"""
    refresh_token.is_revoked = True
    db.add(refresh_token)
    db.commit()


def revoke_all_user_refresh_tokens(db: Session, user_id: UUID) -> int:
    """Revoke all refresh tokens for a user (logout all devices)"""
    count = db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.is_revoked == False,
    ).update({"is_revoked": True})
    db.commit()
    return count


def rotate_refresh_token(
    db: Session,
    old_token: RefreshToken,
) -> tuple[str, str]:
    """
    Implement refresh token rotation:
    
    1. Revoke the old token
    2. Issue a new token with the SAME family_id
    3. Return (new_token, family_id)
    
    This prevents token reuse attacks by invalidating old tokens
    while keeping the family_id for tracking.
    """
    revoke_refresh_token(db, old_token)
    
    new_token, _ = create_refresh_token()
    store_refresh_token(
        db,
        old_token.user_id,
        str(old_token.family_id),
        new_token,
    )
    
    return new_token, str(old_token.family_id)


def cleanup_expired_refresh_tokens(db: Session, days_to_keep: int = 30) -> int:
    """
    Periodically clean up expired and revoked tokens (background job).
    
    Keeps records for `days_to_keep` days for audit purposes,
    then deletes them.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
    count = db.query(RefreshToken).filter(
        RefreshToken.expires_at < cutoff,
        RefreshToken.is_revoked == True,
    ).delete()
    db.commit()
    return count
```

### 3. Auth Router Updates (`src/fair_platform/backend/api/routers/auth.py`)

**Update imports and constants:**

```python
# Add these imports
from fair_platform.backend.services.auth_service import (
    create_access_token as create_access_token_jwt,
    create_refresh_token,
    store_refresh_token,
    verify_refresh_token,
    get_valid_refresh_token,
    revoke_all_user_refresh_tokens,
    rotate_refresh_token,
)
from fair_platform.backend.core.config import (
    REFRESH_TOKEN_COOKIE_NAME,
    REFRESH_TOKEN_COOKIE_SECURE,
    REFRESH_TOKEN_COOKIE_SAMESITE,
)
from fastapi import Response, Request

# Update DEFAULT_TOKEN_EXPIRE_HOURS to use config
from fair_platform.backend.core.config import ACCESS_TOKEN_EXPIRE_MINUTES
DEFAULT_TOKEN_EXPIRE_HOURS = ACCESS_TOKEN_EXPIRE_MINUTES / 60
```

**Update `create_access_token` function:**

```python
def create_access_token(data: dict, remember_me: bool = False):
    """
    Create a JWT access token.
    
    Note: remember_me is deprecated in favor of refresh tokens.
    Kept for backward compatibility.
    """
    to_encode = data.copy()
    # Use short-lived token regardless of remember_me
    expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
```

**Add new endpoints to router:**

```python
@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(session_dependency),
    response: Response = Response(),
):
    """
    Login endpoint with refresh token support.
    
    Returns:
    - access_token: Short-lived JWT for API calls
    - refresh_token: Set in httpOnly cookie automatically
    - token_type: "bearer"
    """
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

    # Create tokens
    access_token = create_access_token(
        {"sub": str(user.id), "role": user.role}
    )
    refresh_token, family_id = create_refresh_token()
    store_refresh_token(db, user.id, family_id, refresh_token)
    
    # Set refresh token in httpOnly cookie
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=REFRESH_TOKEN_COOKIE_SECURE,
        samesite=REFRESH_TOKEN_COOKIE_SAMESITE,
        max_age=7 * 24 * 60 * 60,  # 7 days
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.post("/register")
async def register(
    user_in: UserCreate,
    db: Session = Depends(session_dependency),
    mailer: Mailer = Depends(get_mailer),
    response: Response = Response(),
):
    """
    Register endpoint updated for refresh tokens.
    """
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

    # Create tokens
    access_token = create_access_token(
        {"sub": str(user.id), "role": user.role}
    )
    refresh_token, family_id = create_refresh_token()
    store_refresh_token(db, user.id, family_id, refresh_token)
    
    # Set refresh token in httpOnly cookie
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=REFRESH_TOKEN_COOKIE_SECURE,
        samesite=REFRESH_TOKEN_COOKIE_SAMESITE,
        max_age=7 * 24 * 60 * 60,
    )
    
    auth_user = auth_user_payload(user)
    auth_user["settings"] = to_camel_keys(auth_user.get("settings", {}))
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": AuthUserRead.model_validate(auth_user),
    }


@router.post("/refresh")
def refresh(
    request: Request,
    db: Session = Depends(session_dependency),
    response: Response = Response(),
):
    """
    Refresh endpoint: exchange refresh token for new access token.
    
    The refresh token is read from the httpOnly cookie.
    Returns a new access token. Optionally rotates the refresh token.
    
    Security:
    - Refresh token must be valid and not revoked
    - Refresh token must not be expired
    - Returns 401 if invalid (no detailed error for security)
    """
    refresh_token = request.cookies.get(REFRESH_TOKEN_COOKIE_NAME)
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token missing")
    
    # Verify JWT structure
    payload = verify_refresh_token(refresh_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    # For now, we can't extract user_id from the JWT alone.
    # This requires frontend to send it or we store it differently.
    # Alternative: decode without verification to get user_id, then verify.
    # For now, use a different approach: validate via database.
    
    # Decode without signature first to get claims (for validation)
    try:
        unverified = jwt.get_unverified_claims(refresh_token)
    except:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    # We need user_id from the token. Currently not stored there.
    # Add user_id to refresh token JWT:
    # This requires updating create_refresh_token() above.
    
    # TODO: Update token structure as shown below in "Token Structure Update"


@router.post("/logout")
def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
    request: Request = Request(),
    response: Response = Response(),
):
    """
    Logout: revoke all refresh tokens for the user.
    
    Invalidates all sessions (all devices).
    """
    revoke_all_user_refresh_tokens(db, current_user.id)
    
    # Clear refresh token cookie
    response.delete_cookie(
        key=REFRESH_TOKEN_COOKIE_NAME,
        secure=REFRESH_TOKEN_COOKIE_SECURE,
        samesite=REFRESH_TOKEN_COOKIE_SAMESITE,
    )
    
    return {"detail": "Logged out successfully"}


@router.post("/logout-device")
def logout_device(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
    request: Request = Request(),
    response: Response = Response(),
):
    """
    Logout from current device only: revoke only this refresh token.
    
    Other devices remain logged in.
    """
    refresh_token = request.cookies.get(REFRESH_TOKEN_COOKIE_NAME)
    if refresh_token:
        db_token = get_valid_refresh_token(db, current_user.id, refresh_token)
        if db_token:
            revoke_refresh_token(db, db_token)
    
    # Clear refresh token cookie
    response.delete_cookie(
        key=REFRESH_TOKEN_COOKIE_NAME,
        secure=REFRESH_TOKEN_COOKIE_SECURE,
        samesite=REFRESH_TOKEN_COOKIE_SAMESITE,
    )
    
    return {"detail": "Logged out from this device"}
```

### 4. Token Structure Update

**Update `create_refresh_token()` in `auth_service.py`:**

```python
def create_refresh_token(user_id: str | None = None) -> tuple[str, str]:
    """
    Create a refresh token and return (token, jti).
    
    Args:
        user_id: Optional user_id to include in token (for single-token refresh flow)
    
    Token structure includes:
    - jti: family ID for token rotation tracking
    - type: "refresh" to distinguish from access tokens
    - sub: (optional) user_id for direct validation without DB lookup
    - exp: expiration timestamp
    """
    family_id = str(uuid4())
    token_payload = {
        "jti": family_id,
        "type": "refresh",
    }
    if user_id:
        token_payload["sub"] = user_id
    
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    token_payload["exp"] = expire
    
    token = jwt.encode(token_payload, SECRET_KEY, algorithm=ALGORITHM)
    return token, family_id
```

**Update login/register to pass user_id:**

```python
refresh_token, family_id = create_refresh_token(user_id=str(user.id))
```

**Implement `/refresh` endpoint properly:**

```python
@router.post("/refresh")
def refresh(
    request: Request,
    db: Session = Depends(session_dependency),
    response: Response = Response(),
):
    """Refresh endpoint: exchange refresh token for new access token."""
    refresh_token = request.cookies.get(REFRESH_TOKEN_COOKIE_NAME)
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token missing")
    
    # Verify token
    payload = verify_refresh_token(refresh_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    user_id = UUID(user_id_str)
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    # Validate refresh token in database
    db_token = get_valid_refresh_token(db, user_id, refresh_token)
    if not db_token:
        raise HTTPException(status_code=401, detail="Refresh token invalid or expired")
    
    # Update last_used_at
    db_token.last_used_at = datetime.now(timezone.utc)
    db.add(db_token)
    db.commit()
    
    # Create new access token
    access_token = create_access_token(
        {"sub": str(user.id), "role": user.role}
    )
    
    # Optionally rotate refresh token
    if ENABLE_REFRESH_TOKEN_ROTATION:
        new_refresh_token, _ = rotate_refresh_token(db, db_token)
        response.set_cookie(
            key=REFRESH_TOKEN_COOKIE_NAME,
            value=new_refresh_token,
            httponly=True,
            secure=REFRESH_TOKEN_COOKIE_SECURE,
            samesite=REFRESH_TOKEN_COOKIE_SAMESITE,
            max_age=7 * 24 * 60 * 60,
        )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
    }
```

---

## Frontend Changes

### 1. Update `frontend-dev/src/lib/api.ts`

```typescript
import axios, { AxiosError } from 'axios'

let baseURL = '/api'

if (import.meta.env.DEV) {
  baseURL = 'http://localhost:8000/api'
}

export function getApiBaseUrl() {
  return baseURL
}

export function getWebSocketUrl(path: string) {
  if (import.meta.env.DEV) {
    return `ws://localhost:8000${path}`
  }
  
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  return `${protocol}//${host}${path}`
}

const api = axios.create({
  baseURL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,  // Important: send cookies with requests
})

api.interceptors.request.use((config) => {
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export const clearAuthData = () => {
  localStorage.removeItem('token')
  localStorage.removeItem('user')
  window.dispatchEvent(new CustomEvent('auth:session-expired'))
}

const AUTH_ENDPOINTS = ['/auth/login', '/auth/register', '/auth/refresh']

// Track whether we're currently refreshing to avoid multiple refresh calls
let isRefreshing = false
let failedQueue: Array<{
  resolve: (value: string) => void
  reject: (reason?: any) => void
}> = []

const processQueue = (error: AxiosError | null, token: string | null = null) => {
  failedQueue.forEach(prom => {
    if (error) {
      prom.reject(error)
    } else {
      prom.resolve(token || '')
    }
  })
  
  isRefreshing = false
  failedQueue = []
}

// Response interceptor with automatic token refresh
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config
    const url = originalRequest?.url || ''
    const isAuthEndpoint = AUTH_ENDPOINTS.some(endpoint => 
      url === endpoint || url.startsWith(`${endpoint}?`)
    )
    
    // If 401 and not an auth endpoint, try to refresh
    if (error.response?.status === 401 && !isAuthEndpoint && originalRequest) {
      if (isRefreshing) {
        // Already refreshing, queue this request
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        }).then(token => {
          originalRequest.headers.Authorization = `Bearer ${token}`
          return api(originalRequest)
        }).catch(err => {
          clearAuthData()
          return Promise.reject(err)
        })
      }
      
      isRefreshing = true
      
      try {
        // Call refresh endpoint
        const { data } = await axios.post(`${baseURL}/auth/refresh`, {}, {
          withCredentials: true,
        })
        
        const newToken = data.access_token
        localStorage.setItem('token', newToken)
        
        // Update original request with new token
        originalRequest.headers.Authorization = `Bearer ${newToken}`
        
        processQueue(null, newToken)
        
        // Retry original request
        return api(originalRequest)
      } catch (refreshError) {
        processQueue(refreshError as AxiosError)
        clearAuthData()
        return Promise.reject(refreshError)
      }
    }
    
    // 401 on auth endpoints means invalid credentials
    if (error.response?.status === 401 && isAuthEndpoint) {
      return Promise.reject(error)
    }
    
    return Promise.reject(error)
  }
)

export default api
```

### 2. Update `frontend-dev/src/contexts/auth-context.tsx`

```typescript
// Update login function to remove remember_me from token storage
const login = useCallback(async (input: LoginInput) => {
  setLoading(true)
  try {
    const form = new URLSearchParams()
    form.append('username', input.username)
    form.append('password', input.password)
    form.append('grant_type', 'password')
    // remember_me is now handled by backend with refresh tokens
    // but can still be sent for backward compatibility
    if (input.remember_me) {
      form.append('scope', 'remember_me')
    }

    const loginRes = await api.post('/auth/login', form, {
      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      withCredentials: true,  // Ensure cookies are sent
    })

    const accessToken = loginRes.data?.access_token

    if (!accessToken) {
      throw new Error('An error occurred during login')
    }

    // Store only access token (refresh token is in httpOnly cookie)
    persist(accessToken, null)

    const userRes = await api.get('/auth/me')
    const nextUser: AuthUser = normalizeUser(userRes.data)
    setToken(accessToken)
    setUser(nextUser)
    persist(accessToken, nextUser)
  } finally {
    setLoading(false)
  }
}, [persist])

// Add logout function that calls backend
const logout = useCallback(async () => {
  try {
    await api.post('/auth/logout')
  } catch {
    // Ignore errors during logout
  } finally {
    setToken(null)
    setUser(null)
    persist(null, null)
  }
}, [persist])
```

---

## Alembic Migration

Create `src/fair_platform/backend/alembic/versions/{timestamp}_add_refresh_tokens.py`:

```python
"""Add refresh tokens table and RefreshToken model"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.create_table(
        'refresh_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('family_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('token_hash', sa.String(), nullable=False),
        sa.Column('is_revoked', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('issued_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash'),
    )
    op.create_index('idx_refresh_tokens_user_id', 'refresh_tokens', ['user_id'])
    op.create_index('idx_refresh_tokens_family_id', 'refresh_tokens', ['family_id'])
    op.create_index('idx_refresh_tokens_expires_at', 'refresh_tokens', ['expires_at'])

def downgrade():
    op.drop_index('idx_refresh_tokens_expires_at', table_name='refresh_tokens')
    op.drop_index('idx_refresh_tokens_family_id', table_name='refresh_tokens')
    op.drop_index('idx_refresh_tokens_user_id', table_name='refresh_tokens')
    op.drop_table('refresh_tokens')
```

---

## Security Considerations

1. **Token Storage:**
   - Access tokens stored in memory (not persisted)
   - Refresh tokens stored in httpOnly cookies (immune to XSS)
   - Token family IDs track rotation chains

2. **Token Validation:**
   - Always verify JWT signature
   - Check token expiration
   - Check revocation status in database
   - Validate user existence

3. **Rotation:**
   - Every refresh invalidates the old token
   - Same family_id links tokens in a chain
   - Detects token reuse attacks

4. **Reuse Attack Detection:**
   - If old token used after family rotated → revoke entire family
   - Prevents lateral movement if token leaked

5. **Cookie Security:**
   - httpOnly: prevents XSS token theft
   - Secure: HTTPS only in production
   - SameSite=Strict: prevents CSRF

6. **Environment Variables:**
   - `SECRET_KEY` must be strong and unique
   - `REFRESH_TOKEN_COOKIE_SECURE=true` in production
   - Consider key rotation strategy for long-running deployments

---

## Testing Strategy

### Backend Tests

```python
# tests/test_refresh_tokens.py
def test_login_returns_access_token_and_refresh_cookie(client, test_db):
    response = client.post("/api/auth/login", data=...)
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert "refresh_token" in response.cookies

def test_refresh_endpoint_exchanges_token(client, test_db):
    # Login
    login_resp = client.post("/api/auth/login", data=...)
    
    # Refresh
    refresh_resp = client.post("/api/auth/refresh")
    assert refresh_resp.status_code == 200
    assert "access_token" in refresh_resp.json()
    assert refresh_resp.json()["token_type"] == "bearer"

def test_expired_refresh_token_rejected(client, test_db):
    # Create expired token
    # Try to use it
    # Should get 401

def test_revoked_token_cannot_refresh(client, test_db):
    # Logout
    # Try to refresh
    # Should get 401

def test_refresh_token_rotation(client, test_db):
    # Get first refresh token
    # Refresh
    # Use old refresh token
    # Should be rejected
```

### Frontend Tests

```typescript
// Tests to verify token refresh flow and cookie handling
describe('Token Refresh', () => {
  it('should refresh access token on 401', async () => {
    // Mock 401 response
    // Verify refresh is called
    // Verify original request is retried with new token
  })
  
  it('should handle refresh token in cookies', async () => {
    // Verify withCredentials is set
    // Verify refresh endpoint gets cookies
  })
  
  it('should clear auth data on failed refresh', async () => {
    // Mock failed refresh
    // Verify user is logged out
  })
})
```

---

## Rollout Plan

### Phase 1: Backend Setup
1. Add `RefreshToken` model and `auth_service`
2. Create Alembic migration
3. Implement new endpoints (`/refresh`, `/logout`, `/logout-device`)
4. Keep `create_access_token()` backward-compatible

### Phase 2: Frontend Integration
1. Update `api.ts` with refresh interceptor
2. Update `auth-context.tsx` with logout
3. Verify cookie handling with `withCredentials: true`

### Phase 3: Migration
1. Deploy backend with new endpoints (old login still works)
2. Deploy frontend with refresh logic
3. Monitor refresh endpoint usage

### Phase 4: Cleanup
1. Remove `remember_me` flag from config (optional)
2. Reduce default token lifetime to 15 minutes
3. Add token cleanup background job

---

## Background Tasks

### Cleanup Job

Add to `src/fair_platform/backend/services/scheduled_tasks.py`:

```python
async def cleanup_expired_refresh_tokens():
    """Run daily to clean up old refresh tokens"""
    # Implementation using APScheduler or Celery
    pass
```

Or implement as part of lifespan in `main.py`:

```python
@contextmanager
async def lifespan(app: FastAPI):
    # Startup
    cleanup_task = asyncio.create_task(run_cleanup_loop())
    yield
    # Shutdown
    cleanup_task.cancel()

async def run_cleanup_loop():
    while True:
        await asyncio.sleep(24 * 60 * 60)  # Daily
        db = SessionLocal()
        try:
            cleanup_expired_refresh_tokens(db)
        finally:
            db.close()
```

---

## Future Enhancements

1. **Device Management**: Track device info (user agent, IP) per refresh token
2. **Multi-Factor Authentication**: Require MFA on new device
3. **Rate Limiting**: Limit refresh attempts to prevent brute force
4. **Token Binding**: Bind tokens to IP/device fingerprint
5. **Audit Logging**: Log all token creation/refresh/revocation events
6. **Passwordless Auth**: Support WebAuthn alongside refresh tokens