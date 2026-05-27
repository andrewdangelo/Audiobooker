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
 
import json
import re
from typing import Any, AsyncIterator, Optional
from openai import AsyncOpenAI
 
from app.services.ai_model_factory import ModelFactory, ModelProvider, ModelTask, _get_registry

from app.core.config_settings import settings

from tavily import AsyncTavilyClient

PromptMessages = list[list[str]]

def _to_openai_messages(prompt_messages: PromptMessages) -> list[dict]:
    """Convert [[role, content], ...] -> [{"role": ..., "content": ...}, ...]"""
    return [{"role": m[0], "content": m[1]} for m in prompt_messages]


def _repair_json(raw: str) -> dict:
    """
    Attempt to extract valid JSON from a model response that may be wrapped
    in markdown fences or contain a preamble.
    Raises ValueError if nothing parseable is found.
    """
    # 1. Try raw first (happy path — model behaved)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # 2. Strip markdown fences: ```json ... ``` or ``` ... ```
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if fenced:
        try:
            return json.loads(fenced.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 3. Find the first { ... } or [ ... ] block in the string
    brace = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", raw)
    if brace:
        try:
            return json.loads(brace.group(1))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not extract valid JSON from model output.\n\nRaw:\n{raw}")


def _word_limit_from_preset(preset: Optional[str], ratio: float = 0.75) -> Optional[int]:
    """
    Look up max_output_tokens for a preset from ai_defaults.json and return
    a suggested word limit (ratio * max_output_tokens).
    Returns None if the preset is unknown or has no token value recorded.
    """
    if not preset:
        return None
    entry = _get_registry().get(preset)
    if entry is None or entry.output_tokens is None:
        return None
    return int(entry.output_tokens * ratio)


def _inject_word_limit(prompt_messages: PromptMessages, word_limit: int) -> PromptMessages:
    """
    Append a word-limit instruction to the existing system message, or
    prepend a new system message if none exists.
    Does NOT mutate the original list.
    """
    instruction = f"Limit your response to {word_limit} words."
    messages = [list(m) for m in prompt_messages]  # shallow copy each pair

    if messages and messages[0][0] == "system":
        messages[0][1] = messages[0][1].rstrip() + f"\n{instruction}"
    else:
        messages.insert(0, ["system", instruction])

    return messages


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
        On invalid JSON, attempts to repair the output before raising.
        Raises ValueError if the model returns non-repairable output.
        """
        client, model = await cls._get_client(provider, deployment_name, preset)
        params = _base_params(inputs)
        response = await client.chat.completions.create(
            model=model,
            messages=_to_openai_messages(prompt_messages),
            response_format={"type": "json_object"},
            **params,
        )
        raw = response.choices[0].message.content
        return _repair_json(raw)
 
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
        search_query_text: Optional[str] = None,
        inputs: Optional[dict[str, Any]] = None,
    ) -> tuple[str, list[dict]]:
        """
        RAG over live web results (Tavily).
        If search_query_text is provided, it is used directly as the search query.
        If None, the query is derived from the conversation via LLM.
        Injects a word limit into the system prompt when the preset has a known
        max_output_tokens value in ai_defaults.json.
        Returns (answer, context_snippets).
        """
        client, model = await cls._get_client(provider, deployment_name, preset)

        query = await cls._derive_search_query(client, model, prompt_messages, search_query_text)
        snippets = await _fetch_web_snippets(query)

        context_block = "\n\n".join(
            f"[{i+1}] {s['title']}\n{s['body']}" for i, s in enumerate(snippets)
        )

        context_prefix = (
            f"Search results:\n{context_block}\n\n"
            "Use the above to answer the user's question. Cite source numbers where relevant.\n\n"
        )

        # Inject context into messages
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

        # Inject word limit when we know the model's output capacity
        word_limit = _word_limit_from_preset(preset)
        if word_limit:
            augmented = _inject_word_limit(augmented, word_limit)
            print(f"[RAG] Word limit injected: {word_limit} words (preset={preset})")

        params = _base_params(inputs)
        response = await client.chat.completions.create(
            model=model,
            messages=_to_openai_messages(augmented),
            **params,
        )

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
        search_query_text: Optional[str],
    ) -> str:
        # If a query string was provided, use it directly — no LLM call needed
        if search_query_text:
            return search_query_text

        # Otherwise derive it from the last user message
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

        return (response.choices[0].message.content or "").strip() or last_user_msg
    
# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------
 
def _base_params(inputs: Optional[dict[str, Any]]) -> dict[str, Any]:
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