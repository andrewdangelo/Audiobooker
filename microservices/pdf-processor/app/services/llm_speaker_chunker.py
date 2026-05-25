"""
LLM Chunker — uses internal /chat and /web-rag endpoints
"""
__author__ = "Andrew D'Angelo"
__contributor__ = "Mohammad Saifan"

import asyncio
import json
import time
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable, Tuple, Set

import httpx
from app.core.logging_config import Logger
from app.core.config_settings import settings
from app.services.character_discovery import CharacterDiscovery, CharacterRegistry
from app.services.syntax_analyzer import SyntaxAnalyzer, SpeakerContext, DialogueTagAnalysis
from app.services.fidelity_verifier import FidelityVerifier


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_MODEL                 = "@cf/openai/gpt-oss-120b"
DEFAULT_PROVIDER              = "cf"

BATCH_TOKEN_BUDGET            = 2000 #800
CHARS_PER_TOKEN               = 4
MAX_CONCURRENT_REQUESTS       = 20
REQUEST_TIMEOUT_SECONDS       = 60

MAX_UNIT_CHARS                = 600
MAX_QUOTE_CHARS_IN_PROMPT     = 150
MAX_CONTEXT_CHARS_IN_PROMPT   = 200

SCENE_WINDOW_CHARS   = 1250   
SCENE_OVERLAP_CHARS  = 200  
MAX_QUOTES_PER_SCENE = 4

