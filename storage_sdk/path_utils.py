"""
Path Utilities for R2 Storage

Helper functions for generating and parsing R2 file keys/paths.
Provides consistent naming conventions for organizing files in R2.
"""

from typing import Optional, Dict, Any
import uuid
from pathlib import Path
from datetime import datetime


def generate_file_key(
    user_id: Optional[str] = None,
    book_id: Optional[str] = None,
    file_name: Optional[str] = None,
    file_type: Optional[str] = None,
    include_timestamp: bool = False
) -> str:
    """
    Generate a consistent R2 file key/path
    
    Creates organized paths like:
    - "user_123/book_456/document.pdf"
    - "user_123/book_456/audio/output.mp3"
    - "uploads/2024-10-27/abc123.pdf"
    
    Args:
        user_id: Optional user identifier
        book_id: Optional book/audiobook identifier
        file_name: Optional specific file name (auto-generated if not provided)
        file_type: Optional file type folder (e.g., "pdf", "audio", "temp")
        include_timestamp: Whether to include timestamp in path
    
    Returns:
        Generated file key/path as string
    
    Examples:
        >>> generate_file_key(user_id="user_123", book_id="book_456", file_name="input.pdf")
        "user_123/book_456/input.pdf"
        
        >>> generate_file_key(book_id="book_789", file_type="audio", file_name="output.mp3")
        "book_789/audio/output.mp3"
        
        >>> generate_file_key(file_name="test.pdf", include_timestamp=True)
        "uploads/2024-10-27/test.pdf"
    """
    parts = []
    
    # Add user directory
    if user_id:
        parts.append(user_id)
    
    # Add book directory
    if book_id:
        parts.append(book_id)
    elif not user_id and include_timestamp:
        # If no user/book, use timestamp-based organization
        parts.append("uploads")
        parts.append(datetime.now().strftime("%Y-%m-%d"))
    
    # Add file type subdirectory
    if file_type:
        parts.append(file_type)
    
    # Add filename (generate UUID if not provided)
    if file_name:
        parts.append(file_name)
    else:
        # Generate random filename with UUID
        random_name = f"{uuid.uuid4()}.file"
        parts.append(random_name)
    
    return "/".join(parts)


def generate_unique_key(
    prefix: str = "",
    extension: str = "",
    separator: str = "_"
) -> str:
    """
    Generate a unique file key using UUID
    
    Args:
        prefix: Optional prefix for the key
        extension: File extension (e.g., "pdf", "mp3")
        separator: Separator between prefix and UUID
    
    Returns:
        Unique file key
    
    Examples:
        >>> generate_unique_key(prefix="audiobook", extension="pdf")
        "audiobook_a1b2c3d4-e5f6-7890-abcd-ef1234567890.pdf"
        
        >>> generate_unique_key(extension="mp3")
        "a1b2c3d4-e5f6-7890-abcd-ef1234567890.mp3"
    """
    unique_id = str(uuid.uuid4())
    
    if prefix:
        key = f"{prefix}{separator}{unique_id}"
    else:
        key = unique_id
    
    if extension:
        # Remove leading dot if present
        extension = extension.lstrip('.')
        key = f"{key}.{extension}"
    
    return key


def parse_file_key(key: str) -> Dict[str, Any]:
    """
    Parse an R2 file key into its components
    
    Args:
        key: R2 file key/path to parse
    
    Returns:
        Dictionary with parsed components:
        {
            "full_key": str,         # Original key
            "parts": list,           # Path parts
            "filename": str,         # File name
            "extension": str,        # File extension
            "directory": str,        # Parent directory
            "user_id": str or None,  # User ID if present
            "book_id": str or None   # Book ID if present
        }
    
    Examples:
        >>> parse_file_key("user_123/book_456/document.pdf")
        {
            "full_key": "user_123/book_456/document.pdf",
            "parts": ["user_123", "book_456", "document.pdf"],
            "filename": "document.pdf",
            "extension": "pdf",
            "directory": "user_123/book_456",
            "user_id": "user_123",
            "book_id": "book_456"
        }
    """
    parts = key.split('/')
    
    # Get filename and extension
    filename = parts[-1] if parts else ""
    extension = Path(filename).suffix.lstrip('.') if '.' in filename else ""
    
    # Get directory
    directory = "/".join(parts[:-1]) if len(parts) > 1 else ""
    
    # Try to extract user_id and book_id
    user_id = None
    book_id = None
    
    if len(parts) >= 1 and parts[0].startswith('user_'):
        user_id = parts[0]
    
    if len(parts) >= 2:
        if parts[1].startswith('book_'):
            book_id = parts[1]
        elif parts[0].startswith('user_') and not parts[1].startswith('book_'):
            # Could be book_id without prefix
            book_id = parts[1]
    
    return {
        "full_key": key,
        "parts": parts,
        "filename": filename,
        "extension": extension,
        "directory": directory,
        "user_id": user_id,
        "book_id": book_id
    }


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename for safe storage
    
    Removes special characters and spaces, keeps alphanumeric and common punctuation.
    
    Args:
        filename: Original filename
    
    Returns:
        Sanitized filename
    
    Examples:
        >>> sanitize_filename("My Book (2024).pdf")
        "My_Book_2024.pdf"
        
        >>> sanitize_filename("file with spaces & symbols!.mp3")
        "file_with_spaces_symbols.mp3"
    """
    # Handle None or non-string input
    if not filename or not isinstance(filename, str):
        raise ValueError(f"filename must be a non-empty string, got: {type(filename).__name__}")
    
    # Keep the extension
    path = Path(filename)
    name = path.stem
    ext = path.suffix
    
    # Replace spaces and special chars with underscore
    safe_name = ""
    for char in name:
        if char.isalnum() or char in ('-', '_', '.'):
            safe_name += char
        elif char == ' ':
            safe_name += '_'
    
    # Remove consecutive underscores
    while '__' in safe_name:
        safe_name = safe_name.replace('__', '_')
    
    # Remove leading/trailing underscores
    safe_name = safe_name.strip('_')
    
    return f"{safe_name}{ext}"


def get_content_type(filename: str) -> str:
    """
    Get MIME type from filename extension
    
    Args:
        filename: File name or path
    
    Returns:
        MIME type string
    
    Examples:
        >>> get_content_type("document.pdf")
        "application/pdf"
        
        >>> get_content_type("audio.mp3")
        "audio/mpeg"
    """
    extension = Path(filename).suffix.lower()
    
    content_types = {
        '.pdf': 'application/pdf',
        '.mp3': 'audio/mpeg',
        '.wav': 'audio/wav',
        '.m4a': 'audio/mp4',
        '.txt': 'text/plain',
        '.json': 'application/json',
        '.xml': 'application/xml',
        '.zip': 'application/zip',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
    }
    
    return content_types.get(extension, 'application/octet-stream')
