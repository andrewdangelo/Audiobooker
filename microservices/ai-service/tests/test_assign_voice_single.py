"""
Single Voice Assignment Test
=============================
Tests both modes of assign_voice_single:

  --mode quick   (default)
      Picks a random voice from the is_standard=True shortlist.
      Fast, zero LLM calls. Primary mode for POC narrator assignment.

  --mode vector
      Requires a character profile (loaded from characters_samples/valid_characters.json).
      Runs HyDE → embed → cosine similarity against the non-standard pool
      and returns the single closest match.

Run from the project root:
    python -m tests.test_assign_voice_single              # quick mode
    python -m tests.test_assign_voice_single --mode vector
"""

import asyncio
import argparse
import json
from pathlib import Path

from tests.client_factory import get_clients
from app.services.voice_library import VoiceLibraryManager

SCRIPT_DIR = Path(__file__).resolve().parent
CHARACTERS_PATH = SCRIPT_DIR / "characters_samples" / "valid_characters.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_first_character() -> dict:
    """Load the first character from the test fixtures."""
    if not CHARACTERS_PATH.exists():
        raise FileNotFoundError(
            f"Character samples not found at {CHARACTERS_PATH}. "
            "Create tests/characters_samples/valid_characters.json first."
        )
    with open(CHARACTERS_PATH) as f:
        samples = json.load(f)

    # samples is a list of test cases, each with a "characters" list
    first_char = samples[0]["characters"][0]
    print(f"   Using character: {first_char.get('name', '<unnamed>')}")
    return first_char


async def _fetch_voice_doc(collection, voice_id: str) -> dict:
    """Fetch the voice document from Mongo for display purposes."""
    doc = await collection.find_one({"_id": voice_id}, {"embedding": 0})
    return doc or {}


# ---------------------------------------------------------------------------
# Test runners
# ---------------------------------------------------------------------------

async def test_assign_quick(collection, manager: VoiceLibraryManager):
    print("🚀 Mode: QUICK (random standard voice)\n")

    try:
        voice_id = await manager.assign_voice_single(quick=True)

        doc = await _fetch_voice_doc(collection, voice_id)
        print("✅ Assignment result:")
        print(f"   Voice ID   : {voice_id}")
        print(f"   Filename   : {doc.get('original_filename', 'N/A')}")
        print(f"   Description: {doc.get('description', 'N/A')}")
        print(f"   is_standard: {doc.get('is_standard', 'N/A')}")
        print(f"   Duration   : {doc.get('duration', 'N/A')}s")

    except ValueError as e:
        print(f"❌ Assignment failed (expected if library not seeded): {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()


async def test_assign_vector(collection, manager: VoiceLibraryManager):
    print("🚀 Mode: VECTOR (character-matched non-standard voice)\n")

    try:
        character = _load_first_character()
    except FileNotFoundError as e:
        print(f"❌ {e}")
        return

    print(f"   Character profile: {json.dumps(character, indent=2)}\n")

    try:
        voice_id = await manager.assign_voice_single(
            quick=False,
            character=character,
        )

        doc = await _fetch_voice_doc(collection, voice_id)
        print("\n✅ Assignment result:")
        print(f"   Voice ID   : {voice_id}")
        print(f"   Filename   : {doc.get('original_filename', 'N/A')}")
        print(f"   Description: {doc.get('description', 'N/A')}")
        print(f"   is_standard: {doc.get('is_standard', 'N/A')}")
        print(f"   Duration   : {doc.get('duration', 'N/A')}s")

    except ValueError as e:
        print(f"❌ Assignment failed (expected if library not seeded): {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main(mode: str):
    collection, r2_session, r2_config = get_clients()
    manager = VoiceLibraryManager(collection, r2_session, r2_config)

    print("=" * 50)
    print("  Single Voice Assignment Test")
    print("=" * 50 + "\n")

    if mode == "quick":
        await test_assign_quick(collection, manager)
    elif mode == "vector":
        await test_assign_vector(collection, manager)
    else:
        print(f"❌ Unknown mode '{mode}'. Use --mode quick or --mode vector.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Single voice assignment test")
    parser.add_argument(
        "--mode",
        choices=["quick", "vector"],
        default="quick",
        help="quick = random standard pick | vector = character-matched non-standard pick",
    )
    args = parser.parse_args()
    asyncio.run(main(args.mode))