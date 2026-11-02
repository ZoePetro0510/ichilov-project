"""Local multilingual embeddings (intfloat/multilingual-e5-small, supports Hebrew).

E5 models need a prefix: "passage: " for stored text, "query: " for questions.
The model is loaded lazily so importing the app stays fast.
"""

from __future__ import annotations

from functools import lru_cache

from app.core.config import settings


@lru_cache(maxsize=1)
def _model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(settings.embedding_model)


def _encode(texts: list[str]) -> list[list[float]]:
    vectors = _model().encode(texts, normalize_embeddings=True, batch_size=32)
    return [v.tolist() for v in vectors]


def embed_passages(texts: list[str]) -> list[list[float]]:
    return _encode([f"passage: {t}" for t in texts])


def embed_query(text: str) -> list[float]:
    return _encode([f"query: {text}"])[0]
