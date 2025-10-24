"""
Cloud Storage Service (Cloudflare R2) with Local Fallback
"""

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from config.settings import settings
from typing import Optional
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class StorageService:
    """Service for interacting with storage (R2 or local filesystem)"""
    
    def __init__(self):
        # Check if R2 credentials are configured
        self.use_local = (
            not settings.R2_ENDPOINT_URL or 
            settings.R2_ENDPOINT_URL.startswith("https://<account_id>") or
            settings.R2_ENDPOINT_URL.startswith("https://your_account_id") or
            not settings.R2_ACCESS_KEY_ID or
            settings.R2_ACCESS_KEY_ID == "your_access_key_id_here"
        )
        
        if self.use_local:
            # Use local filesystem storage for development
            logger.info("Using local filesystem storage")
            self.storage_path = Path(settings.UPLOAD_DIR)
            self.storage_path.mkdir(exist_ok=True)
        else:
            # Use Cloudflare R2
            logger.info(f"Using Cloudflare R2 storage: {settings.R2_BUCKET_NAME}")
            try:
                self.s3_client = boto3.client(
                    's3',
                    endpoint_url=settings.R2_ENDPOINT_URL,
                    aws_access_key_id=settings.R2_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
                    config=Config(signature_version='s3v4'),
                    region_name='auto'
                )
                self.bucket_name = settings.R2_BUCKET_NAME
                # Test connection
                self.s3_client.head_bucket(Bucket=self.bucket_name)
                logger.info(f"Successfully connected to R2 bucket: {self.bucket_name}")
            except ClientError as e:
                logger.error(f"Failed to connect to R2: {e}")
                logger.warning("Falling back to local storage")
                self.use_local = True
                self.storage_path = Path(settings.UPLOAD_DIR)
                self.storage_path.mkdir(exist_ok=True)
    
    async def upload_file(
        self,
        file_content: bytes,
        file_name: str,
        content_type: Optional[str] = None
    ) -> str:
        """
        Upload a file to storage (R2 or local)
        
        Args:
            file_content: File content as bytes
            file_name: Name/key for the file in storage
            content_type: MIME type of the file
            
        Returns:
            Path/key of the uploaded file (full R2 path or local path)
        """
        try:
            if self.use_local:
                # Save to local filesystem
                file_path = self.storage_path / file_name
                with open(file_path, 'wb') as f:
                    f.write(file_content)
                logger.info(f"File saved locally: {file_path}")
                return str(file_path)
            else:
                # Upload to R2
                extra_args = {}
                if content_type:
                    extra_args['ContentType'] = content_type
                
                logger.info(f"Uploading to R2: {file_name}")
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=file_name,
                    Body=file_content,
                    **extra_args
                )
                
                # Return the R2 URL path
                r2_path = f"r2://{self.bucket_name}/{file_name}"
                logger.info(f"File uploaded to R2: {r2_path}")
                return r2_path
        except ClientError as e:
            logger.error(f"R2 upload failed: {e}")
            raise Exception(f"Failed to upload file to R2: {str(e)}")
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            raise Exception(f"Failed to upload file to storage: {str(e)}")
    
    async def download_file(self, file_key: str) -> bytes:
        """
        Download a file from storage
        
        Args:
            file_key: Key/path of the file in storage
            
        Returns:
            File content as bytes
        """
        try:
            if self.use_local:
                # Read from local filesystem
                with open(file_key, 'rb') as f:
                    return f.read()
            else:
                # Download from R2
                response = self.s3_client.get_object(
                    Bucket=self.bucket_name,
                    Key=file_key
                )
                return response['Body'].read()
        except Exception as e:
            raise Exception(f"Failed to download file from storage: {str(e)}")
    
    async def delete_file(self, file_key: str) -> bool:
        """
        Delete a file from storage
        
        Args:
            file_key: Key/path of the file to delete
            
        Returns:
            True if successful
        """
        try:
            if self.use_local:
                # Delete from local filesystem
                os.remove(file_key)
                return True
            else:
                # Delete from R2
                self.s3_client.delete_object(
                    Bucket=self.bucket_name,
                    Key=file_key
                )
                return True
        except Exception as e:
            raise Exception(f"Failed to delete file from storage: {str(e)}")
    
    def get_file_url(self, file_key: str, expiration: int = 3600) -> str:
        """
        Generate a presigned URL for file access
        
        Args:
            file_key: Key/path of the file
            expiration: URL expiration time in seconds (default 1 hour)
            
        Returns:
            Presigned URL or local path
        """
        try:
            if self.use_local:
                # Return local file path
                return f"file://{file_key}"
            else:
                # Generate R2 presigned URL
                url = self.s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': self.bucket_name, 'Key': file_key},
                    ExpiresIn=expiration
                )
                return url
        except Exception as e:
            raise Exception(f"Failed to generate URL: {str(e)}")

