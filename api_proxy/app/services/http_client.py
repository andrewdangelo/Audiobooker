"""
HTTP Client Service for proxying requests to microservices
"""

import httpx
from typing import Optional, Dict, Any
from fastapi import UploadFile
import logging

from config.settings import settings

logger = logging.getLogger(__name__)


class HTTPClient:
    """Async HTTP client for microservice communication"""
    
    def __init__(self):
        self.timeout = httpx.Timeout(
            connect=10.0,
            read=settings.REQUEST_TIMEOUT,
            write=settings.REQUEST_TIMEOUT,
            pool=10.0
        )
        self.upload_timeout = httpx.Timeout(
            connect=10.0,
            read=settings.UPLOAD_TIMEOUT,
            write=settings.UPLOAD_TIMEOUT,
            pool=10.0
        )
    
    async def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> httpx.Response:
        """Make GET request to microservice"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params, headers=headers)
            return response
    
    async def post(
        self,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> httpx.Response:
        """Make POST request to microservice"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=json, data=data, headers=headers)
            return response
    
    async def post_file(
        self,
        url: str,
        file: UploadFile,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> httpx.Response:
        """Upload file to microservice"""
        async with httpx.AsyncClient(timeout=self.upload_timeout) as client:
            files = {"file": (file.filename, await file.read(), file.content_type)}
            response = await client.post(url, files=files, data=data, headers=headers)
            return response
    
    async def put(
        self,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> httpx.Response:
        """Make PUT request to microservice"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.put(url, json=json, headers=headers)
            return response
    
    async def delete(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None
    ) -> httpx.Response:
        """Make DELETE request to microservice"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.delete(url, headers=headers)
            return response


# Singleton instance
http_client = HTTPClient()
