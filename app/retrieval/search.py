"""Vector search over chunks (cosine distance, HNSW index)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Chunk, Document
from app.retrieval.embeddings import embed_query


def search_chunks(session: Session, question: str, top_k: int = 5) -> list[dict]:
    qvec = embed_query(question)
    distance = Chunk.embedding.cosine_distance(qvec)
    rows = session.execute(
        select(Chunk, Document, distance.label("distance"))
        .join(Document, Document.id == Chunk.document_id)
        .order_by(distance)
        .limit(top_k)
    ).all()
    return [
        {
            "document_id": d.id,
            "title": d.title,
            "page": c.page,
            "text": c.text,
            "score": round(1 - dist, 4),
        }
        for c, d, dist in rows
    ]
