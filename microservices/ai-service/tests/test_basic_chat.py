import os
import json
import sys
import traceback
from pathlib import Path
import asyncio

root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

if root not in sys.path:
    sys.path.insert(0, root)

from app.services.ai_text_service import AITextService
from app.services.ai_model_factory import ModelProvider 
from app.routers.ai_generation import ChatRequest

script_location = Path(__file__).resolve().parent

mock_req = {
    "prompt_messages": [
        ["system", "You are a helpful assistant."],
        ["human", "Is {person} still in prison?"]
    ],
    "inputs": {
        "person": "Martin Shkreli"
    },
    "provider": "huggingface",
    "deployment_name": "qwen2-5-7b-instruct-bnb-4bit-001"
}

async def main():
    await run_smoke_test()

async def run_smoke_test():

    # Pydantic validation
    req = ChatRequest(**mock_req)

    try:
        answer = await AITextService.chat(
            prompt_messages=req.prompt_messages,
            provider=req.provider,
            inputs=req.inputs,
            deployment_name=req.deployment_name
        )

        print(answer)

    except Exception as e:
        print("\n❌ SOMETHING WENT WRONG:")
        print(f"Error Type: {type(e).__name__}")
        print(f"Details: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":

    asyncio.run(main())