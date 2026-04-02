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


    # @classmethod
    # async def _get_llm(cls, provider, deployment_name):
    #     cache_key = f"{provider}_{deployment_name}"
    #     if cache_key not in cls._model_cache:
    #         # ONLY if we don't have it, we create it
    #         # This is where the HF identity check happens
    #         print(f"🚀 Initializing LLM for {deployment_name}...")
    #         cls._model_cache[cache_key] = await ModelFactory.get_model(
    #             model_task=ModelTask.TXT,
    #             provider=provider,
    #             deployment_name=deployment_name
    #         )
        
    #     return cls._model_cache[cache_key]

    # @staticmethod
    # async def _get_llm(provider=ModelProvider.HF, deployment_name: Optional[str] = None):
    #     """Helper to get a standard LLM instance"""
    #     return await ModelFactory.get_model(
    #         model_task=ModelTask.TXT,
    #         provider=provider,
    #         deployment_name=deployment_name
    #     )

    # @classmethod
    # async def chat(cls, prompt_messages: List[List[str]], inputs: Dict, provider: Optional[ModelProvider] = ModelProvider.HF, deployment_name: Optional[str] = "qwen2-5-7b-instruct-bnb-4bit-001"):
        
    #     llm = await cls._get_llm(provider=provider, deployment_name=deployment_name)
        
    #     if llm is None:
    #         return {"error": "LLM_IS_NONE", "detail": "Your _get_llm method returned None. Check your HF Token and Endpoint status."}

    #     if not prompt_messages:
    #         return {"error": "MESSAGES_ARE_NONE", "detail": "prompt_messages is empty or null."}

    #     try:
    #         # Sanitize to tuples because LangChain's ChatPromptTemplate.from_messages() 
    #         # literally fails to iterate if the internal message format is off.
    #         sanitized_prompt_messages = [tuple(m) for m in prompt_messages]
    #         prompt = ChatPromptTemplate.from_messages(sanitized_prompt_messages)
            
    #         chain = prompt | llm | StrOutputParser()

    #         return await chain.ainvoke(dict(inputs))
            
    #     except Exception as e:
    #         # This will catch the EXACT line and variable name causing the iteration error
    #         import traceback
    #         return {"error": "CHAIN_CRASH", "traceback": traceback.format_exc()}


    # LLM chat Inference + RAG (Web Search)
    # @classmethod
    # async def chat_rag_web_context(cls, 
    #                 prompt_messages: List[Tuple], # Keep it simple -> accept tuple so it's not tied to langchain messages
    #                 inputs: Dict[str, Any],
    #                 search_query_template: str = "{book_title} book characters list wikipedia",  # This is just the default for 
    #                 provider: Optional[ModelProvider] = ModelProvider.HF,
    #                 deployment_name: Optional[str] = "qwen2-5-7b-instruct-bnb-4bit-001"):
    #     """
    #     LLM chat Inference + RAG (Web Search)
    #     - prompt_messages: List of messages[("system", "..."),("human", "...")]
    #     - inputs: dictionary of string values as inputs into your prompt
    #     - search_query_template: Template for web search query
    #     """

    #     # Search Sub-Chain
    #     llm = await cls._get_llm(provider=provider, deployment_name=deployment_name)
    #     search = DuckDuckGoSearchRun()
    #     search_query_template = PromptTemplate.from_template(search_query_template)

    #     sanitized_prompt_messages = [tuple(m) for m in prompt_messages]
    #     prompt = ChatPromptTemplate.from_messages(sanitized_prompt_messages)  # system and user prompts

    #     answer_generator = prompt | llm | StrOutputParser()

    #     # Main Chain
    #     chain = (
    #         # Get web context to use in the main request to LLM
    #         RunnablePassthrough.assign(
    #             web_context= lambda x: search.run(search_query_template.format(**x))
    #         )
    #         # Generate answer using web context
    #         | RunnableParallel(
    #             final_answer=answer_generator,
    #             web_context=lambda x: x["web_context"],
    #             original_input=RunnablePassthrough()
    #         )
    #     )

    #     debug_data = await chain.ainvoke(inputs)

    #     return debug_data["final_answer"], debug_data["web_context"]

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
        system_msg = (
            "You are a helpful assistant. Use the following web search results "
            "to answer the user's question. Cite source numbers where relevant.\n\n"
            f"Search results:\n{context_block}"
        )
        augmented: PromptMessages = [["system", system_msg], *prompt_messages]
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
        template: Optional[str],
    ) -> str:
        if template:
            conversation_text = "\n".join(f"{m[0]}: {m[1]}" for m in prompt_messages)
            query_prompt = template.format(conversation=conversation_text)
        else:
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
            max_tokens=32,
            temperature=0.0,
        )
        return response.choices[0].message.content.strip()
    
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
        "max_tokens": 2048,
        "temperature": 0.2,
    }
    if inputs:
        defaults.update(inputs)
    return defaults
 
 
async def _fetch_web_snippets(query: str, max_results: int = 5) -> list[dict]:
    """
    DuckDuckGo text search - returns a list of {title, body, url} dicts.
    Requires: pip install duckduckgo-search
    """
    from duckduckgo_search import AsyncDDGS
 
    results = []
    async with AsyncDDGS() as ddgs:
        async for r in ddgs.text(query, max_results=max_results):
            results.append({
                "title": r.get("title", ""),
                "body": r.get("body", ""),
                "url": r.get("href", ""),
            })
    return results