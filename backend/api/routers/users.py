from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from data.models.user import User
from api.schema.user import UserCreate, UserRead, UserUpdate
from data.database import session_dependency

router = APIRouter()

# TODO: For now, the User object is managed without authentication, just for testing/development.
#  In the future, the real end users (professors/admin) will have to authenticate, and maybe setup
#  a "MockUser" for students that aren't part of the system.

@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db: Session = Depends(session_dependency)):
    role_value = user.role if isinstance(user.role, str) else getattr(user.role, "value", user.role)
    db_user = User(id=uuid4(), name=user.name, email=user.email, role=role_value)
    db.add(db_user)

    db.commit()
    db.refresh(db_user)
    return db_user


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: UUID, db: Session = Depends(session_dependency)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.put("/{user_id}", response_model=UserRead)
def update_user(user_id: UUID, payload: UserUpdate, db: Session = Depends(session_dependency)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if payload.name is not None:
        user.name = payload.name
    if payload.email is not None:
        user.email = payload.email
    if payload.role is not None:
        user.role = payload.role if isinstance(payload.role, str) else getattr(payload.role, "value", payload.role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: UUID, db: Session = Depends(session_dependency)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    db.delete(user)
    db.commit()
    return None


__all__ = ["router"]
