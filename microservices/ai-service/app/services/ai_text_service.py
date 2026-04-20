"""
AITextService — recipes for text generation.
 
Design rules:
- No LangChain. openai.AsyncOpenAI drives everything.
- The factory returns an AsyncOpenAI client. This service calls it.
- Each public method is a self-contained "recipe" with a clear input/output contract.
- Streaming is opt-in per recipe.
- Model cache lives here (keyed by provider+deployment), not in the factory.
"""
 
from __future__ import annotations
 
from typing import Any, AsyncIterator, Optional
from openai import AsyncOpenAI
 
from app.services.ai_model_factory import ModelFactory, ModelProvider, ModelTask

from app.core.config_settings import settings

from tavily import AsyncTavilyClient

PromptMessages = list[list[str]]

def _to_openai_messages(prompt_messages: PromptMessages) -> list[dict]:
    """Convert [[role, content], ...] -> [{"role": ..., "content": ...}, ...]"""
    return [{"role": m[0], "content": m[1]} for m in prompt_messages]



class AITextService:
    """
    Generate text with LLM
    """

    _model_cache: dict[str, tuple[AsyncOpenAI, str]] = {}

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------
 
    @classmethod
    async def _get_client(
        cls,
        provider: ModelProvider,
        deployment_name: Optional[str] = None,
        preset: Optional[str] = None,
    ) -> tuple[AsyncOpenAI, str]:
        """Returns (AsyncOpenAI client, model_name_string)."""
        cache_key = preset or f"{provider.value}_{deployment_name}"
        if cache_key not in cls._model_cache:
            print(f"Initializing client for {cache_key}...")
            # get_model returns (AsyncOpenAI, model_name) for TXT tasks
            cls._model_cache[cache_key] = await ModelFactory.get_model(
                model_task=ModelTask.TXT,
                provider=provider,
                deployment_name=deployment_name,
                preset=preset,
            )
        return cls._model_cache[cache_key]


    # ------------------------------------------------------------------
    # Recipe 1 - plain chat (single response)
    # ------------------------------------------------------------------
 
    @classmethod
    async def chat(
        cls,
        prompt_messages: PromptMessages,
        provider: ModelProvider = ModelProvider.CF,
        deployment_name: Optional[str] = None,
        preset: Optional[str] = None,
        inputs: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Simplest recipe: messages in, assistant text out.
        inputs: optional overrides (temperature, max_tokens, top_p, etc.)
        """
        client, model = await cls._get_client(provider, deployment_name, preset)
        params = _base_params(inputs)
        response = await client.chat.completions.create(
            model=model,
            messages=_to_openai_messages(prompt_messages),
            **params,
        )
        return response.choices[0].message.content
 
    # ------------------------------------------------------------------
    # Recipe 2 - streaming chat
    # ------------------------------------------------------------------
 
    @classmethod
    async def chat_stream(
        cls,
        prompt_messages: PromptMessages,
        provider: ModelProvider = ModelProvider.CF,
        deployment_name: Optional[str] = None,
        preset: Optional[str] = None,
        inputs: Optional[dict[str, Any]] = None,
    ) -> AsyncIterator[str]:
        """
        Yields text chunks as they arrive — wire into a FastAPI SSE endpoint:
            async for chunk in AITextService.chat_stream(...):
                yield f"data: {chunk}\\n\\n"
        """
        client, model = await cls._get_client(provider, deployment_name, preset)
        params = _base_params(inputs)
        stream = await client.chat.completions.create(
            model=model,
            messages=_to_openai_messages(prompt_messages),
            stream=True,
            **params,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
 
    # ------------------------------------------------------------------
    # Recipe 3 - system + user shorthand
    # ------------------------------------------------------------------
 
    @classmethod
    async def chat_with_system(
        cls,
        system: str,
        user: str,
        provider: ModelProvider = ModelProvider.CF,
        deployment_name: Optional[str] = None,
        preset: Optional[str] = None,
        inputs: Optional[dict[str, Any]] = None,
    ) -> str:
        """Convenience wrapper for the common [system, user] -> answer pattern."""
        messages: PromptMessages = [["system", system], ["user", user]]
        return await cls.chat(messages, provider, deployment_name, preset, inputs)
 
    # ------------------------------------------------------------------
    # Recipe 4 - structured / JSON output
    # ------------------------------------------------------------------
 
    @classmethod
    async def chat_json(
        cls,
        prompt_messages: PromptMessages,
        provider: ModelProvider = ModelProvider.CF,
        deployment_name: Optional[str] = None,
        preset: Optional[str] = None,
        inputs: Optional[dict[str, Any]] = None,
    ) -> dict:
        """
        Forces json_object response mode and returns a parsed dict.
        Prompt must instruct the model to respond in JSON.
        Raises ValueError if the model returns non-JSON.
        """
        import json
 
        client, model = await cls._get_client(provider, deployment_name, preset)
        params = _base_params(inputs)
        response = await client.chat.completions.create(
            model=model,
            messages=_to_openai_messages(prompt_messages),
            response_format={"type": "json_object"},
            **params,
        )
        raw = response.choices[0].message.content
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"Model did not return valid JSON: {e}\n\nRaw:\n{raw}")
 
    # ------------------------------------------------------------------
    # Recipe 5 - web RAG chat
    # ------------------------------------------------------------------
 
    @classmethod
    async def chat_rag_web_context(
        cls,
        prompt_messages: PromptMessages,
        provider: ModelProvider = ModelProvider.CF,
        deployment_name: Optional[str] = None,
        preset: Optional[str] = None,
        search_query_template: Optional[str] = None,
        inputs: Optional[dict[str, Any]] = None,
    ) -> tuple[str, list[dict]]:
        """
        RAG over live web results (DuckDuckGo).
        Flow: derive query -> fetch snippets -> inject as system context -> answer.
        Returns (answer, context_snippets).
        """
        client, model = await cls._get_client(provider, deployment_name, preset)
 
        query = await cls._derive_search_query(client, model, prompt_messages, search_query_template)
        snippets = await _fetch_web_snippets(query)
 
        context_block = "\n\n".join(
            f"[{i+1}] {s['title']}\n{s['body']}" for i, s in enumerate(snippets)
        )

        # print(f"CONTEXT BLOCK: {context_block}")

        context_prefix = (
            f"Search results:\n{context_block}\n\n"
            "Use the above to answer the user's question. Cite source numbers where relevant.\n\n"
        )

        # Inject into existing system message if present, otherwise prepend one
        if prompt_messages[0][0] == "system":
            augmented = [
                ["system", context_prefix + prompt_messages[0][1]],
                *prompt_messages[1:]
            ]
        else:
            augmented = [
                ["system", context_prefix],
                *prompt_messages
            ]


        params = _base_params(inputs)
 
        response = await client.chat.completions.create(
            model=model,
            messages=_to_openai_messages(augmented),
            **params,
        )

        # print("CHAT COMPLETION RESPONSE\n" + response.model_dump_json(indent=2))
        return response.choices[0].message.content, snippets
    
    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
 
    @classmethod
    async def _derive_search_query(
        cls,
        client: AsyncOpenAI,
        model: str,
        prompt_messages: PromptMessages,
        template: Optional[str],
    ) -> str:
        # If template provided, use it directly — no model call needed
        if template:
            return template.format(
                conversation="\n".join(f"{m[0]}: {m[1]}" for m in prompt_messages)
            )

        last_user_msg = next(
            (m[1] for m in reversed(prompt_messages) if m[0] == "user"), ""
        )
        query_prompt = (
            "Convert the following user message into a short web search query "
            f"(max 10 words, no quotes, no explanation):\n\n{last_user_msg}"
        )
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": query_prompt}],
            max_tokens=64,
            temperature=0.0,
        )

        # print("SEARCH QUERY RESPONSE\n" + response.model_dump_json(indent=2))

        return (response.choices[0].message.content or "").strip() or last_user_msg
    
# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------
 
def _base_params(inputs: Optional[dict[str, Any]]) -> dict[str, Any]:
    """
    Build the base completion params dict.
    Callers can override temperature, max_tokens etc. via inputs.
    Sensible defaults so every recipe behaves consistently without
    requiring callers to pass boilerplate.
    """
    defaults: dict[str, Any] = {
        "max_tokens": 8192,
        "temperature": 0.2,
    }
    if inputs:
        defaults.update(inputs)
    return defaults
 
 
async def _fetch_web_snippets(query: str, max_results: int = 5) -> list[dict]:
    client = AsyncTavilyClient(api_key=settings.TAVILY_API_KEY)
    response = await client.search(query=query, max_results=max_results, include_raw_content=False)
    return [{"title": r["title"], "body": r["content"], "url": r["url"]} for r in response["results"]]