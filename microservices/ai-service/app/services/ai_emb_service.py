from typing import List, Union, Optional
from langchain_community.embeddings import HuggingFaceInstructEmbeddings
from app.services.ai_model_factory import ModelFactory, ModelProvider, ModelTask
from app.services.ai_hf_clients import HFEmbeddingClient 

class AIEmbeddingService:
    """
    Generate embeddings with AI
    """

    _model_cache = {}

    @classmethod
    async def _get_embedding_model(cls, provider, deployment_name):
        cache_key = f"{provider}_{deployment_name}"
        if cache_key not in cls._model_cache:
            # ONLY if we don't have it, we create it
            # This is where the HF identity check happens
            print(f"🚀 Initializing LLM for {deployment_name}...")
            cls._model_cache[cache_key] = await ModelFactory.get_model(
                model_task=ModelTask.EMB,
                provider=provider,
                deployment_name=deployment_name
            )
        
        return cls._model_cache[cache_key]

    @classmethod
    async def generate_embedding(cls, text: str, provider=ModelProvider.HF, deployment_name: Optional[str] = "e5-small-v2-yec") -> List[float]:
        """Generates embedding vector for a single string"""
        model = await cls._get_embedding_model(provider=provider, deployment_name=deployment_name)
        
        return await model.generate_embedding(text)