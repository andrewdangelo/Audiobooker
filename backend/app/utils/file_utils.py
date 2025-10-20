"""
File utility functions
"""

import os
import uuid
from pathlib import Path
from typing import Optional


def generate_unique_filename(original_filename: str, extension: Optional[str] = None) -> str:
    """
    Generate a unique filename
    
    Args:
        original_filename: Original file name
        extension: File extension (with dot)
        
    Returns:
        Unique filename
    """
    if extension is None:
        extension = Path(original_filename).suffix
    
    unique_id = str(uuid.uuid4())
    return f"{unique_id}{extension}"


def get_file_extension(filename: str) -> str:
    """Get file extension including the dot"""
    return Path(filename).suffix


def validate_file_extension(filename: str, allowed_extensions: list[str]) -> bool:
    """
    Validate file extension
    
    Args:
        filename: Name of the file
        allowed_extensions: List of allowed extensions (with dots)
        
    Returns:
        True if extension is allowed
    """
    extension = get_file_extension(filename).lower()
    return extension in [ext.lower() for ext in allowed_extensions]


def ensure_directory_exists(directory_path: str) -> None:
    """Create directory if it doesn't exist"""
    Path(directory_path).mkdir(parents=True, exist_ok=True)


def get_file_size(file_path: str) -> int:
    """Get file size in bytes"""
    return os.path.getsize(file_path)
