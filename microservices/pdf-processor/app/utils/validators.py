"""
Validation Utilities

Common validation functions for the microservice.
"""

import re
from typing import Optional
from pathlib import Path


class ValidationError(Exception):
    """Custom validation error"""
    pass


def validate_r2_key(key: str) -> str:
    """
    Validate R2 storage key format
    
    Args:
        key: R2 key to validate
    
    Returns:
        Cleaned key
    
    Raises:
        ValidationError: If key is invalid
    """
    if not key or not key.strip():
        raise ValidationError("R2 key cannot be empty")
    
    key = key.strip()
    
    # Check for invalid characters
    invalid_chars = ['\\', '<', '>', '|', '"', '?', '*']
    for char in invalid_chars:
        if char in key:
            raise ValidationError(f"R2 key contains invalid character: {char}")
    
    # Check if it's a PDF TODO we must check for ebooks as well with those respective extensions
    if not key.lower().endswith('.pdf'):
        raise ValidationError("R2 key must point to a PDF file (.pdf extension)")
    
    return key


def validate_chunk_parameters(chunk_size: int, chunk_overlap: int) -> None:
    """
    Validate chunking parameters
    
    Args:
        chunk_size: Chunk size in characters
        chunk_overlap: Overlap in characters
    
    Raises:
        ValidationError: If parameters are invalid
    """
    if chunk_size < 100:
        raise ValidationError("Chunk size must be at least 100 characters")
    
    if chunk_size > 5000:
        raise ValidationError("Chunk size cannot exceed 5000 characters")
    
    if chunk_overlap < 0:
        raise ValidationError("Chunk overlap cannot be negative")
    
    if chunk_overlap >= chunk_size:
        raise ValidationError("Chunk overlap must be less than chunk size")


def validate_file_size(size_bytes: int, max_size_mb: int = 100) -> None:
    """
    Validate file size
    
    Args:
        size_bytes: File size in bytes
        max_size_mb: Maximum allowed size in MB
    
    Raises:
        ValidationError: If file is too large
    """
    max_bytes = max_size_mb * 1024 * 1024
    
    if size_bytes > max_bytes:
        raise ValidationError(
            f"File size ({size_bytes:,} bytes) exceeds maximum "
            f"allowed size ({max_bytes:,} bytes)"
        )


def is_valid_pdf_magic_number(data: bytes) -> bool:
    """
    Check if bytes start with PDF magic number
    
    Args:
        data: File bytes to check
    
    Returns:
        True if valid PDF or other extensions, otherwise False
    """
    if len(data) < 4:
        return False
    
    # PDF files start with %PDF
    return data[:4] == b'%PDF' #TODO check for other ebook formats as well


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe storage
    
    Args:
        filename: Original filename
    
    Returns:
        Sanitized final filename
    """
    # Remove path components
    filename = Path(filename).name
    
    # Replace spaces or white spaces with underscores
    filename = filename.replace(' ', '_')
    
    # Removing any non-alphanumeric characters except dots, hyphens, underscores #TODO might be more restrictions to be added later on
    filename = re.sub(r'[^\w\.\-]', '', filename)
    
    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:250] + ('.' + ext if ext else '')
    
    return filename