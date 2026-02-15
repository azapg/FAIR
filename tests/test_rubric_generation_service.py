from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException

from fair_platform.backend.services.rubric_service import RubricService


def _mock_completion_content(content: str):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content),
            )
        ]
    )


@pytest.mark.asyncio
async def test_generate_rubric_from_instruction_accepts_json_code_block():
    model_output = """```json
    {
      "levels": ["Poor", "Fair", "Good", "Excellent"],
      "criteria": [
        {"name": "Content", "weight": 0.5, "levels": ["Missing", "Basic", "Solid", "Strong"]},
        {"name": "Style", "weight": 0.5, "levels": ["Weak", "Developing", "Clear", "Excellent"]}
      ]
    }
    ```"""

    fake_client = Mock()
    fake_client.chat.completions.create = AsyncMock(
        return_value=_mock_completion_content(model_output)
    )

    service = RubricService(db=None)

    with patch(
        "fair_platform.backend.services.rubric_service.get_ai_client",
        return_value=fake_client,
    ), patch(
        "fair_platform.backend.services.rubric_service.get_llm_model",
        return_value="test-model",
    ):
        generated = await service.generate_rubric_from_instruction("Essay rubric")

    assert generated["levels"] == ["Poor", "Fair", "Good", "Excellent"]
    assert len(generated["criteria"]) == 2


@pytest.mark.asyncio
async def test_generate_rubric_from_instruction_rejects_invalid_json():
    fake_client = Mock()
    fake_client.chat.completions.create = AsyncMock(
        return_value=_mock_completion_content("not-json")
    )

    service = RubricService(db=None)

    with patch(
        "fair_platform.backend.services.rubric_service.get_ai_client",
        return_value=fake_client,
    ), patch(
        "fair_platform.backend.services.rubric_service.get_llm_model",
        return_value="test-model",
    ):
        with pytest.raises(HTTPException) as exc_info:
            await service.generate_rubric_from_instruction("Essay rubric")

    assert exc_info.value.status_code == 400
