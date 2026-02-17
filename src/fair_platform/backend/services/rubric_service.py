import math
import json
import re
from typing import Optional
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from fair_platform.backend.data.models.rubric import Rubric
from fair_platform.backend.data.models.user import User
from fair_platform.backend.services.ai_service import get_ai_client, get_llm_model


WEIGHT_TOLERANCE = 1e-9
RUBRIC_GENERATION_MAX_ATTEMPTS = 3


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

    def update_rubric(
        self,
        rubric_id: UUID,
        name: str | None = None,
        content: dict | None = None,
    ) -> Optional[Rubric]:
        rubric = self.db.get(Rubric, rubric_id)
        if not rubric:
            return None

        if name is not None:
            rubric.name = name

        if content is not None:
            validate_rubric_content(content)
            rubric.content = content

        self.db.add(rubric)
        self.db.flush()
        return rubric

    def delete_rubric(self, rubric_id: UUID) -> bool:
        rubric = self.db.get(Rubric, rubric_id)
        if not rubric:
            return False
        self.db.delete(rubric)
        self.db.flush()
        return True

    async def generate_rubric_from_instruction(self, instruction: str) -> dict:
        prompt = (
            "You generate grading rubrics in strict JSON.\n"
            "Return only a JSON object with this exact structure:\n"
            "{\n"
            '  "levels": ["Level 1", "Level 2", ...],\n'
            '  "criteria": [\n'
            "    {\n"
            '      "name": "Criterion name",\n'
            '      "weight": 0.25,\n'
            '      "levels": ["desc for level 1", "desc for level 2", ...]\n'
            "    }\n"
            "  ]\n"
            "}\n"
            "Rules:\n"
            "- criteria weights must sum exactly to 1.0\n"
            "- each criterion levels array length must match top-level levels length\n"
            "- keep names concise and clear\n"
            "- output valid JSON only, with no markdown code fences\n"
            f"Instruction:\n{instruction}"
        )

        client = get_ai_client()
        model = get_llm_model()

        for attempt in range(RUBRIC_GENERATION_MAX_ATTEMPTS):
            try:
                response = await client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=1,
                )
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Failed to generate rubric content: {str(e)}",
                ) from e

            try:
                content = response.choices[0].message.content if response.choices else None
                if not content:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail="Model returned empty rubric content",
                    )

                parsed = _extract_rubric_json(content)
                validate_rubric_content(parsed)
                return parsed
            except HTTPException as e:
                if e.status_code != status.HTTP_400_BAD_REQUEST:
                    raise
                if attempt == RUBRIC_GENERATION_MAX_ATTEMPTS - 1:
                    raise



def _extract_rubric_json(content: str) -> dict:
    cleaned = content.strip()
    code_block_match = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", cleaned)
    if code_block_match:
        cleaned = code_block_match.group(1).strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        first_brace = cleaned.find("{")
        last_brace = cleaned.rfind("}")
        if first_brace == -1 or last_brace == -1 or first_brace >= last_brace:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Model output did not contain valid rubric JSON",
            )

        try:
            parsed = json.loads(cleaned[first_brace:last_brace + 1])
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Model output did not contain valid rubric JSON",
            ) from e

    if not isinstance(parsed, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Model output must be a JSON object",
        )
    return parsed


def get_rubric_service(db: Session) -> RubricService:
    return RubricService(db)


__all__ = [
    "RubricService",
    "get_rubric_service",
    "validate_rubric_content",
    "WEIGHT_TOLERANCE",
]
