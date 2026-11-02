"""FastAPI entry point.  Run:  uvicorn app.main:app --reload   then open /docs"""

from fastapi import FastAPI

from app.api import documents, qa
from app.api.deps import llm_dependency  # noqa: F401  (re-exported for tests)
from app.core.config import settings

app = FastAPI(title="Medical AI Assistant")
app.include_router(documents.router)
app.include_router(qa.router)


@app.get("/health")
def health():
    return {"status": "ok", "llm_configured": bool(settings.llm_api_key)}
