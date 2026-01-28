"""
LLM-based Speaker Chunking Service

Converts processed PDF chunks into speaker-attributed script lines
using OpenAI for intelligent dialogue and narration separation.
"""
__author__ = "Andrew D'Angelo"

import json
import time
import re
import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

from openai import OpenAI

from app.core.logging_config import Logger
from app.core.config_settings import settings


# -----------------------------
# Config / helpers
# -----------------------------

DEFAULT_MODEL = "gpt-4o"
DEFAULT_DELAY_BETWEEN_REQUESTS = 3.0  # seconds between API calls to respect rate limits
DEFAULT_MAX_CHARS_PER_WINDOW = 15000  # Reduced from 35000 to use fewer tokens per request


def sleep_ms(ms: int) -> None:
    """Sleep for milliseconds"""
    time.sleep(ms / 1000.0)


def parse_rate_limit_wait_time(error_message: str) -> float:
    """
    Parse the wait time from OpenAI's rate limit error message.
    Example: 'Please try again in 3.232s'
    
    Returns:
        Wait time in seconds, or 20 as default
    """
    match = re.search(r'Please try again in ([\d.]+)s', str(error_message))
    if match:
        return float(match.group(1)) + 1.0  # Add 1 second buffer
    return 20.0  # Default wait time


def format_time_remaining(seconds: float) -> str:
    """
    Format seconds into a human-readable time string.
    
    Args:
        seconds: Number of seconds remaining
    
    Returns:
        Formatted string like "2m 30s" or "1h 15m"
    """
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def estimate_remaining_time(
    windows_completed: int,
    total_windows: int,
    elapsed_time: float,
    delay_per_request: float = DEFAULT_DELAY_BETWEEN_REQUESTS
) -> Dict[str, Any]:
    """
    Estimate the remaining time for LLM processing.
    
    Args:
        windows_completed: Number of windows already processed
        total_windows: Total number of windows to process
        elapsed_time: Time elapsed so far in seconds
        delay_per_request: Delay between requests in seconds
    
    Returns:
        Dict with estimation details
    """
    if windows_completed == 0:
        # Estimate based on typical processing time per window
        avg_time_per_window = 8.0 + delay_per_request  # ~8s API call + delay
        estimated_total = avg_time_per_window * total_windows
        return {
            "windows_completed": 0,
            "total_windows": total_windows,
            "percent_complete": 0,
            "elapsed_time": elapsed_time,
            "estimated_remaining": estimated_total,
            "estimated_remaining_formatted": format_time_remaining(estimated_total),
            "avg_time_per_window": avg_time_per_window,
        }
    
    avg_time_per_window = elapsed_time / windows_completed
    remaining_windows = total_windows - windows_completed
    estimated_remaining = avg_time_per_window * remaining_windows
    percent_complete = (windows_completed / total_windows) * 100
    
    return {
        "windows_completed": windows_completed,
        "total_windows": total_windows,
        "percent_complete": round(percent_complete, 1),
        "elapsed_time": round(elapsed_time, 1),
        "estimated_remaining": round(estimated_remaining, 1),
        "estimated_remaining_formatted": format_time_remaining(estimated_remaining),
        "avg_time_per_window": round(avg_time_per_window, 2),
    }


def chunk_windows_from_pdf_chunks(
    pdf_chunks: List[Dict[str, Any]],
    max_chars_per_window: int = 35000,
) -> List[Dict[str, Any]]:
    """
    Takes the preprocessed PDF 'chunks' (each has 'text' + metadata),
    and groups them into larger windows for LLM input.

    Returns: windows = [
      {
        "window_index": 0,
        "chunk_ids": [1,2,3,...],
        "page_numbers": sorted unique pages,
        "text": "combined text..."
      },
      ...
    ]
    """
    windows: List[Dict[str, Any]] = []
    current_text_parts: List[str] = []
    current_chunk_ids: List[int] = []
    current_pages: set = set()
    current_len = 0
    window_index = 0

    for ch in pdf_chunks:
        txt = (ch.get("text") or "").strip()
        if not txt:
            continue

        # +2 for separator newlines
        add_len = len(txt) + (2 if current_text_parts else 0)

        if current_len + add_len > max_chars_per_window and current_text_parts:
            windows.append({
                "window_index": window_index,
                "chunk_ids": current_chunk_ids,
                "page_numbers": sorted(current_pages),
                "text": "\n\n".join(current_text_parts),
            })
            window_index += 1
            current_text_parts = [txt]
            current_chunk_ids = [int(ch.get("chunk_id", -1))]
            current_pages = set(ch.get("page_numbers") or [])
            current_len = len(txt)
        else:
            current_text_parts.append(txt)
            current_chunk_ids.append(int(ch.get("chunk_id", -1)))
            for p in (ch.get("page_numbers") or []):
                current_pages.add(p)
            current_len += add_len

    if current_text_parts:
        windows.append({
            "window_index": window_index,
            "chunk_ids": current_chunk_ids,
            "page_numbers": sorted(current_pages),
            "text": "\n\n".join(current_text_parts),
        })

    return windows


