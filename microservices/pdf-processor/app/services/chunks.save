"""
LLM-based Speaker Tagging Service (Context-Aware Dialogue Tagger)

1. Generates a Book Primer (POV, Narrator Identity, Tense) to solve the Cold Start problem.
2. Stitches fragmented PDF chunks into a coherent stream.
3. Smart-splits text into atomic units preserving paragraph structure and multi-paragraph quotes.
4. Pre-tags narration units locally (no LLM call needed for ~50% of units).
5. Uses adaptive token-based batching (quote-only) to maximize LLM context utilization.
6. Hybrid parallel-serial processing: parallel chains with context sync at boundaries.
7. Reconstructs segments with 100% verbatim fidelity.

Key Features:
- Smart Splitting: Paragraph-aware, handles multi-paragraph quotes, merges orphan punctuation
- Local Narration Tagging: Narration units are pre-assigned to the narrator without LLM calls
- Adaptive Batching: Token-budget packing (~6000 tokens) on quote-only units
- Hybrid Parallelism: Chains of N batches run in parallel, context syncs at chain boundaries
- First Person Handling: Correctly attributes narration to protagonist (e.g., "Holden" not "Narrator")
"""
__author__ = "Andrew D'Angelo"

import json
import time
import re
import math
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable, Tuple

from openai import OpenAI
from app.core.logging_config import Logger
from app.core.config_settings import settings


# -----------------------------
# Configuration
# -----------------------------

DEFAULT_MODEL = "FruitClamp/qwen-finetuned"
# Token budget for the *user-content* portion of each batch.
# Kept small (2000) to leave room for the model's JSON output within its
# total context window (input + output share the same budget on HF endpoints).
BATCH_TOKEN_BUDGET = 2000
# Heuristic: 1 token ≈ 4 characters (conservative, works for English prose).
CHARS_PER_TOKEN = 4
# Estimated system-prompt overhead in tokens (measured once, used to guard budget).
SYSTEM_PROMPT_OVERHEAD_TOKENS = 600
# Number of resolved context items passed between parallel chain boundaries.
CONTEXT_OVERLAP_UNITS = 3
# How many batches to fire in parallel within each chain.
# Context is synced at chain boundaries (every PARALLEL_CHAIN_SIZE batches).
PARALLEL_CHAIN_SIZE = 5
# Default concurrency — controls max simultaneous API calls.
DEFAULT_CONCURRENCY = 5


@dataclass
class TextUnit:
    """An atomic unit of text (either a quote or a piece of narration).

    Attributes:
        uid: Unique sequential identifier.
        text: Verbatim text content (never truncated during processing).
        is_quote: True when the unit is direct speech.
        new_paragraph: True when this unit begins a new paragraph in the source.
        continuation_quote: True when this quote is a multi-paragraph continuation
                           (opens with a quote mark but the *previous* quote had no
                           closing mark — standard typographic convention).
        source_chunk_ids: Original PDF chunk IDs this text came from.
        predicted_speaker: Assigned after LLM classification; default is "Narrator".
    """
    uid: int
    text: str
    is_quote: bool
    new_paragraph: bool = False
    continuation_quote: bool = False
    source_chunk_ids: List[int] = field(default_factory=list)
    predicted_speaker: str = "Narrator"


@dataclass
class Character:
    name: str
    gender: str
    description: str


# ---------------------------------------------------------------------------
# Tokenisation helpers
# ---------------------------------------------------------------------------

