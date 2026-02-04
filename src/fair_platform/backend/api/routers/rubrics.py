from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from fair_platform.backend.data.database import session_dependency
from fair_platform.backend.data.models.rubric import Rubric
from fair_platform.backend.data.models.user import User, UserRole
from fair_platform.backend.api.schema.rubric import RubricCreate, RubricRead
from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.services.rubric_service import get_rubric_service

router = APIRouter()


@router.post("/", response_model=RubricRead, status_code=status.HTTP_201_CREATED)
def create_rubric(
    payload: RubricCreate,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in (UserRole.admin, UserRole.professor):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only professors or admins can create rubrics",
        )

    try:
        service = get_rubric_service(db)
        rubric = service.create_rubric(
            name=payload.name,
            content=payload.content,
            creator=current_user,
        )
        db.commit()
        db.refresh(rubric)
        return rubric
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create rubric: {str(e)}",
        )


@router.get("/", response_model=List[RubricRead])
def list_rubrics(
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == UserRole.admin:
        rubrics = db.query(Rubric).all()
    else:
        rubrics = db.query(Rubric).filter(Rubric.created_by_id == current_user.id).all()
    return rubrics


@router.get("/{rubric_id}", response_model=RubricRead)
def get_rubric(
    rubric_id: UUID,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    rubric = db.get(Rubric, rubric_id)
    if not rubric:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rubric not found",
        )

    if current_user.role != UserRole.admin and rubric.created_by_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this rubric",
        )

    return rubric


@router.delete("/{rubric_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rubric(
    rubric_id: UUID,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    rubric = db.get(Rubric, rubric_id)
    if not rubric:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rubric not found",
        )

    if current_user.role != UserRole.admin and rubric.created_by_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this rubric",
        )

    try:
        service = get_rubric_service(db)
        service.delete_rubric(rubric_id)
        db.commit()
        return None
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete rubric: {str(e)}",
        )


__all__ = ["router"]
