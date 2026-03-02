from pydantic import BaseModel, Field, field_validator

from fair_platform.extension_sdk.contracts.common import contract_model_config


class RubricCriterion(BaseModel):
    model_config = contract_model_config

    name: str
    weight: float
    levels: list[str]


class RubricContent(BaseModel):
    model_config = contract_model_config

    levels: list[str]
    criteria: list[RubricCriterion]


class RubricJobRequest(BaseModel):
    model_config = contract_model_config

    instruction: str = Field(min_length=1)

    @field_validator("instruction")
    @classmethod
    def validate_instruction(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Instruction cannot be empty")
        return normalized


class RubricGenerateResponse(BaseModel):
    model_config = contract_model_config

    content: RubricContent


__all__ = [
    "RubricCriterion",
    "RubricContent",
    "RubricJobRequest",
    "RubricGenerateResponse",
]
