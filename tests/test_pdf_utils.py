"""Tests for Hebrew extraction.

We generate two PDFs with the same synthetic protocol text:
  - logical order (how a well-made PDF stores Hebrew)
  - visual order  (how many government PDFs store it -> extracts reversed)
Both must come out of extract_clean() as the original, readable text.
"""

from pathlib import Path

import pytest

from app.ingestion.pdf_utils import (
    extract_clean,
    fix_reversed_line,
    is_reversed,
)
from scripts.fonts import find_hebrew_font

FONT = find_hebrew_font()

PROTOCOL = [
    "נוהל דיווח על אירוע בטיחות מספר 12/2024",
    "כל עובד שזיהה אירוע חריג ידווח למנהל המחלקה תוך 24 שעות.",
    "הדיווח יתבצע בטופס המקוון במערכת EMR של בית החולים.",
    "מנהל המחלקה יעביר את הדיווח לוועדת הבטיחות בתוך שלושה ימים.",
    "יש לתעד את שם המטופל, מיקום האירוע והצעדים שננקטו מיד.",
]


def make_pdf(path: Path, lines: list[str]) -> Path:
    reportlab = pytest.importorskip("reportlab")  # noqa: F841
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas

    if not FONT:
        pytest.skip("No Hebrew-capable TTF font found")
    pdfmetrics.registerFont(TTFont("DejaVu", FONT))
    c = canvas.Canvas(str(path))
    c.setFont("DejaVu", 12)
    y = 800
    for line in lines:
        c.drawString(40, y, line)
        y -= 24
    c.save()
    return path


@pytest.fixture
def logical_pdf(tmp_path):
    return make_pdf(tmp_path / "logical.pdf", PROTOCOL)


@pytest.fixture
def visual_pdf(tmp_path):
    bidi = pytest.importorskip("bidi")  # noqa: F841
    from bidi import get_display

    return make_pdf(tmp_path / "visual.pdf", [get_display(line) for line in PROTOCOL])


# ---- unit tests ----


def test_fix_keeps_numbers_and_english():
    visual = "EMR תכרעמב 12/2024 רפסמ"
    assert fix_reversed_line(visual) == "רפסמ"[::-1] + " 12/2024 " + "תכרעמב"[::-1] + " EMR"


def test_detects_reversed_text():
    good = " ".join(PROTOCOL)
    assert is_reversed(good) is False
    assert is_reversed(good[::-1]) is True


def test_too_little_hebrew_is_unsure():
    assert is_reversed("Hello world 2024") is None


# ---- end-to-end on real PDF files ----


def test_logical_pdf_extracts_as_is(logical_pdf):
    r = extract_clean(logical_pdf)  # default method: pdfplumber
    assert r.reversed_detected is False
    for line in PROTOCOL:
        assert line in r.pages[0]


def test_visual_pdf_is_detected_and_fixed(visual_pdf):
    r = extract_clean(visual_pdf)
    assert r.reversed_detected is True
    assert r.verdict == "FIXED (was reversed)"
    for line in PROTOCOL:
        assert line in r.pages[0]


@pytest.mark.xfail(
    strict=True,
    reason="Known issue: PyMuPDF's own bidi reordering moves numbers, English "
    "and punctuation to the wrong side of Hebrew lines. This is why the app "
    "uses pdfplumber. If this test starts passing, PyMuPDF fixed it.",
)
def test_pymupdf_misplaces_numbers_in_hebrew(visual_pdf):
    r = extract_clean(visual_pdf, method="pymupdf")
    for line in PROTOCOL:
        assert line in r.pages[0]
