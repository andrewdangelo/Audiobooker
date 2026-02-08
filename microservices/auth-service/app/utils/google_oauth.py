"""
Google OAuth Utilities
"""

from typing import Optional, Dict, Any
import httpx
from google.auth.transport.requests import Request
from google.oauth2 import id_token
from app.core.config_settings import settings
import logging

logger = logging.getLogger(__name__)


class GoogleOAuthManager:
    """Manager for Google OAuth operations"""
    
    def __init__(self):
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET
        self.redirect_uri = settings.GOOGLE_REDIRECT_URI
    
    def get_authorization_url(self, state: str) -> str:
        """Generate Google OAuth authorization URL"""
        auth_url = (
            f"https://accounts.google.com/o/oauth2/v2/auth?"
            f"client_id={self.client_id}&"
            f"redirect_uri={self.redirect_uri}&"
            f"response_type=code&"
            f"scope=openid%20email%20profile&"
            f"state={state}"
        )
        return auth_url
    
    async def exchange_code_for_token(self, code: str) -> Optional[Dict[str, Any]]:
        """Exchange authorization code for access token"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "code": code,
                        "grant_type": "authorization_code",
                        "redirect_uri": self.redirect_uri,
                    }
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"Failed to exchange code for token: {str(e)}")
                return None
    
    async def get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """Get user information from Google using access token"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    "https://www.googleapis.com/oauth2/v1/userinfo",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"Failed to get user info: {str(e)}")
                return None
    
    def verify_id_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify Google ID token"""
        try:
            payload = id_token.verify_oauth2_token(
                token,
                Request(),
                self.client_id
            )
            return payload
        except Exception as e:
            logger.error(f"Failed to verify ID token: {str(e)}")
            return None


google_oauth_manager = GoogleOAuthManager()
