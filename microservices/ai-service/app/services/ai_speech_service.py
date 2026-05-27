"""
AISpeechService — TTS generation recipes.

Design rules (mirrors AITextService):
- Endpoint URL is cached (a string — never goes stale).
- On each generate_speech() call, endpoint health is checked first.
  If the endpoint is scaled down, it is resumed and waited on before inference.
- The HFTTSClient is cheap to construct (just a URL + token) so it is
  created fresh per call — no client object cache that can go stale across
  process restarts or endpoint state changes.
- generate_speech() takes raw voice bytes, the quote, emotion string, and
  emotion strength. R2 fetching/uploading is the caller's responsibility.
"""

import asyncio
from typing import Optional

from app.core.config_settings import settings
from app.services.ai_model_factory import ModelFactory, ModelProvider, ModelTask
from app.services.ai_hf_clients import HFTTSClient


class AISpeechService:

    # Cache the endpoint URL only — a string never goes stale.
    # The client object is constructed fresh each call from this URL.
    _endpoint_url_cache: dict[str, str] = {}
    _init_lock: asyncio.Lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Cache helper
    # ------------------------------------------------------------------

    @classmethod
    async def _get_tts_client(
        cls,
        provider: ModelProvider = ModelProvider.HF,
        deployment_name: Optional[str] = None,
    ) -> HFTTSClient:
        """
        Returns a ready HFTTSClient.

        Cache strategy:
        - Cache the endpoint URL (stable, never changes for a given deployment).
        - On each call, check the live endpoint status via HF API.
          If scaled down, resume and wait — then construct a fresh client.
        - If already running, construct client from cached URL immediately.

        This avoids the stale client problem: a cached client object holds
        a reference to an endpoint that may have scaled down since it was
        created. A URL + fresh client has no such issue.
        """
        cache_key = f"{provider.value}_{deployment_name}"

        # Fast path — URL already cached and endpoint assumed healthy
        # (health check is cheap: one GET to HF status API)
        async with cls._init_lock:
            if cache_key not in cls._endpoint_url_cache:
                # First time — do full initialization: find endpoint, wake if needed
                print(f"🚀 Initialising TTS endpoint for {deployment_name}...")
                ep = await ModelFactory._get_deployments_and_pick(
                    provider, ModelTask.TTS, deployment_name, None
                )
                cls._endpoint_url_cache[cache_key] = ep.url
                print(f"✅ TTS endpoint ready: {ep.url}")
            else:
                # URL cached — check live status and wake up if scaled down
                await ModelFactory._ensure_endpoint_is_ready(deployment_name)

        url = cls._endpoint_url_cache[cache_key]
        return HFTTSClient(endpoint_url=url, hf_token=settings.HF_TOKEN)

    # ------------------------------------------------------------------
    # Warmup — called explicitly before the generation loop
    # ------------------------------------------------------------------

    @classmethod
    async def warmup(
        cls,
        provider: ModelProvider = ModelProvider.HF,
        deployment_name: str = "indextts2-dix",
    ) -> None:
        """
        Pre-initialize the TTS client and ensure the HF endpoint is running
        before the generation loop starts. Blocks until ready.

        Call this once before firing concurrent chunk tasks so that no
        chunk task races on endpoint initialization.
        """
        await cls._get_tts_client(provider=provider, deployment_name=deployment_name)

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