def run_with_concurrency(
    tasks: List[Callable[[], Any]],
    concurrency: int = 1,
    delay_between_tasks: float = 0.0,
    on_progress: Optional[Callable[[int, int, float, Dict[str, Any]], None]] = None
) -> List[Any]:
    """
    Concurrency runner with progress tracking and ETA calculation.
    Adapted from TypeScript pattern for Python with thread pool.
    
    Args:
        tasks: List of callables that return results
        concurrency: Number of concurrent workers (default: 1 for rate limiting)
        delay_between_tasks: Seconds to wait after each task completion
        on_progress: Optional callback called after each task completes with:
                    (completed, total, estimated_seconds_remaining, progress_info)
    
    Returns:
        List of results in original task order
    """
    import threading
    
    results: List[Any] = [None] * len(tasks)
    completed = 0
    next_index = 0
    start_time = time.time()
    lock = threading.Lock()
    
    def worker():
        nonlocal completed, next_index
        
        while True:
            # Atomically get next task index
            with lock:
                if next_index >= len(tasks):
                    return
                index = next_index
                next_index += 1
            
            # Execute task
            try:
                result = tasks[index]()
                results[index] = result
            except Exception as e:
                print(f"Task {index} failed: {e}")
                results[index] = {"script": [], "new_characters": [], "error": str(e)}
            
            # Update progress
            with lock:
                completed += 1
                current_completed = completed
            
            # Calculate ETA
            elapsed = time.time() - start_time
            avg_time_per_task = elapsed / current_completed if current_completed > 0 else 0
            remaining_tasks = len(tasks) - current_completed
            estimated_remaining = remaining_tasks * avg_time_per_task
            
            # Create progress info dict
            progress_info = {
                "completed": current_completed,
                "total": len(tasks),
                "percent_complete": round((current_completed / len(tasks)) * 100, 1),
                "elapsed_time": round(elapsed, 1),
                "estimated_remaining": round(estimated_remaining, 1),
                "estimated_remaining_formatted": format_time_remaining(estimated_remaining),
                "avg_time_per_task": round(avg_time_per_task, 2),
            }
            
            # Call progress callback if provided
            if on_progress:
                try:
                    on_progress(current_completed, len(tasks), estimated_remaining, progress_info)
                except Exception as e:
                    print(f"Progress callback error: {e}")
            
            # Delay between tasks (rate limiting)
            if delay_between_tasks > 0 and current_completed < len(tasks):
                time.sleep(delay_between_tasks)
    
    # Create and start worker threads
    workers = []
    for _ in range(min(concurrency, len(tasks))):
        t = threading.Thread(target=worker)
        t.start()
        workers.append(t)
    
    # Wait for all workers to complete
    for t in workers:
        t.join()
    
    return results


def run_with_concurrency_async(
    tasks: List[Callable[[], Any]],
    concurrency: int = 1,
    delay_between_tasks: float = 0.0,
    on_progress: Optional[Callable[[int, int, float, Dict[str, Any]], None]] = None
) -> List[Any]:
    """
    Synchronous wrapper that processes tasks sequentially with delay.
    Best for rate-limited APIs where concurrency=1 is required.
    
    This is simpler and more predictable for rate-limited scenarios.
    
    Args:
        tasks: List of callables that return results
        concurrency: Number of concurrent workers (ignored if 1, uses sequential)
        delay_between_tasks: Seconds to wait between task completions
        on_progress: Optional callback for progress updates
    
    Returns:
        List of results in original task order
    """
    if concurrency > 1:
        # Use threaded version for actual concurrency
        return run_with_concurrency(tasks, concurrency, delay_between_tasks, on_progress)
    
    # Sequential processing (best for rate limiting)
    results: List[Any] = []
    start_time = time.time()
    
    for i, task in enumerate(tasks):
        try:
            result = task()
            results.append(result)
        except Exception as e:
            print(f"Task {i} failed: {e}")
            results.append({"script": [], "new_characters": [], "error": str(e)})
        
        completed = i + 1
        
        # Calculate ETA
        elapsed = time.time() - start_time
        avg_time_per_task = elapsed / completed
        remaining_tasks = len(tasks) - completed
        estimated_remaining = remaining_tasks * avg_time_per_task
        
        # Create progress info
        progress_info = {
            "completed": completed,
            "total": len(tasks),
            "percent_complete": round((completed / len(tasks)) * 100, 1),
            "elapsed_time": round(elapsed, 1),
            "estimated_remaining": round(estimated_remaining, 1),
            "estimated_remaining_formatted": format_time_remaining(estimated_remaining),
            "avg_time_per_task": round(avg_time_per_task, 2),
        }
        
        # Call progress callback
        if on_progress:
            try:
                on_progress(completed, len(tasks), estimated_remaining, progress_info)
            except Exception as e:
                print(f"Progress callback error: {e}")
        
        # Delay between tasks (except after last one)
        if delay_between_tasks > 0 and completed < len(tasks):
            time.sleep(delay_between_tasks)
    
    return results


