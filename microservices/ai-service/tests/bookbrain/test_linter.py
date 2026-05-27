"""
Unit Tests — BookBrainLinter
=============================
Tests the linter in complete isolation:
  - No MongoDB (store is a lightweight in-memory stub)
  - No LLM calls (AITextService.chat_json is patched)
  - No embedding calls (AIEmbeddingService.generate_embedding is patched)
  - Runs in milliseconds, costs $0

What is tested
--------------
  _find_missing_fields     — gap detection heuristic (pure function)
  BookBrainLinter.lint     — orchestration: which entries get enrichment calls
  BookBrainLinter._enrich  — enrichment: correct content is upserted back
  Edge cases               — LLM returns empty content, LLM raises, all fields present
"""

import json
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

# conftest patches settings before any app.* import
from tests.conftest import FAKE_SETTINGS  # noqa: F401 — triggers the settings patch


# ---------------------------------------------------------------------------
# Helpers — build fake WikiEntryPublic objects
# ---------------------------------------------------------------------------

def _make_entry(
    entry_type: str,
    title: str,
    content: str,
    entry_id: str = "eid-001",
    source_chunk_indices: list | None = None,
) -> "WikiEntryPublic":
    from app.bookbrain.schemas import EntryType, WikiEntryPublic
    return WikiEntryPublic(
        entry_id=entry_id,
        book_id="test-book",
        entry_type=EntryType(entry_type),
        title=title,
        content=content,
        source_chunk_indices=source_chunk_indices or [0],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


# ---------------------------------------------------------------------------
# Minimal in-memory store stub
# ---------------------------------------------------------------------------

class _StubStore:
    """Replaces BookBrainWikiStore — holds entries in a list, records upserts."""

    def __init__(self, entries: list):
        self._entries = list(entries)
        self.upserted: list = []

    async def get_entries(self, book_id, entry_type=None):
        if entry_type:
            return [e for e in self._entries if e.entry_type == entry_type]
        return list(self._entries)

    async def upsert_entry(self, entry):
        self.upserted.append(entry)
        return entry.entry_id


# ---------------------------------------------------------------------------
# Tests — _find_missing_fields (pure function, no mocking needed)
# ---------------------------------------------------------------------------

class TestFindMissingFields:

    def test_character_all_missing(self):
        from app.bookbrain.linter import _find_missing_fields
        entry = _make_entry("character", "Kane", "A private detective in Drenholm.")
        missing = _find_missing_fields(entry)
        assert "speech_patterns"    in missing
        assert "personality_traits" in missing
        assert "relationships"      in missing
        assert "narrative_arc"      in missing

    def test_character_nothing_missing(self):
        from app.bookbrain.linter import _find_missing_fields
        content = (
            "Kane speaks in a terse, clipped pattern — short sentences, no pleasantries.\n"
            "His personality traits include honesty and calm under pressure.\n"
            "His relationships are few: Roz is his ally; Marcus is a client he distrusts.\n"
            "His narrative arc moves from cynical observer to reluctant protector."
        )
        entry = _make_entry("character", "Kane", content)
        assert _find_missing_fields(entry) == []

    def test_character_only_speech_missing(self):
        from app.bookbrain.linter import _find_missing_fields
        content = (
            "Kane's personality traits are honesty and restraint.\n"
            "His relationships include Roz (ally) and Marcus (client).\n"
            "His narrative arc leads him from isolation toward trust."
        )
        entry = _make_entry("character", "Kane", content)
        missing = _find_missing_fields(entry)
        assert "speech_patterns" in missing
        assert "personality_traits" not in missing
        assert "relationships" not in missing
        assert "narrative_arc" not in missing

    def test_plot_entry_missing_consequence(self):
        from app.bookbrain.linter import _find_missing_fields
        content = "The letter is stolen from Roz's shop. Kane, Marcus, and Roz are all involved."
        entry = _make_entry("plot", "The Theft", content)
        missing = _find_missing_fields(entry)
        assert "consequence" in missing
        assert "characters_involved" not in missing

    def test_theme_missing_evidence(self):
        from app.bookbrain.linter import _find_missing_fields
        content = "The theme of hidden truth runs throughout the novel."
        entry = _make_entry("theme", "Hidden Truth", content)
        missing = _find_missing_fields(entry)
        assert "textual_evidence" in missing

    def test_setting_not_checked(self):
        from app.bookbrain.linter import _find_missing_fields
        entry = _make_entry("setting", "Drenholm", "A grey industrial city by the sea.")
        assert _find_missing_fields(entry) == []

    def test_terminology_not_checked(self):
        from app.bookbrain.linter import _find_missing_fields
        entry = _make_entry("terminology", "Sedition", "The crime Marcus is charged with.")
        assert _find_missing_fields(entry) == []


# ---------------------------------------------------------------------------
# Tests — BookBrainLinter.lint (orchestration)
# ---------------------------------------------------------------------------

class TestLinterOrchestration:

    @pytest.mark.asyncio
    async def test_skips_entries_with_no_gaps(self):
        """Entries that are already complete never trigger an LLM call."""
        from app.bookbrain.linter import BookBrainLinter

        complete_content = (
            "Kane speaks tersely with no small talk.\n"
            "Personality traits: honest, restrained.\n"
            "Relationships: Roz (ally), Marcus (client).\n"
            "Narrative arc: from isolation toward reluctant trust."
        )
        store = _StubStore([_make_entry("character", "Kane", complete_content)])
        linter = BookBrainLinter(store=store)

        with patch("app.bookbrain.linter.AITextService.chat_json", new=AsyncMock()) as mock_llm:
            report = await linter.lint("test-book")

        mock_llm.assert_not_called()
        assert report.entries_checked == 1
        assert report.entries_enriched == 0
        assert report.gaps == []

    @pytest.mark.asyncio
    async def test_enriches_entry_with_gaps(self):
        """An entry missing speech_patterns triggers one LLM call and one upsert."""
        from app.bookbrain.linter import BookBrainLinter

        sparse_content = (
            "Kane has personality traits of honesty and restraint.\n"
            "His relationships include Roz as an ally.\n"
            "His narrative arc leads him toward trust."
        )
        store = _StubStore([_make_entry("character", "Kane", sparse_content)])
        linter = BookBrainLinter(store=store)

        enriched_response = {
            "missing_fields": ["speech_patterns"],
            "enriched_content": sparse_content + "\n\nKane speaks in short, clipped sentences.",
        }
        mock_emb = AsyncMock(return_value=[0.1] * 768)

        with patch("app.bookbrain.linter.AITextService.chat_json", new=AsyncMock(return_value=enriched_response)):
            with patch("app.bookbrain.linter.AIEmbeddingService.generate_embedding", new=mock_emb):
                report = await linter.lint("test-book")

        assert report.entries_enriched == 1
        assert len(report.gaps) == 1
        assert report.gaps[0].title == "Kane"
        assert "speech_patterns" in report.gaps[0].missing_fields
        assert report.gaps[0].was_enriched is True
        assert len(store.upserted) == 1
        assert "clipped sentences" in store.upserted[0].content

    @pytest.mark.asyncio
    async def test_multiple_entry_types_checked(self):
        """Character, plot, and theme entries are all evaluated; settings are skipped."""
        from app.bookbrain.linter import BookBrainLinter

        entries = [
            _make_entry("character", "Kane",      "A detective.", entry_id="e1"),
            _make_entry("plot",      "The Theft", "Someone stole the letter.", entry_id="e2"),
            _make_entry("theme",     "Deception", "Runs throughout.", entry_id="e3"),
            _make_entry("setting",   "Drenholm",  "A grey city.", entry_id="e4"),
        ]
        store = _StubStore(entries)
        linter = BookBrainLinter(store=store)

        enriched_response = {
            "missing_fields": ["speech_patterns"],
            "enriched_content": "Enriched content.",
        }
        mock_emb = AsyncMock(return_value=[0.0] * 768)

        with patch("app.bookbrain.linter.AITextService.chat_json", new=AsyncMock(return_value=enriched_response)):
            with patch("app.bookbrain.linter.AIEmbeddingService.generate_embedding", new=mock_emb):
                report = await linter.lint("test-book")

        assert report.entries_checked == 4
        # setting has no gaps by design — exactly 3 entries should have gaps
        gap_titles = {g.title for g in report.gaps}
        assert "Kane"      in gap_titles
        assert "The Theft" in gap_titles
        assert "Deception" in gap_titles
        assert "Drenholm"  not in gap_titles

    @pytest.mark.asyncio
    async def test_llm_failure_marks_not_enriched(self):
        """If the LLM call raises, the gap is recorded but was_enriched=False."""
        from app.bookbrain.linter import BookBrainLinter

        store = _StubStore([_make_entry("character", "Kane", "A detective.")])
        linter = BookBrainLinter(store=store)

        with patch("app.bookbrain.linter.AITextService.chat_json", new=AsyncMock(side_effect=RuntimeError("timeout"))):
            report = await linter.lint("test-book")

        assert report.entries_enriched == 0
        assert report.gaps[0].was_enriched is False
        assert len(store.upserted) == 0

    @pytest.mark.asyncio
    async def test_llm_empty_content_marks_not_enriched(self):
        """If the LLM returns empty enriched_content, was_enriched=False and no upsert."""
        from app.bookbrain.linter import BookBrainLinter

        store = _StubStore([_make_entry("character", "Kane", "A detective.")])
        linter = BookBrainLinter(store=store)

        with patch("app.bookbrain.linter.AITextService.chat_json", new=AsyncMock(return_value={"enriched_content": ""})):
            report = await linter.lint("test-book")

        assert report.entries_enriched == 0
        assert report.gaps[0].was_enriched is False
        assert len(store.upserted) == 0

    @pytest.mark.asyncio
    async def test_empty_wiki_returns_clean_report(self):
        """A book with no wiki entries produces a valid zero-count report."""
        from app.bookbrain.linter import BookBrainLinter

        store = _StubStore([])
        linter = BookBrainLinter(store=store)
        report = await linter.lint("test-book")

        assert report.entries_checked == 0
        assert report.entries_enriched == 0
        assert report.gaps == []
        assert report.duration_seconds >= 0

    @pytest.mark.asyncio
    async def test_report_duration_is_populated(self):
        """LintReport.duration_seconds is a non-negative float."""
        from app.bookbrain.linter import BookBrainLinter

        store = _StubStore([])
        linter = BookBrainLinter(store=store)
        report = await linter.lint("test-book")

        assert isinstance(report.duration_seconds, float)
        assert report.duration_seconds >= 0.0
