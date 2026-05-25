"""SpeakerChunker structural helpers (stitch + smart split) without LLM calls."""

import pytest

from app.services.llm_speaker_chunker import SpeakerChunker, TextUnit


@pytest.fixture
def chunker() -> SpeakerChunker:
    return SpeakerChunker()


def test_stitch_chunks_builds_char_map(chunker: SpeakerChunker):
    chunks = [
        {"chunk_id": 1, "text": "Hello"},
        {"chunk_id": 2, "text": "World"},
    ]
    full_text, char_map = chunker._stitch_chunks(chunks)
    assert full_text == "Hello\nWorld"
    assert len(char_map) == len(full_text)
    assert char_map[0] == 1
    assert char_map[-1] == 2
    assert char_map[5] is None  # newline separator


def test_smart_split_quote_and_narration(chunker: SpeakerChunker):
    # Single paragraph: narration then curly-quote dialogue
    body = 'She looked up. \u201cHello there.\u201d Then she left.'
    char_map = [None] * len(body)
    units = chunker._smart_split(body, char_map)
    quotes = [u for u in units if u.is_quote]
    narr = [u for u in units if not u.is_quote]
    assert quotes, "expected at least one quote unit"
    assert narr, "expected narration units"
    assert any("\u201c" in u.text or '"' in u.text for u in quotes)


def test_looks_like_job_id(chunker: SpeakerChunker):
    assert chunker._looks_like_job_id("job_abc123") is True
    assert chunker._looks_like_job_id("uploads_user/file.pdf") is True
    assert chunker._looks_like_job_id("The Great Novel") is False