# -----------------------------
# Data classes
# -----------------------------

@dataclass
class Character:
    name: str
    description: str
    gender: str
    suggestedVoiceId: Optional[str] = None


@dataclass
class ScriptLine:
    speaker: str
    text: str
    # Optional metadata hooks you might want:
    page_numbers: Optional[List[int]] = None
    chunk_ids: Optional[List[int]] = None


# -----------------------------
# LLM chunking by speaker
# -----------------------------

class SpeakerChunker(Logger):
    """
    LLM-based speaker chunking service
    
    Converts prose text into speaker-attributed script lines
    using OpenAI's API for intelligent dialogue separation.
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = DEFAULT_MODEL):
        """
        Initialize the SpeakerChunker
        
        Args:
            api_key: OpenAI API key (defaults to environment variable)
            model: OpenAI model to use (default: gpt-4o)
        """
        self.client = OpenAI(api_key=api_key or settings.OPENAI_API_KEY)
        self.model = model
        self.logger.info(f"SpeakerChunker initialized with model: {model}")

    def discover_characters(self, discovery_text: str) -> List[Character]:
        """
        One-time character discovery to keep naming consistent.
        
        Args:
            discovery_text: Sample text from the beginning of the document
        
        Returns:
            List of discovered Character objects
        """
        self.logger.info("Discovering characters from text...")
        
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an expert casting director. Return valid JSON only."},
                {"role": "user", "content": (
                    "Identify main characters (including Narrator) from this text. For each character, provide:\n"
                    "- name (string)\n"
                    "- description (string)\n"
                    "- gender (\"MALE\", \"FEMALE\", or \"NEUTRAL\")\n"
                    "- suggestedVoiceId (you can suggest any descriptive voice name)\n\n"
                    "Return JSON in this format:\n"
                    "{\"characters\": [{\"name\": \"...\", \"description\": \"...\", \"gender\": \"...\", \"suggestedVoiceId\": \"...\"}]}\n\n"
                    f"Text:\n{discovery_text}"
                )},
            ],
            response_format={"type": "json_object"},
        )

        content = resp.choices[0].message.content or "{}"
        data = json.loads(content)
        out: List[Character] = []
        for c in data.get("characters", []) or []:
            out.append(Character(
                name=c.get("name", "").strip(),
                description=c.get("description", "").strip(),
                gender=c.get("gender", "NEUTRAL").strip(),
                suggestedVoiceId=c.get("suggestedVoiceId", None),
            ))
        
        # Always ensure Narrator exists
        if not any(ch.name.lower() == "narrator" for ch in out):
            out.append(Character(name="Narrator", description="Narration / description", gender="NEUTRAL"))
        
        self.logger.info(f"Discovered {len(out)} characters")
        return out

    def parse_window_to_script(
        self,
        window_text: str,
        part_index: int,
        known_char_names: str,
        retries: int = 5,
    ) -> Dict[str, Any]:
        """
        This is the core "LLM chunking by speaker":
        prose -> JSON script lines with speakers.
        
        Args:
            window_text: Text window to parse
            part_index: Index of this window in the document
            known_char_names: Comma-separated list of known character names
            retries: Number of retry attempts for API calls
        
        Returns:
            Dict with 'script' and 'new_characters' arrays
        """
        prompt = (
            f"Rewrite the text into a script.\n"
            f"CONTEXT: Part {part_index} of story.\n"
            f"KNOWN CHARACTERS: {known_char_names}.\n"
            f"RULES:\n"
            f"1. Use known names if applicable.\n"
            f"2. Add new characters if needed (return in new_characters array).\n"
            f"3. Use 'Narrator' for description.\n"
            f"4. IMPORTANT: If a new Chapter or Section starts, create a line with speaker \"Chapter\" and text \"Chapter Name\".\n\n"
            f"Return JSON format:\n"
            f"{{\"script\": [{{\"speaker\": \"...\", \"text\": \"...\"}}], "
            f"\"new_characters\": [{{\"name\": \"...\", \"description\": \"...\", \"gender\": \"...\"}}]}}\n\n"
            f"TEXT:\n{window_text}"
        )

        last_err = None
        for attempt in range(retries):
            try:
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a scriptwriter converting a novel to a script. Return valid JSON only."},
                        {"role": "user", "content": prompt},
                    ],
                    response_format={"type": "json_object"},
                )
                content = resp.choices[0].message.content or '{"script": [], "new_characters": []}'
                return json.loads(content)
            except Exception as e:
                last_err = e
                error_str = str(e)
                
                # Check if it's a rate limit error
                if '429' in error_str or 'rate_limit' in error_str.lower():
                    wait_time = parse_rate_limit_wait_time(error_str)
                    self.logger.warning(f"Rate limit hit (attempt {attempt + 1}/{retries}), waiting {wait_time:.1f}s...")
                    time.sleep(wait_time)
                else:
                    self.logger.warning(f"LLM call failed (attempt {attempt + 1}/{retries}): {error_str}")
                    # Exponential backoff for non-rate-limit errors
                    time.sleep(2 ** attempt)
        
        self.logger.error(f"All retry attempts failed: {str(last_err)}")
        return {"script": [], "new_characters": [], "error": str(last_err)}

    def chunk_by_speaker_from_processed_data(
        self,
        processed_data: Dict[str, Any],
        discovery_chars: int = 30000,
        max_chars_per_window: int = DEFAULT_MAX_CHARS_PER_WINDOW,
        concurrency: int = 1,  # Default to 1 to respect rate limits
        delay_between_requests: float = DEFAULT_DELAY_BETWEEN_REQUESTS,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        """
        Full pipeline for: processed PDF data -> speaker-attributed script lines.
        
        Args:
            processed_data: The processed PDF data dictionary (with 'chunks' key)
            discovery_chars: Number of characters to use for character discovery
            max_chars_per_window: Maximum characters per LLM processing window
            concurrency: Number of concurrent LLM requests (default: 1 for rate limits)
            delay_between_requests: Seconds to wait between API calls
            progress_callback: Optional callback function that receives progress updates
                               with time estimates. Called with dict containing:
                               - windows_completed, total_windows, percent_complete
                               - elapsed_time, estimated_remaining, estimated_remaining_formatted
        
        Returns:
            Dict with 'characters', 'script', and 'meta' keys
        """
        self.logger.info("Starting speaker-based chunking from processed data...")
        start_time = time.time()
        
        pdf_chunks = processed_data.get("chunks", []) or []
        if not pdf_chunks:
            raise ValueError("No chunks found in processed data.")

        # Combine early text for discovery
        discovery_parts: List[str] = []
        total = 0
        for ch in pdf_chunks:
            t = (ch.get("text") or "")
            if not t:
                continue
            if total + len(t) > discovery_chars:
                discovery_parts.append(t[: max(0, discovery_chars - total)])
                break
            discovery_parts.append(t)
            total += len(t)

        characters = self.discover_characters("\n\n".join(discovery_parts))
        known_char_names = ", ".join([c.name for c in characters if c.name])
        
        # Wait after character discovery to respect rate limits
        self.logger.info(f"Waiting {delay_between_requests}s after character discovery...")
        time.sleep(delay_between_requests)

        # Group the preprocessed chunks into larger LLM windows
        self.logger.info("Creating processing windows...")
        windows = chunk_windows_from_pdf_chunks(pdf_chunks, max_chars_per_window=max_chars_per_window)
        total_windows = len(windows)
        self.logger.info(f"Created {total_windows} windows for LLM processing")
        
        # Initial time estimate
        initial_estimate = estimate_remaining_time(0, total_windows, 0, delay_between_requests)
        self.logger.info(f"Estimated total processing time: {initial_estimate['estimated_remaining_formatted']}")
        
        if progress_callback:
            progress_callback(initial_estimate)

        # Process windows - use sequential processing with delay for rate limiting
        results = []
        window_start_time = time.time()
        
        if concurrency <= 1:
            # Sequential processing with delay between requests (recommended for rate limits)
            self.logger.info(f"Processing windows sequentially with {delay_between_requests}s delay...")
            for i, w in enumerate(windows):
                # Calculate and log time estimate
                elapsed = time.time() - window_start_time
                time_info = estimate_remaining_time(i, total_windows, elapsed, delay_between_requests)
                
                self.logger.info(
                    f"Processing window {i + 1}/{total_windows} "
                    f"({time_info['percent_complete']:.1f}% complete, "
                    f"~{time_info['estimated_remaining_formatted']} remaining)..."
                )
                
                # Call progress callback if provided
                if progress_callback:
                    progress_callback(time_info)
                
                result = self.parse_window_to_script(
                    window_text=w["text"],
                    part_index=w["window_index"] + 1,
                    known_char_names=known_char_names
                )
                results.append(result)
                
                # Wait between requests (except after the last one)
                if i < len(windows) - 1:
                    time.sleep(delay_between_requests)
        else:
            # Concurrent processing (use only if you have higher rate limits)
            self.logger.info(f"Processing windows with {concurrency} concurrent requests...")
            tasks = []
            for w in windows:
                idx = w["window_index"]
                text = w["text"]
                tasks.append(lambda idx=idx, text=text: self.parse_window_to_script(
                    window_text=text,
                    part_index=idx + 1,
                    known_char_names=known_char_names
                ))
            
            # Progress callback wrapper for run_with_concurrency
            def on_task_progress(completed: int, total: int, est_remaining: float, info: Dict[str, Any]):
                self.logger.info(
                    f"Processing window {completed}/{total} "
                    f"({info['percent_complete']:.1f}% complete, "
                    f"~{info['estimated_remaining_formatted']} remaining)..."
                )
                if progress_callback:
                    # Convert to the format expected by progress_callback
                    progress_callback({
                        "windows_completed": completed,
                        "total_windows": total,
                        "percent_complete": info["percent_complete"],
                        "elapsed_time": info["elapsed_time"],
                        "estimated_remaining": info["estimated_remaining"],
                        "estimated_remaining_formatted": info["estimated_remaining_formatted"],
                        "avg_time_per_window": info["avg_time_per_task"],
                    })
            
            results = run_with_concurrency_async(
                tasks, 
                concurrency=concurrency,
                delay_between_tasks=delay_between_requests,
                on_progress=on_task_progress
            )

        # Merge script + merge characters
        char_map: Dict[str, Dict[str, Any]] = {c.name: {
            "name": c.name,
            "description": c.description,
            "gender": c.gender,
            "suggestedVoiceId": c.suggestedVoiceId
        } for c in characters}

        final_script: List[Dict[str, Any]] = []

        for w, res in zip(windows, results):
            # merge new characters
            for nc in (res.get("new_characters") or []):
                nm = (nc.get("name") or "").strip()
                if nm and nm not in char_map:
                    char_map[nm] = {
                        "name": nm,
                        "description": (nc.get("description") or "").strip(),
                        "gender": (nc.get("gender") or "NEUTRAL").strip(),
                    }

            # attach window provenance to each line (optional but very useful)
            for line in (res.get("script") or []):
                speaker = (line.get("speaker") or "").strip()
                text = (line.get("text") or "").strip()
                if not speaker or not text:
                    continue
                final_script.append({
                    "speaker": speaker,
                    "text": text,
                    "page_numbers": w.get("page_numbers"),
                    "source_chunk_ids": w.get("chunk_ids"),
                })

        processing_time = time.time() - start_time
        avg_time_per_window = processing_time / total_windows if total_windows > 0 else 0
        
        self.logger.info(
            f"Speaker chunking completed - "
            f"Script lines: {len(final_script)}, "
            f"Characters: {len(char_map)}, "
            f"Time: {processing_time:.2f}s "
            f"(avg {avg_time_per_window:.2f}s/window)"
        )
        
        # Final progress callback
        if progress_callback:
            progress_callback({
                "windows_completed": total_windows,
                "total_windows": total_windows,
                "percent_complete": 100.0,
                "elapsed_time": round(processing_time, 1),
                "estimated_remaining": 0,
                "estimated_remaining_formatted": "0s",
                "avg_time_per_window": round(avg_time_per_window, 2),
                "status": "completed"
            })

        return {
            "characters": list(char_map.values()),
            "script": final_script,
            "meta": {
                "source_total_pdf_chunks": len(pdf_chunks),
                "llm_windows": total_windows,
                "model": self.model,
                "processing_time": round(processing_time, 2),
                "processing_time_formatted": format_time_remaining(processing_time),
                "avg_time_per_window": round(avg_time_per_window, 2),
                "total_script_lines": len(final_script),
                "total_characters": len(char_map),
            }
        }
