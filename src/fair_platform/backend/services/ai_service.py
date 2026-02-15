import os
from typing import Optional

from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

FAIR_LLM_API_KEY: Optional[str] = os.getenv("FAIR_LLM_API_KEY")
FAIR_LLM_BASE_URL: str = os.getenv("FAIR_LLM_BASE_URL", "https://api.openai.com/v1")
FAIR_LLM_MODEL: str = os.getenv("FAIR_LLM_MODEL", "gpt-4o")

_ai_client: Optional[AsyncOpenAI] = None


def get_ai_client() -> AsyncOpenAI:
    global _ai_client
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
]
