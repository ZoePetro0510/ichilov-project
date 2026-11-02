"""Ingest every PDF in data/raw/ (skips files already loaded).

Usage:  python -m scripts.load_corpus
"""

from pathlib import Path

from app.core.db import SessionLocal
from app.ingestion.pipeline import IngestError, ingest_pdf

CATEGORIES = {
    "hygiene_hands": "בקרת זיהומים",
    "high_risk_medication": "תרופות",
    "fall_prevention": "בטיחות",
    "patient_admission": "קבלת מטופלים",
    "safety_incident": "בטיחות",
}


def main() -> None:
    with SessionLocal() as session:
        for pdf in sorted(Path("data/raw").glob("*.pdf")):
            try:
                doc = ingest_pdf(session, pdf, pdf.name, category=CATEGORIES.get(pdf.stem))
                print(f"loaded {pdf.name}: {doc.num_pages} pages, {len(doc.chunks)} chunks")
            except IngestError as e:
                print(f"skipped {pdf.name}: {e}")


if __name__ == "__main__":
    main()
