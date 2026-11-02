"""Day 1 check: does Hebrew come out of your PDFs readable?

Usage:
    python -m scripts.check_pdf_hebrew                 # all PDFs in data/raw
    python -m scripts.check_pdf_hebrew file1.pdf ...   # specific files

For each file it tries PyMuPDF and pdfplumber, prints a verdict and the first
lines of cleaned text so you can eyeball them. Read the sample: if the Hebrew
looks right, you're good to go.
"""

import sys
from pathlib import Path

from app.ingestion.pdf_utils import extract_clean

METHODS = ("pdfplumber", "pymupdf")  # pdfplumber is the one the app uses


def first_lines(text: str, n: int = 3, width: int = 90) -> str:
    lines = [ln for ln in text.splitlines() if ln.strip()][:n]
    return "\n".join("      " + ln[:width] for ln in lines)


def main(paths: list[str]) -> None:
    files = [Path(p) for p in paths] or sorted(Path("data/raw").glob("*.pdf"))
    if not files:
        print("No PDFs found. Put some in data/raw/ or pass paths as arguments.")
        return

    for f in files:
        print(f"\n=== {f.name} ===")
        for method in METHODS:
            try:
                r = extract_clean(f, method)
            except Exception as e:  # keep going on a broken file
                print(f"  [{method}] ERROR: {e}")
                continue
            print(
                f"  [{method}] pages={r.num_pages} chars={r.num_chars} "
                f"hebrew={r.hebrew_ratio:.0%} finals end/start="
                f"{r.finals_at_end}/{r.finals_at_start} -> {r.verdict}"
            )
            print(first_lines(r.pages[0] if r.pages else ""))


if __name__ == "__main__":
    main(sys.argv[1:])
