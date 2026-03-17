"""
PDF Processing Service

Core service for extracting and processing text from PDFs.
"""
__author__ = "Mohammad Saifan"

import io
import time
import asyncio
from typing import (Dict, Any, List)
from datetime import datetime

import fitz  # PyMuPDF
from PIL import Image
import pytesseract
import easyocr
import numpy as np

from PyPDF2 import PdfReader
from PyPDF2.errors import PdfReadError

from app.core.logging_config import Logger
from app.core.redis_manager import redis_manager
from app.core.config_settings import settings
from app.utils.chunker import TextChunker

from app.services import r2_service
from app.services.llm_speaker_chunker import SpeakerChunker
from app.database import (database, db_engine)


class PDFProcessorService(Logger):
    """
    PDF Processing Service
    
    Handles PDF text extraction, chunking, and formatting.
    """
    
    def __init__(self):
        """Initialize PDF processor"""
        self.chunker = TextChunker()
        self.logger.info("PDF Processor Service initialized")
    
    # ==================== Redis Job Manageer ====================

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
        # Refresh TTL on each update
        await redis_manager.expire(key, redis_manager.JOB_TTL)

    async def create_job(self, job_id: str, job_data: Dict[str, Any]) -> None:
        """Create new job in Redis with TTL"""
        key = f"{redis_manager.JOB_PREFIX}:{job_id}"
        for field, value in job_data.items():
            await redis_manager.hset(key, field, value)
        await redis_manager.expire(key, redis_manager.JOB_TTL)
    
    # ==================== PDF PROCESSOR TASKS ====================
    
    async def process_pdf_task(self, job_id: str, user_id: str, r2_key: str, chunk_size: int, chunk_overlap: int, output_format: str):
        """Background task for processing PDF"""
        try:
            self.logger.info(f"Starting PDF processing for job {job_id}, user {user_id}")
            
            r2_svc = r2_service.R2Service()
            
            await self.update_job(job_id, {"status": "processing", "message": "Downloading PDF from R2", "progress": 10})
            
            pdf_data = r2_svc.download_file(r2_key)
            
            await self.update_job(job_id, {"message": "Extracting text from PDF", "progress": 30})
            
            result = await self.process_pdf(pdf_data=pdf_data, chunk_size=chunk_size, chunk_overlap=chunk_overlap, output_format=output_format)
            
            await self.update_job(job_id, {"progress": 80, "message": "Uploading processed data to R2"})
            
            output_key = f"processed_audiobooks/{job_id.replace('.pdf', '')}_processed.json"
            r2_svc.upload_processed_data(key=output_key, data=result)
            
            # LLM Speaker Chunking (if enabled)
            script_output_key = None
            if settings.ENABLE_LLM_CHUNKING and settings.HF_TOKEN:
                try:
                    self.logger.info(f"Starting LLM speaker chunking for job {job_id}")
                    await self.update_job(job_id, {
                        "progress": 85,
                        "message": "Processing speaker attribution with LLM"
                    })
                    
                    # Initialize LLM chunker
                    llm_chunker = SpeakerChunker(
                        api_key=settings.HF_TOKEN,
                        model=settings.LLM_MODEL,
                        base_url=settings.HF_ENDPOINT_URL
                    )
                    
                    # Warmup endpoint if serverless mode is enabled
                    """ if settings.LLM_SERVERLESS:
                        self.logger.info("Warming up serverless endpoint...")
                        llm_chunker.warmup_endpoint() """
                    
                    # Track progress for job updates
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
                    script_output_key = f"processed_audiobooks/{job_id.replace('.pdf', '')}_script.json"
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
            
            # Create audiobook record in database
            self.logger.info(f"Creating database record for job {job_id}")
            from app.database import database, db_engine
            from app.models.db_models import Collections
            
            db_func = database.get_db()
            db = db_func()
            audiobook_service = db_engine.MongoDBService(db, Collections.PROCESSED_AUDIOBOOKS)
            
            audiobook_data = {"r2_key": job_id, "user_id": user_id, "title": r2_key.split("/")[-1], "pdf_path": r2_key, "status": "COMPLETED"}
            
            audiobook = audiobook_service.create(audiobook_data)
            
            self.logger.info(f"Upload complete - ID: {audiobook.get('r2_key')}")
            
            # Update job with completion results
            job_result = {
                "output_key": output_key,
                "total_chunks": result.get("total_chunks", 0),
                "total_pages": result.get("total_pages", 0),
                "total_characters": result.get("total_characters", 0)
            }
            
            # Add script output if LLM chunking was performed
            if script_output_key:
                job_result["script_output_key"] = script_output_key
                job_result["llm_chunking_enabled"] = True
            
            await self.update_job(job_id, {
                "status": "completed",
                "progress": 100,
                "message": "Processing completed successfully",
                "completed_at": f"{datetime.now().strftime('%m-%d-%Y')} at {datetime.now().strftime('%I:%M %p')}",
                "result": job_result
            })
            
            self.logger.info(f"Job {job_id} completed successfully")
            
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

    def _extract_text_from_pdf(self, pdf_data: bytes) -> Dict[str, Any]:
        """
        Extract text from PDF bytes with automatic OCR for scanned PDFs
        
        Args:
            pdf_data: PDF file as bytes
        
        Returns:
            Dict with full_text, page_map, total_pages, and metadata
        """
        pdf = fitz.open(stream=pdf_data, filetype="pdf")
        
        full_text_parts = []
        page_map = []
        current_pos = 0
        
        for page_num, page in enumerate(pdf, start=1):
            # Try normal text extraction first
            text = page.get_text("text")
            
            # If too little text, use OCR
            if len(text.strip()) < 50:
                try:
                    self.logger.info(f"Performing OCR on page {page_num}")
                    
                    # Convert page to image at 300 DPI for better OCR
                    mat = fitz.Matrix(300/72, 300/72)
                    pix = page.get_pixmap(matrix=mat)
                    
                    # Convert pixmap to PIL Image for pytesseract
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    
                    # Run OCR
                    text = pytesseract.image_to_string(img)
                    
                except Exception as e:
                    self.logger.error(f"OCR failed for page {page_num}: {e}")
                    text = ""
            
            # Clean up whitespace
            cleaned_text = " ".join(text.split()) if text else ""
            
            start_pos = current_pos
            end_pos = current_pos + len(cleaned_text)
            
            page_map.append(
                {
                    "page": page_num,
                    "start": start_pos,
                    "end": end_pos,
                    "char_count": len(cleaned_text)
                }
            )
            
            full_text_parts.append(cleaned_text)
            current_pos = end_pos + 1
        
        # Extract metadata
        metadata = pdf.metadata or {}
        
        pdf.close()
        combined_text = "\n".join(full_text_parts)
        
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
        Perform OCR on a specific PDF page using EasyOCR
        
        Args:
            pdf_data: PDF file as bytes
            page_index: Zero-based page index
        
        Returns:
            Extracted text from the page
        """
        try:
            pdf_document = fitz.open(stream=pdf_data, filetype="pdf")
            page = pdf_document[page_index]

            # Render page to image at 300 DPI
            mat = fitz.Matrix(300/72, 300/72)
            pix = page.get_pixmap(matrix=mat)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            # EasyOCR extraction
            reader = easyocr.Reader(['en'], gpu=False)
            text_results = reader.readtext(np.array(img), detail=0)
            text = "\n".join(text_results)

            pdf_document.close()
            self.logger.info(f"OCR extracted {len(text)} characters from page {page_index + 1}")
            return text

        except Exception as e:
            self.logger.error(f"OCR failed for page {page_index + 1}: {str(e)}")
            return ""
    
    def _extract_metadata(self, reader: PdfReader) -> Dict[str, Any]:
        """
        Extract metadata from PDF
        
        Args:
            reader: PdfReader instance
        
        Returns:
            Metadata dict
        """
        metadata = {}
        
        try:
            if reader.metadata:
                for key, value in reader.metadata.items():
                    # Clean metadata keys (remove leading slashes)
                    clean_key = key.lstrip('/')
                    metadata[clean_key] = str(value) if value else None
        except Exception as e:
            self.logger.warning(f"Failed to extract metadata: {str(e)}")
        
        return metadata
    
    def _clean_text(self, text: str) -> str:
        """
        Clean extracted text
        
        Args:
            text: Raw extracted text
        
        Returns:
            Cleaned text
        """
        # Remove excessive whitespace
        text = ' '.join(text.split())
        
        # Remove null bytes
        text = text.replace('\x00', '')
        
        # Normalize line breaks
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        return text.strip()