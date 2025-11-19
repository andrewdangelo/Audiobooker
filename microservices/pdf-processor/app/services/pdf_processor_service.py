"""
PDF Processing Service

Core service for extracting and processing text from PDFs.
"""

import io
import time
from typing import Dict, Any, List
from datetime import datetime

from PyPDF2 import PdfReader
from PyPDF2.errors import PdfReadError

from app.core.logging_config import Logger
from app.utils.chunker import TextChunker


class PDFProcessorService(Logger):
    """
    PDF Processing Service
    
    Handles PDF text extraction, chunking, and formatting.
    """
    
    def __init__(self):
        """Initialize PDF processor"""
        self.chunker = TextChunker()
        self.logger.info("PDF Processor Service initialized")
    
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
                "r2_key": "",  # Will be set by caller
                "total_pages": extracted_data["total_pages"],
                "total_characters": len(extracted_data["full_text"]),
                "total_chunks": len(chunks),
                "chunks": chunks,
                "metadata": extracted_data["metadata"],
                "processing_time": round(processing_time, 2),
                "created_at": datetime.utcnow().isoformat()
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
        Extract text from PDF bytes
        
        Args:
            pdf_data: PDF file as bytes
        
        Returns:
            Dict with full_text, page_map, total_pages, and metadata
        """
        try:
            # Create PDF reader from bytes
            pdf_file = io.BytesIO(pdf_data)
            reader = PdfReader(pdf_file)
            
            # Extract metadata
            metadata = self._extract_metadata(reader)
            
            # Extract text from each page
            full_text = []
            page_map = []  # Maps character positions to page numbers
            current_pos = 0
            
            for page_num, page in enumerate(reader.pages, start=1):
                try:
                    page_text = page.extract_text()
                    
                    if page_text:
                        # Clean up text
                        page_text = self._clean_text(page_text)
                        
                        # Track page boundaries
                        start_pos = current_pos
                        end_pos = current_pos + len(page_text)
                        
                        page_map.append({
                            "page": page_num,
                            "start": start_pos,
                            "end": end_pos,
                            "char_count": len(page_text)
                        })
                        
                        full_text.append(page_text)
                        current_pos = end_pos + 1  # +1 for newline
                        
                except Exception as e:
                    self.logger.warning(f"Failed to extract text from page {page_num}: {str(e)}")
                    continue
            
            # Combine all text
            combined_text = "\n".join(full_text)
            
            self.logger.info(
                f"Extracted text from PDF - "
                f"Pages: {len(reader.pages)}, "
                f"Characters: {len(combined_text):,}"
            )
            
            return {
                "full_text": combined_text,
                "page_map": page_map,
                "total_pages": len(reader.pages),
                "metadata": metadata
            }
            
        except Exception as e:
            self.logger.error(f"Text extraction failed: {str(e)}", exc_info=True)
            raise
    
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
                    # Clean metadata keys (remove leading slashes from the left side)
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

