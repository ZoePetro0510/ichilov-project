"""Find a TTF font with Hebrew glyphs on this machine (used to generate sample PDFs)."""

from pathlib import Path

CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",  # macOS
    "C:/Windows/Fonts/arial.ttf",  # Windows
]


def find_hebrew_font() -> str | None:
    return next((f for f in CANDIDATES if Path(f).exists()), None)
