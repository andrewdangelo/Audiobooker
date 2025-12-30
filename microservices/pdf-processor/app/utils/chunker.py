"""
Text Chunking library
"""
__author__ = "Mohammad Saifan"

from typing import List, Dict, Any, Optional
import re
import httpx


class TextChunker:
    """
    Text chunking utility
    """
    
    def __init__(self):
        """Initialize text chunker"""
        # Sentence boundary patterns
        self.sentence_endings = re.compile(r'[.!?]+[\s\n]+')
    
    async def chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200, page_map: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """
        Split text into overlapping chunks with page tracking
        
        Args:
            text: Full text to chunk
            chunk_size: Target size of each chunk in characters
            overlap: Number of characters to overlap between chunks
            page_map: Optional page boundary information
        
        Returns:
            List of chunk dictionaries
        """
        if not text or not text.strip():
            return []
        
        chunks = []
        start = 0
        chunk_id = 1
        
        while start < len(text):
            # Calculate end position
            end = start + chunk_size
            
            # If this is the last chunk, take everything
            if end >= len(text):
                chunk_text = text[start:].strip()
                if chunk_text:
                    chunk = await self._create_chunk(chunk_id=chunk_id, text=chunk_text, start_char=start, end_char=len(text), page_map=page_map)
                    chunks.append(chunk)
                break
            
            # Try to break at sentence boundary
            chunk_end = self._find_sentence_boundary(text, end, chunk_size)
                        
            # Extract chunk text
            chunk_text = text[start:chunk_end].strip()
            
            if chunk_text:
                chunk = await self._create_chunk(chunk_id=chunk_id, text=chunk_text, start_char=start, end_char=chunk_end, page_map=page_map)
                chunks.append(chunk)
                chunk_id += 1
            
            # Move to next chunk with overlap > 1
            next_start = max(chunk_end - overlap, chunk_end - 1)
            start = next_start
        
        return chunks
    
    def _find_sentence_boundary(self, text: str, target_pos: int, max_search: int = 200) -> int:
        """
        Find the nearest sentence boundary near target position
        
        Args:
            text: Full text
            target_pos: Target position
            max_search: Maximum characters to search forward/backward
        
        Returns:
            Position of sentence boundary
        """
        # Search forward for sentence ending
        search_end = min(target_pos + max_search, len(text))
        forward_text = text[target_pos:search_end]
        
        match = self.sentence_endings.search(forward_text)
        if match:
            return target_pos + match.end()
        
        # Search backward for sentence ending
        search_start = max(0, target_pos - max_search)
        backward_text = text[search_start:target_pos]
        
        # Find all matches and take the last one
        matches = list(self.sentence_endings.finditer(backward_text))
        if matches:
            last_match = matches[-1]
            return search_start + last_match.end()
        
        # No sentence boundary found, use target position
        return target_pos
    
    async def _create_chunk(self, chunk_id: int, text: str, start_char: int, end_char: int, page_map: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Create a dict of chunked items
        
        Args:
            chunk_id: Chunk sequence number
            text: Chunk text
            start_char: Starting character position
            end_char: Ending character position
            page_map: Page boundary information
        
        Returns:
            Chunk dictionary
        """
        # Determine which pages this chunk spans
        page_numbers = []
        if page_map:
            for page_info in page_map:
                # Check if chunk overlaps with this page
                if not (end_char <= page_info["start"] or start_char >= page_info["end"]):
                    page_numbers.append(page_info["page"])
        
        # CALLING TTS MICROSERVICE HERE Generate audio for the chunk #TODO: DELETE later
        # tts_response = await call_tts_service(
        #     chunk_id=str(chunk_id),
        #     text=text,
        #     provider="elevenlabs",
        #     voice_id="EXAVITQu4vr4xnSDxMaL",
        #     model_id="eleven_multilingual_v2",
        #     voice_settings={
        #         "stability": 0.5,
        #         "similarity_boost": 0.75
        #         }
        # )

        return {
            "chunk_id": chunk_id,
            "text": text,
            "page_numbers": page_numbers,
            "character_count": len(text),
            "start_char": start_char,
            "end_char": end_char
        }


async def call_tts_service(chunk_id, text, provider, voice_id, model_id, voice_settings):
    TTS_SERVICE_URL = "http://127.0.0.1:8002/api/v1/tts/tts_processor/generate"
    async with httpx.AsyncClient() as client:
        payload = {
            "chunk_id": chunk_id,
            "text": text,
            "provider": provider,
            "voice_id": voice_id,
            "model_id": model_id,
            "voice_settings": voice_settings
        }

        try:
            response = await client.post(TTS_SERVICE_URL, json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            # Log the error but continue processing
            print(f"TTS service failed for chunk {chunk_id}: {e}")
            return {
                "chunk_id": chunk_id,
                "status": "failed",
                "error": str(e),
                "audio_url": None
            }
        except Exception as e:
            # Catch network errors, timeouts, etc.
            print(f"TTS service error for chunk {chunk_id}: {e}")
            return {
                "chunk_id": chunk_id,
                "status": "error",
                "error": str(e),
                "audio_url": None
            }
