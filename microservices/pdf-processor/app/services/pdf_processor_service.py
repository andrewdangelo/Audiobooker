"""
PDF Processing Service

Core service for extracting and processing text from PDFs.
"""
__author__ = "Mohammad Saifan"
__contributor__ = "Andrew D'Angelo"

import io
import re
import time
import asyncio
import html as html_module
import unicodedata
from typing import (Dict, Any, List)
from datetime import datetime
import ebooklib
import pytesseract
from ebooklib import epub
import fitz  
from PIL import Image
import easyocr
import numpy as np
import re
from PyPDF2 import PdfReader


from PyPDF2.errors import PdfReadError

from app.core.logging_config import Logger
from app.core.redis_manager import redis_manager
from app.core.config_settings import settings

from app.utils.chunker import TextChunker

from app.services import r2_service
from app.services.llm_speaker_chunker import SpeakerChunker
from app.services.pipeline_client import notify_backend_conversion_complete, ping_service_health

from app.database import (database, db_engine)

from app.models.db_models import Collections


class PDFProcessorService(Logger):
    """
    PDF Processing Service
    
    Handles PDF text extraction, chunking, and formatting.
    """
    
    def __init__(self):
        """Initialize PDF processor"""
        self.chunker = TextChunker()
        self.logger.info("PDF Processor Service initialized")
    
    # ==================== Redis Job Manager ====================

    async def get_all_jobs(self) -> Dict[str, Dict[str, Any]]:
        """Retrieve all jobs from Redis"""
        pattern = f"{redis_manager.JOB_PREFIX}*"
        keys = await redis_manager.scan_keys(pattern)
        jobs = {}

        for key in keys:
            job_id = key.replace(redis_manager.JOB_PREFIX, "")
            job_data = await redis_manager.hgetall(key)

            if job_data:
                jobs[job_id] = job_data
        return jobs
    
    async def get_job_by_id(self, job_id: str) -> Dict[str, Any]:
        """Retrieve job from Redis"""
        job_data = await redis_manager.hgetall(f"{redis_manager.JOB_PREFIX}:{job_id}")
        return job_data if job_data else None

    async def update_job(self, job_id: str, updates: Dict[str, Any]) -> None:
        """Update job fields in Redis"""
        key = f"{redis_manager.JOB_PREFIX}:{job_id}"
        for field, value in updates.items():
            await redis_manager.hset(key, field, value)
        await redis_manager.expire(key, redis_manager.JOB_TTL)

    async def create_job(self, job_id: str, job_data: Dict[str, Any]) -> None:
        """Create new job in Redis with TTL"""
        key = f"{redis_manager.JOB_PREFIX}:{job_id}"
        for field, value in job_data.items():
            await redis_manager.hset(key, field, value)
        await redis_manager.expire(key, redis_manager.JOB_TTL)
    
    # ==================== PDF PROCESSOR TASKS ====================

    def _strip_html_to_text(self, html: str) -> str:
        t = re.sub(r"(?is)<script.*?>.*?</script>", " ", html)
        t = re.sub(r"(?is)<style.*?>.*?</style>", " ", t)
        t = re.sub(r"<[^>]+>", " ", t)
        return html_module.unescape(re.sub(r"\s+", " ", t).strip())

    def _process_epub_sync(
        self, epub_data: bytes, chunk_size: int, chunk_overlap: int, output_format: str
    ) -> Dict[str, Any]:
        start_time = time.time()
        book = epub.read_epub(io.BytesIO(epub_data))
        texts: List[str] = []
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            raw = item.get_content()
            html = raw.decode("utf-8", errors="ignore")
            chunk = self._strip_html_to_text(html)
            if chunk:
                texts.append(chunk)
        full_text = "\n".join(texts)
        if not full_text.strip():
            raise ValueError("EPUB contains no extractable text")

        title_guess = ""
        author_guess = ""
        try:
            tmeta = book.get_metadata("DC", "title")
            if tmeta:
                title_guess = tmeta[0][0]
            ameta = book.get_metadata("DC", "creator")
            if ameta:
                author_guess = ameta[0][0]
        except Exception:
            pass

        chunks = asyncio.run(
            self.chunker.chunk_text(
                text=full_text, chunk_size=chunk_size, overlap=chunk_overlap, page_map=None
            )
        )
        processing_time = time.time() - start_time
        return {
            "r2_key": "",
            "total_pages": 0,
            "total_characters": len(full_text),
            "total_chunks": len(chunks),
            "chunks": chunks,
            "metadata": {
                "title": title_guess or "",
                "author": author_guess or "",
                "subject": "",
                "creator": "",
                "producer": "epub",
                "creation_date": "",
                "mod_date": "",
            },
            "processing_time": round(processing_time, 2),
            "created_at": f"{datetime.now().strftime('%m-%d-%Y')} at {datetime.now().strftime('%I:%M %p')}",
        }

    async def process_epub(self, epub_data: bytes, chunk_size: int, chunk_overlap: int, output_format: str) -> Dict[str, Any]:
        return await asyncio.to_thread(
            self._process_epub_sync, epub_data, chunk_size, chunk_overlap, output_format
        )


    async def process_pdf_task(self, job_id: str, user_id: str, r2_key: str, chunk_size: int, chunk_overlap: int, output_format: str, credit_type: str = "basic"):
        """Background task for processing a PDF or EPUB from R2"""
        try:
            self.logger.info(f"Starting book processing for job {job_id}, user {user_id}")
            
            r2_svc = r2_service.R2Service()
            
            await self.update_job(
                job_id,
                {
                    "status": "processing",
                    "pipeline_stage": "pdf_processing",
                    "message": "Downloading source from R2",
                    "progress": 10,
                },
            )
            
            file_data = r2_svc.download_file(r2_key)
            
            await self.update_job(
                job_id,
                {"message": "Extracting text", "pipeline_stage": "text_extraction", "progress": 30},
            )

            is_epub = r2_key.lower().endswith(".epub")
            if is_epub:
                result = await self.process_epub(
                    epub_data=file_data,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    output_format=output_format,
                )
            else:
                result = await self.process_pdf(
                    pdf_data=file_data,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    output_format=output_format,
                )
            
            await self.update_job(job_id, {"progress": 80, "message": "Uploading processed data to R2"})

            job_base = job_id.replace(".pdf", "").replace(".epub", "")
            output_key = f"processed_audiobooks/{job_base}_processed.json"
            r2_svc.upload_processed_data(key=output_key, data=result)
            
            # LLM Speaker Chunking (if enabled)
            script_output_key = None
            if settings.ENABLE_LLM_CHUNKING and settings.HF_TOKEN:
                try:
                    self.logger.info(f"Starting LLM speaker chunking for job {job_id}")
                    await self.update_job(job_id, {
                        "progress": 85,
                        "pipeline_stage": "ai_enrichment",
                        "message": "Processing speaker attribution with LLM"
                    })
                    
                    # Initialize LLM chunker
                    llm_chunker = SpeakerChunker()
                    
                    if settings.LLM_SERVERLESS:
                        self.logger.info("Warming up serverless endpoint...")
                        warmup = llm_chunker.warmup_endpoint() 
                        if not warmup:
                            return {
                                "Status": "LLM Not responsive!"
                            }
                    
                    llm_progress = {"last_update": None}
                    
                    def progress_callback(progress_info: dict):
                        """Store progress info for logging"""
                        llm_progress["last_update"] = progress_info
                        
                        # Extract progress details
                        percent = progress_info.get('percent_complete', 0)
                        batches_done = progress_info.get('batches_completed', 0)
                        total_batches = progress_info.get('total_batches', 0)
                        eta = progress_info.get('estimated_remaining_formatted', 'calculating...')
                        throughput = progress_info.get('units_per_second', 0)
                        avg_batch = progress_info.get('avg_batch_time', 0)
                        
                        # Log detailed progress
                        self.logger.info(
                            f"LLM Progress: {percent}% complete | "
                            f"Batches: {batches_done}/{total_batches} | "
                            f"ETA: {eta} | "
                            f"Throughput: {throughput} units/s"
                        )
                        
                        if avg_batch:
                            self.logger.debug(f"Average batch time: {avg_batch}s")
                    
                    # Process with LLM (using rate-limit-safe defaults)
                    # Run in thread to avoid blocking the event loop
                    script_result = await asyncio.to_thread(
                        llm_chunker.chunk_by_speaker,
                        processed_data=result,
                        concurrency=settings.LLM_CONCURRENCY,
                        progress_callback=progress_callback
                    )
                    
                    # Upload script to R2
                    script_output_key = f"processed_audiobooks/{job_base}_script.json"
                    r2_svc.upload_processed_data(key=script_output_key, data=script_result)
                    
                    # Log detailed completion stats
                    meta = script_result.get('meta', {})
                    segments_count = len(script_result.get('segments', []))
                    self.logger.info(f"✓ LLM speaker chunking completed successfully")
                    self.logger.info(f"  → Segments created: {segments_count}")
                    self.logger.info(f"  → Processing time: {meta.get('processing_time', 0):.1f}s")
                    self.logger.info(f"  → Compression ratio: {meta.get('compression_ratio', 1)}x")
                    
                    if meta.get('speaker_distribution'):
                        top_speakers = sorted(meta['speaker_distribution'].items(), key=lambda x: x[1], reverse=True)[:5]
                        speakers_str = ", ".join([f"{name} ({count})" for name, count in top_speakers])
                        self.logger.info(f"  → Top speakers: {speakers_str}")
                    
                    await self.update_job(job_id, {
                        "progress": 90,
                        "message": f"LLM speaker chunking completed ({segments_count} segments)"
                    })
                    
                except Exception as e:
                    self.logger.error(f"LLM speaker chunking failed for job {job_id}: {str(e)}", exc_info=True)
                    # Continue processing even if LLM chunking fails
                    script_output_key = None
            else:
                await self.update_job(job_id, {
                    "pipeline_stage": "ai_enrichment",
                    "progress": 86,
                    "message": "Speaker enrichment skipped (LLM disabled)",
                })

            await self.update_job(job_id, {
                "pipeline_stage": "ai_service",
                "progress": 88,
                "message": "Contacting AI microservice (optional)",
            })
            await ping_service_health(settings.AI_SERVICE_HEALTH_URL, "AI service")

            await self.update_job(job_id, {
                "pipeline_stage": "tts",
                "progress": 91,
                "message": "TTS infrastructure (optional health check)",
            })
            await ping_service_health(settings.TTS_SERVICE_HEALTH_URL, "TTS service")

            # Create processed-audiobook record in pdf-processor Mongo (processing audit)
            self.logger.info(f"Creating database record for job {job_id}")
            
            db_func = database.get_db()
            db = db_func()
            audiobook_service = db_engine.MongoDBService(db, Collections.PROCESSED_AUDIOBOOKS)

            audiobook_data = {"r2_key": job_id, "user_id": user_id, "title": r2_key.split("/")[-1], "pdf_path": r2_key, "status": "COMPLETED"}

            audiobook_service.create(audiobook_data)

            meta = result.get("metadata") or {}
            title = (meta.get("title") or "").strip() or r2_key.split("/")[-1].rsplit(".", 1)[0]
            author = (meta.get("author") or "").strip() or "Unknown"
            chunk_list = result.get("chunks") or []
            desc_bits: List[str] = []
            for c in chunk_list[:10]:
                if isinstance(c, dict) and c.get("text"):
                    desc_bits.append(str(c["text"]))
            description = (" ".join(desc_bits))[:4000] if desc_bits else None
            source_format = "epub" if r2_key.lower().endswith(".epub") else "pdf"

            await self.update_job(job_id, {
                "pipeline_stage": "backend_sync",
                "progress": 95,
                "message": "Creating library audiobook in backend",
            })

            backend_book_id = await notify_backend_conversion_complete(
                user_id=user_id,
                processor_job_id=job_id,
                title=title,
                author=author,
                description=description,
                credit_type=credit_type if credit_type in ("basic", "premium") else "basic",
                source_format=source_format,
                source_r2_path=r2_key,
                processed_text_r2_key=output_key,
                script_r2_key=script_output_key,
            )

            job_result = {
                "output_key": output_key,
                "total_chunks": result.get("total_chunks", 0),
                "total_pages": result.get("total_pages", 0),
                "total_characters": result.get("total_characters", 0),
            }

            if script_output_key:
                job_result["script_output_key"] = script_output_key
                job_result["llm_chunking_enabled"] = True

            if not backend_book_id:
                await self.update_job(job_id, {
                    "status": "failed",
                    "pipeline_stage": "backend_sync",
                    "progress": 0,
                    "message": "Backend library sync failed",
                    "completed_at": f"{datetime.now().strftime('%m-%d-%Y')} at {datetime.now().strftime('%I:%M %p')}",
                    "error": "backend_conversion_failed",
                    "result": job_result,
                })
                self.logger.error("Job %s: backend did not return book_id", job_id)
                return

            await self.update_job(job_id, {
                "status": "completed",
                "pipeline_stage": "completed",
                "progress": 100,
                "message": "Processing completed successfully",
                "completed_at": f"{datetime.now().strftime('%m-%d-%Y')} at {datetime.now().strftime('%I:%M %p')}",
                "result": job_result,
                "audiobook_id": backend_book_id,
            })

            self.logger.info(f"Job {job_id} completed successfully (backend book {backend_book_id})")
            
        except Exception as e:
            self.logger.error(f"Job {job_id} failed: {str(e)}", exc_info=True)
            
            # Update job with failure status
            await self.update_job(job_id, {
                "status": "failed",
                "progress": 0,
                "message": "Processing failed",
                "completed_at": f"{datetime.now().strftime('%m-%d-%Y')} at {datetime.now().strftime('%I:%M %p')}",
                "error": str(e)
            })
    
    # ==================== PDF Processing ====================
    
    async def process_pdf(self, pdf_data: bytes, chunk_size: int = 1000, chunk_overlap: int = 200, output_format: str = "json") -> Dict[str, Any]:
        """
        Process PDF and extract text with chunking
        
        Args:
            pdf_data: PDF file as bytes
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks
            output_format: Output format (json, text, markdown)
        
        Returns:
            Processing result dict
        
        Raises:
            ValueError: If PDF is invalid or empty
            Exception: For processing errors
        """
        start_time = time.time()
        try:
            self.logger.info("Starting PDF processing")
            
            # Extract text from PDF
            extracted_data = self._extract_text_from_pdf(pdf_data)

            if not extracted_data["full_text"].strip():
                raise ValueError("PDF contains no extractable text")
            
            # Chunk the text
            chunks = await self.chunker.chunk_text(text=extracted_data["full_text"], chunk_size=chunk_size, overlap=chunk_overlap, page_map=extracted_data["page_map"])
            
            # Build result
            processing_time = time.time() - start_time
            
            result = {
                "r2_key": "",  
                "total_pages": extracted_data["total_pages"],
                "total_characters": len(extracted_data["full_text"]),
                "total_chunks": len(chunks),
                "chunks": chunks,
                "metadata": extracted_data["metadata"],
                "processing_time": round(processing_time, 2),
                "created_at": f"{datetime.now().strftime('%m-%d-%Y')} at {datetime.now().strftime('%I:%M %p')}"
            }
            
            self.logger.info(
                f"PDF processing completed - "
                f"Pages: {extracted_data['total_pages']}, "
                f"Chunks: {len(chunks)}, "
                f"Time: {processing_time:.2f}s"
            )
            
            return result
            
        except PdfReadError as e:
            self.logger.error(f"Invalid PDF file: {str(e)}")
            raise ValueError(f"Invalid or corrupted PDF file: {str(e)}")
        
        except Exception as e:
            self.logger.error(f"PDF processing failed: {str(e)}", exc_info=True)
            raise Exception(f"PDF processing failed: {str(e)}")

    def _clean_extracted_text(self, text: str) -> str:
        """
        Clean up of extracted text from PDF:
        """
        if not text:
            return ""

        # Remove null bytes
        text = text.replace('\x00', '')

        # Remove soft hyphens (U+00AD)
        text = text.replace('\xad', '')

        # --- Explicit Unicode → ASCII translation table ---
        UNICODE_TO_ASCII = {
            # Curly / smart quotes
            '\u2018': "'",
            '\u2019': "'",
            '\u201a': "'",
            '\u201b': "'",
            '\u201c': '"',
            '\u201d': '"',
            '\u201e': '"',
            '\u201f': '"',
            '\u2039': '<',
            '\u203a': '>',
            '\u00ab': '"',
            '\u00bb': '"',
            # Dashes
            '\u2012': '-',
            '\u2013': '-',
            '\u2014': '--',
            '\u2015': '--',
            '\u2212': '-',
            # Spaces and separators
            '\u00a0': ' ',
            '\u2002': ' ',
            '\u2003': ' ',
            '\u2004': ' ',
            '\u2005': ' ',
            '\u2009': ' ',
            '\u200a': ' ',
            '\u200b': '',
            '\u200c': '',
            '\u200d': '',
            '\ufeff': '',
            # Line/paragraph separators
            '\u2028': '\n',
            '\u2029': '\n\n',
            # Ellipsis
            '\u2026': '...',
            # Bullets
            '\u2022': '-',
            '\u2023': '-',
            '\u25cf': '-',
            '\u25e6': '-',
            # Misc typographic
            '\u2122': '(TM)',
            '\u00ae': '(R)',
            '\u00a9': '(C)',
            '\u00b7': '.',
            '\u2044': '/',
        }
        translation_table = str.maketrans(UNICODE_TO_ASCII)
        text = text.translate(translation_table)

        # Normalize remaining ligatures and compatibility forms
        text = unicodedata.normalize('NFKC', text)

        # Normalize line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')

        # Rejoin mid-word hyphen breaks (e.g. "some-\nthing" → "something")
        text = re.sub(r'-\n(\S)', r'\1', text)

        # Collapse single newlines that split what should be a continuous sentence,
        # but preserve paragraph breaks (double newlines)
        text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)

        # --- Fix missing spaces from PDF block merging ---
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)

        # 2. Closing punctuation immediately followed by a letter with no space
        text = re.sub(r'([.!?][\'"]?)([A-Za-z])', r'\1 \2', text)

        # 3. Comma/semicolon/colon immediately followed by a letter
        text = re.sub(r'([,;:])([A-Za-z])', r'\1 \2', text)

        # Preserve paragraph breaks but collapse excessive ones
        text = re.sub(r'\n{3,}', '\n\n', text)

        # Collapse multiple spaces/tabs on a single line to one space
        text = re.sub(r'[ \t]+', ' ', text)

        # Strip leading/trailing whitespace per line
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)

        return text.strip()

    def _extract_text_from_pdf(self, pdf_data: bytes) -> Dict[str, Any]:
        """
        Extract text from PDF bytes with automatic OCR for scanned PDFs.
        Preserves paragraph structure for accurate chunking downstream.

        OCR fallback logic:
        - Only triggers when PyMuPDF finds zero text content on a page AND
            the page contains at least one image object — i.e. it's a scanned page.
        - Legitimate short-text pages (titles, copyright, chapter breaks) are
            never sent to OCR regardless of character count.
        """
        pdf = fitz.open(stream=pdf_data, filetype="pdf")

        full_text_parts = []
        page_map = []
        current_pos = 0

        for page_num, page in enumerate(pdf, start=1):
            blocks = page.get_text("blocks")

            # Separate text blocks (type 0) from image blocks (type 1)
            text_blocks = [b for b in blocks if b[6] == 0 and b[4].strip()]
            image_blocks = [b for b in blocks if b[6] == 1]

            raw_text = ""
            used_ocr = False

            if text_blocks:
                # Normal text extraction — trust PyMuPDF completely
                raw_text = "\n\n".join(
                    b[4] for b in sorted(text_blocks, key=lambda b: (b[1], b[0]))
                )
            else:
                has_images = len(image_blocks) > 0 or len(page.get_images(full=True)) > 0

                if has_images:
                    try:
                        self.logger.info(
                            f"Page {page_num}: no text layer found but images present — falling back to OCR"
                        )
                        raw_text = self._ocr_pdf_page(pdf_data, page_num - 1)
                        used_ocr = True
                    except Exception as e:
                        self.logger.error(f"OCR failed for page {page_num}: {e}")
                        raw_text = ""
                else:
                    self.logger.debug(f"Page {page_num}: blank page, skipping OCR")

            if not used_ocr and text_blocks:
                self.logger.debug(
                    f"Page {page_num}: extracted {sum(1 for c in raw_text if c.isalnum())} alnum chars via text layer"
                )

            cleaned_text = self._clean_extracted_text(raw_text)

            start_pos = current_pos
            end_pos = current_pos + len(cleaned_text)

            page_map.append({
                "page": page_num,
                "start": start_pos,
                "end": end_pos,
                "char_count": len(cleaned_text)
            })

            full_text_parts.append(cleaned_text)
            current_pos = end_pos + 2

        metadata = pdf.metadata or {}
        pdf.close()

        combined_text = "\n\n".join(full_text_parts)

        return {
            "full_text": combined_text,
            "page_map": page_map,
            "total_pages": len(page_map),
            "metadata": {
                "title": metadata.get("title", ""),
                "author": metadata.get("author", ""),
                "subject": metadata.get("subject", ""),
                "creator": metadata.get("creator", ""),
                "producer": metadata.get("producer", ""),
                "creation_date": metadata.get("creationDate", ""),
                "mod_date": metadata.get("modDate", "")
            }
        }

    def _ocr_pdf_page(self, pdf_data: bytes, page_index: int) -> str:
        """
        Perform OCR on a specific PDF page using EasyOCR.
        """
        try:
            pdf_document = fitz.open(stream=pdf_data, filetype="pdf")
            page = pdf_document[page_index]

            mat = fitz.Matrix(300/72, 300/72)
            pix = page.get_pixmap(matrix=mat)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            reader = easyocr.Reader(['en'], gpu=False)
            text_results = reader.readtext(np.array(img), detail=0)
            text = "\n".join(text_results)

            pdf_document.close()
            self.logger.info(f"OCR extracted {len(text)} characters from page {page_index + 1}")
            return text

        except Exception as e:
            self.logger.error(f"OCR failed for page {page_index + 1}: {str(e)}")
            return ""