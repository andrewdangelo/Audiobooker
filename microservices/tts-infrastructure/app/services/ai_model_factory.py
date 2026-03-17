from typing import Optional, Dict, Tuple, Any, Type, Callable
from abc import ABC, abstractmethod
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.embeddings import HuggingFaceInferenceAPIEmbeddings
from langchain_cloudflare import ChatCloudflareWorkersAI, CloudflareWorkersAIEmbeddings
from huggingface_hub import list_inference_endpoints, get_inference_endpoint, InferenceTimeoutError
from app.services.ai_hf_clients import HFEmbeddingClient, HFTTSClient
from app.core.config_settings import settings
from enum import Enum
import asyncio
import httpx

class ModelProvider(Enum):
    OPENAI = "openai"
    HF = "huggingface"
    CF = "cloudflare"   # This is the goal for all AI model deployments

    @classmethod
    def _missing_(cls, value):
        aliases = {
            "HF": cls.HF,
        }
        return aliases.get(value)

class ModelTask(Enum):
    TXT = "txt"
    TTS = "tts"  # CUSTOM TASK
    STT = "stt"  # CUSTOM TASK
    EMB = "emb" # Default for hf

    @classmethod
    def _missing_(cls, value):
        aliases = {
            "sentence-similarity": cls.EMB, # HF
            "text-generation": cls.TXT, # HF
            "custom": cls.TTS   # HF
        }
        return aliases.get(value)

    @classmethod
    def try_parse(cls, value):
        try:
            return cls(value)
        except ValueError:
            return None

# TODO: Mapping of deployments fields to standardized name (currently is the HF field names)

class ModelFactory:

    @classmethod
    async def get_model(cls, model_task: ModelTask = ModelTask.TXT, provider: Optional[ModelProvider] = ModelProvider.HF, deployment_name: Optional[str] = None, model_name: Optional[str] = None, max_tokens: int = 4096, temp: float = 0.2):

        deployments = await cls._get_deployments(provider)

        ep = cls._choose_valid_deployment(deployments, model_task, deployment_name=deployment_name, model_name=model_name)

        # wait for it to warm up to avoid 503
        await cls._ensure_endpoint_is_ready(ep.name)

        if not ep:
            raise ValueError(f"Valid AI deployment not found for specified task")

        # Text - LangChain Interface
        if model_task == ModelTask.TXT:
            match provider:
                case ModelProvider.OPENAI | ModelProvider.HF:
                    return ChatOpenAI(
                        base_url=ep.url.rstrip('/') + "/v1",
                        api_key=settings.HF_TOKEN,
                        model=ep.repository,
                        max_tokens=max_tokens,
                        temperature=temp
                    )

                case ModelProvider.CF:
                    raise NotImplementedError("CF is not yet a supported text model provider")
            

        # Embeddings - return client set up for custom web request
        if model_task == ModelTask.EMB:
            match provider:
                case ModelProvider.OPENAI:
                    raise NotImplementedError("OpenAI is not yet a supported embedding model provider")
                
                case ModelProvider.HF:
                    return HFEmbeddingClient(
                        endpoint_url=ep.url,
                        hf_token=settings.HF_TOKEN
                    )
            
                case ModelProvider.CF:
                    raise NotImplementedError("CloudFlare is not yet a supported embedding model provider")

        # TTS
        if model_task == ModelTask.TTS:
            match provider:
                case ModelProvider.OPENAI:
                    raise NotImplementedError("OpenAI is not yet a supported TTS model provider")
                
                case ModelProvider.HF:
                    return HFTTSClient(
                        endpoint_url=ep.url,
                        hf_token=settings.HF_TOKEN
                    )
            
                case ModelProvider.CF:
                    raise NotImplementedError("CloudFlare is not yet a supported TTS model provider")
                    # will be populated later

        raise ValueError(f"Unsupported combo: {model_task} + {provider}")

    @staticmethod
    async def _get_deployments(provider):
        if provider == ModelProvider.HF:

            endpoints = await asyncio.to_thread(
                list_inference_endpoints, 
                token=settings.HF_TOKEN
            )

            valid_statuses = {"running", "scaledToZero"}

            # print({ep.name: ep for ep in endpoints if ep.status in valid_statuses})

            return {ep.name: ep for ep in endpoints if ep.status in valid_statuses} # default format
        
        elif provider == ModelProvider.OPENAI:
            raise NotImplementedError("OpenAI Model Deployments not supported yet")
        
        elif provider == ModelProvider.CF:
            raise NotImplementedError("CloudFlare Model Deployments not supported yet")
        
    @staticmethod
    def _choose_valid_deployment(deployments, task, deployment_name: Optional[str] = None, model_name: Optional[str] = None):
        # 1. Handle both List and Dict inputs safely
        # If it's a dict, get .values(). If it's a list, use it as is.
        dep_vals = deployments.values() if isinstance(deployments, dict) else deployments

        # If no deployments match the task, then we cant do it
        task_deps = [i for i in dep_vals if ModelTask.try_parse(i.task) == task]

        print(f"Available models for current task: {len(task_deps)}")
        if len(task_deps) == 0:
            raise ValueError(f"No valid deployments found for model: {model_name or deployment_name}")

        # 2. Requested deployment name
        match = next((i for i in task_deps if i.name == deployment_name), None)
        if match: return match

        # 3. Requested foundational model (Note: HF uses .repository, ensure it exists)
        match = next((i for i in task_deps if i.repository == model_name), None)
        if match: return match

        # 4. Default deployment name from settings
        match = next((i for i in task_deps if i.name == settings.LLM_ENDPOINT_NAME), None)
        if match: return match

        # 6. Throw error if nothing was found
        raise ValueError(f"No valid deployments found for model: {model_name or deployment_name}")
    
    @staticmethod
    async def _ensure_endpoint_is_ready(endpoint_name):
        endpoint = get_inference_endpoint(name=endpoint_name, token=settings.HF_WRITE_TOKEN)

        endpoint = await asyncio.to_thread(
            get_inference_endpoint, 
            name=endpoint_name, 
            token=settings.HF_WRITE_TOKEN
        )
        
        # If it's paused or initializing, wake it up
        if endpoint.status in ["paused", "scaledToZero", "pending"]:
            print(f"🔄 Waking up {endpoint_name}...")
            await asyncio.to_thread(endpoint.resume)
        
        try:
            await asyncio.to_thread(endpoint.wait, timeout=300)
            print(f"✅ {endpoint_name} is LIVE at {endpoint.url}")
            return endpoint
        except InferenceTimeoutError:
            print(f"❌ Timed out waiting for {endpoint_name}")
            return None