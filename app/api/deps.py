"""Shared FastAPI dependencies."""

from fastapi import HTTPException

from app.llm import LLMClient, LLMError, get_llm


def llm_dependency() -> LLMClient:
    """The configured LLM client, or a clear 503 when no API key is set."""
    try:
        return get_llm()
    except LLMError as e:
        raise HTTPException(503, str(e)) from e
