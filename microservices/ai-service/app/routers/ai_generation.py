from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
 
from app.services.ai_model_factory import ModelProvider
from app.services.ai_text_service import AITextService
from app.services.ai_emb_service import AIEmbeddingService

router = APIRouter()

# Request for AI inference tasks
class AIRequest(BaseModel):
    provider: ModelProvider = ModelProvider.CF
    # preset (e.g. "chat-basic") only active in development mode — maps to ai_defaults.json id.
    # In production, use deployment_name or model_name for live lookup.
    preset: Optional[str] = None
    deployment_name: Optional[str] = None

class ChatRequest(AIRequest):
    prompt_messages: List[List[str]]    # [[role, content], ...]
    inputs: Optional[Dict[str, Any]] = None # optional overrides: temperature, max_tokens, etc.

class RagChatRequest(ChatRequest):
    search_query_template: Optional[str] = None

class EmbeddingRequest(AIRequest):
    text: str

# --- Endpoints ---

@router.post("/chat")
async def basic_chat(req: ChatRequest):
    """Standard LLM Chat - messages in, text out."""
    try:
        response = await AITextService.chat(
            prompt_messages=req.prompt_messages,
            provider=req.provider,
            deployment_name=req.deployment_name,
            preset=req.preset,
            inputs=req.inputs,
        )
        return {"answer": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/chat/stream")
async def stream_chat(req: ChatRequest):
    """
    Streaming chat via SSE.
    Connect with EventSource or fetch + ReadableStream on the client.
    """
    async def event_stream():
        try:
            async for chunk in AITextService.chat_stream(
                prompt_messages=req.prompt_messages,
                provider=req.provider,
                deployment_name=req.deployment_name,
                preset=req.preset,
                inputs=req.inputs,
            ):
                yield f"data: {chunk}\n\n"
        except Exception as e:
            yield f"data: [ERROR] {str(e)}\n\n"
 
    return StreamingResponse(event_stream(), media_type="text/event-stream")

@router.post("/chat/web-rag")
async def rag_chat(req: RagChatRequest):
    """
    Chat with automated Web Context (RAG) via DuckDuckGo.
    """
    try:
        answer, context = await AITextService.chat_rag_web_context(
            prompt_messages=req.prompt_messages,
            provider=req.provider,
            deployment_name=req.deployment_name,
            preset=req.preset,
            search_query_template=req.search_query_template,
            inputs=req.inputs,
        )
        
        return {"answer": answer, "context": context}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.post("/embedding")
async def embed_text(req: EmbeddingRequest):
    """Generate an embedding vector from text."""
    try:
        embedding = await AIEmbeddingService.generate_embedding(
            req.text,
            req.provider,
            req.deployment_name,
            preset=req.preset,
        )

        return {"embedding": embedding}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))