# ---------------------------------------------------------------------------
# Speech-verb regex
# ---------------------------------------------------------------------------
SPEECH_VERBS = (
    r"said|says|asked|asks|replied|replies|answered|answers|"
    r"shouted|shouts|whispered|whispers|muttered|mutters|"
    r"exclaimed|exclaims|demanded|demands|cried|cries|"
    r"called|calls|yelled|yells|screamed|screams|"
    r"snapped|snaps|growled|growls|hissed|hisses|"
    r"sighed|sighs|laughed|laughs|chuckled|chuckles|"
    r"murmured|murmurs|breathed|breathes|gasped|gasps|"
    r"groaned|groans|moaned|moans|declared|declares|"
    r"announced|announces|continued|continues|added|adds|"
    r"began|begins|went on|interrupted|interrupts|"
    r"inquired|inquires|wondered|wonders|observed|observes|"
    r"commented|comments|noted|notes|remarked|remarks|"
    r"admitted|admits|agreed|agrees|protested|protests|"
    r"suggested|suggests|explained|explains|insisted|insists|"
    r"responded|responds|retorted|retorts|countered|counters|"
    r"confirmed|confirms|denied|denies|pleaded|pleads"
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class TextUnit:
    uid: int
    text: str
    is_quote: bool
    new_paragraph: bool = False
    continuation_quote: bool = False
    chunk_id: Optional[int] = None
    heuristic_confidence: float = 0.0


# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------

def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // CHARS_PER_TOKEN)

def _estimate_unit_prompt_tokens(unit: TextUnit) -> int:
    quote_chars   = min(len(unit.text), MAX_QUOTE_CHARS_IN_PROMPT)
    context_chars = MAX_CONTEXT_CHARS_IN_PROMPT * 2
    return 20 + _estimate_tokens("x" * (quote_chars + context_chars))


# ===========================================================================
# Internal API wrapper
# ===========================================================================

class _InternalAPI:
    """Routes all LLM calls through the internal /chat and /web-rag endpoints."""

    def __init__(self, base_url: str, model: str, provider: str):
        self.chat_url = f"{base_url}/ai/chat"
        self.rag_url  = f"{base_url}/ai/chat/web-rag"
        self.cloudflare_structured_url = f"{base_url}/chat/cloudflare-structured"
        self.model    = model
        self.provider = provider

    def _chat_payload(self, prompt_messages: List[List[str]], inputs: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "provider":        self.provider,
            "preset": "chat-knowledge",
            "prompt_messages": prompt_messages,
            # LangChain ChatPromptTemplate requires a non-empty inputs dict
        }

    def _rag_payload(self, prompt_messages: List[List[str]], inputs: Dict[str, Any],
                     search_query_template: str) -> Dict[str, Any]:
        return {
            "provider":              self.provider,
            "preset":       "chat-knowledge",
            "prompt_messages":       prompt_messages,
            "search_query_template": None,
        }

    # --- sync ---

    def sync_chat(self, prompt_messages: List[List[str]], inputs: Dict[str, Any],
                  timeout: int = REQUEST_TIMEOUT_SECONDS) -> str:
        payload = self._chat_payload(prompt_messages, inputs)
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(self.chat_url, json=payload)
            if not resp.is_success:
                raise httpx.HTTPStatusError(
                    f"Chat {resp.status_code}: {resp.text[:300]}",
                    request=resp.request, response=resp)
            return resp.json()["answer"]

    def sync_rag_chat(self, prompt_messages: List[List[str]], inputs: Dict[str, Any],
                      search_query_template: str, timeout: int = REQUEST_TIMEOUT_SECONDS) -> Tuple[str, str]:
        payload = self._rag_payload(prompt_messages, inputs, search_query_template)
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(self.rag_url, json=payload)
            if not resp.is_success:
                raise httpx.HTTPStatusError(
                    f"RAG {resp.status_code}: {resp.text[:300]}",
                    request=resp.request, response=resp)
            data = resp.json()
            return data["answer"], data.get("context", "")

    # --- async ---
    async def async_chat(self, client: httpx.AsyncClient, prompt_messages: List[List[str]],
                         inputs: Dict[str, Any], timeout: int = REQUEST_TIMEOUT_SECONDS) -> str:
        payload = self._chat_payload(prompt_messages, inputs)
        resp = await client.post(self.chat_url, json=payload, timeout=timeout)
        if not resp.is_success:
            raise httpx.HTTPStatusError(
                f"Chat {resp.status_code}: {resp.text[:300]}",
                request=resp.request, response=resp)
        return resp.json()["answer"]


# ===========================================================================
# SpeakerChunker
# ===========================================================================

class SpeakerChunker(Logger):

    def __init__(self, model: str = DEFAULT_MODEL, provider: str = DEFAULT_PROVIDER):
        self.model              = model
        self.provider           = provider
        self._uid_to_idx:       Dict[int, int] = {}   # populated in _smart_split
        self._alias_to_canonical: Dict[str, str] = {} # populated in _chunk_by_speaker_async
        self.api                = _InternalAPI(
            base_url = settings.INTERNAL_LLM_BASE_URL,
            model    = model,
            provider = provider,
        )
        self.logger.info(f"SpeakerChunker initialised — model: {model}  provider: {provider}")

    # ====================================================================
    # Warmup
    # ====================================================================

    def warmup_endpoint(self, max_attempts: int = 20, delay_seconds: int = 10) -> bool:
        self.logger.info(f"Warming up RAG endpoint (max_attempts={max_attempts}, delay={delay_seconds}s)")

        # Keep this simple + deterministic
        system_msg = "You are a helpful assistant."
        user_msg   = "Give a short test response."

        for attempt in range(1, max_attempts + 1):
            try:
                t0 = time.time()

                ans = self.api.sync_chat(
                    prompt_messages=[["user", "hi"]],
                    inputs={},
                    timeout=30,
                )

                answer, web_context = self.api.sync_rag_chat(
                    prompt_messages=[
                        ["system", system_msg],
                        ["user", user_msg]
                    ],
                    inputs={},
                    search_query_template="test query warmup"
                )
                

                dur = time.time() - t0

                # Validate BOTH answer + retrieval happened + ans
                if answer and web_context is not None and ans:
                    self.logger.info(
                        f"RAG endpoint warm (attempt {attempt}, {dur:.2f}s, context_len={len(web_context)})"
                    )
                    return True

            except Exception as e:
                self.logger.warning(f"Warmup attempt {attempt} failed: {e}")

            if attempt < max_attempts:
                self.logger.info("RAG still cold — retrying...")
                time.sleep(delay_seconds)

        self.logger.error("RAG endpoint failed to warm after retries")
        return False

    # ====================================================================
    # Title extraction
    # ====================================================================

    def _extract_book_title(self, chunks: List[Dict[str, Any]]) -> str:
        self.logger.info("Extracting book title from opening pages...")
        intro_text = " ".join(c["text"] for c in chunks[:5])[:3000]

        # Escape { and } to avoid LangChain format errors
        intro_text = intro_text.replace("{", "{{").replace("}", "}}")

        try:
            answer = self.api.sync_chat(
                prompt_messages=[
                    ["system", "You are a literary assistant. Given the opening pages of a book, return ONLY the book title as a plain string — no quotes, no explanation."],
                    ["user",  f"Opening text:\n\n{intro_text}\n\nWhat is the title of this book?"],
                ],
                inputs={},
            )

            # Normalize in case it's a dict
            if isinstance(answer, dict):
                answer = (
                    answer.get("title")
                    or answer.get("text")
                    or answer.get("answer")
                    or str(answer)
                )

            title = str(answer).strip().strip('"').strip("'")
            self.logger.info(f"Extracted book title: '{title}'")
            return title or "Unknown Book"

        except Exception as e:
            self.logger.warning(f"Title extraction failed: {e} — using 'Unknown Book'")
            return "Unknown Book"

    @staticmethod
    def _looks_like_job_id(title: str) -> bool:
        """Returns True if the string looks like a job/file ID rather than a real book title."""
        return bool(re.search(r'[0-9a-f]{8}-[0-9a-f]{4}|job_|_pdf_|uploads_', title, re.IGNORECASE))

    # ====================================================================
    # STEP 1 — stitch chunks
    # ====================================================================

    def _stitch_chunks(self, chunks: List[Dict[str, Any]]) -> Tuple[str, List[Optional[int]]]:
        SEPARATOR = "\n"
        parts:    List[str]           = []
        char_map: List[Optional[int]] = []

        for ch in chunks:
            txt = ch.get("text", "")
            if not txt:
                continue
            cid = ch.get("chunk_id")
            if parts:
                parts.append(SEPARATOR)
                char_map.extend([None])
            parts.append(txt)
            char_map.extend([cid] * len(txt))

        full_text = "".join(parts)
        assert len(full_text) == len(char_map), \
            f"char_map {len(char_map)} != full_text {len(full_text)}"
        self.logger.info(f"Stitched {len(chunks)} chunks → {len(full_text)} chars")
        return full_text, char_map

    def _resolve_chunk_id(self, char_map: List[Optional[int]], start: int, length: int) -> Optional[int]:
        if length <= 0:
            return None
        end = min(start + length, len(char_map))
        s   = min(start, len(char_map) - 1)
        coverage: Dict[int, int] = {}
        for i in range(s, end):
            cid = char_map[i]
            if cid is not None:
                coverage[cid] = coverage.get(cid, 0) + 1
        return max(coverage, key=lambda k: coverage[k]) if coverage else None

    # ====================================================================
    # STEP 2 — smart split
    # ====================================================================

    def _split_long_narration(self, text: str, start_offset: int, char_map: List[Optional[int]],
                               uid_counter: int, is_new_paragraph: bool,
                               continuation_quote: bool) -> List[TextUnit]:
        if len(text) <= MAX_UNIT_CHARS:
            cid = self._resolve_chunk_id(char_map, start_offset, len(text))
            return [TextUnit(uid=uid_counter, text=text, is_quote=False,
                             new_paragraph=is_new_paragraph, continuation_quote=continuation_quote, chunk_id=cid)]

        sentences      = re.compile(r'(?<=[.!?])\s+').split(text)
        units:         List[TextUnit] = []
        current        = ""
        current_offset = start_offset
        first          = True

        for sentence in sentences:
            if current and len(current) + len(sentence) + 1 > MAX_UNIT_CHARS:
                cid = self._resolve_chunk_id(char_map, current_offset, len(current))
                units.append(TextUnit(uid=uid_counter, text=current, is_quote=False,
                                      new_paragraph=(is_new_paragraph if first else False),
                                      continuation_quote=(continuation_quote if first else False), chunk_id=cid))
                uid_counter    += 1
                first           = False
                current_offset += len(current)
                current         = sentence
            else:
                current = (current + " " + sentence) if current else sentence

        if current:
            cid = self._resolve_chunk_id(char_map, current_offset, len(current))
            units.append(TextUnit(uid=uid_counter, text=current, is_quote=False,
                                  new_paragraph=(is_new_paragraph if not units else False),
                                  continuation_quote=(continuation_quote if not units else False), chunk_id=cid))
        return units

    @staticmethod
    def _collapse_newlines_in_quotes(text: str) -> str:
        def _fix(m: re.Match) -> str:
            return m.group(0).replace("\n", " ")
        text = re.sub(r'"[^"]*?"',               _fix, text, flags=re.DOTALL)
        text = re.sub(r'\u201c[^\u201d]*?\u201d', _fix, text, flags=re.DOTALL)
        return text

    def _smart_split(self, full_text: str, char_map: List[Optional[int]]) -> List[TextUnit]:
        self.logger.info("Smart-splitting text...")
        normalised = self._collapse_newlines_in_quotes(full_text)
        para_re    = re.compile(r'(\n\n+|\n)')
        fragments  = para_re.split(normalised)

        paragraphs: List[Tuple[str, int]] = []
        offset = 0
        for frag in fragments:
            if frag and not re.fullmatch(r'\s+', frag):
                paragraphs.append((frag, offset))
            offset += len(frag)

        quote_pattern = re.compile(
            r'('
            r'\u201c[^\u201d]*?\u201d'
            r'|"[^"]*?"'
            r'|\u201c[^\u201d]*?$'
            r'|"[^"]*?$'
            r')',
            re.DOTALL
        )

        units: List[TextUnit] = []
        uid   = 0
        open_multi_para_quote = False

        for para_text, para_offset in paragraphs:
            stripped = para_text.strip()
            if not stripped:
                continue

            is_new_paragraph = True
            is_continuation  = open_multi_para_quote and stripped.startswith(('"', '\u201c'))
            segments         = quote_pattern.split(para_text)

            unclosed_this_para = False
            for seg in segments:
                ss = seg.strip() if seg else ""
                if ss.startswith('\u201c') and not ss.endswith('\u201d'):
                    unclosed_this_para = True
                elif ss.startswith('"') and not ss.endswith('"'):
                    unclosed_this_para = True

            seg_offset = para_offset
            for seg in segments:
                if not seg:
                    continue
                ss = seg.strip()
                if not ss:
                    seg_offset += len(seg)
                    continue

                is_quote = ss[0] in ('"', '\u201c')

                if is_quote:
                    cid = self._resolve_chunk_id(char_map, seg_offset, len(seg))
                    units.append(TextUnit(uid=uid, text=seg, is_quote=True,
                                        new_paragraph=is_new_paragraph,
                                        continuation_quote=(is_continuation and is_new_paragraph),
                                        chunk_id=cid))
                    uid += 1
                else:
                    for nu in self._split_long_narration(
                        text=seg, start_offset=seg_offset, char_map=char_map,
                        uid_counter=uid, is_new_paragraph=is_new_paragraph,
                        continuation_quote=(is_continuation and is_new_paragraph),
                    ):
                        nu.uid = uid
                        units.append(nu)
                        uid += 1

                is_new_paragraph = False
                seg_offset += len(seg)

            open_multi_para_quote = unclosed_this_para

        QUOTE_STRIP = " \t\n\r\u201c\u201d\u2018\u2019\"\'"
        orphan_re   = re.compile(r'^[\s,.\-;:!?]+$')
        merged: List[TextUnit] = []

        for unit in units:
            if merged and orphan_re.match(unit.text.strip()):
                merged[-1].text += unit.text
            elif unit.is_quote and len(unit.text.strip(QUOTE_STRIP)) < 2:
                self.logger.debug(f"Dropping empty quote: {repr(unit.text)}")
            else:
                merged.append(unit)

        for i, u in enumerate(merged):
            u.uid = i

        self._uid_to_idx = {u.uid: i for i, u in enumerate(merged)}

        self.logger.info(
            f"Smart-split → {len(merged)} units "
            f"({sum(1 for u in merged if u.is_quote)} quotes, "
            f"{sum(1 for u in merged if not u.is_quote)} narration)"
        )
        return merged

    # ====================================================================
    # STEP 3 — scene windows
    # ====================================================================

    def _build_scene_windows(
        self,
        full_text: str,
        all_units: List[TextUnit],
    ) -> List[Dict[str, Any]]:
        text_len = len(full_text)
        step     = SCENE_WINDOW_CHARS - SCENE_OVERLAP_CHARS

        unit_char_offsets: Dict[int, int] = {}
        search_from = 0
        for u in all_units:
            target = u.text[:60]
            pos    = full_text.find(target, search_from)
            if pos == -1:
                pos = full_text.find(target)
            if pos != -1:
                unit_char_offsets[u.uid] = pos
                search_from = pos

        scenes: List[Dict[str, Any]] = []
        start = 0
        while start < text_len:
            end        = min(start + SCENE_WINDOW_CHARS, text_len)
            window_quotes = [
                u for u in all_units
                if u.is_quote
                and u.uid in unit_char_offsets
                and start <= unit_char_offsets[u.uid] < end
            ]

            if window_quotes:
                if len(window_quotes) > MAX_QUOTES_PER_SCENE:
                    mid      = len(window_quotes) // 2
                    mid_off  = unit_char_offsets.get(window_quotes[mid].uid, (start + end) // 2)
                    scenes.append({
                        "text":   full_text[max(0, start - 300):min(text_len, mid_off + 300)],
                        "start":  start,
                        "end":    mid_off,
                        "quotes": window_quotes[:mid],
                    })
                    scenes.append({
                        "text":   full_text[max(0, mid_off - 300):min(text_len, end + 300)],
                        "start":  mid_off,
                        "end":    end,
                        "quotes": window_quotes[mid:],
                    })
                else:
                    scenes.append({
                        "text":   full_text[max(0, start - 300):min(text_len, end + 300)],
                        "start":  start,
                        "end":    end,
                        "quotes": window_quotes,
                    })

            start += step

        seen_uids: Set[int]             = set()
        deduped:   List[Dict[str, Any]] = []
        for scene in scenes:
            unique = [q for q in scene["quotes"] if q.uid not in seen_uids]
            if unique:
                seen_uids.update(q.uid for q in unique)
                scene["quotes"] = unique
                deduped.append(scene)

        missed_uids = {
            u.uid for u in all_units
            if u.is_quote and u.uid not in seen_uids
        }
        if missed_uids:
            self.logger.warning(f"{len(missed_uids)} quotes had no offset match — adding as micro-scenes")
            for u in all_units:
                if u.uid in missed_uids:
                    pos = full_text.find(u.text[:40])
                    if pos == -1:
                        pos = 0
                    w_start = max(0, pos - 400)
                    w_end   = min(text_len, pos + 600)
                    deduped.append({
                        "text":   full_text[w_start:w_end],
                        "start":  w_start,
                        "end":    w_end,
                        "quotes": [u],
                    })
                    seen_uids.add(u.uid)

        total_covered = sum(len(s["quotes"]) for s in deduped)
        self.logger.info(
            f"Scene windowing: {len(deduped)} scenes | "
            f"{total_covered} quotes covered"
        )
        return deduped

    # ====================================================================
    # STEP 6 — adaptive batching
    # ====================================================================

    def _build_scene_system_prompt(self, primer: Dict[str, str], known_chars_str: str) -> str:
        narrator = primer.get('narrator_name', 'Narrator')
        pov      = primer.get('pov', 'Third Person')
        tense    = primer.get('tense', 'Past')
        return (
            f"You are an expert dialogue attribution system for literary fiction.\n\n"
            f"BOOK CONTEXT:\n"
            f"- POV: {pov}\n"
            f"- Narrator: {narrator}\n"
            f"- Tense: {tense}\n"
            f"- Known characters: {known_chars_str}\n\n"
            "You will receive a passage of text with [Q:N] or [CONT:N] tags marking quoted dialogue. "
            "Read the ENTIRE passage including all narration before attributing any quote.\n\n"
            "HOW TO IDENTIFY THE SPEAKER:\n"
            "- Look at the narration IMMEDIATELY before and after each tagged quote.\n"
            "- The speaker is the character described as acting, speaking, or moving in that narration.\n"
            "- A name at the START of a quote followed by a comma is being ADDRESSED, not speaking.\n"
            "  e.g. 'Ponyboy, come here!' → someone else speaks TO Ponyboy.\n"
            "- A character who reacts, stares, or looks AFTER a quote is the LISTENER — find the speaker BEFORE the quote.\n"
            "  e.g. 'Get out.' Darry stared at him. → Darry is the LISTENER. Speaker is whoever acted before the quote.\n"
            "  e.g. 'Get out.' Soda nodded. → Soda is the SPEAKER (physical action = speaker).\n"
            "- [CONT] always has the SAME speaker as the quote immediately before it.\n"
            "- ONLY use characters who are actually present in THIS passage. Ignore characters from earlier scenes.\n\n"
            "SPECIAL CASES:\n"
            f"- A word or term being defined in narration (not spoken aloud) → {narrator}.\n"
            "- Anonymous voice with no named actor → Unknown.\n"
            "- Truly ambiguous after reading full context → Unknown.\n"
            "- NEVER output pronouns. Always resolve he/she/they to the character's name.\n\n"
            "EXAMPLES (study these carefully before attributing):\n\n"
            "Passage: Soda threw his arm over my shoulder. [Q:0] \"Don't sweat it, Pony.\"\n"
            "0|Sodapop Curtis\n\n"
            "Passage: [Q:0] \"Ponyboy,\" Darry said sharply, [Q:1] \"get inside now.\"\n"
            "0|Darry\n"
            "1|Darry\n\n"
            "Passage: Dally lit a cigarette and walked off. Later, lying in bed, Soda mumbled [Q:0] \"I'm gonna marry Sandy someday.\"\n"
            "0|Sodapop Curtis\n\n"
            "Passage: [Q:0] \"Johnny, I ain't mad at you.\" He pushed his white-blond hair back. [Q:1] \"I just don't want you getting hurt.\"\n"
            "0|Dallas Winston\n"
            "1|Dallas Winston\n\n"
            "Passage: Johnny gulped but said [Q:0] \"You heard me. Leave her alone.\" Dallas scowled.\n"
            "0|Johnny Cade\n\n"
            "Passage: [Q:0] \"Need a haircut, greaser?\" I remembered that voice from earlier that night.\n"
            f"0|Unknown\n\n"
            "---\n\n"
            "OUTPUT FORMAT — one pipe-delimited line per tagged quote, nothing else:\n"
            "0|Speaker Name\n"
            "1|Speaker Name\n\n"
            "OUTPUT ONLY PIPE-DELIMITED LINES. No explanation. No reasoning. No JSON."
        )


    def _validate_attribution(
        self,
        uid: int,
        speaker: str,
        all_units: List[TextUnit],
        alias_map: Dict[str, str],
    ) -> str:
        if speaker in ("Unknown", "Narrator"):
            return speaker

        idx = self._uid_to_idx.get(uid)
        if idx is None:
            return speaker

        window_narration = " ".join(
            all_units[j].text
            for j in range(max(0, idx - 4), min(len(all_units), idx + 5))
            if not all_units[j].is_quote
        )

        if not window_narration.strip():
            return speaker

        # If "I said/asked/pleaded" etc. is in window — narrator speaking, trust LLM
        first_person_speech_re = re.compile(
            rf'\bI\s+({SPEECH_VERBS})\b', re.IGNORECASE
        )
        if first_person_speech_re.search(window_narration):
            return speaker

        canonical_lower  = speaker.lower()
        speaker_surfaces = {speaker}
        for alias, canon in alias_map.items():
            if canon.lower() == canonical_lower:
                speaker_surfaces.add(alias)
        first = speaker.split()[0]
        if len(first) >= 3:
            speaker_surfaces.add(first)

        name_pattern = "|".join(re.escape(s) for s in sorted(speaker_surfaces, key=len, reverse=True))

        speech_re = re.compile(
            rf'(?:'
            rf'\b({name_pattern})\b.{{0,80}}\b({SPEECH_VERBS})\b'
            rf'|'
            rf'\b({SPEECH_VERBS})\b.{{0,80}}\b({name_pattern})\b'
            rf')',
            re.IGNORECASE | re.DOTALL,
        )

        if speech_re.search(window_narration):
            return speaker

        any_speech_re = re.compile(rf'\b({SPEECH_VERBS})\b', re.IGNORECASE)
        if not any_speech_re.search(window_narration):
            return speaker

        return "Unknown"



    async def _classify_scene_async(
        self,
        client:        httpx.AsyncClient,
        scene:         Dict[str, Any],
        system_prompt: str,
        alias_map:     Dict[str, str],
    ) -> Dict[int, str]:
        quotes     = scene["quotes"]
        raw_text   = scene["text"]

        # Inject [Q:N] / [CONT:N] markers into the passage
        marked_text   = raw_text
        quote_index:  Dict[int, int] = {}
        local_to_uid: Dict[int, int] = {}

        for local_idx, q in enumerate(quotes):
            quote_index[q.uid]       = local_idx
            local_to_uid[local_idx]  = q.uid
            label  = f"[CONT:{local_idx}]" if q.continuation_quote else f"[Q:{local_idx}]"
            target = q.text.replace("\n", " ").strip()[:80]
            pos    = marked_text.find(target)
            if pos != -1:
                marked_text = marked_text[:pos] + label + " " + marked_text[pos:]

        valid_uids = {q.uid for q in quotes}

        prompt_messages = [
            ["system", system_prompt],
            ["user", (
                f'Passage:\n\n{marked_text}\n\n'
                f'There are exactly {len(quotes)} tagged quotes in this passage.\n\n'
                'BEFORE attributing, silently work through each quote in order:\n'
                '1. Find the action beat or narration immediately BEFORE the quote — who is acting?\n'
                '2. Find the action beat or speech verb immediately AFTER the quote — who is acting?\n'
                '3. A name inside a quote is being ADDRESSED — it is NOT the speaker.\n'
                '4. The speaker is whoever is described acting/speaking in the surrounding narration.\n\n'
                f'Tagged quotes to attribute:\n'
                + '\n'.join(f'{i}: {q.text.strip()[:80]}' for i, q in enumerate(quotes))
                + '\n\nOutput ONLY pipe-delimited lines (N|Speaker), one per quote.'
            )],
        ]

        def _resolve(raw_speaker: str) -> str:
            """Resolve a raw speaker string to canonical name via alias map."""
            # Fix concatenated names e.g. "JohnnyCade" → "Johnny Cade"
            speaker = re.sub(r'([a-z])([A-Z])', r'\1 \2', raw_speaker).strip()

            # Filter garbage — must have at least 2 chars and contain a letter
            if len(speaker) < 2 or not re.search(r'[A-Za-z]', speaker):
                return ""

            # Filter non-ASCII garbage e.g. "警官"
            if not re.match(r'^[A-Za-z\s\-\.\'\,]+$', speaker):
                return ""

            # Direct alias map lookup
            canonical = alias_map.get(speaker.lower())
            if canonical:
                return canonical

            # First-name fallback — "Ponyboy" → alias_map["ponyboy"]
            first = speaker.split()[0].lower()
            canonical = alias_map.get(first)
            if canonical:
                return canonical

            # Last-name fallback — "Curtis" → find canonical with that last name
            if len(speaker.split()) == 1:
                for key, val in alias_map.items():
                    if key.endswith(speaker.lower()):
                        return val

            return speaker  # return as-is if no match found

        max_retries = 2
        for attempt in range(max_retries):
            try:
                answer = await self.api.async_chat(
                    client=client,
                    prompt_messages=prompt_messages,
                    inputs={},
                    timeout=REQUEST_TIMEOUT_SECONDS,
                )
                
                result: Dict[int, str] = {}
                for m in re.compile(r'^(\d+)\s*[|:]\s*(.+?)\s*$', re.MULTILINE).finditer(answer):
                    try:
                        local_idx = int(m.group(1))
                        raw       = m.group(2).strip()
                        uid       = local_to_uid.get(local_idx)
                        if uid is None or uid not in valid_uids:
                            continue

                        if raw.lower() in ("unknown", "?", "unclear", "ambiguous"):
                            result[uid] = "Unknown"
                            continue

                        resolved = _resolve(raw)
                        if resolved:
                            result[uid] = resolved

                    except ValueError:
                        continue

                if result:
                    return result

                if attempt < max_retries - 1:
                    self.logger.warning(f"Scene parse empty — retrying (attempt {attempt + 1})")
                    await asyncio.sleep(0.5)
                else:
                    self.logger.warning(f"Scene attribution failed — {len(quotes)} quotes untagged")

            except httpx.HTTPStatusError as e:
                self.logger.error(f"HTTP {e.response.status_code}: {e.response.text[:200]}")
                if e.response.status_code == 503 and attempt < max_retries - 1:
                    await asyncio.sleep(2 ** (attempt + 1))
            except httpx.TimeoutException:
                if attempt < max_retries - 1:
                    self.logger.warning(f"Scene timeout — retrying (attempt {attempt + 1})")
                else:
                    self.logger.error(f"Scene timed out — skipping {len(quotes)} quotes")
                    return {}
            except Exception as e:
                self.logger.error(f"Unexpected scene error: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5)

        return {}

    # ====================================================================
    # STEP 7 — entry point
    # ====================================================================

    def chunk_by_speaker(
        self,
        processed_data:    Dict[str, Any],
        book_title:        str = "Unknown Book",
        concurrency:       int = MAX_CONCURRENT_REQUESTS,
        progress_callback: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        return asyncio.run(
            self._chunk_by_speaker_async(processed_data, book_title, concurrency, progress_callback)
        )


    async def _chunk_by_speaker_async(self, processed_data: Dict[str, Any], book_title: str = "Unknown Book",
                                      concurrency: int = MAX_CONCURRENT_REQUESTS,
                                      progress_callback: Optional[Callable] = None) -> Dict[str, Any]:

        start_time = time.time()
        chunks     = processed_data.get("chunks", [])
        fidelity   = FidelityVerifier()

        # 1. Stitch + split
        full_text, char_map = self._stitch_chunks(chunks)
        all_units           = self._smart_split(full_text, char_map)

        total_units  = len(all_units)
        total_quotes = sum(1 for u in all_units if u.is_quote)
        self.logger.info(f"Split -> {total_units} units ({total_quotes} quotes, {total_units - total_quotes} narration)")

        # Fidelity: verify smart-split preserved all text
        split_report = fidelity.verify_smart_split(full_text, all_units)
        if not split_report.passed:
            self.logger.warning("Smart-split fidelity check failed (confidence=%.4f)", split_report.confidence_score)

        # 2. Title extraction (if needed)
        need_title = not book_title or book_title == "Unknown Book" or self._looks_like_job_id(book_title)
        if need_title:
            book_title = await asyncio.to_thread(self._extract_book_title, chunks)

        # 3. Character discovery (new hybrid NER + LLM module)
        char_discovery = CharacterDiscovery(llm_api=self.api)
        registry       = await asyncio.to_thread(char_discovery.discover, full_text, book_title)

        characters      = registry.characters
        alias_map       = dict(registry.alias_to_canonical)
        narrator_name   = registry.narrator_name
        pov             = registry.pov
        self._alias_to_canonical = alias_map

        known_chars_str  = ", ".join(c.name for c in characters if c.name != "Narrator")
        known_char_names = {c.name for c in characters} | set(alias_map.keys())
        self.logger.info(f"Characters + aliases: {len(known_char_names)} total name entries")

        primer = {
            "pov":           pov,
            "narrator_name": narrator_name,
            "tense":         "Past",
        }

        # 4. Syntax pre-pass: analyse dialogue tags before LLM
        syntax    = SyntaxAnalyzer()
        context   = SpeakerContext()
        char_genders = {c.name: c.gender for c in characters}

        results_map: Dict[int, str] = {}
        syntax_resolved = 0

        for u in all_units:
            if not u.is_quote:
                results_map[u.uid] = narrator_name
                context.update_from_narration(u.text, alias_map, char_genders)
                continue

            idx = self._uid_to_idx.get(u.uid, 0)
            window_start = max(0, idx - 5)
            window_end   = min(len(all_units), idx + 6)
            surrounding  = all_units[window_start:window_end]

            analysis = syntax.analyze_quote(u, surrounding, registry, context)

            if analysis.confidence >= 0.7 and analysis.speaker_candidates:
                speaker = analysis.speaker_candidates[0]
                results_map[u.uid] = speaker
                u.heuristic_confidence = analysis.confidence
                context.update_after_attribution(speaker, char_genders.get(speaker, "unknown"))
                syntax_resolved += 1

        self.logger.info(f"Syntax pre-pass: resolved {syntax_resolved}/{total_quotes} quotes locally")

        # 5. Build scene windows for remaining unresolved quotes
        system_prompt    = self._build_scene_system_prompt(primer, known_chars_str)
        unresolved_units = [u for u in all_units if u.is_quote and u.uid not in results_map]
        scenes           = self._build_scene_windows(full_text, all_units)

        # Filter scenes to only those with unresolved quotes
        unresolved_uids = {u.uid for u in unresolved_units}
        if unresolved_uids:
            for scene in scenes:
                scene["quotes"] = [q for q in scene["quotes"] if q.uid in unresolved_uids]
            scenes = [s for s in scenes if s["quotes"]]

        total_scenes = len(scenes)

        # 6. Async LLM scene attribution (only for unresolved quotes)
        llm_processing_time = 0.0
        scene_times: List[float] = []

        if total_scenes > 0:
            self.logger.info(f"LLM processing {total_scenes} scenes ({len(unresolved_uids)} remaining quotes) @ concurrency={concurrency}")
            completed_count  = 0
            processing_start = time.time()
            semaphore        = asyncio.Semaphore(concurrency)

            async def process_scene(_idx: int, scene: Dict[str, Any], client: httpx.AsyncClient) -> None:
                nonlocal completed_count
                async with semaphore:
                    t0      = time.time()
                    mapping = await self._classify_scene_async(client, scene, system_prompt, alias_map)
                    dur     = time.time() - t0

                    if pov == "First Person" and narrator_name != "Narrator":
                        for uid in list(mapping.keys()):
                            if mapping[uid] in ("Narrator", "I"):
                                mapping[uid] = narrator_name

                    validated_mapping = {
                        uid: self._validate_attribution(uid, spk, all_units, alias_map)
                        for uid, spk in mapping.items()
                    }
                    results_map.update(validated_mapping)

                    # Update speaker context from LLM results
                    for uid, spk in validated_mapping.items():
                        context.update_after_attribution(spk, char_genders.get(spk, "unknown"))

                    scene_times.append(dur)
                    completed_count += 1

                    elapsed  = time.time() - processing_start
                    pct      = round(completed_count / total_scenes * 100, 1)
                    avg_t    = sum(scene_times) / len(scene_times)
                    eta_secs = ((total_scenes - completed_count) / concurrency) * avg_t
                    eta_fmt  = self._format_duration(eta_secs)

                    self.logger.info(
                        f"Scene {completed_count}/{total_scenes} "
                        f"({len(scene['quotes'])} quotes, {dur:.1f}s) | "
                        f"{pct}% | elapsed {self._format_duration(elapsed)} | ETA {eta_fmt}"
                    )
                    if progress_callback:
                        progress_callback({
                            "percent_complete":              pct,
                            "batches_completed":             completed_count,
                            "total_batches":                 total_scenes,
                            "estimated_remaining_formatted": eta_fmt,
                            "estimated_remaining_seconds":   eta_secs,
                            "avg_batch_time":                round(avg_t, 2),
                            "units_per_second":              round(len(scene["quotes"]) / max(dur, 0.01), 2),
                        })

            async with httpx.AsyncClient() as client:
                await asyncio.gather(*[
                    process_scene(i, scene, client)
                    for i, scene in enumerate(scenes)
                ])

            llm_processing_time = time.time() - processing_start
            self.logger.info(f"Scene attribution done in {self._format_duration(llm_processing_time)}")
            if scene_times:
                self.logger.info(
                    f"Scene stats: avg={sum(scene_times)/len(scene_times):.1f}s | "
                    f"min={min(scene_times):.1f}s | max={max(scene_times):.1f}s"
                )
        else:
            self.logger.info("All quotes resolved by syntax pre-pass — no LLM needed")

        # 7. Heuristic recovery for missed quotes
        missed_before_recovery = [u for u in all_units if u.is_quote and u.uid not in results_map]
        if missed_before_recovery:
            self.logger.info(f"Attempting heuristic recovery for {len(missed_before_recovery)} missed quotes...")
            recovered = 0

            all_names    = sorted(alias_map.keys(), key=len, reverse=True)
            name_pat_str = "|".join(re.escape(n) for n in all_names if len(n) >= 2)
            speech_re    = re.compile(
                rf'\b({name_pat_str})\s+({SPEECH_VERBS})\b'
                rf'|({SPEECH_VERBS})\s+({name_pat_str})\b',
                re.IGNORECASE
            )

            for u in missed_before_recovery:
                idx = self._uid_to_idx.get(u.uid, 0)

                for j in range(idx + 1, min(len(all_units), idx + 5)):
                    next_u = all_units[j]
                    if next_u.is_quote:
                        break
                    m = speech_re.search(next_u.text)
                    if m:
                        raw = (m.group(1) or m.group(4) or "").strip()
                        if raw:
                            canonical = alias_map.get(raw.lower(), raw.title())
                            results_map[u.uid] = canonical
                            recovered += 1
                            break

                if u.uid not in results_map:
                    for j in range(max(0, idx - 4), idx):
                        prev_u = all_units[j]
                        if prev_u.is_quote:
                            continue
                        m = speech_re.search(prev_u.text)
                        if m:
                            raw = (m.group(1) or m.group(4) or "").strip()
                            if raw:
                                canonical = alias_map.get(raw.lower(), raw.title())
                                results_map[u.uid] = canonical
                                recovered += 1
                                break

                if u.uid not in results_map:
                    for j in range(idx - 1, max(0, idx - 4), -1):
                        prev_u = all_units[j]
                        if prev_u.is_quote and prev_u.uid in results_map:
                            gap_units     = all_units[j + 1:idx]
                            has_narration = any(not gu.is_quote for gu in gap_units)
                            if not has_narration:
                                results_map[u.uid] = results_map[prev_u.uid]
                                recovered += 1
                            break

            self.logger.info(f"Heuristic recovery: recovered {recovered}/{len(missed_before_recovery)} missed quotes")

        # 8. Reassembly with single merge pass
        self.logger.info("Reassembling segments...")
        is_first_person = pov == "First Person"

        first_person_starters = re.compile(
            r'^[\"\u201c]?\s*I\s+(\'m|was|said|asked|told|thought|knew|felt|saw|heard|'
            r'wanted|needed|tried|started|turned|looked|went|came|got|had|didn\'t|couldn\'t|'
            r'wouldn\'t|shouldn\'t|can\'t|won\'t|don\'t|am|will|would|could|should|might|must)',
            re.IGNORECASE
        )

        # Normalize all speakers first
        for uid in list(results_map.keys()):
            speaker = results_map[uid]
            canonical = alias_map.get(speaker.lower())
            if canonical and canonical != speaker:
                results_map[uid] = canonical
                continue
            if is_first_person and narrator_name != "Narrator" and speaker in ("Unknown", "Narrator", "I"):
                unit = all_units[self._uid_to_idx.get(uid, 0)]
                if not unit.is_quote and first_person_starters.match(unit.text.strip()):
                    results_map[uid] = narrator_name
                elif speaker == "I":
                    results_map[uid] = narrator_name

        # Single merge pass
        STRIP_CHARS = " \t\n\r\u201c\u201d\u2018\u2019\"\'"
        final_segments: List[Dict[str, Any]] = []
        current_segment: Optional[Dict[str, Any]] = None

        for unit in all_units:
            speaker = results_map.get(unit.uid, "Unknown" if unit.is_quote else narrator_name)

            if current_segment is None:
                current_segment = {"speaker": speaker, "text": unit.text,
                                   "chunk_id": unit.chunk_id, "is_quote": unit.is_quote}
            elif (
                current_segment["speaker"] == speaker
                and not unit.is_quote
                and not current_segment["is_quote"]
                and (unit.chunk_id is None or unit.chunk_id == current_segment["chunk_id"])
            ):
                current_segment["text"] += unit.text
            else:
                if len(current_segment.get("text", "").strip(STRIP_CHARS)) >= 2:
                    final_segments.append(current_segment)
                current_segment = {"speaker": speaker, "text": unit.text,
                                   "chunk_id": unit.chunk_id, "is_quote": unit.is_quote}

        if current_segment and len(current_segment.get("text", "").strip(STRIP_CHARS)) >= 2:
            final_segments.append(current_segment)

        # 9. Fidelity final gate
        known_char_set = {c.name for c in characters}
        final_segments, gate_report = fidelity.run_final_gate(
            original_text=full_text,
            segments=final_segments,
            known_characters=known_char_set,
            alias_map=alias_map,
            narrator_name=narrator_name,
            pov=pov,
        )

        fidelity_dict = fidelity.generate_report_dict(gate_report)

        # Strip is_quote from final output
        final_segments = [
            {k: v for k, v in s.items() if k != "is_quote"}
            for s in final_segments
        ]

        # 10. Final stats
        total_time     = time.time() - start_time
        covered_quotes = len([u for u in all_units if u.is_quote and u.uid in results_map])
        compression    = round(total_units / max(len(final_segments), 1), 2)
        speaker_counts: Dict[str, int] = {}
        for seg in final_segments:
            speaker_counts[seg["speaker"]] = speaker_counts.get(seg["speaker"], 0) + 1

        still_missed = total_quotes - covered_quotes
        self.logger.info(f"Quote coverage: {covered_quotes}/{total_quotes} ({round(covered_quotes/max(total_quotes,1)*100,1)}%)")
        self.logger.info(f"Final segments: {len(final_segments)} (compression {compression}x)")
        self.logger.info(f"Speaker distribution: {dict(sorted(speaker_counts.items(), key=lambda x: x[1], reverse=True))}")
        self.logger.info(f"Syntax pre-pass resolved: {syntax_resolved} | LLM resolved: {covered_quotes - syntax_resolved - (len(missed_before_recovery) - still_missed if missed_before_recovery else 0)}")
        self.logger.info(f"Fidelity: {fidelity_dict['overall_status']} (completeness={fidelity_dict['text_completeness']:.4f})")
        self.logger.info(f"Total time: {self._format_duration(total_time)}")

        return {
            "characters": [c.__dict__ for c in characters],
            "segments":   final_segments,
            "primer":     primer,
            "fidelity":   fidelity_dict,
            "meta": {
                "processing_time":        total_time,
                "total_segments":         len(final_segments),
                "total_units":            total_units,
                "compression_ratio":      compression,
                "llm_processing_time":    llm_processing_time,
                "total_quotes":           total_quotes,
                "covered_quotes":         covered_quotes,
                "quote_coverage_pct":     round(covered_quotes / max(total_quotes, 1) * 100, 1),
                "syntax_resolved":        syntax_resolved,
                "avg_scene_time":         sum(scene_times) / len(scene_times) if scene_times else 0,
                "min_scene_time":         min(scene_times) if scene_times else 0,
                "max_scene_time":         max(scene_times) if scene_times else 0,
                "total_scenes":           total_scenes,
                "concurrency":            concurrency,
                "speaker_distribution":   speaker_counts,
                "book_context": {
                    "pov":      pov,
                    "narrator": narrator_name,
                    "tense":    primer.get("tense"),
                },
            },
        }


    @staticmethod
    def _format_duration(seconds: float) -> str:
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            return f"{seconds / 60:.1f}m"
        return f"{seconds / 3600:.1f}h"