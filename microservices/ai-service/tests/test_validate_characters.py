import os
import json
import sys
import traceback
from pathlib import Path
import asyncio

root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

if root not in sys.path:
    sys.path.insert(0, root)

from app.services.pdf_utils_service import PDFUtilsService

script_location = Path(__file__).resolve().parent

test_cases_path = script_location / "characters_samples" / "wrong_characters.json"
with open(test_cases_path, 'r') as f:
    samples = json.load(f)

async def main():
    # Now that we are inside an 'async def', we can use await!
    for s in samples:
        print(f"🧪 Testing: {s['book']}")
        await run_smoke_test(s["book"], s["characters"])

async def run_smoke_test(book_title, chars):
    try:
        corrected_list, web_context = await PDFUtilsService.validate_characters(
            characters_list=chars,
            book_title=book_title
        )

        print("\n✅ CORRECTED LIST:")
        print("-" * 50)
        print(json.dumps(corrected_list, indent=2))

        print("\n✅ WEB CONTEXT:")
        print("-" * 50)
        print(web_context[:800])

    except Exception as e:
        print("\n❌ SOMETHING WENT WRONG:")
        print(f"Error Type: {type(e).__name__}")
        print(f"Details: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":

    asyncio.run(main())