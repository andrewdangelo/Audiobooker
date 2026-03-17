import ast
from typing import List, Dict, Any, Optional, Callable, Tuple
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableParallel
from langchain_core.output_parsers import StrOutputParser
from app.services.ai_model_factory import ModelFactory, ModelProvider, ModelTask
from langchain_community.retrievers import TavilySearchAPIRetriever
import asyncio
import httpx

class AITextService:
    """
    Generate text with LLM
    """

    _model_cache = {}  # Store the LLM here so we don't keep asking HF who we are

    @classmethod
    async def _get_llm(cls, provider, deployment_name):
        cache_key = f"{provider}_{deployment_name}"
        if cache_key not in cls._model_cache:
            # ONLY if we don't have it, we create it
            # This is where the HF identity check happens
            print(f"🚀 Initializing LLM for {deployment_name}...")
            cls._model_cache[cache_key] = await ModelFactory.get_model(
                model_task=ModelTask.TXT,
                provider=provider,
                deployment_name=deployment_name
            )
        
        return cls._model_cache[cache_key]

    # @staticmethod
    # async def _get_llm(provider=ModelProvider.HF, deployment_name: Optional[str] = None):
    #     """Helper to get a standard LLM instance"""
    #     return await ModelFactory.get_model(
    #         model_task=ModelTask.TXT,
    #         provider=provider,
    #         deployment_name=deployment_name
    #     )

    @classmethod
    async def chat(cls, prompt_messages: List[List[str]], inputs: Dict, provider: Optional[ModelProvider] = ModelProvider.HF, deployment_name: Optional[str] = "qwen2-5-7b-instruct-bnb-4bit-001"):
        
        llm = await cls._get_llm(provider=provider, deployment_name=deployment_name)
        
        if llm is None:
            return {"error": "LLM_IS_NONE", "detail": "Your _get_llm method returned None. Check your HF Token and Endpoint status."}

        if not prompt_messages:
            return {"error": "MESSAGES_ARE_NONE", "detail": "prompt_messages is empty or null."}

        try:
            # Sanitize to tuples because LangChain's ChatPromptTemplate.from_messages() 
            # literally fails to iterate if the internal message format is off.
            sanitized_prompt_messages = [tuple(m) for m in prompt_messages]
            prompt = ChatPromptTemplate.from_messages(sanitized_prompt_messages)
            
            chain = prompt | llm | StrOutputParser()

            return await chain.ainvoke(dict(inputs))
            
        except Exception as e:
            # This will catch the EXACT line and variable name causing the iteration error
            import traceback
            return {"error": "CHAIN_CRASH", "traceback": traceback.format_exc()}


    # LLM chat Inference + RAG (Web Search)
    @classmethod
    async def chat_rag_web_context(cls, 
                    prompt_messages: List[Tuple], # Keep it simple -> accept tuple so it's not tied to langchain messages
                    inputs: Dict[str, Any],
                    search_query_template: str = "{book_title} book characters list wikipedia",  # This is just the default for 
                    provider: Optional[ModelProvider] = ModelProvider.HF,
                    deployment_name: Optional[str] = "qwen2-5-7b-instruct-bnb-4bit-001"):
        """
        LLM chat Inference + RAG (Web Search)
        - prompt_messages: List of messages[("system", "..."),("human", "...")]
        - inputs: dictionary of string values as inputs into your prompt
        - search_query_template: Template for web search query
        """

        # Search Sub-Chain
        llm = await cls._get_llm(provider=provider, deployment_name=deployment_name)
        search = DuckDuckGoSearchRun()
        search_query_template = PromptTemplate.from_template(search_query_template)

        sanitized_prompt_messages = [tuple(m) for m in prompt_messages]
        prompt = ChatPromptTemplate.from_messages(sanitized_prompt_messages)  # system and user prompts

        answer_generator = prompt | llm | StrOutputParser()

        # Main Chain
        chain = (
            # Get web context to use in the main request to LLM
            RunnablePassthrough.assign(
                web_context= lambda x: search.run(search_query_template.format(**x))
            )
            # Generate answer using web context
            | RunnableParallel(
                final_answer=answer_generator,
                web_context=lambda x: x["web_context"],
                original_input=RunnablePassthrough()
            )
        )

        debug_data = await chain.ainvoke(inputs)

        return debug_data["final_answer"], debug_data["web_context"]