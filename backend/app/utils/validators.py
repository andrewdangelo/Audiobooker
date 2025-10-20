"""
Validation utility functions
"""

from typing import Optional


def validate_file_size(file_size: int, max_size: int) -> tuple[bool, Optional[str]]:
    """
    Validate file size
    
    Args:
        file_size: Size of the file in bytes
        max_size: Maximum allowed size in bytes
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if file_size > max_size:
        max_size_mb = max_size / 1024 / 1024
        return False, f"File size exceeds maximum allowed size of {max_size_mb:.1f}MB"
    return True, None


def validate_pdf_content(content: bytes) -> tuple[bool, Optional[str]]:
    """
    Basic validation for PDF content
    
    Args:
        content: File content as bytes
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check if file starts with PDF magic number
    if not content.startswith(b'%PDF'):
        return False, "Invalid PDF file format"
    
    if len(content) < 10:
        return False, "File is too small to be a valid PDF"
    
    return True, None


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing potentially dangerous characters
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove path separators and other dangerous characters
    dangerous_chars = ['/', '\\', '..', '<', '>', ':', '"', '|', '?', '*']
    sanitized = filename
    
    for char in dangerous_chars:
        sanitized = sanitized.replace(char, '_')
    
    return sanitized.strip()
