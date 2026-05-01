# Custom clients for HF Models with custom tasks 
# TODO: Rewrite for other providers

import asyncio
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

    async def generate_audio(
        self,
        voice_sample_bytes: bytes,
        text: str,
        emotion: str,
        emotion_strength: float,
        max_retries: int = 5,
        retry_delay: float = 30.0,
    ) -> bytes:
        """
        Calls the TTS endpoint and returns raw audio bytes.
        Retries on 503 (endpoint cold / initializing) with a fixed wait between attempts.

        Args:
            voice_sample_bytes: Raw WAV bytes of the reference voice clip.
            text:               Text to synthesise.
            emotion:            Emotion description string.
            emotion_strength:   0.0–1.0 float.
            max_retries:        How many times to retry on 503 before giving up.
            retry_delay:        Seconds to wait between retries (HF cold start ~60-120s).
        """
        payload = {
            "inputs": {
                "Quote": text,
                "ReferenceAudio": base64.b64encode(voice_sample_bytes).decode(),
                "EmoText": emotion,
                "EmotionAlpha": emotion_strength
            }
        }

        last_error = None

        for attempt in range(1, max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=300.0) as client:
                    response = await client.post(self.url, headers=self.headers, json=payload)
                    
                    # temporary debug — add after the status check, before return
                    # print(f"Response Content-Type: {response.headers.get('content-type')}")
                    # print(f"First 100 bytes: {response.content[:100]}")

                if response.status_code == 503:
                    print(
                        f"   HF endpoint cold/initializing (503) — "
                        f"attempt {attempt}/{max_retries}, "
                        f"waiting {retry_delay}s..."
                    )
                    last_error = RuntimeError(f"TTS endpoint returned 503 after {attempt} attempt(s)")
                    await asyncio.sleep(retry_delay)
                    continue

                if response.status_code != 200:
                    raise RuntimeError(f"TTS Error {response.status_code}: {response.text}")

                # return response.content   X WRONG
                return base64.b64decode(response.json()["generated_audio"])
                
            except httpx.ReadTimeout:
                print(
                    f"   HF endpoint timed out — "
                    f"attempt {attempt}/{max_retries}, "
                    f"waiting {retry_delay}s..."
                )
                last_error = RuntimeError(f"TTS endpoint timed out after {attempt} attempt(s)")
                await asyncio.sleep(retry_delay)
                continue

        raise last_error