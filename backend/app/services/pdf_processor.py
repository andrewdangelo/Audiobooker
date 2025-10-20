"""
PDF Processing Service
Handles extraction of text from PDF documents
"""

import PyPDF2
from typing import List, Dict
import io


class PDFProcessorService:
    """Service for processing PDF files"""
    
    def extract_text(self, pdf_content: bytes) -> str:
        """
        Extract all text from a PDF file
        
        Args:
            pdf_content: PDF file content as bytes
            
        Returns:
            Extracted text as string
        """
        pdf_file = io.BytesIO(pdf_content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        
        return text.strip()
    
    def extract_text_by_page(self, pdf_content: bytes) -> List[Dict[str, any]]:
        """
        Extract text from PDF, organized by page
        
        Args:
            pdf_content: PDF file content as bytes
            
        Returns:
            List of dictionaries with page number and text
        """
        pdf_file = io.BytesIO(pdf_content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        pages = []
        for i, page in enumerate(pdf_reader.pages):
            pages.append({
                "page_number": i + 1,
                "text": page.extract_text()
            })
        
        return pages
    
    def get_page_count(self, pdf_content: bytes) -> int:
        """
        Get the number of pages in a PDF
        
        Args:
            pdf_content: PDF file content as bytes
            
        Returns:
            Number of pages
        """
        pdf_file = io.BytesIO(pdf_content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        return len(pdf_reader.pages)
