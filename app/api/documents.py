"""Upload, list and search documents."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_session
from app.ingestion.pipeline import IngestError, ingest_pdf
from app.models import Document
from app.retrieval.search import search_chunks

router = APIRouter(tags=["documents"])


class SearchRequest(BaseModel):
    question: str = Field(min_length=2)
    top_k: int = Field(5, ge=1, le=20)


@router.post("/documents", status_code=201)
def upload_document(
    file: UploadFile = File(...),
    title: str | None = Form(None),
    category: str | None = Form(None),
    session: Session = Depends(get_session),
):
    name = Path(file.filename or "").name
    if not name.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are accepted")
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / name
        with path.open("wb") as out:
            shutil.copyfileobj(file.file, out)
        try:
            doc = ingest_pdf(session, path, name, title=title, category=category)
        except IngestError as e:
            raise HTTPException(422, str(e)) from e
    return {"id": doc.id, "title": doc.title, "pages": doc.num_pages, "chunks": len(doc.chunks)}


@router.get("/documents")
def list_documents(session: Session = Depends(get_session)):
    docs = session.scalars(select(Document).order_by(Document.id)).all()
    return [
        {
            "id": d.id,
            "title": d.title,
            "filename": d.filename,
            "category": d.category,
            "pages": d.num_pages,
        }
        for d in docs
    ]


@router.post("/search")
def search(req: SearchRequest, session: Session = Depends(get_session)):
    return search_chunks(session, req.question, req.top_k)
