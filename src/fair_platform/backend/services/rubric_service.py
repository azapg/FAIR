import math
from typing import Optional
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from fair_platform.backend.data.models.rubric import Rubric
from fair_platform.backend.data.models.user import User


WEIGHT_TOLERANCE = 1e-9


def validate_rubric_content(content: dict) -> None:
    if not isinstance(content, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rubric content must be a dictionary",
        )

    if "levels" not in content or not isinstance(content.get("levels"), list):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rubric content must have a 'levels' array",
        )

    levels = content["levels"]
    if len(levels) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rubric must have at least one level",
        )

    for lvl in levels:
        if not isinstance(lvl, str):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Each level must be a string",
            )

    if "criteria" not in content or not isinstance(content.get("criteria"), list):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rubric content must have a 'criteria' array",
        )

    criteria = content["criteria"]
    if len(criteria) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rubric must have at least one criterion",
        )

    expected_levels_count = len(levels)
    total_weight = 0.0

    for i, criterion in enumerate(criteria):
        if not isinstance(criterion, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Criterion at index {i} must be an object",
            )

        if "name" not in criterion or not isinstance(criterion.get("name"), str):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Criterion at index {i} must have a 'name' string field",
            )

        if "weight" not in criterion:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Criterion at index {i} must have a 'weight' field",
            )

        weight = criterion["weight"]
        if not isinstance(weight, (int, float)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Criterion at index {i} weight must be a number",
            )

        total_weight += float(weight)

        if "levels" not in criterion or not isinstance(criterion.get("levels"), list):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Criterion at index {i} must have a 'levels' array",
            )

        criterion_levels = criterion["levels"]
        if len(criterion_levels) != expected_levels_count:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Criterion at index {i} has {len(criterion_levels)} levels but expected {expected_levels_count}",
            )

        for j, lvl in enumerate(criterion_levels):
            if not isinstance(lvl, str):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Criterion at index {i}, level at index {j} must be a string",
                )

    if not math.isclose(total_weight, 1.0, abs_tol=WEIGHT_TOLERANCE):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Criterion weights must sum to 1.0, got {total_weight}",
        )


class RubricService:

    def __init__(self, db: Session):
        self.db = db

    def create_rubric(
        self,
        name: str,
        content: dict,
        creator: User,
    ) -> Rubric:
        validate_rubric_content(content)

        rubric = Rubric(
            id=uuid4(),
            name=name,
            created_by_id=creator.id,
            content=content,
        )
        self.db.add(rubric)
        self.db.flush()
        return rubric

    def get_rubric(self, rubric_id: UUID) -> Optional[Rubric]:
        return self.db.get(Rubric, rubric_id)

    def delete_rubric(self, rubric_id: UUID) -> bool:
        rubric = self.db.get(Rubric, rubric_id)
        if not rubric:
            return False
        self.db.delete(rubric)
        self.db.flush()
        return True


def get_rubric_service(db: Session) -> RubricService:
    return RubricService(db)


__all__ = ["RubricService", "get_rubric_service", "validate_rubric_content", "WEIGHT_TOLERANCE"]
