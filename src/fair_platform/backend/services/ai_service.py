import os
from typing import Optional

from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

FAIR_LLM_API_KEY: Optional[str] = os.getenv("FAIR_LLM_API_KEY")
FAIR_LLM_BASE_URL: str = os.getenv("FAIR_LLM_BASE_URL", "https://api.openai.com/v1")
FAIR_LLM_MODEL: str = os.getenv("FAIR_LLM_MODEL", "gpt-4o")

_ai_client: Optional[AsyncOpenAI] = None
MISSING_AI_CONFIG_MESSAGE = (
    "AI features are not configured yet. Ask an administrator to set FAIR_LLM_API_KEY "
    "and review the AI service setup documentation."
)


def get_ai_client() -> AsyncOpenAI:
    global _ai_client
    if not FAIR_LLM_API_KEY:
        raise RuntimeError(MISSING_AI_CONFIG_MESSAGE)

    if _ai_client is None:
        _ai_client = AsyncOpenAI(
            api_key=FAIR_LLM_API_KEY,
            base_url=FAIR_LLM_BASE_URL,
        )
    return _ai_client


def get_llm_model() -> str:
    return FAIR_LLM_MODEL


__all__ = [
    "get_ai_client",
    "get_llm_model",
    "FAIR_LLM_API_KEY",
    "FAIR_LLM_BASE_URL",
    "FAIR_LLM_MODEL",
    "MISSING_AI_CONFIG_MESSAGE",
]
