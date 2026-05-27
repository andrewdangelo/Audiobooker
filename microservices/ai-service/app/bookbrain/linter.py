"""
BookBrainLinter
===============
A periodic health-check pass over a book's wiki that identifies and fills gaps
in wiki entries — the Karpathy "linting" step.

Primary purpose: the Audiobooker book knowledge base product.
  After chunk ingestion is complete, run this once (or periodically) so that
  every character, theme, and plot entry is fully enriched for reader-facing
  consumption and for the SpeakerChunker's scene attribution prompts.

Secondary purpose: chunking quality.
  A fully enriched character entry (speech patterns, personality traits,
  relationships) gives the scene attribution LLM far better signal than
  a bare name list — especially for ambiguous dialogue on 900-page books.

What it checks
--------------
  character entries:
    - speech_patterns  — how the character speaks (register, dialect, catchphrases)
    - personality_traits — core traits (deceptive, warm, driven, fearful, …)
    - relationships    — key dynamics with other characters
    - narrative_arc    — how they change across the story

  plot entries:
    - characters_involved — which characters appear in this plot point
    - consequence         — what changes as a result

  theme entries:
    - textual_evidence — at least one concrete example from the text

  All other entry types are passed through unchecked for now.

How to run
----------
  As a background job (call from ARQ worker or a cron endpoint):
      linter = BookBrainLinter(store=app.state.bookbrain_agent.store)
      report = await linter.lint(book_id)

  As an HTTP endpoint (registered in bookbrain.py router):
      POST /bookbrain/{book_id}/lint → LintReport
"""
from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime
from typing import List

from app.bookbrain.schemas import EntryType, LintGap, LintReport, WikiEntry, WikiEntryPublic
from app.bookbrain.wiki_store import BookBrainWikiStore
from app.services.ai_emb_service import AIEmbeddingService
from app.services.ai_model_factory import ModelProvider
from app.services.ai_text_service import AITextService

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Gap detection — keyword heuristics per entry type
# ---------------------------------------------------------------------------

_CHARACTER_FIELDS: dict[str, list[str]] = {
    "speech_patterns":   ["speech", "speaks", "pattern", "dialect", "tone", "says", "voice", "register", "catchphrase"],
    "personality_traits":["personality", "trait", "deceptive", "honest", "warm", "cold", "driven", "fearful", "arrogant", "humble", "cunning", "loyal"],
    "relationships":     ["relationship", "ally", "enemy", "friend", "rival", "mentor", "trusts", "distrusts", "loves", "hates"],
    "narrative_arc":     ["arc", "change", "growth", "transforms", "evolves", "redeems", "deteriorates", "journey"],
}

_PLOT_FIELDS: dict[str, list[str]] = {
    "characters_involved": ["involves", "character", "who", "protagonist", "antagonist"],
    "consequence":         ["result", "consequence", "leads to", "causes", "aftermath", "effect"],
}

_THEME_FIELDS: dict[str, list[str]] = {
    "textual_evidence": ["for example", "illustrated by", "seen when", "demonstrated", "exemplified", "such as"],
}


def _find_missing_fields(entry: WikiEntryPublic) -> list[str]:
    """
    Returns a list of field names that appear absent from the entry's content.
    Uses keyword presence as a fast heuristic — no LLM call needed for detection.
    """
    content_lower = entry.content.lower()

    field_map = {
        EntryType.CHARACTER:   _CHARACTER_FIELDS,
        EntryType.PLOT:        _PLOT_FIELDS,
        EntryType.THEME:       _THEME_FIELDS,
    }.get(EntryType(entry.entry_type))

    if not field_map:
        return []

    missing = []
    for field, keywords in field_map.items():
        if not any(kw in content_lower for kw in keywords):
            missing.append(field)
    return missing


# ---------------------------------------------------------------------------
# Enrichment prompts
# ---------------------------------------------------------------------------

_CHARACTER_SYSTEM = """\
You are a literary analyst enriching a character profile for a book knowledge base.
You will receive an existing character wiki entry and the specific fields that are missing.

Fill in ONLY the missing fields — do not restate or paraphrase existing content.
Integrate the new content naturally into the existing markdown.

Missing fields to add:
  speech_patterns  — HOW this character speaks: register (formal/casual), verbosity,
                     dialect, typical phrasing, punctuation habits, catchphrases.
  personality_traits — Core traits that drive behaviour (honest/deceptive, warm/cold,
                       dominant/submissive, impulsive/calculated, etc.)
  relationships    — Key dynamics with other characters (ally, antagonist, mentor,
                     rival, family). Include the emotional quality of each bond.
  narrative_arc    — How the character's situation or inner state changes across the
                     story. What do they want? What do they get?

Respond ONLY with JSON — no preamble, no markdown fences:
{
  "missing_fields": ["field1", "field2"],
  "enriched_content": "<complete updated markdown — existing content + new sections>"
}
"""

