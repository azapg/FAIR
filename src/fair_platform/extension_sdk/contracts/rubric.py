from pydantic import BaseModel

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


__all__ = [
    "RubricCriterion",
    "RubricContent",
]
