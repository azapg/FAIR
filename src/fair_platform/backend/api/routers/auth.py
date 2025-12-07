import os  
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from fair_platform.backend.api.schema.user import UserCreate, UserRead
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt, JWTError
import bcrypt
from sqlalchemy.orm import Session

from fair_platform.backend.data.database import session_dependency
from fair_platform.backend.data.models import User
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


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(session_dependency)
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError as e:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.get(User, UUID(user_id))
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(session_dependency)):
    """Register a new user with password hashing"""
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    password_hash = hash_password(user_in.password)
    
    user = User(
        id=uuid4(),
        name=user_in.name,
        email=user_in.email,
        role=user_in.role,
        password_hash=password_hash
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    access_token = create_access_token(
        {"sub": str(user.id), "role": user.role},
        remember_me=False
    )
    return {"access_token": access_token, "token_type": "bearer", "user": UserRead.model_validate(user)}


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

    remember_me = "remember_me" in form_data.scopes

    access_token = create_access_token(
        {"sub": str(user.id), "role": user.role},
        remember_me=remember_me
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserRead)
def read_me(current_user: User = Depends(get_current_user)):
    """
    Return the currently authenticated user's public information.
    """
    return current_user