_PLOT_SYSTEM = """\
You are a literary analyst enriching a plot entry for a book knowledge base.
Fill in ONLY what is listed as missing. Do not restate existing content.

Missing fields:
  characters_involved — which named characters appear in or drive this plot point
  consequence         — what changes in the story as a direct result of this event

Respond ONLY with JSON:
{
  "missing_fields": ["field1"],
  "enriched_content": "<complete updated markdown>"
}
"""

_THEME_SYSTEM = """\
You are a literary analyst enriching a theme entry for a book knowledge base.
Fill in ONLY what is listed as missing. Do not restate existing content.

Missing fields:
  textual_evidence — at least one concrete example from the text that illustrates this theme

Respond ONLY with JSON:
{
  "missing_fields": ["field1"],
  "enriched_content": "<complete updated markdown>"
}
"""

_SYSTEM_BY_TYPE: dict[EntryType, str] = {
    EntryType.CHARACTER: _CHARACTER_SYSTEM,
    EntryType.PLOT:      _PLOT_SYSTEM,
    EntryType.THEME:     _THEME_SYSTEM,
}


# ---------------------------------------------------------------------------
# Linter
# ---------------------------------------------------------------------------

class BookBrainLinter:
    """
    Runs a targeted enrichment pass over a book's wiki.

    Designed to run as a background job — not latency-critical.
    For a 900-page book: ~30-50 character entries → ~30-50 LLM calls.
    Each call is focused and fast (fill in 1-2 missing fields, not full generation).
    """

    def __init__(
        self,
        store: BookBrainWikiStore,
        text_provider: ModelProvider = ModelProvider.CF,
        text_preset: str = "chat-knowledge",
    ):
        self.store = store
        self._text_provider = text_provider
        self._text_preset = text_preset

    async def lint(self, book_id: str) -> LintReport:
        """
        Run a full lint pass over all entries in the book's wiki.
        Returns a LintReport summarising what was checked and what was enriched.
        """
        t0 = time.monotonic()
        all_entries = await self.store.get_entries(book_id)
        gaps: list[LintGap] = []
        enriched_count = 0

        for entry in all_entries:
            missing = _find_missing_fields(entry)
            if not missing:
                continue

            was_enriched = await self._enrich_entry(book_id, entry, missing)
            gaps.append(LintGap(
                entry_id=entry.entry_id,
                entry_type=EntryType(entry.entry_type),
                title=entry.title,
                missing_fields=missing,
                was_enriched=was_enriched,
            ))
            if was_enriched:
                enriched_count += 1

        duration = time.monotonic() - t0
        logger.info(
            "BookBrain lint [book=%s]: checked=%d gaps=%d enriched=%d duration=%.1fs",
            book_id, len(all_entries), len(gaps), enriched_count, duration,
        )
        return LintReport(
            book_id=book_id,
            entries_checked=len(all_entries),
            entries_enriched=enriched_count,
            gaps=gaps,
            duration_seconds=round(duration, 2),
        )

    async def _enrich_entry(
        self,
        book_id: str,
        entry: WikiEntryPublic,
        missing_fields: list[str],
    ) -> bool:
        """
        Call the LLM to fill in missing fields for one entry.
        Returns True if the entry was successfully enriched and upserted.
        """
        system_prompt = _SYSTEM_BY_TYPE.get(EntryType(entry.entry_type))
        if not system_prompt:
            return False

        missing_str = ", ".join(missing_fields)
        user_message = (
            f"Character: **{entry.title}**\n"
            f"Missing fields: {missing_str}\n\n"
            f"Existing content:\n\n{entry.content}"
        )

        try:
            raw = await AITextService.chat_json(
                prompt_messages=[
                    ["system", system_prompt],
                    ["user", user_message],
                ],
                provider=self._text_provider,
                preset=self._text_preset,
            )
        except Exception as e:
            logger.warning("Lint enrichment failed for '%s': %s", entry.title, e)
            return False

        enriched_content = (raw.get("enriched_content") or "").strip()
        if not enriched_content:
            logger.warning("Lint: empty enriched_content for '%s'", entry.title)
            return False

        # Re-embed and upsert the enriched entry
        emb = await AIEmbeddingService.generate_embedding(
            text=f"{entry.title}: {enriched_content}",
            provider=ModelProvider.CF,
            preset="embedding-768",
        )

        updated = WikiEntry(
            entry_id=entry.entry_id,
            book_id=book_id,
            entry_type=EntryType(entry.entry_type),
            title=entry.title,
            content=enriched_content,
            embedding=emb,
            source_chunk_indices=entry.source_chunk_indices,
            updated_at=datetime.utcnow(),
        )
        await self.store.upsert_entry(updated)
        logger.info("Lint enriched '%s' (%s) — filled: %s", entry.title, entry.entry_type, missing_str)
        return True
