"""
AISpeechService — TTS generation recipes.

Design rules (mirrors AITextService):
- Model cache lives here, keyed by provider+deployment_name.
- generate_speech() takes voice_id (looked up from R2 externally),
  raw voice bytes, the quote, emotion string, and emotion strength.
- The service only drives the model — R2 fetching/uploading is the
  caller's responsibility (keeps the service single-responsibility).
"""

from typing import Optional
from app.services.ai_model_factory import ModelFactory, ModelProvider, ModelTask
from app.services.ai_hf_clients import HFTTSClient


class AISpeechService:

    _model_cache: dict[str, HFTTSClient] = {}

    # ------------------------------------------------------------------
    # Cache helper
    # ------------------------------------------------------------------

    @classmethod
    async def _get_tts_client(
        cls,
        provider: ModelProvider = ModelProvider.HF,
        deployment_name: Optional[str] = None,
    ) -> HFTTSClient:
        """Return a cached HFTTSClient, initialising it on first use."""
        cache_key = f"{provider.value}_{deployment_name}"
        if cache_key not in cls._model_cache:
            print(f"🚀 Initialising TTS client for {deployment_name}...")
            cls._model_cache[cache_key] = await ModelFactory.get_model(
                model_task=ModelTask.TTS,
                provider=provider,
                deployment_name=deployment_name,
            )
        return cls._model_cache[cache_key]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @classmethod
    async def generate_speech(
        cls,
        voice_sample_bytes: bytes,
        quote: str,
        emotion: str = "narrative, calm",
        emotion_strength: float = 0.5,
        provider: ModelProvider = ModelProvider.HF,
        deployment_name: str = "indextts2-dix",
    ) -> bytes:
        """
        Generate speech for a single quote.

        Args:
            voice_sample_bytes: Raw WAV bytes of the reference voice clip
                                (fetched from R2 by the caller using voice_id).
            quote:              The line of text to synthesise.
            emotion:            IndexTTS2-compatible emotion description string.
                                Defaults to "narrative, calm".
            emotion_strength:   0.0–1.0 float controlling emotion intensity.
                                Defaults to 0.5 (baseline).
            provider:           Model provider — always HF for TTS.
            deployment_name:    HF endpoint name.

        Returns:
            Raw WAV bytes of the generated audio.
        """
        client = await cls._get_tts_client(provider=provider, deployment_name=deployment_name)
        return await client.generate_audio(
            voice_sample_bytes=voice_sample_bytes,
            text=quote,
            emotion=emotion,
            emotion_strength=emotion_strength,
        )