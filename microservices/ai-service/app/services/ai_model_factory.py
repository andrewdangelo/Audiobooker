from typing import Optional, Dict, Tuple, Any, Type, Callable
from abc import ABC, abstractmethod
from openai import AsyncOpenAI 
from huggingface_hub import list_inference_endpoints, get_inference_endpoint, InferenceTimeoutError
from app.services.ai_hf_clients import HFEmbeddingClient, HFTTSClient
from app.core.config_settings import settings
from enum import Enum
import asyncio
import httpx
import os
import json

class ModelProvider(Enum):
    OPENAI = "openai"
    HF = "huggingface"
    CF = "cloudflare"   # This is the goal for all AI model deployments

    @classmethod
    def _missing_(cls, value):
        aliases = {
            "HF": cls.HF, "hf": cls.HF,
            "CF": cls.CF, "cf": cls.CF,
        }
        return aliases.get(value)

class ModelTask(Enum):
    TXT = "txt"
    TTS = "tts"  # CUSTOM TASK
    STT = "stt"  # CUSTOM TASK
    EMB = "emb" 

    @classmethod
    def _missing_(cls, value):
        aliases = {
            "text-generation": cls.TXT, #HF
            "sentence-similarity": cls.EMB, #HF
            "custom": cls.TTS,   # HF
            "Text Generation": cls.TXT, #CF
            "Text Embeddings": cls.EMB, #CF
        }
        return aliases.get(value)

    @classmethod
    def try_parse(cls, value):
        try:
            return cls(value)
        except ValueError:
            return None



# ---------------------------------------------------------------------------
# Preset registry — provider-agnostic, loaded once from ai_defaults.json
# ---------------------------------------------------------------------------
 
class _PresetRegistry:
    """
    Wraps ai_defaults.json. Each entry can belong to any provider (cf, hf, openai).
    Exposes a dict-like .values() interface so _choose_valid_deployment works
    identically against this and against live HF endpoint lists.
 
    _Entry mirrors the HF endpoint object shape so downstream code needs no
    special-casing: .name, .task, .repository, .url, .deployment_name.
    """
 
    class _Entry:
        def __init__(self, data: dict):
            self.name: str = data["id"]                    # preset id, e.g. "chat-basic"
            self.repository: str = data["model_name"]      # underlying model name
            self.task: str = data["task"]                  # "txt" | "emb" | "tts"
            self.provider: ModelProvider = ModelProvider(data["provider"])
            self.deployment_name: str = data["deployment_name"]
            self.context_window: Any = data.get("context_window_tokens")
            self.output_tokens: Any = data.get("max_output_tokens")
            self.description: str = data.get("description", "")
 
            # Build the base URL per provider so the factory doesn't have to.
            self.url: str = _build_base_url(self.provider, data)
 
    def __init__(self, json_path: str):
        with open(json_path) as f:
            raw: list = json.load(f)
        self._entries: Dict[str, "_PresetRegistry._Entry"] = {
            item["id"]: self._Entry(item) for item in raw
        }
 
    def values(self):
        return self._entries.values()
 
    def get(self, key: str) -> Optional["_PresetRegistry._Entry"]:
        return self._entries.get(key)
 
    def values_for_provider(self, provider: ModelProvider):
        """Returns only entries matching a given provider — used by _get_deployments."""
        return [e for e in self._entries.values() if e.provider == provider]
 
    def __contains__(self, key: str):
        return key in self._entries
 
 
def _build_base_url(provider: ModelProvider, data: dict) -> str:
    """Construct the API base URL for each provider type."""
    match provider:
        case ModelProvider.CF:
            return (
                f"https://api.cloudflare.com/client/v4/accounts"
                f"/{settings.MATT_CF_ACCOUNT_ID}/ai/v1"
            )
        case ModelProvider.HF:
            # HF entries in the JSON would carry a "url" field directly
            return data.get("url", "")
        case ModelProvider.OPENAI:
            return "https://api.openai.com/v1"
        case _:
            return data.get("url", "")
 
 
# Loaded once at import time
_PRESETS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "ai_defaults.json")
_registry: Optional[_PresetRegistry] = None
 
def _get_registry() -> _PresetRegistry:
    global _registry
    if _registry is None:
        _registry = _PresetRegistry(_PRESETS_PATH)
    return _registry
 
 
