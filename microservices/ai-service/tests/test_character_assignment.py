import asyncio
import json
from tests.client_factory import get_clients
from app.services.voice_library import VoiceLibraryManager
from pathlib import Path

script_location = Path(__file__).resolve().parent

test_cases_path = script_location / "characters_samples" / "valid_characters.json"
with open(test_cases_path, 'r') as f:
    samples = json.load(f)

async def test_character_assignment(characters):
    collection, r2_session, r2_config = get_clients()
    manager = VoiceLibraryManager(collection, r2_session, r2_config)

    print(f"🚀 Starting Multiple Character Assignment Test for {len(characters)} characters...")

    try:
        # Summary -> Embedding -> Big Matrix Similarity -> Hungarian Algorithm -> LLM Veto Loop
        assignments = await manager.assign_voice_multiple(characters)

        print("\n✨ FINAL CASTING RESULTS:")
        print("==========================")
        for char_name, voice_id in assignments.items():
            voice_doc = await collection.find_one({"_id": voice_id})
            desc = voice_doc.get("description", "No description found") if voice_doc else "N/A"
            
            print(f"👤 Character: {char_name}")
            print(f"🎙️ Voice ID:  {voice_id}")
            print(f"📝 Voice Vibe: {desc}")
            print("-" * 30)

    except Exception as e:
        print(f"❌ Assignment Test Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    for s in samples:
        asyncio.run(test_character_assignment(s["characters"]))