"""Retrieval evaluation: for each question, is the right (file, page) in the top-k?

Reports hit@1, hit@3, hit@5 and MRR. Needs no LLM key.
Usage:  python -m eval.run_eval [--k 5]
"""

import argparse
import json
from pathlib import Path

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models import Document
from app.retrieval.search import search_chunks


def main(k: int) -> None:
    questions = json.loads((Path(__file__).parent / "questions.json").read_text())
    ranks: list[int | None] = []
    with SessionLocal() as session:
        files = dict(session.execute(select(Document.id, Document.filename)).all())
        for item in questions:
            hits = search_chunks(session, item["q"], k)
            rank = next(
                (
                    i
                    for i, h in enumerate(hits, 1)
                    if files[h["document_id"]] == item["file"] and h["page"] == item["page"]
                ),
                None,
            )
            ranks.append(rank)
            mark = f"rank {rank}" if rank else "MISS"
            print(f"  [{mark:>7}] {item['q']}")

    n = len(ranks)
    summary = {
        "questions": n,
        "hit@1": sum(1 for r in ranks if r == 1) / n,
        "hit@3": sum(1 for r in ranks if r and r <= 3) / n,
        f"hit@{k}": sum(1 for r in ranks if r) / n,
        "mrr": sum(1 / r for r in ranks if r) / n,
    }
    print(
        json.dumps(
            {key: round(v, 3) if isinstance(v, float) else v for key, v in summary.items()},
            indent=2,
        )
    )


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=5)
    main(ap.parse_args().k)
