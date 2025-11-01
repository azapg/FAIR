---
title: Proper Authentication System Design
status: ready
last_updated: 2025-10-31
---

## Goal
Replace the mock authentication system (`test_password_123` for everyone) with a robust authentication system that properly handles both:
1. Real authenticated users who can log in
2. Synthetic/research-generated submissions without real user accounts

## Context
Current implementation creates synthetic users with fake emails (`{uuid}@fair.com`) for every submission created by a professor. This pollutes the users table and makes authentication impossible to implement properly since the User model lacks a password field.

The core tension: Submissions need a submitter_id (FK to users), but many submissions in research workflows are generated synthetically and don't correspond to real accounts.

## Selected Approach: Submitter Table with is_synthetic Flag

After discussion, we're going with a variation of Option A that keeps Submissions unified but extracts submitter info into a separate lightweight table.

### Key Design Decisions

1. **Submissions remain a single table** - no need to duplicate logic for real vs synthetic
2. **New `Submitter` table** acts as a lightweight profile:
   - Can represent real student accounts OR synthetic test data
   - Has optional FK to User (for real students who can authenticate)
   - Always has display name/email for plugins
3. **Track creation separately** - `Submission.created_by_id` points to the User who created it (professor/admin)

### Schema Changes

```python
class Submitter(Base):
    __tablename__ = "submitters"
    
    id: UUID (PK)
    name: str  # Display name: "John Smith" or "Synthetic Student 001"
    email: Optional[str]  # Real email for students, null for synthetic
    user_id: Optional[UUID] (FK to users, nullable)  # Only set for real students
    is_synthetic: bool
    created_at: datetime
    
class Submission(Base):
    # ... existing fields ...
    submitter_id: UUID (FK to submitters)  # Changed from FK to users
    created_by_id: UUID (FK to users)  # NEW: who actually created this submission
    
class User(Base):
    # Add password field for authentication
    password_hash: str  # NOT NULL - all users must have passwords
```

## Implementation Scope

### Database Layer (Backend Models)
**Files to modify:**
- `src/fair_platform/backend/data/models/submission.py`
  - Change `submitter_id` FK from `users` → `submitters`
  - Add `created_by_id` FK to `users`
  - Add relationship to new `Submitter` model
- `src/fair_platform/backend/data/models/user.py`
  - Add `password_hash: Optional[str]` field
  - Add relationship to submissions they created
- **NEW FILE**: `src/fair_platform/backend/data/models/submitter.py`
  - Create new `Submitter` model
- `src/fair_platform/backend/alembic/versions/` 
  - **NEW MIGRATION**: Create `submitters` table, migrate existing data, update FK constraints

### API Schemas (Pydantic)
**Files to modify:**
- `src/fair_platform/backend/api/schema/submission.py`
  - Update `SubmissionBase.submitter_id` to reference Submitter
  - Add `created_by_id` field
  - Update response models to include submitter details
- **NEW FILE**: `src/fair_platform/backend/api/schema/submitter.py`
  - Create `SubmitterRead`, `SubmitterCreate` schemas
- `src/fair_platform/backend/api/schema/user.py`
  - Add `password` to `UserCreate` (already exists but ignored)
  - Implement password hashing in registration

### API Endpoints
**Files to modify:**
- `src/fair_platform/backend/api/routers/submissions.py`
  - **`create_submission()` endpoint**: Instead of creating synthetic User, create Submitter
  - Change logic from:
    ```python
    synthetic_user = User(name=submitter_name, email=f"{uuid}@fair.com", ...)
    ```
    To:
    ```python
    submitter = Submitter(name=submitter_name, email=None, is_synthetic=True, user_id=None)
    submission = Submission(submitter_id=submitter.id, created_by_id=current_user.id)
    ```
  - Update GET endpoints to join Submitter data
- `src/fair_platform/backend/api/routers/auth.py`
  - **`register()` endpoint**: Actually hash and store passwords
  - **`login()` endpoint**: Verify hashed passwords instead of hardcoded `test_password_123`
  - Use `passlib` or `bcrypt` for hashing

