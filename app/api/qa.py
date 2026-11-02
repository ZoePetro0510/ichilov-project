"""Question answering (RAG), the agent, and the query log."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agent.agent import run_agent
from app.api.deps import llm_dependency
from app.core.db import get_session
from app.llm import LLMClient, LLMError
from app.models import Query
from app.rag import answer_question

router = APIRouter(tags=["qa"])


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=1000)
    top_k: int = Field(5, ge=1, le=10)


@router.post("/ask")
def ask(
    req: AskRequest,
    session: Session = Depends(get_session),
    llm: LLMClient = Depends(llm_dependency),
):
    try:
        return answer_question(session, llm, req.question, req.top_k)
    except LLMError as e:
        raise HTTPException(502, str(e)) from e


@router.post("/agent")
def agent(
    req: AskRequest,
    session: Session = Depends(get_session),
    llm: LLMClient = Depends(llm_dependency),
):
    try:
        return run_agent(session, llm, req.question)
    except LLMError as e:
        raise HTTPException(502, str(e)) from e


@router.get("/queries/{query_id}")
def get_query(query_id: int, session: Session = Depends(get_session)):
    q = session.get(Query, query_id)
    if not q:
        raise HTTPException(404, "Query not found")
    return {
        "id": q.id,
        "question": q.question,
        "answer": q.answer,
        "sources": q.sources,
        "latency_ms": q.latency_ms,
        "steps": [
            {
                "step": s.step_order,
                "tool": s.tool_name,
                "input": s.tool_input,
                "output": s.tool_output,
            }
            for s in sorted(q.steps, key=lambda s: s.step_order)
        ],
    }
