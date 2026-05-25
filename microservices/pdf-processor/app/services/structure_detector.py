"""
Structure Detector

Identifies chapter boundaries in PDFs and EPUBs using a four-tier cascade:
Tier 1 - PDF TOC bookmarks (highest confidence)
Tier 2 - Font/position heuristics via PyMuPDF span metadata
Tier 3 - Regex pattern matching
Tier 4 - LLM validation for low-confidence candidates (optional, graceful degradation)
"""
__author__ = "Andrew D'Angelo"

import re
import io
import statistics
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import fitz
import ebooklib
from ebooklib import epub
import httpx

from app.core.logging_config import Logger
from app.core.config_settings import settings


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Font size ratio above which a span is considered a heading candidate
_HEADING_FONT_RATIO = 1.3

# Minimum character count for a chapter to be considered non-trivial
_MIN_CHAPTER_CHARS = 100

# Characters of surrounding context sent to the LLM for Tier 4 validation
_LLM_CONTEXT_CHARS = 500

# Confidence threshold below which Tier 4 LLM validation is attempted
_LLM_CONFIDENCE_THRESHOLD = 0.7

# fitz span flag bitmask for bold weight
_FITZ_BOLD_FLAG = 1 << 4

# fitz span flag bitmask for italic
_FITZ_ITALIC_FLAG = 1 << 1

# Patterns that mark scene breaks within a chapter
_SCENE_BREAK_PATTERNS = re.compile(
    r"^\s*(\*\s*\*\s*\*|\*{3,}|-{3,}|_{3,}|~\s*~\s*~)\s*$",
    re.MULTILINE,
)

_BLANK_LINE_SCENE_BREAK = re.compile(r"(\n\s*){3,}")

# ---------------------------------------------------------------------------
# Regex chapter-heading patterns (Tier 3)
# ---------------------------------------------------------------------------

