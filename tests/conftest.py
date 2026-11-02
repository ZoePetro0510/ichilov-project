import pytest
from sqlalchemy import text

from app.core.db import SessionLocal, engine
from app.llm import LLMResponse, ToolCall


class FakeLLM:
    """Scripted LLM: returns the queued responses in order and records calls."""

    def __init__(self, *responses: LLMResponse):
        self.responses = list(responses)
        self.calls: list[dict] = []

    def complete(self, system, messages, tools=None):
        self.calls.append({"system": system, "messages": list(messages), "tools": tools})
        return self.responses.pop(0)


def tool_call(name: str, **args) -> LLMResponse:
    return LLMResponse(tool_calls=[ToolCall(id=f"call_{name}", name=name, input=args)])


@pytest.fixture(scope="session")
def db_ready():
    """Skip DB tests when Postgres is down or the sample corpus is not loaded."""
    try:
        with engine.connect() as conn:
            n = conn.execute(text("SELECT count(*) FROM documents")).scalar()
    except Exception:
        pytest.skip("PostgreSQL is not available")
    if not n:
        pytest.skip("Run `python -m scripts.load_corpus` first")


@pytest.fixture
def session(db_ready):
    with SessionLocal() as s:
        yield s
