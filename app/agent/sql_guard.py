"""Safety checks for LLM-generated SQL. This is layer 1 of 3:
1. this validator (single SELECT only, documents table only)
2. a database user with SELECT on `documents` only (agent_readonly)
3. a READ ONLY transaction with a statement timeout
"""

from __future__ import annotations

import re

ALLOWED_TABLE = "documents"
FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|truncate|grant|revoke|copy|"
    r"call|do|execute|set|reset|vacuum|pg_\w+|information_schema|into)\b",
    re.IGNORECASE,
)
TABLE_REF = re.compile(r"\b(?:from|join)\s+([\w.\"]+)", re.IGNORECASE)


class UnsafeSQL(ValueError):
    pass


def validate_select(sql: str) -> str:
    """Return the cleaned query or raise UnsafeSQL."""
    cleaned = re.sub(r"--[^\n]*|/\*.*?\*/", " ", sql, flags=re.DOTALL).strip()
    cleaned = cleaned.rstrip(";").strip()
    if not cleaned:
        raise UnsafeSQL("Empty query")
    if ";" in cleaned:
        raise UnsafeSQL("Only a single statement is allowed")
    if not re.match(r"(?is)^\s*(select|with)\b", cleaned):
        raise UnsafeSQL("Only SELECT queries are allowed")
    if FORBIDDEN.search(cleaned):
        raise UnsafeSQL("Query contains a forbidden keyword")
    tables = {t.strip('"').lower().removeprefix("public.") for t in TABLE_REF.findall(cleaned)}
    if not tables:
        raise UnsafeSQL("Query must read from the documents table")
    if tables != {ALLOWED_TABLE}:
        raise UnsafeSQL(f"Only the '{ALLOWED_TABLE}' table may be queried")
    return cleaned
