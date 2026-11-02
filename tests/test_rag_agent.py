"""RAG + agent behaviour against the real database with a scripted fake LLM."""

import pytest
from sqlalchemy import text

from app.agent.agent import run_agent
from app.agent.tools import query_metadata_sql
from app.llm import LLMResponse
from app.models import AgentStep, Query
from app.rag import answer_question, cited_sources
from tests.conftest import FakeLLM, tool_call


def test_rag_cites_the_right_page_and_logs_query(session):
    llm = FakeLLM(LLMResponse(text="יש לדווח תוך 24 שעות [1]."))
    out = answer_question(session, llm, "תוך כמה זמן יש לדווח על אירוע חריג?", top_k=3)
    assert out["sources"][0]["page"] == 1
    assert "דיווח" in out["sources"][0]["title"] or out["sources"][0]["title"]
    # the retrieved context was really sent to the model
    assert "עמוד" in llm.calls[0]["messages"][0]["content"]
    assert session.get(Query, out["query_id"]).answer == out["answer"]


def test_cited_sources_falls_back_to_all_chunks():
    chunks = [
        {"document_id": 1, "title": "A", "page": 2},
        {"document_id": 2, "title": "B", "page": 1},
    ]
    assert len(cited_sources("אין ציטוטים", chunks)) == 2
    assert cited_sources("כן [2]", chunks) == [{"document_id": 2, "title": "B", "page": 1}]


def test_agent_runs_sql_tool_then_answers(session):
    llm = FakeLLM(
        tool_call("query_metadata_sql", sql="SELECT count(*) AS n FROM documents"),
        LLMResponse(text="יש 5 נהלים."),
    )
    out = run_agent(session, llm, "כמה נהלים יש?")
    assert out["answer"] == "יש 5 נהלים."
    assert out["steps"][0]["tool"] == "query_metadata_sql"
    assert '"n"' in out["steps"][0]["output"]
    # tool result was fed back to the model
    assert llm.calls[1]["messages"][-1]["role"] == "tool"
    assert session.query(AgentStep).filter_by(query_id=out["query_id"]).count() == 1


def test_agent_search_then_checklist(session):
    llm = FakeLLM(
        tool_call("search_protocols", query="היגיינת ידיים"),
        tool_call("build_checklist", topic="היגיינת ידיים"),
        LLMResponse(text="- [ ] לשטוף ידיים [1]"),  # consumed by build_checklist's own LLM call
        LLMResponse(text="הנה הרשימה."),
    )
    out = run_agent(session, llm, "בנה לי צ'קליסט להיגיינת ידיים")
    assert [s["tool"] for s in out["steps"]] == ["search_protocols", "build_checklist"]
    assert "לשטוף" in out["steps"][1]["output"]


def test_agent_stops_after_max_steps(session):
    looping = [tool_call("search_protocols", query="x") for _ in range(10)]
    out = run_agent(session, FakeLLM(*looping), "לולאה")
    assert len(out["steps"]) == 6
    assert "לא הצלחתי" in out["answer"]


def test_unsafe_sql_is_rejected_and_unknown_tool_handled(session):
    assert query_metadata_sql("DROP TABLE documents").startswith("Rejected")
    llm = FakeLLM(tool_call("no_such_tool"), LLMResponse(text="סיום"))
    out = run_agent(session, llm, "בדיקה")
    assert "Unknown tool" in out["steps"][0]["output"]


def test_database_user_itself_is_read_only(db_ready):
    """Layer 2: even if the validator were bypassed, the DB role blocks it."""
    from sqlalchemy import create_engine
    from sqlalchemy.exc import ProgrammingError

    from app.core.config import settings

    eng = create_engine(settings.agent_database_url)
    with eng.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM documents")).scalar() > 0
        for bad in [
            "SELECT count(*) FROM chunks",
            "SELECT * FROM queries",
            "DELETE FROM documents",
        ]:
            with pytest.raises(ProgrammingError):
                conn.execute(text(bad))
            conn.rollback()
