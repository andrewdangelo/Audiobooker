from typing import List, Dict, Any, Optional, Callable
from app.services.ai_model_factory import ModelFactory, ModelProvider, ModelTask
from app.services.ai_hf_clients import HFTTSClient
import asyncio
import httpx

class AISpeechService:

    @staticmethod
    def _get_tts_model(provider: ModelProvider = ModelProvider.HF, deployment_name: Optional[str] = None):
        """Get a TTS Model from the factory"""
        return ModelFactory.get_model(
            model_task=ModelTask.TTS,
            provider=provider,
            deployment_name=deployment_name
        )

    @classmethod
    async def generate_speech(cls, voice_sample_bytes: bytes, text: str, emotion: str, emotion_strength: float, provider=ModelProvider.HF, deployment_name="indextts2-dix") -> bytes:
        """Generates speech using TTS model"""
        model = cls._get_tts_model(provider=provider, deployment_name=deployment_name)
        
        return await model.generate_audio(voice_sample_bytes, text, emotion, emotion_strength)