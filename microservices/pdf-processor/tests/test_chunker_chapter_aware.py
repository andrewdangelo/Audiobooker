"""Tests for chapter-scoped chunking (no cross-chapter overlap in chunk text)."""

import pytest

from app.utils.chunker import TextChunker


@pytest.fixture
def chunker() -> TextChunker:
    return TextChunker()


@pytest.mark.asyncio
async def test_chunk_by_chapters_assigns_ids_and_metadata(chunker: TextChunker):
    chapters = [
        {
            "chapter_number": 1,
            "title": "Alpha",
            "text": "Sentence one. " * 20,
            "start_page": 1,
            "end_page": 1,
        },
        {
            "chapter_number": 2,
            "title": "Beta",
            "text": "Other chapter. " * 20,
            "start_page": 2,
            "end_page": 2,
        },
    ]
    chunks = await chunker.chunk_by_chapters(
        chapters=chapters,
        chunk_size=80,
        overlap=10,
        page_map=None,
    )
    assert len(chunks) >= 2
    ids = [c["chunk_id"] for c in chunks]
    assert ids == sorted(set(ids)), "chunk_id must be unique and monotonic"
    ch1 = [c for c in chunks if c.get("chapter_id") == 1]
    ch2 = [c for c in chunks if c.get("chapter_id") == 2]
    assert ch1 and ch2
    assert all(c.get("chapter_title") == "Alpha" for c in ch1)
    assert all(c.get("chapter_title") == "Beta" for c in ch2)
    joined1 = "".join(c["text"] for c in ch1)
    joined2 = "".join(c["text"] for c in ch2)
    assert "Other chapter" in joined2
    assert "Sentence one" in joined1


@pytest.mark.asyncio
async def test_chunk_text_splits_long_input(chunker: TextChunker):
    text = "Sentence here. " * 120
    chunks = await chunker.chunk_text(text=text, chunk_size=100, overlap=15)
    assert len(chunks) >= 2
    joined = "".join(c["text"] for c in chunks)
    assert "Sentence here" in joined