_CHAPTER_PATTERNS: List[re.Pattern] = [
    # "Chapter 1", "CHAPTER 1", "chapter 1"
    re.compile(r"^\s*(chapter)\s+\d+[:\.\-\s]*.*$", re.IGNORECASE | re.MULTILINE),
    # "Chapter One", "CHAPTER TWO", etc.
    re.compile(
        r"^\s*(chapter)\s+(one|two|three|four|five|six|seven|eight|nine|ten|"
        r"eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|"
        r"nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|"
        r"hundred)[:\.\-\s]*.*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    # "Part 1", "PART II"
    re.compile(r"^\s*(part)\s+(\d+|[IVXivx]+)[:\.\-\s]*.*$", re.IGNORECASE | re.MULTILINE),
    # Standalone roman numerals on their own line: "I.", "II.", "III.", "IV." etc.
    re.compile(r"^\s*(M{0,4}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3}))\.\s*$", re.MULTILINE),
    # Special section names
    re.compile(
        r"^\s*(prologue|epilogue|introduction|foreword|afterword|preface|"
        r"acknowledgements?|appendix|interlude|intermission|coda)\s*[:\.\-]?\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    # Numbered sections like "1." or "1 -" at the very start of a line
    re.compile(r"^\s*\d{1,3}[\.\-]\s+\S", re.MULTILINE),
]

# Standalone all-caps lines shorter than 60 chars (possible untitled chapters)
_ALL_CAPS_HEADING = re.compile(r"^[A-Z][A-Z\s\d\-:,'\"]{2,58}[A-Z\d]$", re.MULTILINE)

# Word-numeral roman numeral matcher (reused when checking roman-numeral lines)
_ROMAN_NUMERAL = re.compile(
    r"^(M{0,4}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3}))$",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class TextBlock:
    text: str
    page_num: int
    bbox: tuple  # (x0, y0, x1, y1)
    font_size: float
    is_bold: bool
    is_uppercase: bool
    is_italic: bool
    block_type: str  # "text", "heading_candidate", "scene_break"


@dataclass
class Chapter:
    chapter_number: int
    title: str
    start_page: int
    end_page: int
    text: str
    page_range: List[int]
    detection_method: str  # "toc", "font", "regex", "llm", "none"
    confidence: float
    scene_breaks: List[int] = field(default_factory=list)  # char offsets within `text`


# ---------------------------------------------------------------------------
# Internal LLM API (mirrors llm_speaker_chunker._InternalAPI)
# ---------------------------------------------------------------------------

class _InternalAPI:
    """Routes LLM calls through the internal /ai/chat endpoint."""

    def __init__(self, base_url: str, model: str, provider: str):
        self.chat_url = f"{base_url}/ai/chat"
        self.model = model
        self.provider = provider

    def _payload(self, prompt_messages: List[List[str]], inputs: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "preset": "chat-knowledge",
            "prompt_messages": prompt_messages,
        }

    def sync_chat(
        self,
        prompt_messages: List[List[str]],
        inputs: Dict[str, Any],
        timeout: int = 60,
    ) -> str:
        payload = self._payload(prompt_messages, inputs)
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(self.chat_url, json=payload)
            if not resp.is_success:
                raise httpx.HTTPStatusError(
                    f"Chat {resp.status_code}: {resp.text[:300]}",
                    request=resp.request,
                    response=resp,
                )
            return resp.json()["answer"]


# ---------------------------------------------------------------------------
# StructureDetector
# ---------------------------------------------------------------------------

class StructureDetector(Logger):
    """
    Detects chapter structure in PDFs and EPUBs.

    The four-tier cascade stops as soon as a tier produces results with
    sufficient coverage.  Tier 4 (LLM) is optional and degrades gracefully
    when no llm_api is provided or when the endpoint is unreachable.
    """

    def __init__(self, llm_api: Optional[_InternalAPI] = None):
        self._llm_api = llm_api

    # ------------------------------------------------------------------
    # Public entry points
    # ------------------------------------------------------------------

    def detect_chapters_from_pdf(
        self,
        pdf_data: bytes,
        extracted_blocks: List[TextBlock],
    ) -> List[Chapter]:
        """
        Main entry point for PDF chapter detection.

        Tries tiers in order, falling back to the next tier when the current
        one produces fewer than two chapters.
        """
        pdf_doc = fitz.open(stream=pdf_data, filetype="pdf")

        page_texts: List[str] = [page.get_text("text") for page in pdf_doc]
        full_text = "\n\n".join(page_texts)

        chapters: List[Chapter] = []

        # Tier 1 — TOC bookmarks
        chapters = self._detect_from_toc(pdf_doc, full_text, page_texts)
        if len(chapters) >= 2:
            self.logger.info("Structure: Tier 1 (TOC) found %d chapters", len(chapters))
            pdf_doc.close()
            return self._assign_chapter_text(chapters, full_text, page_texts)

        # Tier 2 — font/position heuristics
        if extracted_blocks:
            font_chapters = self._detect_from_font(extracted_blocks, full_text)
            if len(font_chapters) >= 2:
                self.logger.info("Structure: Tier 2 (font) found %d chapters", len(font_chapters))
                chapters = font_chapters
                if self._needs_llm_validation(chapters):
                    chapters = self._validate_with_llm(chapters, full_text)
                pdf_doc.close()
                return self._assign_chapter_text(chapters, full_text, page_texts)

        # Tier 3 — regex
        regex_chapters = self._detect_from_regex(full_text, page_texts)
        if len(regex_chapters) >= 2:
            self.logger.info("Structure: Tier 3 (regex) found %d chapters", len(regex_chapters))
            chapters = self._merge_chapter_candidates(chapters, regex_chapters)
            if self._needs_llm_validation(chapters):
                chapters = self._validate_with_llm(chapters, full_text)
            pdf_doc.close()
            return self._assign_chapter_text(chapters, full_text, page_texts)

        pdf_doc.close()

        # Fallback — no detectable structure
        self.logger.warning("Structure: no chapter boundaries detected; treating as single chapter")
        return self._single_chapter_fallback(full_text, len(page_texts))

    def detect_chapters_from_epub(self, epub_book) -> List[Chapter]:
        """
        Extract chapters from an EPUB using ebooklib.

        Uses the book's TOC when available; falls back to one chapter per
        spine ITEM_DOCUMENT when no TOC is present.
        """
        chapters: List[Chapter] = []
        chapter_num = 1

        toc_entries = self._flatten_epub_toc(epub_book.toc)

        if toc_entries:
            # Build a map from spine item file name to content
            spine_content: Dict[str, str] = {}
            for item in epub_book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
                spine_content[item.get_name()] = self._epub_item_to_text(item)

            for title, file_name in toc_entries:
                text = spine_content.get(file_name, "")
                if len(text) < _MIN_CHAPTER_CHARS:
                    continue
                scene_breaks = self._find_scene_break_offsets(text)
                chapters.append(
                    Chapter(
                        chapter_number=chapter_num,
                        title=title,
                        start_page=0,
                        end_page=0,
                        text=text,
                        page_range=[],
                        detection_method="toc",
                        confidence=1.0,
                        scene_breaks=scene_breaks,
                    )
                )
                chapter_num += 1
        else:
            for item in epub_book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
                text = self._epub_item_to_text(item)
                if len(text) < _MIN_CHAPTER_CHARS:
                    continue
                scene_breaks = self._find_scene_break_offsets(text)
                chapters.append(
                    Chapter(
                        chapter_number=chapter_num,
                        title=f"Chapter {chapter_num}",
                        start_page=0,
                        end_page=0,
                        text=text,
                        page_range=[],
                        detection_method="toc",
                        confidence=0.8,
                        scene_breaks=scene_breaks,
                    )
                )
                chapter_num += 1

        if not chapters:
            full_text = "\n\n".join(
                self._epub_item_to_text(item)
                for item in epub_book.get_items_of_type(ebooklib.ITEM_DOCUMENT)
            )
            return self._single_chapter_fallback(full_text, 0)

        self.logger.info("Structure (EPUB): %d chapters via %s", len(chapters), "toc" if toc_entries else "spine")
        return chapters

    def extract_text_blocks(
        self, pdf_data: bytes
    ) -> Tuple[List[TextBlock], List[dict]]:
        """
        Extract text blocks with structural metadata from a PDF.

        Uses page.get_text("dict") to capture per-span font information.
        Returns (blocks, page_map) where page_map follows the existing format:
        [{"page": N, "start": M, "end": K, "char_count": C}, ...]
        """
        pdf = fitz.open(stream=pdf_data, filetype="pdf")
        blocks: List[TextBlock] = []
        page_map: List[dict] = []
        current_pos = 0

        for page_num, page in enumerate(pdf, start=1):
            page_dict = page.get_text("dict")
            page_width = page.rect.width
            page_text_parts: List[str] = []

            for raw_block in page_dict.get("blocks", []):
                if raw_block.get("type") != 0:
                    continue

                for line in raw_block.get("lines", []):
                    for span in line.get("spans", []):
                        span_text = span.get("text", "").strip()
                        if not span_text:
                            continue

                        font_size = span.get("size", 0.0)
                        flags = span.get("flags", 0)
                        is_bold = bool(flags & _FITZ_BOLD_FLAG)
                        is_italic = bool(flags & _FITZ_ITALIC_FLAG)
                        is_uppercase = span_text == span_text.upper() and any(c.isalpha() for c in span_text)
                        bbox = span.get("bbox", (0, 0, 0, 0))

                        # Centered: left margin > 15% of page width and right margin symmetrical
                        x0, _, x1, _ = bbox
                        span_width = x1 - x0
                        left_margin = x0
                        right_margin = page_width - x1
                        is_centered = (
                            left_margin > page_width * 0.15
                            and abs(left_margin - right_margin) < page_width * 0.15
                        )

                        block_type = "text"
                        if is_centered or is_bold or is_uppercase:
                            block_type = "heading_candidate"

                        blocks.append(
                            TextBlock(
                                text=span_text,
                                page_num=page_num,
                                bbox=tuple(bbox),
                                font_size=font_size,
                                is_bold=is_bold,
                                is_uppercase=is_uppercase,
                                is_italic=is_italic,
                                block_type=block_type,
                            )
                        )
                        page_text_parts.append(span_text)

            page_text = " ".join(page_text_parts)
            char_count = len(page_text)
            page_map.append(
                {
                    "page": page_num,
                    "start": current_pos,
                    "end": current_pos + char_count,
                    "char_count": char_count,
                }
            )
            current_pos += char_count + 2  # account for separator

        pdf.close()
        return blocks, page_map

    # ------------------------------------------------------------------
    # Tier 1 — PDF TOC
    # ------------------------------------------------------------------

    def _detect_from_toc(
        self,
        pdf_doc: fitz.Document,
        full_text: str,
        page_texts: List[str],
    ) -> List[Chapter]:
        """
        Build chapters from PDF bookmark/outline entries via get_toc().

        get_toc() returns a list of [level, title, page] triples where
        page is 1-based.  We use only level-1 entries to avoid nesting.
        """
        toc = pdf_doc.get_toc(simple=True)
        if not toc:
            return []

        # Use only the shallowest level present
        min_level = min(entry[0] for entry in toc)
        top_entries = [entry for entry in toc if entry[0] == min_level]

        chapters: List[Chapter] = []
        total_pages = pdf_doc.page_count

        for idx, (level, title, page_1based) in enumerate(top_entries):
            start_page = max(1, page_1based)
            if idx + 1 < len(top_entries):
                end_page = max(start_page, top_entries[idx + 1][2] - 1)
            else:
                end_page = total_pages

            # Guard against inverted ranges caused by label offsets
            if end_page < start_page:
                end_page = start_page

            page_range = list(range(start_page, end_page + 1))

            chapters.append(
                Chapter(
                    chapter_number=idx + 1,
                    title=title.strip(),
                    start_page=start_page,
                    end_page=end_page,
                    text="",
                    page_range=page_range,
                    detection_method="toc",
                    confidence=1.0,
                )
            )

        return chapters

    # ------------------------------------------------------------------
    # Tier 2 — Font/position heuristics
    # ------------------------------------------------------------------

    def _detect_from_font(
        self,
        blocks: List[TextBlock],
        full_text: str,
    ) -> List[Chapter]:
        """
        Identify chapter headings by comparing each block's font size against
        the median body font size and checking bold/centered flags.
        """
        median_size = self._compute_median_font_size(blocks)
        if median_size == 0:
            return []

        heading_blocks: List[TextBlock] = []
        seen_pages: set = set()

        for block in blocks:
            if block.page_num in seen_pages:
                continue
            is_large = block.font_size > median_size * _HEADING_FONT_RATIO
            if (is_large or block.is_bold) and block.block_type == "heading_candidate":
                heading_blocks.append(block)
                seen_pages.add(block.page_num)

        if not heading_blocks:
            return []

        chapters: List[Chapter] = []
        for idx, hb in enumerate(heading_blocks):
            confidence = 0.75 if hb.font_size > median_size * _HEADING_FONT_RATIO else 0.6
            if hb.is_bold and hb.font_size > median_size * _HEADING_FONT_RATIO:
                confidence = 0.85

            chapters.append(
                Chapter(
                    chapter_number=idx + 1,
                    title=hb.text[:200],
                    start_page=hb.page_num,
                    end_page=hb.page_num,
                    text="",
                    page_range=[hb.page_num],
                    detection_method="font",
                    confidence=confidence,
                )
            )

        return chapters

    # ------------------------------------------------------------------
    # Tier 3 — Regex pattern matching
    # ------------------------------------------------------------------

    def _detect_from_regex(
        self,
        full_text: str,
        page_texts: List[str],
    ) -> List[Chapter]:
        """
        Find chapter headings by running the compiled regex patterns against
        per-page text so we can recover accurate page numbers.
        """
        candidates: List[Tuple[int, str, float]] = []  # (page_num, title, confidence)

        for page_idx, page_text in enumerate(page_texts):
            page_num = page_idx + 1

            for pattern in _CHAPTER_PATTERNS:
                for match in pattern.finditer(page_text):
                    heading = match.group(0).strip()
                    if not heading or len(heading) > 200:
                        continue
                    # Assign confidence based on how specific the pattern is
                    conf = 0.8 if re.search(r"chapter|part|prologue|epilogue|introduction|foreword|afterword|preface", heading, re.IGNORECASE) else 0.55
                    candidates.append((page_num, heading, conf))
                    break  # one match per pattern per page

            # Standalone all-caps lines
            for match in _ALL_CAPS_HEADING.finditer(page_text):
                heading = match.group(0).strip()
                if not heading:
                    continue
                # Skip if already captured by a named pattern
                already = any(p == page_num and t == heading for p, t, _ in candidates)
                if not already:
                    candidates.append((page_num, heading, 0.5))

        if not candidates:
            return []

        # Deduplicate: one heading per page, keep highest confidence
        by_page: Dict[int, Tuple[str, float]] = {}
        for page_num, title, conf in candidates:
            if page_num not in by_page or conf > by_page[page_num][1]:
                by_page[page_num] = (title, conf)

        chapters: List[Chapter] = []
        for idx, page_num in enumerate(sorted(by_page)):
            title, conf = by_page[page_num]
            chapters.append(
                Chapter(
                    chapter_number=idx + 1,
                    title=title,
                    start_page=page_num,
                    end_page=page_num,
                    text="",
                    page_range=[page_num],
                    detection_method="regex",
                    confidence=conf,
                )
            )

        return chapters

    # ------------------------------------------------------------------
    # Tier 4 — LLM validation
    # ------------------------------------------------------------------

    def _validate_with_llm(
        self,
        candidates: List[Chapter],
        full_text: str,
    ) -> List[Chapter]:
        """
        For each candidate with confidence below the threshold, ask the LLM
        whether the heading is genuinely a chapter/section heading.

        Removes candidates that the LLM says are NOT headings.
        Gracefully degrades if the LLM API is unavailable.
        """
        if self._llm_api is None:
            return candidates

        validated: List[Chapter] = []
        for chapter in candidates:
            if chapter.confidence >= _LLM_CONFIDENCE_THRESHOLD:
                validated.append(chapter)
                continue

            # Locate the heading in full_text and extract surrounding context
            heading_pos = full_text.find(chapter.title)
            if heading_pos == -1:
                validated.append(chapter)
                continue

            ctx_start = max(0, heading_pos - _LLM_CONTEXT_CHARS)
            ctx_end = min(len(full_text), heading_pos + len(chapter.title) + _LLM_CONTEXT_CHARS)
            context_snippet = full_text[ctx_start:ctx_end]

            prompt_messages = [
                [
                    "system",
                    (
                        "You are a text structure analyst. Given a candidate heading and its "
                        "surrounding context from a book, reply with exactly YES if it is a "
                        "chapter or section heading, or NO if it is not."
                    ),
                ],
                [
                    "user",
                    (
                        f'Candidate heading: "{chapter.title}"\n\n'
                        f"Context:\n{context_snippet}\n\n"
                        "Is this a chapter/section heading? Reply YES or NO only."
                    ),
                ],
            ]

            try:
                answer = self._llm_api.sync_chat(prompt_messages, {}, timeout=30)
                if "NO" in answer.upper():
                    self.logger.debug(
                        "LLM rejected heading candidate: %r", chapter.title[:60]
                    )
                    continue
                chapter.confidence = min(1.0, chapter.confidence + 0.2)
                chapter.detection_method = "llm"
            except Exception as exc:
                self.logger.warning(
                    "LLM validation unavailable for %r: %s", chapter.title[:60], exc
                )
                # Keep the candidate unchanged rather than discarding it
                validated.append(chapter)
                continue

            validated.append(chapter)

        return validated

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _compute_median_font_size(self, blocks: List[TextBlock]) -> float:
        """Return the median font size across all text blocks, or 0.0 if none."""
        sizes = [b.font_size for b in blocks if b.font_size > 0]
        if not sizes:
            return 0.0
        return statistics.median(sizes)

    def _merge_chapter_candidates(self, *candidate_lists: List[Chapter]) -> List[Chapter]:
        """
        Merge chapter candidates from multiple tiers.

        Candidates are keyed by start_page; higher-confidence entries win.
        Renumbers chapter_number sequentially after merging.
        """
        by_page: Dict[int, Chapter] = {}
        for candidate_list in candidate_lists:
            for chapter in candidate_list:
                existing = by_page.get(chapter.start_page)
                if existing is None or chapter.confidence > existing.confidence:
                    by_page[chapter.start_page] = chapter

        merged = sorted(by_page.values(), key=lambda c: c.start_page)
        for idx, chapter in enumerate(merged, start=1):
            chapter.chapter_number = idx
        return merged

    def _assign_chapter_text(
        self,
        chapters: List[Chapter],
        full_text: str,
        page_texts: List[str],
    ) -> List[Chapter]:
        """
        Slice full_text between chapter boundaries and assign text + page_range.

        For chapters detected by TOC/font/regex we know only the start page.
        We infer end pages from the start page of the next chapter and then
        extract the corresponding slice from full_text.

        Very short chapters (< _MIN_CHAPTER_CHARS) that contain only a title
        are merged into the following chapter to avoid orphaned title pages.
        """
        if not chapters:
            return chapters

        total_pages = len(page_texts)

        # Fill in end_page from next chapter's start_page
        for idx, chapter in enumerate(chapters):
            if idx + 1 < len(chapters):
                chapter.end_page = max(chapter.start_page, chapters[idx + 1].start_page - 1)
            else:
                chapter.end_page = total_pages
            chapter.page_range = list(range(chapter.start_page, chapter.end_page + 1))

        # Build cumulative character offsets per page so we can slice full_text
        page_offsets: List[Tuple[int, int]] = []  # (start_char, end_char) per page
        current = 0
        for pt in page_texts:
            page_offsets.append((current, current + len(pt)))
            current += len(pt) + 2  # matches "\n\n".join separator

        def char_range_for_pages(start_p: int, end_p: int) -> Tuple[int, int]:
            s_idx = max(0, start_p - 1)
            e_idx = min(len(page_offsets) - 1, end_p - 1)
            return page_offsets[s_idx][0], page_offsets[e_idx][1]

        # First pass: assign raw text slices
        for chapter in chapters:
            char_start, char_end = char_range_for_pages(chapter.start_page, chapter.end_page)
            chapter.text = full_text[char_start:char_end]

        # Second pass: merge title-only chapters (< _MIN_CHAPTER_CHARS) into successor
        merged: List[Chapter] = []
        pending_prefix = ""
        for idx, chapter in enumerate(chapters):
            if len(chapter.text.strip()) < _MIN_CHAPTER_CHARS and idx + 1 < len(chapters):
                pending_prefix += chapter.text + "\n\n"
                self.logger.debug(
                    "Merging title-only chapter %r into successor", chapter.title[:60]
                )
                continue
            if pending_prefix:
                chapter.text = pending_prefix + chapter.text
                pending_prefix = ""
            chapter.scene_breaks = self._find_scene_break_offsets(chapter.text)
            merged.append(chapter)

        # If we ended with a pending prefix (last chapter was title-only), attach to last merged
        if pending_prefix and merged:
            merged[-1].text += "\n\n" + pending_prefix
            merged[-1].scene_breaks = self._find_scene_break_offsets(merged[-1].text)

        # Renumber
        for idx, chapter in enumerate(merged, start=1):
            chapter.chapter_number = idx

        return merged

    def _needs_llm_validation(self, chapters: List[Chapter]) -> bool:
        """Return True if any chapter has confidence below the LLM threshold."""
        return any(c.confidence < _LLM_CONFIDENCE_THRESHOLD for c in chapters)

    def _find_scene_break_offsets(self, text: str) -> List[int]:
        """
        Return character offsets of scene breaks within text.

        Detects explicit typographic separators (*** / --- / etc.) and
        sequences of three or more blank lines.
        """
        offsets: List[int] = []
        for match in _SCENE_BREAK_PATTERNS.finditer(text):
            offsets.append(match.start())
        for match in _BLANK_LINE_SCENE_BREAK.finditer(text):
            if match.start() not in offsets:
                offsets.append(match.start())
        return sorted(offsets)

    def _single_chapter_fallback(self, full_text: str, total_pages: int) -> List[Chapter]:
        """Return a single Chapter wrapping all text when no structure is found."""
        scene_breaks = self._find_scene_break_offsets(full_text)
        return [
            Chapter(
                chapter_number=1,
                title="",
                start_page=1,
                end_page=total_pages,
                text=full_text,
                page_range=list(range(1, total_pages + 1)) if total_pages > 0 else [],
                detection_method="none",
                confidence=0.0,
                scene_breaks=scene_breaks,
            )
        ]

    # ------------------------------------------------------------------
    # EPUB utilities
    # ------------------------------------------------------------------

    def _flatten_epub_toc(
        self, toc: list, depth: int = 0
    ) -> List[Tuple[str, str]]:
        """
        Recursively flatten an ebooklib TOC into (title, file_name) pairs.

        ebooklib TOC entries are either Link objects or (Section, children) tuples.
        """
        entries: List[Tuple[str, str]] = []
        for item in toc:
            if isinstance(item, tuple):
                section, children = item[0], item[1] if len(item) > 1 else []
                title = getattr(section, "title", "") or ""
                href = getattr(section, "href", "") or ""
                file_name = href.split("#")[0] if href else ""
                if title and file_name:
                    entries.append((title, file_name))
                if children:
                    # Only recurse into top-level nesting at depth 0
                    if depth == 0:
                        entries.extend(self._flatten_epub_toc(children, depth + 1))
            else:
                title = getattr(item, "title", "") or ""
                href = getattr(item, "href", "") or ""
                file_name = href.split("#")[0] if href else ""
                if title and file_name:
                    entries.append((title, file_name))

        # Deduplicate while preserving order
        seen: set = set()
        deduped: List[Tuple[str, str]] = []
        for entry in entries:
            if entry[1] not in seen:
                seen.add(entry[1])
                deduped.append(entry)
        return deduped

    def _epub_item_to_text(self, item) -> str:
        """Strip HTML tags from an EPUB spine item and return plain text."""
        raw = item.get_content()
        html = raw.decode("utf-8", errors="ignore")
        # Remove script/style blocks
        html = re.sub(r"(?is)<script.*?>.*?</script>", " ", html)
        html = re.sub(r"(?is)<style.*?>.*?</style>", " ", html)
        # Replace block-level tags with newlines to preserve paragraph structure
        html = re.sub(r"(?i)</(p|div|h[1-6]|li|br|tr)>", "\n", html)
        # Strip remaining tags
        html = re.sub(r"<[^>]+>", "", html)
        # Collapse excessive whitespace while keeping paragraph breaks
        html = re.sub(r"\n{3,}", "\n\n", html)
        html = re.sub(r"[ \t]+", " ", html)
        return html.strip()
