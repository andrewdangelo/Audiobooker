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
    preset: Optional[str] = "chat-knowledge"
    deployment_name: Optional[str] = None

class ChatRequest(AIRequest):
    prompt_messages: List[List[str]] = [
                                        ["system", "You are a literary analysis assistant.\nUsing what you know about the requested book, list every named character from it.\n\nSTRICT RULES:\n1. Canonical name must be the character's REAL full name — no nicknames embedded in it.\n   CORRECT: 'Dallas Winston'   WRONG: 'Dally Winston' or \"Dallas 'Dally' Winston\"\n2. aliases MUST include the most common short name used in dialogue — required, not optional.\ne.g. 'Ponyboy Curtis' → aliases must include 'Ponyboy'\ne.g. 'Dallas Winston' → aliases must include 'Dally'\ne.g. 'Sodapop Curtis' → aliases must include 'Soda'\n3. aliases must ONLY be real nicknames or shortened names — never another character's name.\n4. NEVER truncate names (e.g. 'Ponyc' is NOT valid).\n5. NEVER use non-English characters in names or aliases.\n6. NEVER include a name as an alias if it belongs to a different character.\n7. If unsure about an alias, OMIT it.\n\nReturn ONLY valid JSON — no markdown, no preamble.\n\n{\"characters\": [{\"name\": \"clean full real name — no embedded nicknames\", \"aliases\": [\"most common short name\", \"other nickname\"], \"gender\": \"male|female|unknown\", \"description\": \"One sentence with the age group, physical and mental character traits in universal terms (focus), and relevance to and role in the story\"}]}"],
                                        ["user", "Give me the complete character list from the novel Harry Potter and the Sorcerer's Stone. Please return it in json format. Limit your response to 4000 tokens and there may be NO incomplete characters. ONLY RETURN VALID JSON"]
                                    ]    # [[role, content], ...]
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