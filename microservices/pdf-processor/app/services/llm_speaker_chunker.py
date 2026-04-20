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


@dataclass
class Character:
    name: str
    gender: str
    description: str
    mentioned_count: int = 0
    aliases: List[str] = field(default_factory=list)


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
        self._alias_to_canonical: Dict[str, str] = {} # populated in _discover_characters
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
    # STEP 3 — character discovery via web-RAG (nickname-aware)
    # ====================================================================

    @staticmethod
    def _parse_character_json(raw: str) -> List[Dict]:
        clean = re.sub(r"```(?:json)?|```", "", raw).strip()
        try:
            parsed = json.loads(clean)
            if isinstance(parsed, list):
                return parsed
            return parsed.get("characters", [])
        except json.JSONDecodeError:
            recovered = []
            for m in re.finditer(r'\{[^{}]*"name"[^{}]*\}', clean, re.DOTALL):
                try:
                    obj = json.loads(m.group(0))
                    if obj.get("name"):
                        recovered.append(obj)
                except json.JSONDecodeError:
                    continue
            return recovered


    def _extract_characters_from_text(self, full_text: str) -> List[Dict]:
        self.logger.info("Falling back to text-based character extraction...")
        
        # Use more slices across the full book
        text_len = len(full_text)
        samples = [
            full_text[:8000],
            full_text[text_len//5 : text_len//5 + 6000],
            full_text[text_len//3 : text_len//3 + 6000],
            full_text[text_len//2 : text_len//2 + 6000],
            full_text[2*text_len//3 : 2*text_len//3 + 6000],
        ]
        
        all_chars = []
        
        for i, sample in enumerate(samples):
            try:
                answer = self.api.sync_chat(
                    prompt_messages=[
                        ["system", (
                            "You are a literary analysis assistant. "
                            "Extract every named character who speaks or acts in this text.\n\n"
                            "STRICT RULES:\n"
                            "1. Canonical name must be the character's REAL full name.\n"
                            "2. aliases MUST include the most common short name used in dialogue.\n"
                            "3. NEVER use non-English characters in names or aliases.\n"
                            "4. If unsure about an alias, OMIT it.\n\n"
                            "Return ONLY valid JSON — no markdown, no preamble.\n\n"
                            '{{"characters": [{{"name": "string", "aliases": ["string"], "gender": "male|female|unknown", "description": "1 sentence"}}]}}'
                        )],
                        ["user", f"Text sample {i+1}:\n\n{sample}\n\nReturn ONLY the JSON."],
                    ],
                    inputs={},
                )
                chars = self._parse_character_json(answer)
                self.logger.info(f"Text sample {i+1}: found {len(chars)} characters")
                all_chars.extend(chars)
            except Exception as e:
                self.logger.warning(f"Text sample {i+1} extraction failed: {e}")
                continue
        
        # Deduplicate by name
        seen = {}
        deduped = []
        for c in all_chars:
            name = c.get("name", "").strip().lower()
            if name and name not in seen:
                seen[name] = True
                deduped.append(c)
        
        self.logger.info(f"Text fallback total: {len(deduped)} unique characters found")
        return deduped


    def _discover_characters(self, book_title: str, full_text: str) -> List[Character]:
        self.logger.info(f"Discovering characters: '{book_title}'")

        system_msg = (
            f"You are a literary analysis assistant. "
            f"Using what you know about the '{book_title}' book, list every named character from it'.\n\n"
            "STRICT RULES:\n"
            "1. Canonical name must be the character's REAL full name — no nicknames embedded in it.\n"
            "   CORRECT: 'Dallas Winston'   WRONG: 'Dally Winston' or \"Dallas 'Dally' Winston\"\n"
            "2. aliases MUST include the most common short name used in dialogue — required, not optional.\n"
            "   e.g. 'Ponyboy Curtis' → aliases must include 'Ponyboy'\n"
            "   e.g. 'Dallas Winston' → aliases must include 'Dally'\n"
            "   e.g. 'Sodapop Curtis' → aliases must include 'Soda'\n"
            "3. aliases must ONLY be real nicknames or shortened names — never another character's name.\n"
            "4. NEVER truncate names (e.g. 'Ponyc' is NOT valid).\n"
            "5. NEVER use non-English characters in names or aliases.\n"
            "6. NEVER include a name as an alias if it belongs to a different character.\n"
            "7. If unsure about an alias, OMIT it.\n\n"
            "Return ONLY valid JSON — no markdown, no preamble.\n\n"
            '{{"characters": [{{'
            '"name": "clean full real name — no embedded nicknames", '
            '"aliases": ["most common short name", "other nickname"], '
            '"gender": "male|female|unknown", '
            '"description": "One sentence with the age group, physical and mental character traits in universal terms (focus), and relevance to and role in the story"'
            '}}]}}'
        )

        # system_msg = (
        #     f"You are a literary analysis assistant. "
        #     f"List every named character from '{book_title}'.\n\n"
        #     "STRICT RULES:\n"
        #     "1. Canonical name must be the character's REAL full name — no nicknames embedded in it.\n"
        #     "   CORRECT: 'Dallas Winston'   WRONG: 'Dally Winston' or \"Dallas 'Dally' Winston\"\n"
        #     "2. aliases MUST include the most common short name used in dialogue — required, not optional.\n"
        #     "   e.g. 'Ponyboy Curtis' → aliases must include 'Ponyboy'\n"
        #     "   e.g. 'Dallas Winston' → aliases must include 'Dally'\n"
        #     "   e.g. 'Sodapop Curtis' → aliases must include 'Soda'\n"
        #     "3. aliases must ONLY be real nicknames or shortened names — never another character's name.\n"
        #     "4. NEVER truncate names (e.g. 'Ponyc' is NOT valid).\n"
        #     "5. NEVER use non-English characters in names or aliases.\n"
        #     "6. NEVER include a name as an alias if it belongs to a different character.\n"
        #     "7. If unsure about an alias, OMIT it.\n\n"
        #     "Return ONLY valid JSON — no markdown, no preamble.\n\n"
        #     '{{"characters": [{{'
        #     '"name": "clean full real name — no embedded nicknames", '
        #     '"aliases": ["most common short name", "other nickname"], '
        #     '"gender": "male|female|unknown", '
        #     '"description": "1 sentence"'
        #     '}}]}}'
        # )
        user_msg = (
            f"List every named character from '{book_title}' including nicknames and aliases. "
            "Return ONLY the JSON."
        )

        raw_chars: List[Dict] = []
        try:
            data, _ = self.api.sync_rag_chat(
                prompt_messages=[["system", system_msg], ["user", user_msg]],
                inputs={},
                search_query_template=None,
                # deployment_name="@cf/meta/llama-3.3-70b-instruct-fp8-fast",
                timeout=120,
            )
            breakpoint()
            raw_chars = data.get("characters", [])
            self.logger.info(f"Cloudflare structured returned {len(raw_chars)} raw candidates")
        except Exception as e:
            self.logger.warning(f"Cloudflare character discovery failed: {e}")

        if not raw_chars:
            self.logger.warning("Cloudflare returned 0 characters — using text fallback")
            raw_chars = self._extract_characters_from_text(full_text)

        false_positive_re = [
            r'^(chapter|prologue|epilogue|book|part)(\s+\d+)?$',
            r'^(the\s+)?pattern$',
            r'^(the\s+)?wheel(\s+of\s+time)?$',
            r'^(the\s+)?one\s+power$',
        ]

        validated: List[Character] = []
        seen:      Set[str]        = set()
        alias_to_canonical: Dict[str, str] = {}

        for c in raw_chars:
            name = c.get("name", "").strip()
            if not name or len(name) < 2:
                continue
            if any(re.match(p, name, re.IGNORECASE) for p in false_positive_re):
                continue

            if not re.match(r'^[A-Za-z\s\-\.\'\,]+$', name):
                self.logger.debug(f"Filtered non-ASCII name: {name}")
                continue

            name = re.sub(r"\s*['\"].*?['\"]\s*", " ", name).strip()
            name = re.sub(r"\s+", " ", name)

            key = name.lower()
            if key in seen:
                continue
            seen.add(key)

            raw_aliases = c.get("aliases", [])
            clean_aliases = [
                a.strip() for a in raw_aliases
                if isinstance(a, str)
                and len(a.strip()) >= 2
                and not re.search(r'\d', a)
                and re.match(r'^[A-Za-z\s\-\.\']+$', a.strip())
                and a.strip().lower() != name.lower()
            ]

            first_name = name.split()[0]
            if (first_name.lower() != name.lower()
                    and len(first_name) >= 3
                    and first_name not in clean_aliases
                    and first_name.lower() not in alias_to_canonical):
                clean_aliases.append(first_name)

            name_mentions  = full_text.lower().count(name.lower().split()[0])
            alias_mentions = sum(full_text.lower().count(a.lower()) for a in clean_aliases)
            if name_mentions == 0 and alias_mentions == 0:
                self.logger.debug(f"Filtered zero-mention character: {name}")
                continue

            validated.append(Character(
                name=name,
                gender=c.get("gender", "unknown"),
                description=c.get("description", ""),
                mentioned_count=full_text.lower().count(name.lower()),
                aliases=clean_aliases,
            ))

            alias_to_canonical[name.lower()] = name
            for alias in clean_aliases:
                alias_to_canonical[alias.lower()] = name

        alias_counts: Dict[str, List[str]] = {}
        for alias, canonical in alias_to_canonical.items():
            alias_counts.setdefault(alias, []).append(canonical)
        alias_to_canonical = {
            alias: canonicals[0]
            for alias, canonicals in alias_counts.items()
            if len(canonicals) == 1
        }

        alias_to_chars: Dict[str, List[Character]] = {}
        for char in validated:
            for alias in char.aliases:
                alias_to_chars.setdefault(alias.lower(), []).append(char)

        chars_to_remove: Set[str] = set()
        for alias, chars in alias_to_chars.items():
            if len(chars) > 1:
                chars.sort(key=lambda c: c.mentioned_count, reverse=True)
                for loser in chars[1:]:
                    chars_to_remove.add(loser.name.lower())
                    for a in loser.aliases:
                        if a not in chars[0].aliases:
                            chars[0].aliases.append(a)
                        alias_to_canonical[a.lower()] = chars[0].name

        validated = [c for c in validated if c.name.lower() not in chars_to_remove]

        by_length = sorted(validated, key=lambda c: len(c.name), reverse=True)
        absorbed:  Set[str]        = set()
        deduped:   List[Character] = []

        for char in by_length:
            if char.name.lower() in absorbed:
                continue
            deduped.append(char)
            for other in by_length:
                if other.name != char.name and re.match(
                    r'(?i)^' + re.escape(other.name) + r'\b', char.name
                ):
                    absorbed.add(other.name.lower())

        if not any(c.name == "Narrator" for c in deduped):
            deduped.insert(0, Character("Narrator", "neutral", "The narrative voice of the story", 0))

        deduped.sort(key=lambda c: c.mentioned_count, reverse=True)
        self._alias_to_canonical = alias_to_canonical

        self.logger.info(
            f"Character discovery complete — {len(deduped)} characters, "
            f"{len(alias_to_canonical)} name/alias entries"
        )
        for c in deduped[:15]:
            alias_str = f" aliases: {c.aliases}" if c.aliases else ""
            self.logger.info(f"  → {c.name} ({c.gender}, {c.mentioned_count}x){alias_str}")

        sample = {k: v for k, v in list(alias_to_canonical.items())[:30]}
        self.logger.info(f"Alias map sample (first 30): {sample}")

        return deduped

    # ====================================================================
    # STEP 4 — book primer
    # ====================================================================

    def _generate_book_primer(self, intro_text: str) -> Dict[str, str]:
        self.logger.info("Generating book primer...")
        try:
            answer = self.api.sync_chat(
                prompt_messages=[
                    ["system", (
                        "You are a literary analysis assistant. "
                        "Analyze the opening text and return ONLY valid JSON — no markdown, no preamble.\n\n"
                        "CRITICAL RULES:\n"
                        "- If the text uses 'he', 'she', or character names to describe actions, "
                        "it is THIRD PERSON and narrator_name MUST be 'Narrator'.\n"
                        "- If the narrator uses 'I' or 'me' to describe their own actions, "
                        "it is FIRST PERSON. In that case narrator_name MUST be the actual "
                        "character name of the 'I' narrator — NEVER 'Narrator'.\n"
                        "- To find the First Person narrator's name: look for dialogue tags, "
                        "other characters addressing the narrator by name, or self-identification.\n"
                        "- When in doubt about POV, default to Third Person with narrator_name 'Narrator'.\n\n"
                        '{{"pov": "First Person|Third Person", "narrator_name": "string", "tense": "Past|Present"}}'
                    )],
                    ["user", (
                        f"Opening text:\n\n{intro_text[:6000]}\n\n"
                        "What is the POV? If First Person, what is the narrator's actual name "
                        "(look for other characters calling them by name)? "
                        "Return ONLY the JSON."
                    )],
                ],
                inputs={},
                timeout=120,
            )
            clean = re.sub(r"```(?:json)?|```", "", answer).strip()
            data  = json.loads(clean)

            pov           = data.get("pov", "Third Person")
            narrator_name = data.get("narrator_name", "Narrator")

            if pov == "Third Person":
                narrator_name = "Narrator"

            result = {
                "pov":           pov,
                "narrator_name": narrator_name,
                "tense":         data.get("tense", "Past"),
            }
        except Exception as e:
            self.logger.warning(f"Primer failed: {e} — using defaults")
            result = {"pov": "Third Person", "narrator_name": "Narrator", "tense": "Past"}

        self.logger.info(f"Primer → {result['pov']} | {result['narrator_name']} | {result['tense']}")
        return result

    # ====================================================================
    # STEP 5 — heuristic anchoring (alias-aware)
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

    # ====================================================================
    # STEP 7 — attribution system prompt
    # ====================================================================

    def _build_attribution_system_prompt(self, primer: Dict[str, str]) -> str:
        return (
            f"You are an expert dialogue attribution system.\n\n"
            f"BOOK CONTEXT:\n"
            f"- POV: {primer.get('pov', 'Third Person')}\n"
            f"- Narrator: {primer.get('narrator_name', 'Narrator')}\n"
            f"- Tense: {primer.get('tense', 'Past')}\n\n"
            "TASK: For each [Q] or [CONT] segment, identify the speaker.\n\n"
            "RULES:\n"
            "1. 'Hello,' said John → John. Mary replied, 'Yes.' → Mary.\n"
            "2. Names at START of quote = person ADDRESSED not speaker. 'John, come here!' → someone else speaks.\n"
            "3. [CONT] = ALWAYS same speaker as the immediately preceding quote.\n"
            "4. NEVER output he/she/they — resolve to actual character name from context.\n"
            "5. Truly ambiguous → Unknown\n\n"
            "OUTPUT: one pipe-delimited line per segment: ID|Speaker\n"
            "Example:\n15|Rand\n16|Moiraine\n17|Moiraine\n\n"
            "OUTPUT ONLY PIPE-DELIMITED TAGS. NO explanations. NO JSON."
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
    # STEP 8 — batch formatting  (FIX: O(1) context lookup via _uid_to_idx)
    # ====================================================================

    def _get_surrounding_context(self, unit: TextUnit, all_units: List[TextUnit],
                                  window: int = 2) -> Tuple[str, str]:
        # O(1) lookup instead of O(n) linear scan
        idx = self._uid_to_idx.get(unit.uid)
        if idx is None:
            return "", ""
        before = [all_units[i].text.strip().replace("\n", " ")[:120]
                  for i in range(max(0, idx - window), idx) if not all_units[i].is_quote]
        after  = [all_units[i].text.strip().replace("\n", " ")[:120]
                  for i in range(idx + 1, min(len(all_units), idx + window + 1)) if not all_units[i].is_quote]
        return " ".join(filter(None, before)), " ".join(filter(None, after))

    def _format_batch_lines(self, units: List[TextUnit], all_units: List[TextUnit]) -> str:
        lines = []
        for u in units:
            label      = "[CONT]" if u.continuation_quote else "[Q]"
            quote_text = u.text.replace("\n", " ").strip()[:MAX_QUOTE_CHARS_IN_PROMPT]
            before_ctx, after_ctx = self._get_surrounding_context(u, all_units)
            before_ctx = before_ctx[:MAX_CONTEXT_CHARS_IN_PROMPT]
            after_ctx  = after_ctx[:MAX_CONTEXT_CHARS_IN_PROMPT]
            line = f"{u.uid} {label}: {quote_text}"
            if before_ctx:
                line = f"[Ctx: {before_ctx}] {line}"
            if after_ctx:
                line = f"{line} [After: {after_ctx}]"
            lines.append(line)
        return "\n".join(lines)

    @staticmethod
    def _parse_pipe_response(content: str, valid_uids: Set[int]) -> Dict[int, str]:
        result: Dict[int, str] = {}
        for m in re.compile(r'^(\d+)\s*[|:]\s*(.+?)\s*$', re.MULTILINE).finditer(content):
            try:
                uid     = int(m.group(1))
                speaker = m.group(2).strip()
                if uid in valid_uids and speaker:
                    result[uid] = speaker
            except ValueError:
                continue
        return result

    # ====================================================================
    # STEP 9 — async batch classification
    # ====================================================================

    async def _classify_batch_async(self, client: httpx.AsyncClient, units: List[TextUnit],
                                     all_units: List[TextUnit], known_chars: str,
                                     system_prompt: str) -> Dict[int, str]:
        batch_text = self._format_batch_lines(units, all_units)
        valid_uids = {u.uid for u in units}

        prompt_messages = [
            ["system", system_prompt],
            ["user", (
                f"Characters in this book: {known_chars}\n\n"
                f"Tag these dialogue segments:\n{batch_text}\n\n"
                "Output ONLY pipe-delimited tags (ID|Speaker), one per line."
            )],
        ]

        max_retries = 2
        for attempt in range(max_retries):
            try:
                answer = await self.api.async_chat(
                    client=client,
                    prompt_messages=prompt_messages,
                    inputs={},
                    timeout=REQUEST_TIMEOUT_SECONDS,
                )

                result = self._parse_pipe_response(answer, valid_uids)
                if result:
                    return result

                # fallback JSON parse
                try:
                    clean = re.sub(r"```(?:json)?|```", "", answer).strip()
                    tags  = json.loads(clean).get("tags", {})
                    for k, v in tags.items():
                        uid = int(k)
                        if uid in valid_uids:
                            result[uid] = str(v) if not isinstance(v, dict) else v.get("speaker", "Narrator")
                    if result:
                        return result
                except Exception:
                    pass

                if attempt < max_retries - 1:
                    self.logger.warning(f"Empty parse — retrying (attempt {attempt + 1})")
                    await asyncio.sleep(0.5)
                else:
                    self.logger.warning(f"Batch parse failed — {len(units)} units untagged")

            except httpx.HTTPStatusError as e:
                self.logger.error(f"HTTP {e.response.status_code}: {e.response.text[:200]}")
                if e.response.status_code == 503 and attempt < max_retries - 1:
                    await asyncio.sleep(2 ** (attempt + 1))
            except httpx.TimeoutException:
                if attempt < max_retries - 1:
                    self.logger.warning(f"Timeout — retrying (attempt {attempt + 1})")
                else:
                    self.logger.error(f"Batch timed out after {REQUEST_TIMEOUT_SECONDS}s")
            except Exception as e:
                self.logger.error(f"Unexpected batch error: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5)

        return {}

    # ====================================================================
    # STEP 10 — entry point
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


    async def _chunk_by_speaker_async(self, processed_data:Dict[str, Any], book_title:str = "Unknown Book", concurrency:int = MAX_CONCURRENT_REQUESTS,
                                    progress_callback: Optional[Callable] = None,) -> Dict[str, Any]:

        start_time = time.time()
        chunks     = processed_data.get("chunks", [])

        # 1. Stitch + split
        full_text, char_map = self._stitch_chunks(chunks)
        all_units           = self._smart_split(full_text, char_map)
        
        total_units         = len(all_units)
        total_quotes        = sum(1 for u in all_units if u.is_quote)
        self.logger.info(f"Split → {total_units} units ({total_quotes} quotes, {total_units - total_quotes} narration)")

        # 2. Primer + title in parallel
        intro_text = " ".join(c["text"] for c in chunks[:30])
        need_title = not book_title or book_title == "Unknown Book" or self._looks_like_job_id(book_title)

        if need_title:
            self.logger.info("Running primer + title extraction in parallel...")
            primer, book_title = await asyncio.gather(
                asyncio.to_thread(self._generate_book_primer, intro_text),
                asyncio.to_thread(self._extract_book_title, chunks),
            )
        else:
            primer = await asyncio.to_thread(self._generate_book_primer, intro_text)
        
        # 3. Character discovery
        characters      = self._discover_characters(book_title, full_text)
        known_chars_str = ", ".join(c.name for c in characters if c.name != "Narrator")
        known_char_names: Set[str] = {c.name for c in characters}
        known_char_names |= set(self._alias_to_canonical.keys())
        self.logger.info(f"Characters + aliases: {len(known_char_names)} total name entries")

        # 4. Pre-tag narration
        alias_map = dict(self._alias_to_canonical)
        narrator_name = primer.get("narrator_name", "Narrator")

        # Correct First Person narrator if LLM defaulted to "Narrator"
        if primer.get("pov") == "First Person" and narrator_name == "Narrator":
            best_candidate = None
            best_count     = 0
            for char in characters:
                if char.name == "Narrator":
                    continue
                first = char.name.split()[0].lower()
                count = intro_text.lower().count(first)
                if count >= 5 and count > best_count:
                    best_count     = count
                    best_candidate = char.name
            if best_candidate:
                narrator_name           = best_candidate
                primer["narrator_name"] = narrator_name
                self.logger.info(f"First Person narrator corrected to: '{narrator_name}' ({best_count} mentions in intro)")
            else:
                narrator_name           = "Narrator"
                primer["narrator_name"] = "Narrator"
                self.logger.warning("Could not confidently identify First Person narrator — defaulting to 'Narrator'")

        # Resolve narrator alias to canonical
        narrator_canonical = alias_map.get(narrator_name.lower())
        if narrator_canonical:
            narrator_name           = narrator_canonical
            primer["narrator_name"] = narrator_name
            self.logger.info(f"Narrator name resolved to canonical: '{narrator_name}'")

        results_map: Dict[int, str] = {}
        for u in all_units:
            if not u.is_quote:
                results_map[u.uid] = narrator_name

        self.logger.info(f"Pre-tagged {total_units - total_quotes} narration units as '{narrator_name}'")

        # 5. Build scene windows
        system_prompt = self._build_scene_system_prompt(primer, known_chars_str)
        scenes        = self._build_scene_windows(full_text, all_units)
        total_scenes  = len(scenes)

        # 6. Async scene attribution
        llm_processing_time = 0.0
        scene_times: List[float] = []

        if total_scenes > 0:
            self.logger.info(f"Processing {total_scenes} scenes @ concurrency={concurrency}")
            completed_count  = 0
            processing_start = time.time()
            semaphore        = asyncio.Semaphore(concurrency)

            async def process_scene(_idx: int, scene: Dict[str, Any], client: httpx.AsyncClient) -> None:
                nonlocal completed_count
                async with semaphore:
                    t0      = time.time()
                    mapping = await self._classify_scene_async(
                        client, scene, system_prompt, alias_map)
                    dur     = time.time() - t0

                    # First-person normalisation — "Narrator" and "I" → narrator_name
                    if primer.get("pov") == "First Person" and narrator_name != "Narrator":
                        for uid in list(mapping.keys()):
                            if mapping[uid] in ("Narrator", "I"):
                                mapping[uid] = narrator_name

                    validated_mapping = {
                        uid: self._validate_attribution(uid, spk, all_units, alias_map)
                        for uid, spk in mapping.items()
                    }
                    results_map.update(validated_mapping)
                    
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
            self.logger.error(f"ISSUE getting scene quotes")
        
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

                # Check narration AFTER the quote
                for j in range(idx + 1, min(len(all_units), idx + 5)):
                    next_u = all_units[j]
                    if next_u.is_quote:
                        break
                    m = speech_re.search(next_u.text)
                    if m:
                        raw       = (m.group(1) or m.group(4) or "").strip()
                        if raw:
                            canonical = alias_map.get(raw.lower(), raw.title())
                            results_map[u.uid] = canonical
                            recovered += 1
                            break

                # Check narration BEFORE the quote
                if u.uid not in results_map:
                    for j in range(max(0, idx - 4), idx):
                        prev_u = all_units[j]
                        if prev_u.is_quote:
                            continue
                        m = speech_re.search(prev_u.text)
                        if m:
                            raw       = (m.group(1) or m.group(4) or "").strip()
                            if raw:
                                canonical = alias_map.get(raw.lower(), raw.title())
                                results_map[u.uid] = canonical
                                recovered += 1
                                break

                # Check if previous quote has same speaker (continuation — no narration gap)
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

        # 8. Reassembly
        self.logger.info("Reassembling segments...")
        final_segments: List[Dict[str, Any]]      = []
        current_segment: Optional[Dict[str, Any]] = None

        for unit in all_units:
            speaker = results_map.get(unit.uid, "Unknown" if unit.is_quote else narrator_name)

            if current_segment is None:
                current_segment = {"speaker": speaker, "text": unit.text, 
                                "chunk_id": unit.chunk_id, "is_quote": unit.is_quote}
            elif (
                current_segment["speaker"] == speaker
                and not unit.is_quote                          # ← never merge quotes
                and not current_segment["is_quote"]            # ← never merge into a quote
                and (unit.chunk_id is None or unit.chunk_id == current_segment["chunk_id"])
            ):
                current_segment["text"] += unit.text
            else:
                final_segments.append(current_segment)
                current_segment = {"speaker": speaker, "text": unit.text,
                                "chunk_id": unit.chunk_id, "is_quote": unit.is_quote}

        if current_segment:
            final_segments.append(current_segment)

        # 9. Filter empty/junk segments
        STRIP_CHARS   = " \t\n\r\u201c\u201d\u2018\u2019\"\'"
        before_filter = len(final_segments)
        final_segments = [
            s for s in final_segments
            if len(s.get("text", "").strip(STRIP_CHARS)) >= 2
        ]
        dropped = before_filter - len(final_segments)
        if dropped:
            self.logger.info(f"Filtered {dropped} empty/junk segments")

        # 10. Post-processing normalization
        is_first_person = primer.get("pov") == "First Person"

        first_person_starters = re.compile(
            r'^[\"\u201c]?\s*I\s+(\'m|was|said|asked|told|thought|knew|felt|saw|heard|'
            r'wanted|needed|tried|started|turned|looked|went|came|got|had|didn\'t|couldn\'t|'
            r'wouldn\'t|shouldn\'t|can\'t|won\'t|don\'t|am|will|would|could|should|might|must)',
            re.IGNORECASE
        )

        for seg in final_segments:
            canonical = alias_map.get(seg["speaker"].lower())
            if canonical and canonical != seg["speaker"]:
                seg["speaker"] = canonical
                continue

            if (
                is_first_person
                and narrator_name != "Narrator"
                and seg["speaker"] in ("Unknown", "Narrator", "I")
            ):
                text = seg["text"].strip()
                if first_person_starters.match(text):
                    seg["speaker"] = narrator_name

            if seg["speaker"] == "I" and is_first_person and narrator_name != "Narrator":
                seg["speaker"] = narrator_name

        # Re-merge adjacent same-speaker NARRATION segments after normalization
        # is_quote is still present here — used as guard, stripped at end
        merged_segments: List[Dict[str, Any]] = []
        current_m: Optional[Dict[str, Any]]   = None
        for seg in final_segments:
            if current_m is None:
                current_m = dict(seg)
            elif (
                current_m["speaker"] == seg["speaker"]
                and not seg.get("is_quote")          # never merge quotes
                and not current_m.get("is_quote")    # never merge into a quote
                and (seg["chunk_id"] is None or seg["chunk_id"] == current_m["chunk_id"])
            ):
                current_m["text"] += seg["text"]
            else:
                merged_segments.append(current_m)
                current_m = dict(seg)
        if current_m:
            merged_segments.append(current_m)

        # Strip is_quote now that re-merge is done
        final_segments = [
            {k: v for k, v in s.items() if k != "is_quote"}
            for s in merged_segments
        ]

        # 11. Write missed quotes to moe.txt
        still_missed = [u for u in all_units if u.is_quote and u.uid not in results_map]
        if still_missed:
            try:
                with open("moe.txt", "w", encoding="utf-8") as f:
                    f.write(f"MISSED QUOTES REPORT\n")
                    f.write(f"Book:  {book_title}\n")
                    f.write(f"Total: {len(still_missed)} missed / {total_quotes} total quotes\n")
                    f.write(f"{'=' * 60}\n\n")
                    for i, u in enumerate(still_missed, 1):
                        idx       = self._uid_to_idx.get(u.uid, 0)
                        prev_text = ""
                        next_text = ""
                        for j in range(max(0, idx - 3), idx):
                            if not all_units[j].is_quote:
                                prev_text += all_units[j].text.strip() + " "
                        for j in range(idx + 1, min(len(all_units), idx + 4)):
                            if not all_units[j].is_quote:
                                next_text += all_units[j].text.strip() + " "
                        f.write(f"─── Missed Quote #{i} (uid={u.uid}) ───\n")
                        if prev_text.strip():
                            f.write(f"  [Before] {prev_text.strip()[:200]}\n")
                        f.write(f"  [QUOTE]  {u.text.strip()[:300]}\n")
                        if next_text.strip():
                            f.write(f"  [After]  {next_text.strip()[:200]}\n")
                        f.write("\n")
                self.logger.info(f"Missed quotes written to moe.txt ({len(still_missed)} quotes)")
            except Exception as e:
                self.logger.warning(f"Failed to write moe.txt: {e}")

        # 12. Final stats
        total_time     = time.time() - start_time
        covered_quotes = len([u for u in all_units if u.is_quote and u.uid in results_map])
        compression    = round(total_units / max(len(final_segments), 1), 2)
        speaker_counts: Dict[str, int] = {}
        for seg in final_segments:
            speaker_counts[seg["speaker"]] = speaker_counts.get(seg["speaker"], 0) + 1

        self.logger.info(f"Quote coverage: {covered_quotes}/{total_quotes} ({round(covered_quotes/max(total_quotes,1)*100,1)}%)")
        self.logger.info(f"Final segments: {len(final_segments)} (compression {compression}x)")
        self.logger.info(f"Speaker distribution: {dict(sorted(speaker_counts.items(), key=lambda x: x[1], reverse=True))}")
        self.logger.info(f"Total time: {self._format_duration(total_time)}")

        return {
            "characters": [c.__dict__ for c in characters],
            "segments":   final_segments,
            "primer":     primer,
            "meta": {
                "processing_time":        total_time,
                "total_segments":         len(final_segments),
                "total_units":            total_units,
                "compression_ratio":      compression,
                "llm_processing_time":    llm_processing_time,
                "total_quotes":           total_quotes,
                "covered_quotes":         covered_quotes,
                "quote_coverage_pct":     round(covered_quotes / max(total_quotes, 1) * 100, 1),
                "avg_scene_time":         sum(scene_times) / len(scene_times) if scene_times else 0,
                "min_scene_time":         min(scene_times) if scene_times else 0,
                "max_scene_time":         max(scene_times) if scene_times else 0,
                "total_scenes":           total_scenes,
                "concurrency":            concurrency,
                "speaker_distribution":   speaker_counts,
                "book_context": {
                    "pov":      primer.get("pov"),
                    "narrator": primer.get("narrator_name"),
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