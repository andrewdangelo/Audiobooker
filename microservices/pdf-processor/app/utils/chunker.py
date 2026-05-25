"""
Text Chunking library -- chapter-aware with scene break support.
"""
__author__ = "Mohammad Saifan"
__contributor__ = "Andrew D'Angelo"

from typing import List, Dict, Any, Optional
import re


SCENE_BREAK_PATTERN = re.compile(
    r'(?:^|\n)'
    r'(?:'
    r'\s*[*]{3,}\s*'
    r'|\s*[-]{3,}\s*'
    r'|\s*[_]{3,}\s*'
    r'|\s*[~]\s*[~]\s*[~]\s*'
    r'|\s*[#]{3,}\s*'
    r')'
    r'(?:\n|$)',
)


class TextChunker:

    def __init__(self):
        self.sentence_endings = re.compile(r'[.!?]+[\s\n]+')

    async def chunk_text(
        self,
        text: str,
        chunk_size: int = 1000,
        overlap: int = 200,
        page_map: Optional[List[Dict[str, Any]]] = None,
        chapter_id: Optional[int] = None,
        chapter_title: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Split text into overlapping chunks with page tracking.
        Respects scene breaks as natural chunk boundaries when they fall
        within the chunk window.
        """
        if not text or not text.strip():
            return []

        chunks = []
        start = 0
        chunk_id = 1

        while start < len(text):
            end = start + chunk_size

            if end >= len(text):
                chunk_text = text[start:].strip()
                if chunk_text:
                    chunk = self._create_chunk(
                        chunk_id=chunk_id, text=chunk_text,
                        start_char=start, end_char=len(text),
                        page_map=page_map, chapter_id=chapter_id,
                        chapter_title=chapter_title,
                    )
                    chunks.append(chunk)
                break

            scene_break_pos = self._find_scene_break(text, start, end + 200)
            if scene_break_pos is not None and scene_break_pos > start + (chunk_size // 4):
                chunk_end = scene_break_pos
            else:
                chunk_end = self._find_sentence_boundary(text, end, chunk_size)

            chunk_text = text[start:chunk_end].strip()

            if chunk_text:
                chunk = self._create_chunk(
                    chunk_id=chunk_id, text=chunk_text,
                    start_char=start, end_char=chunk_end,
                    page_map=page_map, chapter_id=chapter_id,
                    chapter_title=chapter_title,
                )
                chunks.append(chunk)
                chunk_id += 1

            next_start = max(chunk_end - overlap, chunk_end - 1)
            start = next_start

        return chunks

    async def chunk_by_chapters(
        self,
        chapters: List[Dict[str, Any]],
        chunk_size: int = 1000,
        overlap: int = 200,
        page_map: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Chunk each chapter independently -- no cross-chapter overlap.
        Each chunk carries its chapter_id and chapter_title.
        """
        all_chunks = []
        global_chunk_id = 1

        for chapter in chapters:
            ch_text = chapter.get("text", "")
            ch_id = chapter.get("chapter_number", chapter.get("chapter_id"))
            ch_title = chapter.get("title", "")
            ch_start_page = chapter.get("start_page", 0)

            chapter_page_map = None
            if page_map and ch_start_page:
                ch_end_page = chapter.get("end_page", ch_start_page)
                chapter_page_map = [
                    p for p in page_map
                    if ch_start_page <= p["page"] <= ch_end_page
                ]

            chapter_chunks = await self.chunk_text(
                text=ch_text,
                chunk_size=chunk_size,
                overlap=overlap,
                page_map=chapter_page_map,
                chapter_id=ch_id,
                chapter_title=ch_title,
            )

            for chunk in chapter_chunks:
                chunk["chunk_id"] = global_chunk_id
                global_chunk_id += 1

            all_chunks.extend(chapter_chunks)

        return all_chunks

    def _find_sentence_boundary(self, text: str, target_pos: int, max_search: int = 200) -> int:
        search_end = min(target_pos + max_search, len(text))
        forward_text = text[target_pos:search_end]

        match = self.sentence_endings.search(forward_text)
        if match:
            return target_pos + match.end()

        search_start = max(0, target_pos - max_search)
        backward_text = text[search_start:target_pos]

        matches = list(self.sentence_endings.finditer(backward_text))
        if matches:
            last_match = matches[-1]
            return search_start + last_match.end()

        return target_pos

    def _find_scene_break(self, text: str, start: int, end: int) -> Optional[int]:
        """Find a scene break within the given range, returning its end position."""
        segment = text[start:min(end, len(text))]
        match = SCENE_BREAK_PATTERN.search(segment)
        if match:
            return start + match.end()
        return None

    def _create_chunk(
        self,
        chunk_id: int,
        text: str,
        start_char: int,
        end_char: int,
        page_map: Optional[List[Dict[str, Any]]] = None,
        chapter_id: Optional[int] = None,
        chapter_title: Optional[str] = None,
    ) -> Dict[str, Any]:
        page_numbers = []
        if page_map:
            for page_info in page_map:
                if not (end_char <= page_info["start"] or start_char >= page_info["end"]):
                    page_numbers.append(page_info["page"])

        result = {
            "chunk_id": chunk_id,
            "text": text,
            "page_numbers": page_numbers,
            "character_count": len(text),
            "start_char": start_char,
            "end_char": end_char,
        }
        if chapter_id is not None:
            result["chapter_id"] = chapter_id
            result["chapter_title"] = chapter_title or ""
        return result