def _is_dev() -> bool:
    return getattr(settings, "ENVIRONMENT", "production").lower() == "development"
 


class ModelFactory:

    @classmethod
    async def get_model(cls,
        model_task: ModelTask = ModelTask.TXT,
        provider: Optional[ModelProvider] = ModelProvider.HF,
        deployment_name: Optional[str] = None,
        model_name: Optional[str] = None,
        max_tokens: int = 4096,
        temp: float = 0.2,
        preset: Optional[str] = None,  # e.g. "chat-basic" — only active in dev mode
    ):

        # ----------------------------------------------------------------
        # TTS — always HF, short-circuit before any text/emb routing
        # ----------------------------------------------------------------
        if model_task == ModelTask.TTS:
            match provider:
                case ModelProvider.HF:
                    ep = await cls._get_deployments_and_pick(
                        provider, model_task, deployment_name, model_name
                    )
                    # HF wakeup always runs for HF endpoints
                    await cls._ensure_endpoint_is_ready(ep.name)
                    return HFTTSClient(endpoint_url=ep.url, hf_token=settings.HF_TOKEN)
                case _:
                    raise NotImplementedError(f"TTS is only supported on HF (got {provider})")

        # ----------------------------------------------------------------
        # Resolve endpoint — preset shortcut only in development
        # ----------------------------------------------------------------
        ep = await cls._resolve_endpoint(
            provider=provider,
            model_task=model_task,
            deployment_name=deployment_name,
            model_name=model_name,
            preset=preset,
        )

        # ----------------------------------------------------------------
        # Text generation — returns AsyncOpenAI, no LangChain
        # ----------------------------------------------------------------
        if model_task == ModelTask.TXT:
            match provider:
                case ModelProvider.CF:
                    return AsyncOpenAI(
                        base_url=ep.url,
                        api_key=settings.MATT_CF_AI_TOKEN,
                    ), ep.deployment_name  # caller uses: client.chat.completions.create(model=model, ...)
 
                case ModelProvider.HF:
                    return AsyncOpenAI(
                        base_url=ep.url.rstrip("/") + "/v1",
                        api_key=settings.HF_TOKEN,
                    ), ep.repository
 
                case ModelProvider.OPENAI:
                    return AsyncOpenAI(
                        api_key=settings.OPENAI_API_KEY,
                    ), ep.repository
 
        # ----------------------------------------------------------------
        # Embeddings
        # ----------------------------------------------------------------
        if model_task == ModelTask.EMB:
            match provider:
                case ModelProvider.CF:
                    return _CFEmbeddingClient(
                        base_url=ep.url,
                        api_key=settings.MATT_CF_AI_TOKEN,
                        model=ep.deployment_name,
                    )
 
                case ModelProvider.HF:
                    return HFEmbeddingClient(
                        endpoint_url=ep.url,
                        hf_token=settings.HF_TOKEN,
                    )
 
                case ModelProvider.OPENAI:
                    raise NotImplementedError("OpenAI embeddings not wired up yet")

        raise ValueError(f"Unsupported combo: {model_task} + {provider}")
    



    # ------------------------------------------------------------------
    # Endpoint resolution
    # ------------------------------------------------------------------
 
    @classmethod
    async def _resolve_endpoint(cls, provider, model_task, deployment_name, model_name, preset):
        """
        Resolution order:
          1. If dev mode AND preset is given → match by id in ai_defaults.json, return immediately.
          2. Otherwise → call _get_deployments() for the provider and run _choose_valid_deployment().
             For HF endpoints, also run _ensure_endpoint_is_ready() after picking.
        """
        # --- Dev preset shortcut ---
        if _is_dev() and preset:
            registry = _get_registry()
            entry = registry.get(preset)
            if not entry:
                raise ValueError(f"Preset '{preset}' not found in ai_defaults.json")
            if entry.provider != provider:
                raise ValueError(
                    f"Preset '{preset}' belongs to provider '{entry.provider.value}' "
                    f"but '{provider.value}' was requested"
                )
            print(f"[DEV] Using preset '{preset}' → {entry.deployment_name}")
            return entry
 
        # --- Normal path: live deployment lookup ---
        return await cls._get_deployments_and_pick(provider, model_task, deployment_name, model_name)

    @classmethod
    async def _get_deployments_and_pick(cls, provider, model_task, deployment_name, model_name):
        """
        Fetch the live deployment list for the given provider, run
        _choose_valid_deployment, and wake up HF endpoints if needed.
        """
        deployments = await cls._get_deployments(provider)
        ep = cls._choose_valid_deployment(
            deployments, model_task,
            deployment_name=deployment_name,
            model_name=model_name,
        )
 
        # HF endpoints may be scaled to zero — wake them up before returning
        if provider == ModelProvider.HF:
            await cls._ensure_endpoint_is_ready(ep.name)
 
        return ep
 
    @staticmethod
    async def _get_deployments(provider: ModelProvider):
        match provider:
            case ModelProvider.HF:
                endpoints = await asyncio.to_thread(
                    list_inference_endpoints,
                    token=settings.HF_TOKEN,
                )
                valid_statuses = {"running", "scaledToZero"}
                return {ep.name: ep for ep in endpoints if ep.status in valid_statuses}
 
            case ModelProvider.CF:
                # CF has no live deployment list API — use the registry filtered by provider
                return {e.name: e for e in _get_registry().values_for_provider(ModelProvider.CF)}
 
            case ModelProvider.OPENAI:
                raise NotImplementedError("OpenAI deployment listing not supported yet")
 
            case _:
                raise ValueError(f"Unknown provider: {provider}")


    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------
 
    @staticmethod
    def _choose_valid_deployment(deployments, task, deployment_name=None, model_name=None):
        dep_vals = deployments.values() if isinstance(deployments, dict) else deployments
        task_deps = [i for i in dep_vals if ModelTask.try_parse(i.task) == task]
 
        print(f"Available models for task '{task}': {len(task_deps)}")
        if not task_deps:
            raise ValueError(f"No valid deployments found for task={task}, model={model_name or deployment_name}")
 
        # 1. Exact deployment name match
        match = next((i for i in task_deps if i.name == deployment_name), None)
        if match:
            return match
 
        # 2. Foundational model name match
        match = next((i for i in task_deps if getattr(i, "repository", None) == model_name), None)
        if match:
            return match
 
        # 3. Default from settings
        match = next((i for i in task_deps if i.name == getattr(settings, "LLM_ENDPOINT_NAME", None)), None)
        if match:
            return match
 
        raise ValueError(f"No valid deployments found for model: {model_name or deployment_name}")
 
    @staticmethod
    async def _ensure_endpoint_is_ready(endpoint_name: str):
        endpoint = await asyncio.to_thread(
            get_inference_endpoint,
            name=endpoint_name,
            token=settings.HF_WRITE_TOKEN,
        )
        if endpoint.status in {"paused", "scaledToZero", "pending"}:
            print(f"🔄 Waking up {endpoint_name}...")
            await asyncio.to_thread(endpoint.resume)
        try:
            await asyncio.to_thread(endpoint.wait, timeout=300)
            print(f"✅ {endpoint_name} is LIVE at {endpoint.url}")
            return endpoint
        except InferenceTimeoutError:
            print(f"❌ Timed out waiting for {endpoint_name}")
            return None
 

 # ---------------------------------------------------------------------------
# _CFEmbeddingClient
# ---------------------------------------------------------------------------
# Thin async wrapper around the OpenAI-compatible /v1/embeddings endpoint.
# Used for CF (and could be reused for any OpenAI-compat provider).
# Keeps the same .embed() / .embed_batch() interface as HFEmbeddingClient.
 
class _CFEmbeddingClient:
    """
    Async embedding client for Cloudflare Workers AI.
    Uses the OpenAI-compatible /v1/embeddings endpoint.
 
    Usage:
        client = _CFEmbeddingClient(base_url=..., api_key=..., model=...)
        vector: list[float] = await client.embed("some text")
        vectors: list[list[float]] = await client.embed_batch(["a", "b"])
    """
 
    def __init__(self, base_url: str, api_key: str, model: str):
        self._client = AsyncOpenAI(base_url=base_url, api_key=api_key)
        self._model = model
 
    async def embed(self, text: str) -> list[float]:
        resp = await self._client.embeddings.create(input=text, model=self._model)
        return resp.data[0].embedding
 
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        resp = await self._client.embeddings.create(input=texts, model=self._model)
        return [item.embedding for item in resp.data]