from openai import AsyncOpenAI
import httpx
import json
from typing import List, Dict

class HuggingFaceService:
    def __init__(
        self,
        token: str,
        emb_url: str,     # intfloat-e5-small-v2
        llm_base_url: str,    # unsloth/Qwen2.5-7B-Instruct-bnb-4bit
        llm_model: str   # unsloth Qwen 
    ):
        self.token = token
        self.emb_url = emb_url

        self.llm_client = AsyncOpenAI(
            base_url=llm_base_url, # e.g., https://[endpoint-url]/v1
            api_key=token
        )
        self.llm_model = llm_model
        self.headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    async def get_embedding(self, text: str) -> List[float]:
        """Calls HF Inference Endpoint for text embeddings."""

        text_to_embed = text.replace("\n", " ")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.emb_url,
                headers=self.headers,
                json={"inputs": f"{text_to_embed}"}
            )
            response.raise_for_status()
            result = response.json()
            # Handle nested list if endpoint returns [[...]]
            return result[0] if isinstance(result[0], list) else result

    async def chat_completion(self, prompt_messages: List[Dict], response_format_json: bool = False) -> str:
        """OpenAI-compatible call to HF LLM Endpoint"""

        response = await self.llm_client.chat.completions.create(
            model=self.llm_model,
            messages=prompt_messages, 
            temperature=0.1,
            max_tokens=4096,
            top_p=0.9,
            frequency_penalty=1.05
        )
        return response.choices[0].message.content