"""PDF text extraction with a Hebrew sanity check.

Many Israeli PDFs store Hebrew in *visual* order (as drawn on screen) instead of
*logical* order (as typed). Extracted text then comes out reversed:
"להונ" instead of "נוהל". Embeddings of reversed text are useless, so we detect
and fix it before anything is stored.

Detection idea: Hebrew final letters (ך ם ן ף ץ) only ever appear at the END of
a word. If most of them show up at the START of words, the text is reversed.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

HEBREW_LETTER = re.compile(r"[א-ת]")
FINAL_LETTERS = set("ךםןףץ")
WORD = re.compile(r"[א-ת]+")
# Left-to-right runs (numbers, English, dates like 12/2024) that must keep their
# own direction when a reversed line is flipped back. Starts and ends with an
# alphanumeric so the pattern behaves the same on reversed text.
LTR_RUN = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9.,:/%\-]*[A-Za-z0-9])?")

MIN_EVIDENCE = 5  # final letters needed before we trust the verdict


# ---------- detection ----------


def hebrew_ratio(text: str) -> float:
    """Share of letters in the text that are Hebrew (0..1)."""
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    return sum(1 for c in letters if HEBREW_LETTER.match(c)) / len(letters)


def final_letter_counts(text: str) -> tuple[int, int]:
    """(finals at word end, finals at word start) over all Hebrew words."""
    at_end = at_start = 0
    for word in WORD.findall(text):
        if len(word) < 2:
            continue
        if word[-1] in FINAL_LETTERS:
            at_end += 1
        if word[0] in FINAL_LETTERS:
            at_start += 1
    return at_end, at_start


def is_reversed(text: str) -> bool | None:
    """True = reversed, False = fine, None = not enough Hebrew to tell."""
    at_end, at_start = final_letter_counts(text)
    if at_end + at_start < MIN_EVIDENCE:
        return None
    return at_start > at_end


# ---------- fixing ----------


def fix_reversed_line(line: str) -> str:
    """Flip a visual-order line back to logical order, keeping numbers/English intact."""
    flipped = line[::-1]
    return LTR_RUN.sub(lambda m: m.group(0)[::-1], flipped)


def fix_reversed_text(text: str) -> str:
    return "\n".join(fix_reversed_line(line) for line in text.split("\n"))


def normalize(text: str) -> str:
    """NFKC turns Hebrew presentation forms (e.g. U+FB2A) into normal letters;
    then tidy whitespace."""
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[ \t ]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ---------- extraction ----------


def extract_pages(path: str | Path, method: str = "pdfplumber") -> list[str]:
    """Raw text per page.

    method="pdfplumber" (default): returns characters in stored order, which our
        fixer handles correctly for both logical- and visual-order PDFs.
    method="pymupdf": faster, but applies its own bidi reordering that misplaces
        numbers, English and punctuation in Hebrew lines (see tests). Avoid for Hebrew.
    """
    if method == "pymupdf":
        import pymupdf

        with pymupdf.open(path) as doc:
            return [page.get_text("text") for page in doc]
    if method == "pdfplumber":
        import pdfplumber

        with pdfplumber.open(path) as pdf:
            return [page.extract_text() or "" for page in pdf.pages]
    raise ValueError(f"Unknown method: {method}")


@dataclass
class ExtractionReport:
    path: str
    method: str
    num_pages: int
    num_chars: int
    hebrew_ratio: float
    finals_at_end: int
    finals_at_start: int
    reversed_detected: bool | None
    pages: list[str] = field(repr=False)  # cleaned text, ready for chunking

    @property
    def verdict(self) -> str:
        if self.num_chars < 50:
            return "EMPTY - probably a scanned PDF, needs OCR"
        if self.hebrew_ratio < 0.2:
            return "LITTLE HEBREW - check the file"
        if self.reversed_detected is None:
            return "UNSURE - too little Hebrew to judge"
        return "FIXED (was reversed)" if self.reversed_detected else "OK"


def extract_clean(path: str | Path, method: str = "pdfplumber") -> ExtractionReport:
    """Extract, detect reversal on the whole document, fix if needed, normalize."""
    raw_pages = [normalize(p) for p in extract_pages(path, method)]
    full = "\n".join(raw_pages)
    reversed_flag = is_reversed(full)
    at_end, at_start = final_letter_counts(full)

    pages = [fix_reversed_text(p) for p in raw_pages] if reversed_flag else raw_pages

    return ExtractionReport(
        path=str(path),
        method=method,
        num_pages=len(pages),
        num_chars=len(full),
        hebrew_ratio=round(hebrew_ratio(full), 2),
        finals_at_end=at_end,
        finals_at_start=at_start,
        reversed_detected=reversed_flag,
        pages=pages,
    )
