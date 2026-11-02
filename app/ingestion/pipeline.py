"""PDF -> documents row + chunks with embeddings."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.chunking import chunk_document
from app.ingestion.pdf_utils import extract_clean
from app.models import Chunk, Document
from app.retrieval.embeddings import embed_passages


class IngestError(Exception):
    pass


def ingest_pdf(
    session: Session,
    path: str | Path,
    filename: str,
    title: str | None = None,
    category: str | None = None,
    source_url: str | None = None,
    published_date: date | None = None,
) -> Document:
    if session.scalar(select(Document).where(Document.filename == filename)):
        raise IngestError(f"'{filename}' was already uploaded")

    try:
        report = extract_clean(path)
    except Exception as e:  # corrupt / encrypted / not really a PDF
        raise IngestError(f"Could not read the PDF: {e}") from e
    if report.verdict.startswith(("EMPTY", "LITTLE HEBREW")):
        raise IngestError(f"Cannot use this PDF: {report.verdict}")

    chunks = chunk_document(report.pages)
    if not chunks:
        raise IngestError("No text found in the PDF")
    vectors = embed_passages([c.text for c in chunks])

    doc = Document(
        title=title or Path(filename).stem,
        filename=filename,
        category=category,
        source_url=source_url,
        published_date=published_date,
        num_pages=report.num_pages,
        chunks=[
            Chunk(page=c.page, chunk_index=c.chunk_index, text=c.text, embedding=v)
            for c, v in zip(chunks, vectors, strict=True)
        ],
    )
    session.add(doc)
    session.commit()
    return doc
