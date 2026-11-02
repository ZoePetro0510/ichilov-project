"""Split page text into overlapping chunks that never cross a page boundary,
so every chunk can be cited as (document, page)."""

from __future__ import annotations

import re
from dataclasses import dataclass

SENTENCE_END = re.compile(r"(?<=[.!?:;])\s+|\n+")


@dataclass
class ChunkData:
    page: int  # 1-based
    chunk_index: int  # running index within the document
    text: str


def _split_units(text: str, max_chars: int) -> list[str]:
    """Sentences/lines; any unit longer than max_chars is cut on spaces."""
    units: list[str] = []
    for part in SENTENCE_END.split(text):
        part = part.strip()
        if not part:
            continue
        while len(part) > max_chars:
            cut = part.rfind(" ", 0, max_chars)
            cut = cut if cut > 0 else max_chars
            units.append(part[:cut].strip())
            part = part[cut:].strip()
        if part:
            units.append(part)
    return units


def chunk_page(text: str, max_chars: int = 800, overlap_chars: int = 150) -> list[str]:
    units = _split_units(text, max_chars)
    chunks: list[str] = []
    current: list[str] = []
    size = 0
    for unit in units:
        if current and size + len(unit) + 1 > max_chars:
            chunks.append(" ".join(current))
            # carry trailing units as overlap
            tail: list[str] = []
            tail_size = 0
            for u in reversed(current):
                if tail_size + len(u) > overlap_chars:
                    break
                tail.insert(0, u)
                tail_size += len(u) + 1
            current, size = tail, tail_size
        current.append(unit)
        size += len(unit) + 1
    if current:
        chunks.append(" ".join(current))
    return chunks


def chunk_document(
    pages: list[str], max_chars: int = 800, overlap_chars: int = 150
) -> list[ChunkData]:
    result: list[ChunkData] = []
    for page_no, text in enumerate(pages, start=1):
        for piece in chunk_page(text, max_chars, overlap_chars):
            result.append(ChunkData(page_no, len(result), piece))
    return result
