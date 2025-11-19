"""
Cloudflare R2 Client

Main module for interacting with Cloudflare R2 storage using boto3 S3 API.
"""

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from typing import Optional, Dict, Any, List, BinaryIO, Union
from pathlib import Path
import os
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)
# Load .env file into the environment
load_dotenv()

class R2Client:
    """
    Cloudflare R2 Storage Client
    
    Handles all interactions with Cloudflare R2 using the S3-compatible API.
    
    Example:
        >>> client = R2Client(
        ...     account_id="your_account_id",
        ...     access_key_id="your_access_key",
        ...     secret_access_key="your_secret_key",
        ...     bucket_name="your_bucket"
        ... )
        >>> result = client.upload("path/to/file.pdf", "/local/file.pdf")
    """
    
    def __init__(
        self,
        account_id: str,
        access_key_id: str,
        secret_access_key: str,
        bucket_name: str,
        endpoint_url: Optional[str] = None
    ):
        """
        Initialize R2 client
        
        Args:
            account_id: Cloudflare account ID
            access_key_id: R2 access key ID
            secret_access_key: R2 secret access key
            bucket_name: Name of the R2 bucket
            endpoint_url: Optional custom endpoint URL. If not provided,
                         will be constructed from account_id
        """
        self.account_id = account_id
        self.bucket_name = bucket_name
        
        # Construct endpoint URL if not provided
        if endpoint_url is None:
            endpoint_url = f"https://{account_id}.r2.cloudflarestorage.com"
        
        self.endpoint_url = endpoint_url
        
        # Initialize S3 client for R2
        self.s3_client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            config=Config(signature_version='s3v4'),
            region_name='auto'
        )
        
        logger.info(f"R2 client initialized for bucket: {bucket_name}")
    
    def upload(
        self,
        key: str,
        file_path: Optional[str] = None,
        file_data: Optional[bytes] = None,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Upload a file to R2
        
        Args:
            key: The key (path) where the file will be stored in R2
            file_path: Local file path to upload (provide either this or file_data)
            file_data: Raw bytes to upload (provide either this or file_path)
            content_type: MIME type of the file (auto-detected if not provided)
            metadata: Optional metadata to attach to the file
        
        Returns:
            Dict with upload details:
            {
                "key": str,              # R2 key where file was uploaded
                "bucket": str,           # Bucket name
                "size": int,             # File size in bytes
                "url": str,              # R2 URL (r2://bucket/key format)
                "content_type": str,     # Content type
                "metadata": dict         # Attached metadata
            }
        
        Raises:
            ValueError: If neither file_path nor file_data provided
            ClientError: If upload fails
        """
        try:
            # Prepare upload arguments
            upload_args = {}
            
            if content_type:
                upload_args['ContentType'] = content_type
            
            if metadata:
                upload_args['Metadata'] = metadata
            
            # Upload from file path or raw data
            if file_path:
                file_size = os.path.getsize(file_path)
                
                # Auto-detect content type if not provided
                if not content_type and file_path.endswith('.pdf'):
                    upload_args['ContentType'] = 'application/pdf'
                elif not content_type and file_path.endswith('.mp3'):
                    upload_args['ContentType'] = 'audio/mpeg'
                
                self.s3_client.upload_file(
                    file_path,
                    self.bucket_name,
                    key,
                    ExtraArgs=upload_args if upload_args else None
                )
                
            elif file_data:
                file_size = len(file_data)
                
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=key,
                    Body=file_data,
                    **upload_args
                )
                
            else:
                raise ValueError("Either file_path or file_data must be provided")
            
            logger.info(f"Uploaded file to R2: {key} ({file_size} bytes)")
            
            return {
                "key": key,
                "bucket": self.bucket_name,
                "size": file_size,
                "url": f"r2://{self.bucket_name}/{key}",
                "content_type": upload_args.get('ContentType'),
                "metadata": metadata or {}
            }
            
        except ClientError as e:
            logger.error(f"Failed to upload to R2: {e}")
            raise Exception(f"R2 upload failed: {str(e)}")
    
    def download(
        self,
        key: str,
        local_path: Optional[str] = None
    ) -> Union[bytes, Dict[str, Any]]:
        """
        Download a file from R2
        
        Args:
            key: The key (path) of the file in R2
            local_path: Optional local file path to save to.
                       If not provided, returns raw bytes.
        
        Returns:
            If local_path provided: Dict with download details
            If no local_path: bytes of the file content
            
            Download details dict:
            {
                "key": str,              # R2 key
                "local_path": str,       # Local file path
                "size": int,             # File size in bytes
                "content_type": str,     # Content type
                "metadata": dict         # File metadata
            }
        
        Raises:
            ClientError: If file not found or download fails
        """
        try:
            if local_path:
                # Download to file
                self.s3_client.download_file(
                    self.bucket_name,
                    key,
                    local_path
                )
                
                # Get file metadata
                response = self.s3_client.head_object(
                    Bucket=self.bucket_name,
                    Key=key
                )
                
                logger.info(f"Downloaded file from R2: {key} -> {local_path}")
                
                return {
                    "key": key,
                    "local_path": local_path,
                    "size": response.get('ContentLength', 0),
                    "content_type": response.get('ContentType'),
                    "metadata": response.get('Metadata', {})
                }
            else:
                # Download to memory
                response = self.s3_client.get_object(
                    Bucket=self.bucket_name,
                    Key=key
                )
                
                file_data = response['Body'].read()
                logger.info(f"Downloaded file from R2 to memory: {key} ({len(file_data)} bytes)")
                
                return file_data
                
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                raise FileNotFoundError(f"File not found in R2: {key}")
            logger.error(f"Failed to download from R2: {e}")
            raise Exception(f"R2 download failed: {str(e)}")
    
    def delete(self, key: str) -> Dict[str, Any]:
        """
        Delete a file from R2
        
        Args:
            key: The key (path) of the file to delete
        
        Returns:
            Dict with deletion details:
            {
                "key": str,              # Deleted key
                "bucket": str,           # Bucket name
                "deleted": bool          # Success status
            }
        
        Raises:
            ClientError: If deletion fails
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )
            
            logger.info(f"Deleted file from R2: {key}")
            
            return {
                "key": key,
                "bucket": self.bucket_name,
                "deleted": True
            }
            
        except ClientError as e:
            logger.error(f"Failed to delete from R2: {e}")
            raise Exception(f"R2 deletion failed: {str(e)}")
    
    def generate_presigned_url(
        self,
        key: str,
        expiration: int = 3600,
        method: str = "get"
    ) -> Dict[str, Any]:
        """
        Generate a presigned URL for temporary access to a file
        
        Args:
            key: The key (path) of the file
            expiration: URL expiration time in seconds (default: 1 hour)
            method: HTTP method - 'get' for download, 'put' for upload
        
        Returns:
            Dict with presigned URL details:
            {
                "key": str,              # R2 key
                "url": str,              # Presigned URL
                "expires_in": int,       # Expiration time in seconds
                "method": str            # HTTP method (GET/PUT)
            }
        
        Raises:
            ClientError: If URL generation fails
        """
        try:
            client_method = 'get_object' if method.lower() == 'get' else 'put_object'
            
            url = self.s3_client.generate_presigned_url(
                client_method,
                Params={
                    'Bucket': self.bucket_name,
                    'Key': key
                },
                ExpiresIn=expiration
            )
            
            logger.info(f"Generated presigned URL for {key} (expires in {expiration}s)")
            
            return {
                "key": key,
                "url": url,
                "expires_in": expiration,
                "method": method.upper()
            }
            
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise Exception(f"Presigned URL generation failed: {str(e)}")
    
    def list_files(
        self,
        prefix: Optional[str] = None,
        max_results: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        List files in the R2 bucket
        
        Args:
            prefix: Optional prefix to filter results (e.g., "user_123/")
            max_results: Maximum number of results to return
        
        Returns:
            List of file details:
            [
                {
                    "key": str,          # File key
                    "size": int,         # File size in bytes
                    "last_modified": datetime,  # Last modification time
                    "url": str           # R2 URL
                },
                ...
            ]
        """
        try:
            params = {
                'Bucket': self.bucket_name,
                'MaxKeys': max_results
            }
            
            if prefix:
                params['Prefix'] = prefix
            
            response = self.s3_client.list_objects_v2(**params)
            
            files = []
            for obj in response.get('Contents', []):
                files.append({
                    "key": obj['Key'],
                    "size": obj['Size'],
                    "last_modified": obj['LastModified'],
                    "url": f"r2://{self.bucket_name}/{obj['Key']}"
                })
            
            logger.info(f"Listed {len(files)} files from R2 (prefix: {prefix or 'none'})")
            
            return files
            
        except ClientError as e:
            logger.error(f"Failed to list R2 files: {e}")
            raise Exception(f"R2 list failed: {str(e)}")
    
    def file_exists(self, key: str) -> bool:
        """
        Check if a file exists in R2
        
        Args:
            key: The key (path) to check
        
        Returns:
            True if file exists, False otherwise
        """
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=key
            )
            return True
        except ClientError:
            return False


# Convenience functions for quick operations

def upload_file(
    key: str,
    file_path: Optional[str] = None,
    file_data: Optional[bytes] = None,
    account_id: Optional[str] = None,
    access_key_id: Optional[str] = None,
    secret_access_key: Optional[str] = None,
    bucket_name: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Quick upload function using environment variables or provided credentials
    
    See R2Client.upload() for full documentation.
    """
    # Get credentials from environment if not provided
    account_id = account_id or os.getenv('R2_ACCOUNT_ID')
    access_key_id = access_key_id or os.getenv('R2_ACCESS_KEY_ID')
    secret_access_key = secret_access_key or os.getenv('R2_SECRET_ACCESS_KEY')
    bucket_name = bucket_name or os.getenv('R2_BUCKET_NAME')
    
    client = R2Client(account_id, access_key_id, secret_access_key, bucket_name)
    return client.upload(key, file_path, file_data, **kwargs)


def download_file(
    key: str,
    local_path: Optional[str] = None,
    account_id: Optional[str] = None,
    access_key_id: Optional[str] = None,
    secret_access_key: Optional[str] = None,
    bucket_name: Optional[str] = None
) -> Union[bytes, Dict[str, Any]]:
    """
    Quick download function using environment variables or provided credentials
    
    See R2Client.download() for full documentation.
    """
    account_id = account_id or os.getenv('R2_ACCOUNT_ID')
    access_key_id = access_key_id or os.getenv('R2_ACCESS_KEY_ID')
    secret_access_key = secret_access_key or os.getenv('R2_SECRET_ACCESS_KEY')
    bucket_name = bucket_name or os.getenv('R2_BUCKET_NAME')
    
    client = R2Client(account_id, access_key_id, secret_access_key, bucket_name)
    return client.download(key, local_path)


def delete_file(
    key: str,
    account_id: Optional[str] = None,
    access_key_id: Optional[str] = None,
    secret_access_key: Optional[str] = None,
    bucket_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Quick delete function using environment variables or provided credentials
    
    See R2Client.delete() for full documentation.
    """
    account_id = account_id or os.getenv('R2_ACCOUNT_ID')
    access_key_id = access_key_id or os.getenv('R2_ACCESS_KEY_ID')
    secret_access_key = secret_access_key or os.getenv('R2_SECRET_ACCESS_KEY')
    bucket_name = bucket_name or os.getenv('R2_BUCKET_NAME')
    
    client = R2Client(account_id, access_key_id, secret_access_key, bucket_name)
    return client.delete(key)


def generate_presigned_url(
    key: str,
    expiration: int = 3600,
    method: str = "get",
    account_id: Optional[str] = None,
    access_key_id: Optional[str] = None,
    secret_access_key: Optional[str] = None,
    bucket_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Quick presigned URL function using environment variables or provided credentials
    
    See R2Client.generate_presigned_url() for full documentation.
    """
    account_id = account_id or os.getenv('R2_ACCOUNT_ID')
    access_key_id = access_key_id or os.getenv('R2_ACCESS_KEY_ID')
    secret_access_key = secret_access_key or os.getenv('R2_SECRET_ACCESS_KEY')
    bucket_name = bucket_name or os.getenv('R2_BUCKET_NAME')
    
    client = R2Client(account_id, access_key_id, secret_access_key, bucket_name)
    return client.generate_presigned_url(key, expiration, method)


def list_files(
    prefix: Optional[str] = None,
    max_results: int = 1000,
    account_id: Optional[str] = None,
    access_key_id: Optional[str] = None,
    secret_access_key: Optional[str] = None,
    bucket_name: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Quick list files function using environment variables or provided credentials
    
    See R2Client.list_files() for full documentation.
    """
    account_id = account_id or os.getenv('R2_ACCOUNT_ID')
    access_key_id = access_key_id or os.getenv('R2_ACCESS_KEY_ID')
    secret_access_key = secret_access_key or os.getenv('R2_SECRET_ACCESS_KEY')
    bucket_name = bucket_name or os.getenv('R2_BUCKET_NAME')
    
    client = R2Client(account_id, access_key_id, secret_access_key, bucket_name)
    return client.list_files(prefix, max_results)
