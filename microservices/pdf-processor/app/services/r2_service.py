"""
R2 Storage Service

Wrapper around the R2 client for microservice-specific operations.
"""

import json
import logging
from typing import Optional, Dict, Any

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config_settings import settings
from app.core.logging_config import Logger


class R2Service(Logger):
    """
    R2 Storage Service for PDF microservice
    
    Handles all R2 storage operations with retry logic and error handling.
    """
    
    def __init__(self):
        """Initialize R2 service with credentials from settings"""
        endpoint_url = settings.R2_ENDPOINT_URL or f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
        
        self.s3_client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            config=Config(signature_version='s3v4'),
            region_name='auto'
        )
        
        self.bucket_name = settings.R2_BUCKET_NAME
        self.logger.info(f"R2 Service initialized - Bucket: {self.bucket_name}")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    def download_file(self, key: str) -> bytes:
        """
        Download a file from R2 with retry logic
        
        Args:
            key: R2 storage key
        
        Returns:
            File content as bytes
        
        Raises:
            FileNotFoundError: If file doesn't exist
            Exception: For other R2 errors
        """
        try:
            self.logger.info(f"Downloading file from R2: {key}")
            
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=key
            )
            
            file_data = response['Body'].read()
            file_size = len(file_data)
            
            self.logger.info(f"Downloaded {key} - Size: {file_size:,} bytes")
            
            # Validate file size
            if file_size > settings.max_file_size_bytes:
                raise ValueError(
                    f"File size ({file_size:,} bytes) exceeds maximum allowed "
                    f"({settings.max_file_size_bytes:,} bytes)"
                )
            
            return file_data
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            
            if error_code == 'NoSuchKey':
                self.logger.error(f"File not found in R2: {key}")
                raise FileNotFoundError(f"File not found in R2: {key}")
            
            self.logger.error(f"R2 download error for {key}: {error_code} - {str(e)}")
            raise Exception(f"Failed to download from R2: {str(e)}")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    def upload_processed_data(self, key: str, data: Dict[str, Any], metadata: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Upload processed data to R2
        
        Args:
            key: R2 storage key for output
            data: Processed data to upload
            metadata: Optional metadata
        
        Returns:
            Upload details
        """
        try:
            self.logger.info(f"Uploading processed data to R2: {key}")
            
            # Convert data to JSON
            json_data = json.dumps(data, default=str, indent=2)
            json_bytes = json_data.encode('utf-8')
            
            # Prepare upload args
            upload_args = {
                'ContentType': 'application/json',
                'ContentLength': len(json_bytes)
            }
            
            if metadata:
                upload_args['Metadata'] = metadata
            
            # Upload to R2
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=json_bytes,
                **upload_args
            )
            
            self.logger.info(f"Successfully uploaded to R2: {key} ({len(json_bytes):,} bytes)")
            
            return {
                "key": key,
                "bucket": self.bucket_name,
                "size": len(json_bytes),
                "content_type": "application/json",
                "url": f"r2://{self.bucket_name}/{key}"
            }
            
        except ClientError as e:
            self.logger.error(f"Failed to upload to R2: {str(e)}", exc_info=True)
            raise Exception(f"R2 upload failed: {str(e)}")
    
    def file_exists(self, key: str) -> bool:
        """
        Check if a file exists in R2
        
        Args:
            key: R2 storage key
        
        Returns:
            True if file exists, False otherwise
        """
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=key
            )
            return True
        except ClientError as e:
            if e.response.get('Error', {}).get('Code') == '404':
                return False
            self.logger.error(f"Error checking file existence: {str(e)}")
            return False
    
    def get_file_metadata(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get file metadata from R2
        
        Args:
            key: R2 storage key
        
        Returns:
            File metadata dict or None if not found
        """
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=key
            )
            
            return {
                "size": response.get('ContentLength', 0),
                "content_type": response.get('ContentType'),
                "last_modified": response.get('LastModified'),
                "metadata": response.get('Metadata', {})
            }
            
        except ClientError as e:
            self.logger.error(f"Failed to get metadata for {key}: {str(e)}")
            return None