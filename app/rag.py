"""RAG: retrieve chunks -> ask the LLM to answer with citations -> log the query."""

from __future__ import annotations

import re
import time

from sqlalchemy.orm import Session

from app.llm import LLMClient
from app.models import Query
from app.prompts import RAG_SYSTEM, RAG_USER
from app.retrieval.search import search_chunks

CITATION = re.compile(r"\[(\d+)\]")


def format_context(chunks: list[dict]) -> str:
    return "\n\n".join(
        f"[{i}] (מסמך: {c['title']}, עמוד {c['page']})\n{c['text']}"
        for i, c in enumerate(chunks, start=1)
    )


def cited_sources(answer: str, chunks: list[dict]) -> list[dict]:
    """Sources the answer actually cites ([n]); falls back to all retrieved chunks."""
    wanted = {int(n) for n in CITATION.findall(answer)}
    picked = [c for i, c in enumerate(chunks, start=1) if i in wanted] or chunks
    seen, sources = set(), []
    for c in picked:
        key = (c["document_id"], c["page"])
        if key not in seen:
            seen.add(key)
            sources.append(
                {"document_id": c["document_id"], "title": c["title"], "page": c["page"]}
            )
    return sources


def answer_question(session: Session, llm: LLMClient, question: str, top_k: int = 5) -> dict:
    started = time.perf_counter()
    chunks = search_chunks(session, question, top_k)
    if not chunks:
        answer, sources = "לא מצאתי מידע על כך בנהלים שבמאגר.", []
    else:
        user = RAG_USER.format(context=format_context(chunks), question=question)
        answer = llm.complete(RAG_SYSTEM, [{"role": "user", "content": user}]).text.strip()
        sources = cited_sources(answer, chunks)

    latency_ms = int((time.perf_counter() - started) * 1000)
    row = Query(question=question, answer=answer, sources=sources, latency_ms=latency_ms)
    session.add(row)
    session.commit()
    return {"query_id": row.id, "answer": answer, "sources": sources, "latency_ms": latency_ms}
