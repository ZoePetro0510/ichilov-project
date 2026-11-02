"""Upload pipeline against the real database (test documents are cleaned up)."""

import pytest
from reportlab.pdfgen import canvas

from app.ingestion.pipeline import IngestError, ingest_pdf
from app.models import Document
from scripts.fonts import find_hebrew_font
from tests.test_pdf_utils import PROTOCOL, make_pdf


@pytest.fixture
def cleanup(session):
    created: list[str] = []
    yield created
    for name in created:
        doc = session.query(Document).filter_by(filename=name).first()
        if doc:
            session.delete(doc)
    session.commit()


def test_ingest_stores_chunks_with_embeddings(session, cleanup, tmp_path):
    if not find_hebrew_font():
        pytest.skip("no Hebrew font")
    pdf = make_pdf(tmp_path / "t.pdf", PROTOCOL)
    cleanup.append("test_ingest.pdf")
    doc = ingest_pdf(session, pdf, "test_ingest.pdf", category="בדיקה")
    assert doc.num_pages == 1 and len(doc.chunks) >= 1
    assert len(doc.chunks[0].embedding) == 384
    assert doc.chunks[0].page == 1


def test_duplicate_filename_rejected(session):
    with pytest.raises(IngestError, match="already"):
        ingest_pdf(session, "unused.pdf", "hygiene_hands.pdf")


def test_pdf_without_text_rejected(session, tmp_path):
    blank = tmp_path / "blank.pdf"
    c = canvas.Canvas(str(blank))
    c.showPage()
    c.save()
    with pytest.raises(IngestError, match="EMPTY"):
        ingest_pdf(session, blank, "blank_test.pdf")


def test_corrupt_file_rejected(session, tmp_path):
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"not a pdf")
    with pytest.raises(IngestError, match="Could not read"):
        ingest_pdf(session, bad, "bad_test.pdf")
