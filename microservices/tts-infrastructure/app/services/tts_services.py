import httpx
import asyncio
from typing import Optional
from pathlib import Path
import os
from abc import ABC, abstractmethod
from app.core.config_settings import settings

class TTSProvider(ABC):
    """Abstract base class for TTS providers"""
    
    @abstractmethod
    async def generate_speech(self, text: str, voice_id: str, model_id: Optional[str] = None, voice_settings: Optional[dict] = None) -> bytes:
        """Generate speech from text"""
        #TODO add more to base class in case of future needs
        pass
    
    @abstractmethod
    async def get_voices(self) -> list[dict]:
        """Get available voices"""
        #TODO add to base class in case of future needs
        pass

class ElevenLabsTTSProvider(TTSProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key 
        self.base_url = "https://api.elevenlabs.io/v1"
        
    async def generate_speech(self, text: str, voice_id: str, model_id: Optional[str] = "eleven_monolingual_v1", voice_settings: Optional[dict] = None) -> bytes:
        """Generate speech using ElevenLabs API"""
        
        url = f"{self.base_url}/text-to-speech/{voice_id}"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }
        
        payload = {
            "text": text,
            "model_id": model_id,
        }
        
        if voice_settings:
            payload["voice_settings"] = voice_settings
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.content
    
    async def get_voices(self) -> list[dict]:
        """Get available ElevenLabs voices"""
        url = f"{self.base_url}/voices"
        headers = {"xi-api-key": self.api_key}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()["voices"]

class OpenAITTSProvider(TTSProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.openai.com/v1"
        
    async def generate_speech(self, text: str, voice_id: str = "alloy", model_id: Optional[str] = "tts-1", voice_settings: Optional[dict] = None) -> bytes:
        """Generate speech using OpenAI TTS API"""
        
        url = f"{self.base_url}/audio/speech"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model_id,
            "input": text,
            "voice": voice_id,
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.content
    
    async def get_voices(self) -> list[dict]:
        """Get available OpenAI voices"""
        return [
            {"voice_id": "alloy", "name": "Alloy"},
            {"voice_id": "echo", "name": "Echo"},
            {"voice_id": "fable", "name": "Fable"},
            {"voice_id": "onyx", "name": "Onyx"},
            {"voice_id": "nova", "name": "Nova"},
            {"voice_id": "shimmer", "name": "Shimmer"}
        ]

class TTSService:
    def __init__(self, output_dir: str = "audio_output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.providers = {}
        
    def register_provider(self, name: str, provider: TTSProvider):
        """Register a TTS provider"""
        self.providers[name] = provider
        
    async def generate_audio(self, chunk_id: str, text: str, provider_name: str = "elevenlabs", voice_id: Optional[str] = None, model_id: Optional[str] = None, voice_settings: Optional[dict] = None) -> tuple[str, float]:
        """
        Generate audio for a single chunk
        Returns: (audio_path, duration_seconds)
        """
        
        provider = self.providers.get(provider_name)
        if not provider:
            raise ValueError(f"Provider '{provider_name}' not registered")
        
        # Generate audio
        audio_bytes = await provider.generate_speech(text=text, voice_id=voice_id, model_id=model_id, voice_settings=voice_settings)
        
        # Save to file
        file_path = self.output_dir / f"{chunk_id}.mp3"
        with open(file_path, "wb") as f:
            f.write(audio_bytes)
        
        # Estimate duration (rough approximation)
        # For better accuracy, use audio libraries like pydub
        duration = len(audio_bytes) / 16000  # rough estimate
        
        return str(file_path), duration
    
    async def process_batch(self, chunks: list[dict], provider_name: str = "elevenlabs", voice_id: Optional[str] = None, model_id: Optional[str] = None, voice_settings: Optional[dict] = None, max_concurrent: int = settings.TTS_MAX_CONCURRENT) -> list[dict]:
        """
        Process multiple chunks concurrently
        chunks: list of dicts with 'chunk_id' and 'text' keys
        """
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_chunk(chunk: dict):
            async with semaphore:
                try:
                    audio_path, duration = await self.generate_audio(chunk_id=chunk["chunk_id"], text=chunk["text"], provider_name=provider_name, voice_id=voice_id, model_id=model_id, voice_settings=voice_settings)
                    return {
                        "chunk_id": chunk["chunk_id"],
                        "status": "success",
                        "audio_path": audio_path,
                        "duration_seconds": duration,
                        "error": None
                    }
                except Exception as e:
                    return {
                        "chunk_id": chunk["chunk_id"],
                        "status": "failed",
                        "audio_path": None,
                        "duration_seconds": None,
                        "error": str(e)
                    }
        
        # Running all chunk processes concurrently with semaphore limit
        results = await asyncio.gather(*[process_chunk(chunk) for chunk in chunks])
        return results
    
    async def get_available_voices(self, provider_name: str = "elevenlabs") -> list[dict]:
        """Get available voices for a provider"""
        provider = self.providers.get(provider_name)
        if not provider:
            raise ValueError(f"Provider '{provider_name}' not registered")
        return await provider.get_voices()