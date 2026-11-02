"""The three tools the agent can call. Each returns a plain string for the LLM."""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.agent.sql_guard import UnsafeSQL, validate_select
from app.core.config import settings
from app.llm import LLMClient
from app.prompts import CHECKLIST_SYSTEM
from app.rag import format_context
from app.retrieval.search import search_chunks

MAX_ROWS = 50

DOCUMENTS_SCHEMA = (
    "documents(id int, title text, filename text, source_url text, "
    "published_date date, category text, num_pages int, created_at timestamp)"
)

TOOL_SPECS = [
    {
        "name": "search_protocols",
        "description": "Semantic search over protocol text. Returns the most relevant "
        "passages with document title and page number.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "What to look for, in Hebrew"},
                "top_k": {"type": "integer", "description": "How many passages (default 5)"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "query_metadata_sql",
        "description": "Run one read-only SELECT on the documents table (title, category, "
        "published_date, num_pages...). Max 50 rows.",
        "parameters": {
            "type": "object",
            "properties": {"sql": {"type": "string", "description": "A single SELECT"}},
            "required": ["sql"],
        },
    },
    {
        "name": "build_checklist",
        "description": "Build an actionable checklist from the protocols about a topic.",
        "parameters": {
            "type": "object",
            "properties": {"topic": {"type": "string", "description": "Topic, in Hebrew"}},
            "required": ["topic"],
        },
    },
]


def _json_default(o):
    if isinstance(o, (date, datetime)):
        return o.isoformat()
    if isinstance(o, Decimal):
        return float(o)
    return str(o)


def search_protocols(session: Session, query: str, top_k: int = 5) -> str:
    chunks = search_chunks(session, query, max(1, min(int(top_k), 10)))
    return format_context(chunks) if chunks else "No relevant passages found."


_agent_engine = None


def _get_agent_engine():
    global _agent_engine
    if _agent_engine is None:
        _agent_engine = create_engine(settings.agent_database_url, pool_pre_ping=True)
    return _agent_engine


def query_metadata_sql(sql: str) -> str:
    try:
        safe = validate_select(sql)
    except UnsafeSQL as e:
        return f"Rejected: {e}"
    try:
        with _get_agent_engine().connect() as conn:
            conn.execute(text("SET TRANSACTION READ ONLY"))
            conn.execute(text("SET LOCAL statement_timeout = 5000"))
            result = conn.execute(text(safe))
            rows = [dict(r._mapping) for r in result.fetchmany(MAX_ROWS)]
    except Exception as e:  # SQL errors go back to the model so it can fix the query
        return f"SQL error: {str(e).splitlines()[0]}"
    return json.dumps(rows, ensure_ascii=False, default=_json_default)


def build_checklist(session: Session, llm: LLMClient, topic: str) -> str:
    chunks = search_chunks(session, topic, 6)
    if not chunks:
        return "No relevant passages found."
    prompt = f"קטעים:\n{format_context(chunks)}\n\nנושא: {topic}"
    return llm.complete(CHECKLIST_SYSTEM, [{"role": "user", "content": prompt}]).text.strip()


def run_tool(name: str, args: dict, session: Session, llm: LLMClient) -> str:
    try:
        if name == "search_protocols":
            return search_protocols(session, args["query"], args.get("top_k", 5))
        if name == "query_metadata_sql":
            return query_metadata_sql(args["sql"])
        if name == "build_checklist":
            return build_checklist(session, llm, args["topic"])
    except KeyError as e:
        return f"Missing argument: {e}"
    return f"Unknown tool: {name}"
