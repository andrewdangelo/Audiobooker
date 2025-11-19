"""
Cloudflare R2 Storage SDK

A lightweight library for interacting with Cloudflare R2 storage.
Provides simple functions for uploading, downloading, deleting files,
and generating presigned URLs.
"""

__version__ = "1.0.0"

from .r2_client import (
    R2Client,
    upload_file,
    download_file,
    delete_file,
    generate_presigned_url,
    list_files,
)

from .path_utils import (
    generate_file_key,
    parse_file_key,
    generate_unique_key,
    sanitize_filename,
)

__all__ = [
    "R2Client",
    "upload_file",
    "download_file",
    "delete_file",
    "generate_presigned_url",
    "list_files",
    generate_unique_key,
    "generate_file_key",
    "parse_file_key",
]
