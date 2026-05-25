"""script_to_tts_batches adapter."""

from app.services.pipeline_client import script_to_tts_batches


def test_script_to_tts_batches_builds_chapter_payloads():
    script = {
        "chapters": [
            {
                "chapter_id": 1,
                "title": "One",
                "segments": [
                    {"speaker": "Narrator", "text": "Opening."},
                    {"speaker": "Hero", "text": "Hello."},
                ],
            }
        ]
    }
    voice_map = {"Narrator": "voice-n", "Hero": "voice-h"}
    batches = script_to_tts_batches(script, voice_map)
    assert len(batches) == 1
    assert batches[0]["chapter_id"] == 1
    assert batches[0]["chapter_title"] == "One"
    chunks = batches[0]["chunks"]
    assert len(chunks) == 2
    assert chunks[0]["voice_id"] == "voice-n"
    assert chunks[1]["voice_id"] == "voice-h"
