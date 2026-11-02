from app.ingestion.chunking import chunk_document, chunk_page


def test_short_page_is_single_chunk():
    assert chunk_page("משפט קצר. עוד משפט.") == ["משפט קצר. עוד משפט."]


def test_long_page_respects_max_and_overlaps():
    text = " ".join(f"זהו משפט מספר {i} בנוהל." for i in range(80))
    chunks = chunk_page(text, max_chars=300, overlap_chars=60)
    assert len(chunks) > 3
    assert all(len(c) <= 300 for c in chunks)
    # consecutive chunks share some text
    assert chunks[1].split(".")[0] in chunks[0]


def test_huge_unbroken_text_is_cut():
    chunks = chunk_page("א" * 2000, max_chars=500)
    assert all(len(c) <= 500 for c in chunks) and len(chunks) == 4


def test_pages_are_tracked_and_indexed_globally():
    out = chunk_document(["עמוד ראשון.", "", "עמוד שלישי."])
    assert [(c.page, c.chunk_index) for c in out] == [(1, 0), (3, 1)]
