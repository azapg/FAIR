from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from fair_platform.backend.data.database import session_dependency
from fair_platform.backend.data.models.rubric import Rubric
from fair_platform.backend.data.models.user import User
from fair_platform.backend.api.schema.rubric import (
    RubricCreate,
    RubricUpdate,
    RubricRead,
    RubricGenerateRequest,
    RubricGenerateResponse,
)
from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.core.security.permissions import has_capability, has_capability_or_owner
from fair_platform.backend.services.rubric_service import get_rubric_service

router = APIRouter()


@router.post("/", response_model=RubricRead, status_code=status.HTTP_201_CREATED)
def create_rubric(
    payload: RubricCreate,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    if not has_capability(current_user, "create_rubric"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to create rubrics",
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
    if has_capability(current_user, "manage_users"):
        rubrics = db.query(Rubric).all()
    else:
        rubrics = db.query(Rubric).filter(Rubric.created_by_id == current_user.id).all()
    return rubrics


@router.post("/generate", response_model=RubricGenerateResponse)
async def generate_rubric(
    payload: RubricGenerateRequest,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    if not has_capability(current_user, "generate_rubric"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to generate rubrics",
        )

    instruction = payload.instruction.strip()
    if not instruction:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Instruction cannot be empty",
        )

    try:
        service = get_rubric_service(db)
        content = await service.generate_rubric_from_instruction(instruction)
        return {"content": content}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate rubric: {str(e)}",
        ) from e



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

    if not has_capability_or_owner(current_user, "manage_rubric", rubric.created_by_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this rubric",
        )

    return rubric


@router.put("/{rubric_id}", response_model=RubricRead)
def update_rubric(
    rubric_id: UUID,
    payload: RubricUpdate,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    rubric = db.get(Rubric, rubric_id)
    if not rubric:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rubric not found",
        )

    if not has_capability_or_owner(current_user, "manage_rubric", rubric.created_by_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this rubric",
        )

    if payload.name is None and payload.content is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field (name or content) must be provided",
        )

    try:
        service = get_rubric_service(db)
        updated = service.update_rubric(
            rubric_id=rubric_id,
            name=payload.name,
            content=payload.content,
        )
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rubric not found",
            )
        db.commit()
        db.refresh(updated)
        return updated
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update rubric: {str(e)}",
        ) from e


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

    if not has_capability_or_owner(current_user, "manage_rubric", rubric.created_by_id):
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
