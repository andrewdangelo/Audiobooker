# Custom clients for HF Models with custom tasks 
# TODO: Rewrite for other providers

import base64
import requests
from app.core.config_settings import settings
import httpx

# All of this stuff needs to be standardized so we can just call "generate_embedding()..."
# If you are handling multiple providers, you need a wrapper
class HFEmbeddingClient:
    """Initialize embedding client with static endpoint configuration."""
    def __init__(self, endpoint_url: str, hf_token: str):
        self.url = endpoint_url
        self.headers = {
            "Authorization": f"Bearer {hf_token}",
            "Content-Type": "application/json"
        }

    async def generate_embedding(self, text: str) -> list[float]:   # return array of floats from model -> whatever size it is
        """Generate embedding"""
        # Standardize the payload
        payload = { 
            "inputs": text.replace("\n", " ")
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(self.url, headers=self.headers, json=payload)
        
        if response.status_code != 200:
            raise RuntimeError(f"HF Endpoint Error {response.status_code}: {response.text}")
            
        resp_obj = response.json()

        return resp_obj[0]

class HFTTSClient:
    def __init__(self, endpoint_url: str, hf_token: str):
        """Initialize TTS client with static endpoint configuration."""
        self.url = endpoint_url
        self.headers = {
            "Authorization": f"Bearer {hf_token}",
            "Content-Type": "application/json"
        }

    async def generate_audio(self, voice_sample_bytes: bytes, text: str, emotion: str, emotion_strength: float) -> bytes:
        """
        Calls the TTS endpoint and returns raw audio bytes
        Generate human speech based on the input voice and quote
        Inputs:
        ref_audio: bytes object of Base64-encoded audio
        Outputs:
        generated_audio: bytes object
        """
        payload = {
            "inputs": {
                "Quote": text,
                "ReferenceAudio": base64.b64encode(voice_sample_bytes),
                "EmoText": emotion,
                "EmotionAlpha": emotion_strength
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(self.url, headers=self.headers, json=payload)

        if response.status_code != 200:
            raise RuntimeError(f"TTS Error {response.status_code}: {response.text}")

        # TTS returns binary data audio/wav
        return response.content