### SDK Schemas
**Files to modify:**
- `src/fair_platform/sdk/schemas.py`
  - Update `Submitter` class (already exists, just ensure it matches)
  - No breaking changes needed since SDK Submitter is already separate from User

### Session Manager / Plugin System
**Files to modify:**
- `src/fair_platform/backend/services/session_manager.py`
  - Lines ~384-395: Change query from `User` to `Submitter`
  - Instead of:
    ```python
    submitter_ids = [s.submitter_id for s in db_submissions]
    submitters = db.query(User).filter(User.id.in_(submitter_ids)).all()
    ```
  - Use:
    ```python
    submitter_ids = [s.submitter_id for s in db_submissions]
    submitters = db.query(Submitter).filter(Submitter.id.in_(submitter_ids)).all()
    ```
  - SDK conversion stays the same (already uses `SDKSubmitter`)

### Frontend (TypeScript)
**Files to modify:**
- `frontend-dev/src/hooks/use-submissions.ts`
  - `Submitter` type already exists and is correct
  - Update `SubmissionCreate` type to send `submitter_name` (no change needed)
  - Backend handles Submitter creation transparently
- `frontend-dev/src/app/courses/course/tabs/submissions.tsx` (if exists)
  - Display `submission.submitter.name` (likely already works)
  - Maybe add badge showing "Synthetic" vs "Real" submission

### Tests
**Files to modify:**
- `tests/test_atomic_submission_creation.py`
  - Update all `submitter_id` references to use Submitter IDs
  - Add tests for synthetic vs real submissions
- `tests/test_auth_integration.py`
  - Update to test real password hashing
  - Remove hardcoded `test_password_123` assertions
- `tests/conftest.py`
  - Update `get_auth_token()` to use real passwords

## Migration Strategy

**Decision**: This is pre-production (alpha) — **no data migration needed**.

Since v0.6 marks the first MVP release and there are no production users yet:

1. **Drop and recreate** approach via Alembic migration:
   - New migration creates `submitters` table
   - Adds `password_hash NOT NULL` to `users` table (no nullable transition needed)
   - Updates `submissions.submitter_id` FK to point to `submitters`
   - Adds `submissions.created_by_id` FK to `users`

2. **Database reset for development**:
   ```bash
   # Delete SQLite database (or drop PostgreSQL database)
   rm instance/fair.db  # or similar
   
   # Run fresh migrations
   alembic upgrade head
   
   # Create admin user with real password
   fair create-admin --email admin@example.com --password <secure-password>
   ```

3. **Migration file will be clean** - no complex data transformation logic needed

## Risks / Tradeoffs

### Benefits
✅ Clean separation: authentication (User) vs display identity (Submitter)  
✅ Plugins can check `is_synthetic` to handle test data appropriately  
✅ Real users can authenticate, synthetic data doesn't pollute auth system  
✅ Track who created synthetic data via `created_by_id`

### Tradeoffs
⚠️ **Migration complexity**: Need to migrate existing synthetic users to submitters  
⚠️ **More joins**: Queries need extra join to get submitter info (but already doing this in session_manager)  
⚠️ **Schema churn**: Touches many files across backend, frontend, tests  

### Mitigation
- Write comprehensive migration with rollback support
- Add database indexes on new FK columns
- Update all tests before merging
- Consider feature flag for gradual rollout

---

## Authentication System Design

### Goals
1. Replace hardcoded `test_password_123` with real password hashing
2. Extend token lifetime for better UX without refresh token complexity
3. Optional "remember me" for long-lived sessions

### Authentication Changes

#### Password Management
**Library**: `passlib[bcrypt]` (already common in FastAPI projects)

**User Model Update**:
```python
class User(Base):
    # ... existing fields ...
    password_hash: str  # NOT NULL - required for all users
```

**Implementation**:
```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)
```

#### JWT Token Lifetimes
**Current**: 60 minutes  
**New Default**: 24 hours (1440 minutes)  
**Remember Me**: 31 days (44640 minutes)

