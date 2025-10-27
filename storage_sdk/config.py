"""
Configuration for R2 Storage SDK

Loads R2 credentials from environment variables.
"""

import os
from typing import Optional


class R2Config:
    """R2 configuration from environment variables"""
    
    def __init__(self):
        self.account_id = os.getenv('R2_ACCOUNT_ID')
        self.access_key_id = os.getenv('R2_ACCESS_KEY_ID')
        self.secret_access_key = os.getenv('R2_SECRET_ACCESS_KEY')
        self.bucket_name = os.getenv('R2_BUCKET_NAME')
        self.endpoint_url = os.getenv('R2_ENDPOINT_URL')
    
    def is_configured(self) -> bool:
        """Check if all required credentials are set"""
        return all([
            self.account_id,
            self.access_key_id,
            self.secret_access_key,
            self.bucket_name
        ])
    
    def get_endpoint_url(self) -> str:
        """Get endpoint URL, constructing from account_id if not set"""
        if self.endpoint_url:
            return self.endpoint_url
        if self.account_id:
            return f"https://{self.account_id}.r2.cloudflarestorage.com"
        raise ValueError("Either R2_ENDPOINT_URL or R2_ACCOUNT_ID must be set")
    
    def validate(self):
        """Validate configuration and raise error if incomplete"""
        if not self.is_configured():
            missing = []
            if not self.account_id:
                missing.append("R2_ACCOUNT_ID")
            if not self.access_key_id:
                missing.append("R2_ACCESS_KEY_ID")
            if not self.secret_access_key:
                missing.append("R2_SECRET_ACCESS_KEY")
            if not self.bucket_name:
                missing.append("R2_BUCKET_NAME")
            
            raise ValueError(
                f"Missing required R2 configuration: {', '.join(missing)}\n"
                "Set these environment variables in your .env file or environment."
            )


# Global config instance
config = R2Config()
