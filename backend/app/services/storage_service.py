"""
Cloud Storage Service (Cloudflare R2)
"""

import boto3
from botocore.client import Config
from config.settings import settings
from typing import Optional


class StorageService:
    """Service for interacting with Cloudflare R2 storage"""
    
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            endpoint_url=settings.R2_ENDPOINT_URL,
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            config=Config(signature_version='s3v4'),
            region_name='auto'
        )
        self.bucket_name = settings.R2_BUCKET_NAME
    
    async def upload_file(
        self,
        file_content: bytes,
        file_name: str,
        content_type: Optional[str] = None
    ) -> str:
        """
        Upload a file to R2 storage
        
        Args:
            file_content: File content as bytes
            file_name: Name/key for the file in storage
            content_type: MIME type of the file
            
        Returns:
            Path/key of the uploaded file
        """
        try:
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=file_name,
                Body=file_content,
                **extra_args
            )
            
            return file_name
        except Exception as e:
            raise Exception(f"Failed to upload file to storage: {str(e)}")
    
    async def download_file(self, file_key: str) -> bytes:
        """
        Download a file from R2 storage
        
        Args:
            file_key: Key/path of the file in storage
            
        Returns:
            File content as bytes
        """
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=file_key
            )
            return response['Body'].read()
        except Exception as e:
            raise Exception(f"Failed to download file from storage: {str(e)}")
    
    async def delete_file(self, file_key: str) -> bool:
        """
        Delete a file from R2 storage
        
        Args:
            file_key: Key/path of the file to delete
            
        Returns:
            True if successful
        """
        try:
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
            Presigned URL
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': file_key},
                ExpiresIn=expiration
            )
            return url
        except Exception as e:
            raise Exception(f"Failed to generate presigned URL: {str(e)}")