**Changes to `auth.py`**:
```python
# Current
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# New
DEFAULT_TOKEN_EXPIRE_HOURS = 24
REMEMBER_ME_TOKEN_EXPIRE_DAYS = 31

def create_access_token(data: dict, remember_me: bool = False):
    if remember_me:
        expires_delta = timedelta(days=REMEMBER_ME_TOKEN_EXPIRE_DAYS)
    else:
        expires_delta = timedelta(hours=DEFAULT_TOKEN_EXPIRE_HOURS)
    # ... rest of logic
```

#### API Endpoint Changes

**Register Endpoint** (`POST /api/auth/register`):
```python
@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(session_dependency)):
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Hash password instead of ignoring it
    password_hash = hash_password(user_in.password)
    
    user = User(
        id=uuid4(),
        name=user_in.name,
        email=user_in.email,
        role=user_in.role,
        password_hash=password_hash  # NEW
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Default: no remember_me on registration
    access_token = create_access_token(
        {"sub": str(user.id), "role": user.role},
        remember_me=False
    )
    return {"access_token": access_token, "token_type": "bearer", "user": user}
```

**Login Endpoint** (`POST /api/auth/login`):
```python
class LoginForm(BaseModel):
    username: str  # Actually email
    password: str
    remember_me: bool = False

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(session_dependency)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Verify hashed password
    if not user.password_hash or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Check for remember_me in scopes (OAuth2 form allows scope field)
    remember_me = "remember_me" in form_data.scopes
    
    access_token = create_access_token(
        {"sub": str(user.id), "role": user.role},
        remember_me=remember_me
    )
    return {"access_token": access_token, "token_type": "bearer"}
```

#### Frontend Changes

**Login Form** (`frontend-dev/src/app/login/page.tsx`):
```tsx
const [rememberMe, setRememberMe] = useState(false)

// In form submission:
await login({ username: email, password, remember_me: rememberMe })
```

**Auth Context** (`frontend-dev/src/contexts/auth-context.tsx`):
```tsx
type LoginInput = { 
  username: string
  password: string
  remember_me?: boolean  // NEW
}

const login = useCallback(async (input: LoginInput) => {
  const form = new URLSearchParams()
  form.append('username', input.username)
  form.append('password', input.password)
  if (input.remember_me) {
    form.append('scope', 'remember_me')  // OAuth2 way to pass flags
  }
  // ... rest of login logic
})
```

### Implementation Checklist

#### Backend
- [ ] Add `passlib[bcrypt]` to `pyproject.toml` dependencies
- [ ] Create password hashing utilities in `backend/api/routers/auth.py`
- [ ] Update `register()` endpoint to hash passwords
- [ ] Update `login()` endpoint to verify passwords
- [ ] Update `create_access_token()` to support variable expiry
- [ ] Create Alembic migration for schema changes (clean, no data migration)
- [ ] Update tests to use real passwords
- [ ] Add CLI command `fair create-admin` for initial admin user

#### Frontend  
- [ ] Add "Remember me" checkbox to login form
- [ ] Update `LoginInput` type to include `remember_me`
- [ ] Pass `remember_me` flag in auth context login function

#### Documentation
- [ ] Update README with new default session length
- [ ] Add security notes about token storage
- [ ] Document that remember_me tokens are long-lived (advise users not to use on shared devices)

### Security Considerations

**What We're Doing Right:**
✅ Bcrypt for password hashing (industry standard)  
✅ JWT tokens are stateless (no database lookups on every request)  
✅ Tokens include role for authorization  
✅ HTTPS enforced in production (existing setup)

**Known Limitations (Acceptable for Research Platform):**
⚠️ No token revocation (acceptable: users control their environment)  
⚠️ No refresh tokens (acceptable: long-lived tokens + occasional re-login is fine)  
⚠️ No rate limiting on login endpoint (future: add after MVP+1)  
⚠️ No email verification (acceptable: controlled access, manual user management)

**No Migration Required:**
Since this is pre-production alpha, we're doing a clean break. All users will be created with passwords from day one. The `password_hash` field is NOT NULL.

### Future Enhancements (Out of Scope)
- Refresh token rotation for long-term sessions
- Email-based password reset flow
- 2FA/MFA for admin accounts
- OAuth integration (GitHub, Google)
- Invite code system for role-based registration
- Session management (view active sessions, revoke tokens)