def _estimate_tokens(text: str) -> int:
    """Fast token estimation.  1 token ≈ 4 chars for English prose."""
    return max(1, len(text) // CHARS_PER_TOKEN)


def _estimate_unit_prompt_tokens(unit: TextUnit) -> int:
    """Estimate how many tokens a single TextUnit will consume inside the
    user prompt (including its ID label, markers, and the text itself)."""
    # Format:  "ID 42 [QUOTE] <P>: some text here..."
    overhead = 12  # "ID", uid digits, label, markers, colon
    return overhead + _estimate_tokens(unit.text)


class SpeakerChunker(Logger):
    def __init__(self, api_key: Optional[str] = None, model: str = DEFAULT_MODEL, base_url: Optional[str] = None):
        self.client = OpenAI(
            base_url=base_url or settings.HF_ENDPOINT_URL,
            api_key=api_key or settings.HF_TOKEN
        )
        self.model = model
        self.logger.info(f"SpeakerChunker initialized (Context-Aware Mode) - Model: {model}")

    def warmup_endpoint(self, max_attempts: int = 3, delay_seconds: int = 10) -> None:
        """
        Pings the serverless endpoint to ensure it's hot.

        For serverless endpoints, multiple pings over time are needed to fully wake up.
        This method sends pings with a 10-second delay between each attempt.

        Args:
            max_attempts: Number of warmup pings (default: 3)
            delay_seconds: Seconds to wait between pings (default: 10)
        """
        self.logger.info(f"Warming up serverless endpoint ({max_attempts} pings, {delay_seconds}s apart)...")

        for attempt in range(1, max_attempts + 1):
            try:
                start = time.time()
                self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": "Ping"}],
                    max_tokens=1
                )
                duration = time.time() - start
                self.logger.info(f"Warmup ping {attempt}/{max_attempts} successful ({duration:.2f}s response time)")

                if attempt < max_attempts:
                    self.logger.info(f"Waiting {delay_seconds}s before next ping...")
                    time.sleep(delay_seconds)

            except Exception as e:
                self.logger.warning(f"Warmup ping {attempt}/{max_attempts} failed: {str(e)}")
                if attempt < max_attempts:
                    time.sleep(delay_seconds)

        self.logger.info("Serverless endpoint warmup complete")

    # ====================================================================
    # STEP 1: Pre-processing — Smart Splitting
    # ====================================================================

    def _stitch_chunks(self, chunks: List[Dict[str, Any]]) -> Tuple[str, List[Optional[int]]]:
        """Concatenate raw PDF chunks into a single string.

        Returns:
            full_text: The concatenated text.
            char_map: A list of the same length as *full_text* where each
                      element is the ``chunk_id`` that character originated from.
        """
        parts: List[str] = []
        char_map: List[Optional[int]] = []
        for ch in chunks:
            txt = ch.get("text", "")
            if not txt:
                continue
            cid = ch.get("chunk_id")
            parts.append(txt)
            char_map.extend([cid] * len(txt))
        return "".join(parts), char_map

    def _resolve_source_chunks(
        self,
        char_map: List[Optional[int]],
        start: int,
        length: int,
    ) -> List[int]:
        """Return the unique, sorted chunk IDs that a character span covers."""
        end = start + length - 1
        s = min(start, len(char_map) - 1)
        e = min(end, len(char_map) - 1)
        ids = {char_map[i] for i in range(s, e + 1) if char_map[i] is not None}
        return sorted(ids)

    def _smart_split(self, full_text: str, char_map: List[Optional[int]]) -> List[TextUnit]:
        """Paragraph-aware, multi-paragraph-quote-aware splitter.

        Algorithm
        ---------
        1. Split the full text on paragraph boundaries (``\\n\\n`` or ``\\n``
           followed by optional whitespace) keeping the separator so character
           offsets stay accurate.
        2. Within each paragraph, split into quote / narration runs using a
           regex that handles standard ``"..."`` **and** smart ``\\u201c...\\u201d`` quotes.
        3. Detect *multi-paragraph quotes* (a paragraph ends inside an open
           quote — no closing mark) and flag the continuation paragraph's
           opening quote with ``continuation_quote=True``.
        4. Merge orphan punctuation (standalone ``,``, ``.``, ``!``, etc.)
           into the preceding unit.
        """
        self.logger.info("Smart-splitting text into paragraph-aware atomic units...")

        # ------------------------------------------------------------------
        # 1. Split into paragraphs (preserve separators for verbatim rebuild)
        # ------------------------------------------------------------------
        para_pattern = re.compile(r'(\n\s*\n|\n)')
        raw_paras = para_pattern.split(full_text)

        # Walk through raw_paras; alternate between content and separator.
        paragraphs: List[Tuple[str, int]] = []  # (text, char_offset)
        offset = 0
        for fragment in raw_paras:
            if not fragment:
                continue
            paragraphs.append((fragment, offset))
            offset += len(fragment)

        # ------------------------------------------------------------------
        # 2. Per-paragraph: quote / narration splitting
        # ------------------------------------------------------------------
        quote_pattern = re.compile(
            r'('
            r'\u201c[^\u201d]*\u201d'   # smart-quoted complete quote
            r'|"[^"]*"'                 # straight-quoted complete quote
            r'|\u201c[^\u201d]*$'       # smart-quote opened but NOT closed (multi-para)
            r'|"[^"]*$'                 # straight-quote opened but NOT closed (multi-para)
            r')',
            re.DOTALL,
        )

        units: List[TextUnit] = []
        uid = 0
        open_multi_para_quote = False  # Track if previous para left a quote unclosed

        for para_text, para_offset in paragraphs:
            stripped = para_text.strip()
            if not stripped:
                continue

            is_para_break = re.fullmatch(r'\s+', para_text)
            if is_para_break:
                continue

            is_new_paragraph = True  # First unit of this paragraph gets the flag

            # Determine if this paragraph is a continuation of an unclosed quote
            is_continuation = open_multi_para_quote and stripped.startswith(('"', '\u201c'))

            # Split this paragraph into quote / narration segments
            segments = quote_pattern.split(para_text)
            seg_offset = para_offset

            # Check if this paragraph leaves a quote unclosed
            unclosed_this_para = False
            for seg in segments:
                if not seg:
                    continue
                seg_stripped = seg.strip()
                if seg_stripped.startswith(('"', '\u201c')):
                    if seg_stripped.startswith('\u201c') and not seg_stripped.endswith('\u201d'):
                        unclosed_this_para = True
                    elif seg_stripped.startswith('"') and not seg_stripped.endswith('"'):
                        unclosed_this_para = True

            for seg in segments:
                if not seg:
                    continue

                length = len(seg)

                # Determine if this segment is a quote
                seg_stripped = seg.strip()
                is_quote = bool(seg_stripped) and seg_stripped[0] in ('"', '\u201c')

                source_ids = self._resolve_source_chunks(char_map, seg_offset, length)

                unit = TextUnit(
                    uid=uid,
                    text=seg,
                    is_quote=is_quote,
                    new_paragraph=is_new_paragraph,
                    continuation_quote=(is_continuation and is_quote and is_new_paragraph),
                    source_chunk_ids=source_ids,
                )
                units.append(unit)
                uid += 1
                is_new_paragraph = False
                seg_offset += length

            open_multi_para_quote = unclosed_this_para

        # ------------------------------------------------------------------
        # 3. Merge orphan punctuation into preceding unit
        # ------------------------------------------------------------------
        merged: List[TextUnit] = []
        orphan_re = re.compile(r'^[\s,.\-;:!?]+$')
        for unit in units:
            if merged and orphan_re.match(unit.text.strip()):
                merged[-1].text += unit.text
                merged[-1].source_chunk_ids = sorted(
                    set(merged[-1].source_chunk_ids + unit.source_chunk_ids)
                )
            else:
                merged.append(unit)

        # Re-index UIDs after merging
        for i, u in enumerate(merged):
            u.uid = i

        self.logger.info(
            f"Smart-split produced {len(merged)} units "
            f"({sum(1 for u in merged if u.is_quote)} quotes, "
            f"{sum(1 for u in merged if not u.is_quote)} narration, "
            f"{sum(1 for u in merged if u.continuation_quote)} multi-para continuations)"
        )
        return merged

    # ====================================================================
    # STEP 2: Adaptive Token-Based Batching
    # ====================================================================

    def _build_adaptive_batches(self, units: List[TextUnit]) -> List[List[TextUnit]]:
        """Pack units into batches that fit within ``BATCH_TOKEN_BUDGET``.

        Long monologues may consume most of a batch; short dialogue lines
        allow many units per batch.  This replaces the old fixed-count approach.
        """
        batches: List[List[TextUnit]] = []
        current_batch: List[TextUnit] = []
        current_tokens = 0

        for unit in units:
            unit_tokens = _estimate_unit_prompt_tokens(unit)
            if current_batch and (current_tokens + unit_tokens) > BATCH_TOKEN_BUDGET:
                batches.append(current_batch)
                current_batch = [unit]
                current_tokens = unit_tokens
            else:
                current_batch.append(unit)
                current_tokens += unit_tokens

        if current_batch:
            batches.append(current_batch)

        sizes = [len(b) for b in batches]
        if sizes:
            self.logger.info(
                f"Adaptive batching: {len(batches)} batches | "
                f"units/batch min={min(sizes)} avg={sum(sizes)//len(sizes)} max={max(sizes)}"
            )
        return batches

    # ====================================================================
    # STEP 3: LLM Classification (Chain-of-Thought, Stateful Context)
    # ====================================================================

    def _build_system_prompt(self, primer: Dict[str, str]) -> str:
        """Construct a compact system prompt once per run (invariant across batches)."""
        pov = primer.get('pov', 'Third Person')
        narrator_name = primer.get('narrator_name', 'Narrator')
        tense = primer.get('tense', 'Past')

        return (
            "You are a dialogue tagger. For each segment, identify the speaker.\n\n"
            f"BOOK: {pov} POV, narrator='{narrator_name}', tense={tense}.\n\n"
            "RULES:\n"
            f"• [NARRATION] segments → speaker is \"{narrator_name}\"\n"
            "• [QUOTE] segments → identify the character speaking\n"
            "• [CONT-QUOTE] → same speaker as preceding quote\n"
            "• <P> = new paragraph; use PREVIOUS CONTEXT for conversation flow\n"
            "• Vocative rule: name at quote start = LISTENER not speaker\n"
            "• Active agent: character acting in narration before quote is likely the speaker\n"
            "• Turn-taking: dialogue alternates A→B→A→B\n\n"
            "OUTPUT: Return ONLY a compact JSON object mapping each numeric ID to a short speaker name.\n"
            "Example: {\"tags\":{\"42\":\"Rand\",\"43\":\"Egwene\",\"44\":\"Narrator\"}}\n"
            "IMPORTANT: Keep values SHORT (just the name). Do NOT include quotes text, reasoning, or extra fields.\n"
            "Use the ACTUAL ID numbers from the input segments."
        )

    def _format_resolved_context(
        self,
        resolved_units: List[Tuple[TextUnit, str]],
    ) -> str:
        """Format the last N resolved (unit, speaker) pairs for the next batch.

        Output example::

            [Rand]: "Don't do that."
            [Egwene]: She shook her head slowly.
            [Rand]: "I mean it."
        """
        if not resolved_units:
            return ""
        lines = []
        for unit, speaker in resolved_units[-CONTEXT_OVERLAP_UNITS:]:
            short = unit.text.replace("\n", " ").strip()
            if len(short) > 120:
                short = short[:120] + "..."
            lines.append(f"[{speaker}]: {short}")
        return "\n".join(lines)

    def _format_batch_lines(self, units: List[TextUnit]) -> str:
        """Render the text units into the visual format the LLM sees."""
        lines = []
        for u in units:
            if u.continuation_quote:
                label = "[CONT-QUOTE]"
            elif u.is_quote:
                label = "[QUOTE]"
            else:
                label = "[NARRATION]"

            para_marker = "<P> " if u.new_paragraph else ""

            # Preserve internal newlines as visible markers so the LLM
            # can still reason about paragraph flow, but keep each unit
            # on a single logical line for parsing.
            sanitized = u.text.replace("\n", " // ").strip()
            # Truncate extreme outliers (> 500 chars) to protect token budget;
            # the full text is always preserved in the TextUnit for reassembly.
            if len(sanitized) > 500:
                sanitized = sanitized[:500] + "..."

            lines.append(f"ID {u.uid} {label} {para_marker}: {sanitized}")
        return "\n".join(lines)

    @staticmethod
    def _repair_truncated_json(raw: str) -> Dict[str, str]:
        """Extract valid key-value pairs from a truncated JSON response.

        When the model's output is cut off mid-JSON, we salvage whatever
        complete ``"id": "speaker"`` pairs exist before the break point.
        This avoids retrying the same oversized batch (which will just
        truncate again) and recovers most of the useful data.
        """
        # Try to find the "tags" block and extract pairs from it
        pairs: Dict[str, str] = {}
        # Match all complete "key": "value" pairs
        pair_pattern = re.compile(r'"(\d+)"\s*:\s*"([^"]+)"')
        for m in pair_pattern.finditer(raw):
            pairs[m.group(1)] = m.group(2)
        return pairs

    def _classify_batch(
        self,
        units: List[TextUnit],
        known_chars: str,
        system_prompt: str,
        resolved_context: str = "",
    ) -> Dict[int, str]:
        """Send a batch to the LLM for speaker attribution.

        On truncated JSON responses, tries to repair the partial JSON first.
        Only retries on non-truncation errors or if repair yields nothing.

        Args:
            units: The units in this batch.
            known_chars: Comma-separated character names.
            system_prompt: Pre-built system prompt (includes primer).
            resolved_context: Formatted resolved speaker lines from the
                              previous batch (stateful handoff).

        Returns:
            Mapping of ``{uid: speaker_name}``.
        """
        batch_text = self._format_batch_lines(units)

        context_block = ""
        if resolved_context:
            context_block = (
                f"--- PREVIOUS RESOLVED CONTEXT (do NOT re-tag) ---\n"
                f"{resolved_context}\n"
                f"-------------------------------------------------\n\n"
            )

        user_prompt = (
            f"Characters: {known_chars}\n\n"
            f"{context_block}"
            f"Segments to tag:\n"
            f"{batch_text}\n\n"
            "Return ONLY the compact JSON tags object. Use the actual ID numbers shown above."
        )

        max_retries = 3
        for attempt in range(max_retries):
            try:
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.1,
                    max_tokens=4096,
                    response_format={"type": "json_object"},
                )

                content = resp.choices[0].message.content
                data = json.loads(content)
                tags_raw = data.get("tags", data)  # Fallback: treat root as tags

                # Convert string keys to integer UIDs
                result: Dict[int, str] = {}
                for k, v in tags_raw.items():
                    try:
                        uid = int(k)
                        if isinstance(v, dict):
                            result[uid] = v.get("speaker", "Narrator")
                        else:
                            result[uid] = str(v)
                    except ValueError:
                        continue
                
                if not result:
                    raise ValueError(f"No valid numeric ID mappings found in response: {list(tags_raw.keys())[:5]}")
                
                return result

            except json.JSONDecodeError as e:
                error_msg = str(e)
                is_truncation = ("Unterminated string" in error_msg
                                 or "Expecting property name" in error_msg
                                 or "Expecting ',' delimiter" in error_msg)

                # Attempt repair on truncated JSON — don't waste retries
                if is_truncation and content:
                    repaired = self._repair_truncated_json(content)
                    if repaired:
                        result: Dict[int, str] = {}
                        for k, v in repaired.items():
                            try:
                                result[int(k)] = v
                            except ValueError:
                                continue
                        if result:
                            coverage = len(result) / len(units) * 100
                            self.logger.warning(
                                f"Repaired truncated JSON: recovered {len(result)}/{len(units)} "
                                f"tags ({coverage:.0f}% coverage) — skipping retries"
                            )
                            return result

                # Only retry if repair failed
                if attempt < max_retries - 1:
                    self.logger.warning(
                        f"JSON parse error: {error_msg}, retrying (attempt {attempt + 1}/{max_retries})"
                    )
                    time.sleep(0.5)
                else:
                    self.logger.error(f"Failed after {max_retries} attempts: {error_msg}")

            except ValueError as e:
                if attempt < max_retries - 1:
                    self.logger.warning(f"Value error: {e}, retrying (attempt {attempt + 1}/{max_retries})")
                    time.sleep(0.5)
                else:
                    self.logger.error(f"Failed after {max_retries} attempts: {e}")
            except Exception as e:
                error_str = str(e)
                if "503" in error_str or "Service Unavailable" in error_str:
                    wait_time = 2 ** (attempt + 1)
                    if attempt < max_retries - 1:
                        self.logger.warning(
                            f"503 error on batch, retrying in {wait_time}s "
                            f"(attempt {attempt + 1}/{max_retries})"
                        )
                        time.sleep(wait_time)
                    else:
                        self.logger.error(f"Failed after {max_retries} attempts (503)")
                else:
                    if attempt < max_retries - 1:
                        self.logger.warning(f"Batch error: {error_str}, retrying...")
                        time.sleep(0.5)
                    else:
                        self.logger.error(f"Batch failed after {max_retries} attempts: {error_str}")

        # Fail-safe: return empty dict (caller will use fallback speaker)
        self.logger.warning(f"Batch classification failed completely - {len(units)} units will use fallback speaker")
        return {}

    # ====================================================================
    # STEP 4: Orchestration — Stateful Serial Processing
    # ====================================================================

    def chunk_by_speaker(
        self,
        processed_data: Dict[str, Any],
        concurrency: int = DEFAULT_CONCURRENCY,
        progress_callback: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """Main entry point: process PDF chunks into speaker-attributed segments.

        Processing is now **serial by default** (``concurrency=1``) so that each
        batch receives the resolved speaker tags of its predecessor, maintaining
        conversational turn continuity (A -> B -> A).
        """
        start_time = time.time()
        chunks = processed_data.get("chunks", [])

        # -- 1. Book Primer ------------------------------------------------
        self.logger.info("Analyzing book context (POV, narrator, tense)...")
        intro_text = " ".join([c["text"] for c in chunks[:5]])
        primer = self._generate_book_primer(intro_text)
        self.logger.info(
            f"Book Primer: {primer.get('pov')} POV, "
            f"Narrator: {primer.get('narrator_name')}, "
            f"Tense: {primer.get('tense')}"
        )

        # -- 2. Character Discovery ----------------------------------------
        self.logger.info("Discovering characters from intro text...")
        characters = self._discover_characters(intro_text)
        known_chars_str = ", ".join([c.name for c in characters])
        self.logger.info(f"Discovered {len(characters)} characters: {known_chars_str}")

        # -- 3. Smart Split ------------------------------------------------
        full_text, char_map = self._stitch_chunks(chunks)
        all_units = self._smart_split(full_text, char_map)
        total_units = len(all_units)
        self.logger.info(
            f"Split into {total_units} text units "
            f"({sum(1 for u in all_units if u.is_quote)} quotes, "
            f"{sum(1 for u in all_units if not u.is_quote)} narration)"
        )

        # -- 4. Pre-tag narration locally (no LLM needed) -----------------
        narrator_name = primer.get("narrator_name", "Narrator")
        results_map: Dict[int, str] = {}
        quote_units: List[TextUnit] = []
        for u in all_units:
            if not u.is_quote:
                results_map[u.uid] = narrator_name
            else:
                quote_units.append(u)

        narration_count = len(all_units) - len(quote_units)
        self.logger.info(
            f"Pre-tagged {narration_count} narration units locally as '{narrator_name}' "
            f"— only {len(quote_units)} quote units need LLM classification"
        )

        # Re-batch only the quote units (with surrounding narration context
        # embedded in the resolved-context window)
        quote_batches = self._build_adaptive_batches(quote_units)
        total_batches = len(quote_batches)

        # -- 5. Hybrid Parallel-Serial Processing --------------------------
        #   Batches are grouped into *chains* of PARALLEL_CHAIN_SIZE.
        #   Within a chain, all batches share the same resolved context and
        #   run in parallel.  At chain boundaries, context is synced from the
        #   last batch of the completed chain.
        system_prompt = self._build_system_prompt(primer)
        batch_times: List[float] = []
        processing_start = time.time()
        lock = threading.Lock()
        completed_count = {"n": 0}

        # Resolved context accumulator (synced at chain boundaries)
        resolved_tail: List[Tuple[TextUnit, str]] = []

        chain_size = min(PARALLEL_CHAIN_SIZE, concurrency)
        chains = [quote_batches[i:i + chain_size] for i in range(0, total_batches, chain_size)]

        self.logger.info(
            f"Processing {total_batches} quote-only batches in {len(chains)} chains "
            f"(chain_size={chain_size}, concurrency={concurrency}, "
            f"token_budget={BATCH_TOKEN_BUDGET})..."
        )
        self.logger.info(f"Total quote units to classify: {len(quote_units)}")

        # -- Upfront time estimation ----------------------------------------
        # Use a rough estimate of ~60s per batch (typical for this model).
        # Parallel chains reduce wall time proportionally.
        est_secs_per_batch = 60
        effective_parallel = max(1, chain_size)
        est_total_secs = (total_batches / effective_parallel) * est_secs_per_batch
        est_fmt = self._format_duration(est_total_secs)
        self.logger.info(
            f"*** Estimated total LLM processing time: {est_fmt} "
            f"({total_batches} batches, ~{est_secs_per_batch}s/batch, "
            f"{effective_parallel}x parallel) ***"
        )

        for chain_idx, chain_batches in enumerate(chains):
            # Snapshot context for this chain (all batches in the chain see
            # the same context from the previous chain's last batch)
            resolved_context = self._format_resolved_context(resolved_tail)
            chain_results: Dict[int, Dict[int, str]] = {}  # batch_pos -> mapping

            def _process_one(pos: int, batch_units: List[TextUnit]) -> Tuple[int, Dict[int, str], float]:
                t0 = time.time()
                mapping = self._classify_batch(
                    batch_units,
                    known_chars_str,
                    system_prompt,
                    resolved_context,
                )
                # First Person normalisation
                if primer.get("pov") == "First Person" and narrator_name != "Narrator":
                    for uid in list(mapping.keys()):
                        if mapping[uid] == "Narrator":
                            mapping[uid] = narrator_name
                return pos, mapping, time.time() - t0

            # Fire chain batches in parallel
            with ThreadPoolExecutor(max_workers=min(concurrency, len(chain_batches))) as pool:
                futures = {
                    pool.submit(_process_one, i, b): i
                    for i, b in enumerate(chain_batches)
                }
                for future in as_completed(futures):
                    pos, mapping, duration = future.result()
                    chain_results[pos] = mapping
                    batch_times.append(duration)

                    with lock:
                        results_map.update(mapping)
                        completed_count["n"] += 1
                        completed = completed_count["n"]
                        remaining = total_batches - completed
                        percent = round((completed / total_batches) * 100, 1)

                        recent = batch_times[-20:] if len(batch_times) > 20 else batch_times
                        avg_bt = sum(recent) / len(recent)
                        # With parallelism, effective wall time per batch is lower
                        effective_parallel = max(1, min(concurrency, len(chain_batches)))
                        eta_secs = (remaining / effective_parallel) * avg_bt
                        eta_fmt = self._format_duration(eta_secs)

                        elapsed = time.time() - processing_start
                        elapsed_fmt = self._format_duration(elapsed)
                        throughput = completed / elapsed if elapsed > 0 else 0

                    self.logger.info(
                        f"Batch {completed}/{total_batches} done "
                        f"({len(chain_batches[pos])} units, {duration:.2f}s) | "
                        f"{percent}% | Elapsed: {elapsed_fmt} | ETA: {eta_fmt}"
                    )

                    if progress_callback:
                        progress_callback({
                            "percent_complete": percent,
                            "batches_completed": completed,
                            "total_batches": total_batches,
                            "estimated_remaining_formatted": eta_fmt,
                            "estimated_remaining_seconds": eta_secs,
                            "units_per_second": round(throughput, 2),
                            "avg_batch_time": round(avg_bt, 2),
                        })

            # Sync context: use the LAST batch in the chain (by position)
            # to seed the resolved tail for the next chain
            last_pos = len(chain_batches) - 1
            last_mapping = chain_results.get(last_pos, {})
            last_batch_units = chain_batches[last_pos]
            resolved_tail = []
            for u in last_batch_units:
                speaker = last_mapping.get(u.uid, narrator_name)
                resolved_tail.append((u, speaker))
            resolved_tail = resolved_tail[-CONTEXT_OVERLAP_UNITS:]

        # -- Log LLM phase completion --------------------------------------
        llm_processing_time = time.time() - processing_start
        self.logger.info(f"LLM batch processing complete in {self._format_duration(llm_processing_time)}")
        self.logger.info(
            f"Tagged {len(results_map)}/{total_units} units "
            f"({round(len(results_map) / max(total_units, 1) * 100, 1)}% success rate)"
        )

        if batch_times:
            recent = batch_times[-20:] if len(batch_times) > 20 else batch_times
            self.logger.info(
                f"Batch time stats: Overall avg: {sum(batch_times)/len(batch_times):.2f}s | "
                f"Recent avg: {sum(recent)/len(recent):.2f}s | "
                f"Min: {min(batch_times):.2f}s | Max: {max(batch_times):.2f}s"
            )

        # -- 6. Reassembly & Merge -----------------------------------------
        self.logger.info("Reassembling segments and merging adjacent speakers...")
        reassembly_start = time.time()

        final_segments: List[Dict[str, Any]] = []
        current_segment: Optional[Dict[str, Any]] = None

        for unit in all_units:
            speaker = results_map.get(unit.uid, primer.get("narrator_name", "Narrator"))

            if current_segment is None:
                current_segment = {
                    "speaker": speaker,
                    "text": unit.text,
                    "source_chunk_ids": list(unit.source_chunk_ids),
                }
            elif current_segment["speaker"] == speaker:
                current_segment["text"] += unit.text
                current_segment["source_chunk_ids"] = sorted(
                    set(current_segment["source_chunk_ids"] + unit.source_chunk_ids)
                )
            else:
                final_segments.append(current_segment)
                current_segment = {
                    "speaker": speaker,
                    "text": unit.text,
                    "source_chunk_ids": list(unit.source_chunk_ids),
                }

        if current_segment:
            final_segments.append(current_segment)

        reassembly_time = time.time() - reassembly_start
        total_time = time.time() - start_time

        # -- Final statistics -----------------------------------------------
        self.logger.info(f"Reassembly complete in {self._format_duration(reassembly_time)}")
        self.logger.info(f"Created {len(final_segments)} final segments from {total_units} units")
        compression = round(total_units / max(len(final_segments), 1), 2)
        self.logger.info(f"Compression ratio: {compression}x (merged adjacent same-speaker units)")

        speaker_counts: Dict[str, int] = {}
        for seg in final_segments:
            speaker_counts[seg["speaker"]] = speaker_counts.get(seg["speaker"], 0) + 1

        self.logger.info(
            f"Speaker distribution: "
            f"{dict(sorted(speaker_counts.items(), key=lambda x: x[1], reverse=True))}"
        )
        self.logger.info(f"Total processing time: {self._format_duration(total_time)}")

        return {
            "characters": [c.__dict__ for c in characters],
            "segments": final_segments,
            "primer": primer,
            "meta": {
                "processing_time": total_time,
                "total_segments": len(final_segments),
                "total_units": total_units,
                "compression_ratio": compression,
                "llm_processing_time": llm_processing_time,
                "reassembly_time": reassembly_time,
                "avg_batch_time_overall": (
                    sum(batch_times) / len(batch_times) if batch_times else 0
                ),
                "avg_batch_time_recent": (
                    sum(batch_times[-20:]) / len(batch_times[-20:])
                    if batch_times else 0
                ),
                "min_batch_time": min(batch_times) if batch_times else 0,
                "max_batch_time": max(batch_times) if batch_times else 0,
                "total_batches": total_batches,
                "batch_token_budget": BATCH_TOKEN_BUDGET,
                "speaker_distribution": speaker_counts,
                "book_context": {
                    "pov": primer.get("pov"),
                    "narrator": primer.get("narrator_name"),
                    "tense": primer.get("tense"),
                },
            },
        }

    # ====================================================================
    # Helpers — Primer & Character Discovery
    # ====================================================================

    def _generate_book_primer(self, intro_text: str) -> Dict[str, str]:
        """Analyzes the first few pages to establish Global Truths.

        Solves the 'Cold Start' problem where the narrator is unknown.

        Returns:
            Dict with keys: pov, narrator_name, tense
        """
        prompt = (
            "Analyze the following opening text of a novel.\n"
            "Determine:\n"
            "1. POV: 'First Person' (I) or 'Third Person' (He/She).\n"
            "2. Narrator Name: If First Person, who is the 'I'? If unknown, use 'Narrator'.\n"
            "3. Tense: 'Past' or 'Present'.\n\n"
            "Return JSON: {\"pov\": \"...\", \"narrator_name\": \"...\", \"tense\": \"...\"}\n\n"
            f"TEXT:\n{intro_text[:5000]}"
        )

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=200,
                response_format={"type": "json_object"},
            )
            data = json.loads(resp.choices[0].message.content)
            return {
                "pov": data.get("pov", "Third Person"),
                "narrator_name": data.get("narrator_name", "Narrator"),
                "tense": data.get("tense", "Past"),
            }
        except Exception as e:
            self.logger.warning(f"Failed to generate book primer: {e}, using defaults")
            return {"pov": "Third Person", "narrator_name": "Narrator", "tense": "Past"}

    def _discover_characters(self, text: str) -> List[Character]:
        """Identify major characters from the opening text."""
        prompt = (
            "Identify characters in this story intro. Return JSON "
            "{\"characters\": [{\"name\": \"...\", \"gender\": \"...\", \"description\": \"...\"}]}.\n\n"
            f"TEXT: {text[:4000]}"
        )
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                response_format={"type": "json_object"},
            )
            data = json.loads(resp.choices[0].message.content)
            chars = [
                Character(c["name"], c["gender"], c.get("description", ""))
                for c in data.get("characters", [])
            ]
            if not any(c.name == "Narrator" for c in chars):
                chars.insert(0, Character("Narrator", "NEUTRAL", "Narrator"))
            return chars
        except Exception:
            return [Character("Narrator", "NEUTRAL", "Narrator")]

    # ====================================================================
    # Utility
    # ====================================================================

    @staticmethod
    def _format_duration(seconds: float) -> str:
        """Format seconds into a human-readable duration string."""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds // 60)}m {int(seconds % 60)}s"
        else:
            return f"{int(seconds // 3600)}h {int((seconds % 3600) // 60)}m"
