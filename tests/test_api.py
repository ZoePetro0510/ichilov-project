import pytest
from fastapi.testclient import TestClient

from app.llm import LLMResponse
from app.main import app, llm_dependency
from tests.conftest import FakeLLM


@pytest.fixture
def client(db_ready):
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_health_and_listing(client):
    assert client.get("/health").json()["status"] == "ok"
    assert len(client.get("/documents").json()) >= 5


def test_search_returns_best_page(client):
    r = client.post("/search", json={"question": "כמה זמן נמשך חיטוי ידיים בג'ל?", "top_k": 2})
    assert r.status_code == 200
    assert r.json()[0]["page"] == 2


def test_ask_and_fetch_logged_query(client):
    app.dependency_overrides[llm_dependency] = lambda: FakeLLM(LLMResponse(text="תשובה [1]"))
    r = client.post("/ask", json={"question": "מהו סולם מורס?"})
    assert r.status_code == 200
    logged = client.get(f"/queries/{r.json()['query_id']}").json()
    assert logged["answer"] == "תשובה [1]"


def test_missing_llm_key_gives_503(client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "llm_api_key", "")
    r = client.post("/ask", json={"question": "שאלה כלשהי"})
    assert r.status_code == 503


def test_validation_and_errors(client):
    app.dependency_overrides[llm_dependency] = lambda: FakeLLM()
    assert client.post("/ask", json={"question": "א"}).status_code == 422
    assert client.get("/queries/999999").status_code == 404
    assert client.post("/documents", files={"file": ("a.txt", b"x")}).status_code == 400
    empty_pdf = b"%PDF-1.4\n%%EOF"
    assert client.post("/documents", files={"file": ("bad.pdf", empty_pdf)}).status_code == 422
