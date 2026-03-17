from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from fastapi.responses import FileResponse
from typing import Optional
import json
import uuid
from datetime import datetime
from app.services.ai_text_service import AITextService
from app.services.ai_emb_service import AIEmbeddingService
from app.services.ai_speech_service import AISpeechService

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Tuple, Dict, Any, Optional

from app.services.ai_model_factory import ModelProvider

# Assuming your imports and ModelProvider enum are available
# from your_app.services import AITextService
# from your_app.constants import ModelProvider

router = APIRouter()

# --- Request/Response Models ---

# Request for AI inference tasks
class AIRequest(BaseModel):
    provider: ModelProvider
    deployment_name: Optional[str] = "qwen2-5-7b-instruct-bnb-4bit-001"

class ChatRequest(AIRequest):
    prompt_messages: List[List[str]]  # e.g., [("system", "You are a bot"), ("human", "Hello")]
    inputs: Optional[Dict[str, Any]]

class RagChatRequest(ChatRequest):
    # For RAG, we might want to pass specific keys for the search query generator
    search_query_template: Optional[str]


class EmbeddingRequest(AIRequest):
    text: str

# --- Endpoints ---

@router.post("/chat")
async def basic_chat(req: ChatRequest):
    """
    Standard LLM Chat
    """
    try:
        response = await AITextService.chat(
            prompt_messages=req.prompt_messages,
            provider=req.provider,
            inputs=req.inputs,
            deployment_name=req.deployment_name
        )
        return {"answer": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat/web-rag")
async def rag_chat(req: RagChatRequest):
    """
    Chat with automated Web Context (RAG) via DuckDuckGo.
    """
    try:
        # If book_title is provided in the root of the request, 
        # ensure it's in the inputs dict for the lambda

        answer, context = await AITextService.chat_rag_web_context(
            prompt_messages=req.prompt_messages,
            search_query_template=req.search_query_template ,
            inputs=req.inputs,
            provider=req.provider,
            deployment_name=req .deployment_name
        )
        
        return {
            "answer": answer,
            "context": context
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    


@router.post("/embedding")
async def embed_text(req: EmbeddingRequest):
    """
    Generate an embedding vector from text
    """

    try:
        embedding = await AIEmbeddingService.generate_embedding(req.text, req.provider, req.deployment_name)

        return {"embedding": embedding}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))