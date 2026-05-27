"""
Unit tests for BookGenerationService concurrency behaviour.

Tests the semaphore cap without hitting any real external services.
All of _call_tts, _r2_upload, Redis, and ai-service are mocked.

Run from tts-infrastructure root:
    pytest tests/unit/test_book_generation_concurrency.py -v
"""

import asyncio
import json
from typing import Dict, List, Optional
from unittest.mock import AsyncMock, patch

import pytest

from app.services.book_generation_service import (
    TTS_CONCURRENCY,
    _process_chunk,
    run_book_generation,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_line(idx: int, speaker: str = "Narrator") -> Dict:
    return {
        "speaker": speaker,
        "text": f"This is line {idx}.",
        "emotion": "narrative, calm",
        "emotion_strength": 0.5,
    }


def _make_script(n: int) -> Dict:
    return {
        "characters": [{"name": "Narrator", "gender": "NEUTRAL"}],
        "script": [_make_line(i) for i in range(n)],
    }


# ---------------------------------------------------------------------------
# Test 1 — semaphore caps concurrency at TTS_CONCURRENCY
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_semaphore_caps_concurrency():
    """
    Fires NUM_CHUNKS chunk tasks simultaneously and asserts that no more
    than TTS_CONCURRENCY were ever in _call_tts at the same time.

    Approach:
      - Replace _call_tts with a fake that records the high-water mark of
        concurrent executions using a shared counter.
      - Each fake call holds for a short delay so overlap is observable.
      - After all tasks complete, assert high_water <= TTS_CONCURRENCY.
    """
    NUM_CHUNKS = 20  # well above TTS_CONCURRENCY so the cap is exercised

    active = 0
    high_water = 0
    lock = asyncio.Lock()

    async def fake_tts(voice_bytes, text, emotion, emotion_strength):
        nonlocal active, high_water
        async with lock:
            active += 1
            high_water = max(high_water, active)
        await asyncio.sleep(0.05)  # simulate inference time
        async with lock:
            active -= 1
        return b"fake_wav_bytes"

    async def fake_r2_upload(session, key, data, content_type="audio/wav"):
        pass

    session = None  # not used since r2 is mocked
    voice_cache = {"voice-001": b"fake_voice_bytes"}
    assignment_map = {"Narrator": "voice-001"}
    fallback_voice_id = "voice-001"
    results: List[Optional[str]] = [None] * NUM_CHUNKS
    counter = {"completed": 0, "failed": 0}
    semaphore = asyncio.Semaphore(TTS_CONCURRENCY)

    with patch("app.services.book_generation_service._call_tts", side_effect=fake_tts), \
         patch("app.services.book_generation_service._r2_upload", side_effect=fake_r2_upload):

        tasks = [
            _process_chunk(
                idx=idx,
                line=_make_line(idx),
                session=session,
                voice_cache=voice_cache,
                assignment_map=assignment_map,
                fallback_voice_id=fallback_voice_id,
                book_id="test-book",
                job_id="test-job",
                semaphore=semaphore,
                results=results,
                counter=counter,
            )
            for idx in range(NUM_CHUNKS)
        ]

        await asyncio.gather(*tasks)

    assert high_water <= TTS_CONCURRENCY, (
        f"Concurrency exceeded TTS_CONCURRENCY={TTS_CONCURRENCY}: "
        f"high water mark was {high_water}"
    )
    assert counter["completed"] == NUM_CHUNKS
    assert counter["failed"] == 0
    assert all(r == f"audiobook_chunks/test-book/{i}.wav" for i, r in enumerate(results))


# ---------------------------------------------------------------------------
# Test 2 — results written to correct index regardless of completion order
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_results_written_by_index():
    """
    Chunks complete in reverse order (last chunk finishes first due to
    varying sleep times). Assert that results[i] always contains the
    key for chunk i — not whatever finished last.
    """
    NUM_CHUNKS = 10

    async def fake_tts_variable_delay(voice_bytes, text, emotion, emotion_strength):
        # Extract idx from text "This is line {idx}."
        idx = int(text.split("line ")[1].rstrip("."))
        # Later chunks sleep less so they finish first
        await asyncio.sleep((NUM_CHUNKS - idx) * 0.01)
        return b"fake_wav_bytes"

    async def fake_r2_upload(session, key, data, content_type="audio/wav"):
        pass

    results: List[Optional[str]] = [None] * NUM_CHUNKS
    counter = {"completed": 0, "failed": 0}
    semaphore = asyncio.Semaphore(NUM_CHUNKS)  # no cap — all run freely

    with patch("app.services.book_generation_service._call_tts", side_effect=fake_tts_variable_delay), \
         patch("app.services.book_generation_service._r2_upload", side_effect=fake_r2_upload):

        tasks = [
            _process_chunk(
                idx=idx,
                line=_make_line(idx),
                session=None,
                voice_cache={"voice-001": b"bytes"},
                assignment_map={"Narrator": "voice-001"},
                fallback_voice_id="voice-001",
                book_id="test-book",
                job_id="test-job",
                semaphore=semaphore,
                results=results,
                counter=counter,
            )
            for idx in range(NUM_CHUNKS)
        ]

        await asyncio.gather(*tasks)

    for i in range(NUM_CHUNKS):
        assert results[i] == f"audiobook_chunks/test-book/{i}.wav", (
            f"results[{i}] = {results[i]} — expected key for chunk {i}"
        )


# ---------------------------------------------------------------------------
# Test 3 — failed chunks don't poison other chunks
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_failed_chunks_isolated():
    """
    Every other chunk raises an exception in _call_tts.
    Assert that the successful chunks still complete and failed chunks
    leave results[idx] = None without affecting neighbours.
    """
    NUM_CHUNKS = 10

    async def fake_tts_alternating(voice_bytes, text, emotion, emotion_strength):
        idx = int(text.split("line ")[1].rstrip("."))
        if idx % 2 == 0:
            raise RuntimeError(f"Simulated TTS failure for chunk {idx}")
        return b"fake_wav_bytes"

    async def fake_r2_upload(session, key, data, content_type="audio/wav"):
        pass

    results: List[Optional[str]] = [None] * NUM_CHUNKS
    counter = {"completed": 0, "failed": 0}
    semaphore = asyncio.Semaphore(TTS_CONCURRENCY)

    with patch("app.services.book_generation_service._call_tts", side_effect=fake_tts_alternating), \
         patch("app.services.book_generation_service._r2_upload", side_effect=fake_r2_upload):

        tasks = [
            _process_chunk(
                idx=idx,
                line=_make_line(idx),
                session=None,
                voice_cache={"voice-001": b"bytes"},
                assignment_map={"Narrator": "voice-001"},
                fallback_voice_id="voice-001",
                book_id="test-book",
                job_id="test-job",
                semaphore=semaphore,
                results=results,
                counter=counter,
            )
            for idx in range(NUM_CHUNKS)
        ]

        await asyncio.gather(*tasks)

    assert counter["completed"] == 5   # odd indices
    assert counter["failed"] == 5      # even indices

    for i in range(NUM_CHUNKS):
        if i % 2 == 0:
            assert results[i] is None, f"results[{i}] should be None (failed chunk)"
        else:
            assert results[i] == f"audiobook_chunks/test-book/{i}.wav"


# ---------------------------------------------------------------------------
# Test 4 — empty text lines are skipped, not counted as failures
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_empty_lines_skipped():
    """
    Lines with empty text should be silently skipped — results[idx] = None
    but counter["failed"] should NOT increment.
    """
    lines = [
        {"speaker": "Narrator", "text": "Real text here.", "emotion": "calm", "emotion_strength": 0.5},
        {"speaker": "Narrator", "text": "   ", "emotion": "calm", "emotion_strength": 0.5},  # empty
        {"speaker": "Narrator", "text": "More real text.", "emotion": "calm", "emotion_strength": 0.5},
    ]

    async def fake_tts(voice_bytes, text, emotion, emotion_strength):
        return b"fake_wav_bytes"

    async def fake_r2_upload(session, key, data, content_type="audio/wav"):
        pass

    results: List[Optional[str]] = [None] * len(lines)
    counter = {"completed": 0, "failed": 0}
    semaphore = asyncio.Semaphore(TTS_CONCURRENCY)

    with patch("app.services.book_generation_service._call_tts", side_effect=fake_tts), \
         patch("app.services.book_generation_service._r2_upload", side_effect=fake_r2_upload):

        tasks = [
            _process_chunk(
                idx=idx,
                line=line,
                session=None,
                voice_cache={"voice-001": b"bytes"},
                assignment_map={"Narrator": "voice-001"},
                fallback_voice_id="voice-001",
                book_id="test-book",
                job_id="test-job",
                semaphore=semaphore,
                results=results,
                counter=counter,
            )
            for idx, line in enumerate(lines)
        ]

        await asyncio.gather(*tasks)

    assert counter["completed"] == 2
    assert counter["failed"] == 0      # empty line is not a failure
    assert results[0] is not None
    assert results[1] is None          # skipped
    assert results[2] is not None