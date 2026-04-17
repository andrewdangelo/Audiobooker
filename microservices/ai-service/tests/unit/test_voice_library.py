"""
Unit Tests — VoiceLibraryManager
==================================
Tests the business logic of VoiceLibraryManager in full isolation:
  - No MongoDB calls (mock_mongo_collection fixture)
  - No R2 / S3 calls (mock_r2 fixture)
  - No LLM / embedding calls (patched at method level)
  - No audio processing (patched _clean_audio)

Each test answers ONE question about ONE behaviour.
"""

import pytest
import io
import numpy as np
from unittest.mock import AsyncMock, MagicMock, patch, call


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_manager(mock_mongo_collection, mock_r2, r2_config):
    """Build a VoiceLibraryManager with all real I/O replaced by mocks."""
    from app.services.voice_library import VoiceLibraryManager
    from app.services.ai_model_factory import ModelProvider

    r2_session, _ = mock_r2
    return VoiceLibraryManager(
        mongo_collection=mock_mongo_collection,
        r2_session=r2_session,
        r2_config=r2_config,
        text_provider=ModelProvider.CF,
        text_preset="chat-basic",
        emb_provider=ModelProvider.CF,
        emb_preset="embedding-768",
    )


def _make_voice_doc(voice_id: str, is_standard: bool = False) -> dict:
    return {
        "_id": voice_id,
        "original_filename": f"{voice_id}.wav",
        "description": "deep, calm, male, middle-aged, neutral accent",
        "embedding": [0.1] * 768,
        "duration": 12.0,
        "is_standard": is_standard,
    }


# ---------------------------------------------------------------------------
# add_voice
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestAddVoice:

    async def test_returns_a_uuid_string(
        self, mock_mongo_collection, mock_r2, r2_config
    ):
        """
        add_voice must return a non-empty string ID (UUID format).
        We don't care what exact UUID it generates — just that it returns one.
        """
        import uuid
        manager = _make_manager(mock_mongo_collection, mock_r2, r2_config)

        fake_audio = io.BytesIO(b"fake wav bytes")
        fake_buffer = io.BytesIO(b"processed wav")

        with patch.object(manager, "_clean_audio", return_value=(fake_buffer, 12.0)):
            with patch.object(manager, "_get_voice_description", new=AsyncMock(return_value="calm male")):
                with patch(
                    "app.services.voice_library.AIEmbeddingService.generate_embedding",
                    new=AsyncMock(return_value=[0.0] * 768),
                ):
                    with patch.object(manager, "_upload_to_r2", new=AsyncMock()):
                        voice_id = await manager.add_voice(
                            input_audio=fake_audio,
                            filename="test.wav",
                        )

        # Must be a valid UUID string
        parsed = uuid.UUID(voice_id)
        assert str(parsed) == voice_id

    async def test_inserts_document_into_mongo(
        self, mock_mongo_collection, mock_r2, r2_config
    ):
        """
        After processing, a document must be written to MongoDB.
        Verifies the insert was called and the document shape is correct.
        """
        manager = _make_manager(mock_mongo_collection, mock_r2, r2_config)
        fake_buffer = io.BytesIO(b"processed")

        with patch.object(manager, "_clean_audio", return_value=(fake_buffer, 10.0)):
            with patch.object(manager, "_get_voice_description", new=AsyncMock(return_value="deep male")):
                with patch(
                    "app.services.voice_library.AIEmbeddingService.generate_embedding",
                    new=AsyncMock(return_value=[0.5] * 768),
                ):
                    with patch.object(manager, "_upload_to_r2", new=AsyncMock()):
                        await manager.add_voice(
                            input_audio=io.BytesIO(b"audio"),
                            filename="voice.wav",
                            is_standard=True,
                        )

        mock_mongo_collection.insert_one.assert_called_once()
        doc = mock_mongo_collection.insert_one.call_args[0][0]

        assert doc["original_filename"] == "voice.wav"
        assert doc["is_standard"] is True
        assert doc["description"] == "deep male"
        assert len(doc["embedding"]) == 768

    async def test_uploads_to_r2_before_mongo_insert(
        self, mock_mongo_collection, mock_r2, r2_config
    ):
        """
        R2 upload should happen before Mongo insert.
        If Mongo fails after R2 upload that's a known acceptable trade-off,
        but upload must not be skipped.
        """
        manager = _make_manager(mock_mongo_collection, mock_r2, r2_config)
        call_order = []

        async def fake_upload(*a, **kw): call_order.append("r2")
        async def fake_insert(*a, **kw): call_order.append("mongo"); return MagicMock()

        mock_mongo_collection.insert_one = AsyncMock(side_effect=fake_insert)

        fake_buffer = io.BytesIO(b"data")
        with patch.object(manager, "_clean_audio", return_value=(fake_buffer, 5.0)):
            with patch.object(manager, "_get_voice_description", new=AsyncMock(return_value="x")):
                with patch("app.services.voice_library.AIEmbeddingService.generate_embedding", new=AsyncMock(return_value=[0.0] * 768)):
                    with patch.object(manager, "_upload_to_r2", side_effect=fake_upload):
                        await manager.add_voice(io.BytesIO(b"a"), "a.wav")

        assert call_order == ["r2", "mongo"]


# ---------------------------------------------------------------------------
# delete_voice_by_id
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestDeleteVoiceById:

    async def test_returns_true_when_voice_found(
        self, mock_mongo_collection, mock_r2, r2_config
    ):
        manager = _make_manager(mock_mongo_collection, mock_r2, r2_config)
        # delete_result already has deleted_count=1 from the fixture

        with patch.object(manager, "_delete_from_r2", new=AsyncMock()):
            result = await manager.delete_voice_by_id("existing-voice-id")

        assert result is True

    async def test_returns_false_when_voice_not_found(
        self, mock_mongo_collection, mock_r2, r2_config
    ):
        manager = _make_manager(mock_mongo_collection, mock_r2, r2_config)

        # Simulate Mongo finding nothing to delete
        not_found = MagicMock()
        not_found.deleted_count = 0
        mock_mongo_collection.delete_one = AsyncMock(return_value=not_found)

        result = await manager.delete_voice_by_id("nonexistent-id")
        assert result is False

    async def test_r2_failure_does_not_raise(
        self, mock_mongo_collection, mock_r2, r2_config
    ):
        """
        R2 deletion is documented as best-effort. If R2 fails, the method must
        still return True (Mongo was deleted) and must NOT raise an exception.
        """
        manager = _make_manager(mock_mongo_collection, mock_r2, r2_config)

        with patch.object(manager, "_delete_from_r2", new=AsyncMock(side_effect=RuntimeError("R2 down"))):
            result = await manager.delete_voice_by_id("some-id")

        assert result is True  # Mongo deletion succeeded

    async def test_mongo_delete_called_with_correct_id(
        self, mock_mongo_collection, mock_r2, r2_config
    ):
        manager = _make_manager(mock_mongo_collection, mock_r2, r2_config)

        with patch.object(manager, "_delete_from_r2", new=AsyncMock()):
            await manager.delete_voice_by_id("voice-abc-123")

        mock_mongo_collection.delete_one.assert_called_once_with({"_id": "voice-abc-123"})


# ---------------------------------------------------------------------------
# assign_voice_single — quick mode
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestAssignVoiceSingleQuick:

    async def test_returns_one_of_the_standard_voice_ids(
        self, mock_mongo_collection, mock_r2, r2_config
    ):
        """
        Quick mode must return a voice_id that belongs to the standard pool.
        """
        manager = _make_manager(mock_mongo_collection, mock_r2, r2_config)

        standard_voices = [{"_id": "std-1"}, {"_id": "std-2"}, {"_id": "std-3"}]
        cursor = MagicMock()
        cursor.to_list = AsyncMock(return_value=standard_voices)
        mock_mongo_collection.find = MagicMock(return_value=cursor)

        voice_id = await manager.assign_voice_single(quick=True)

        assert voice_id in {"std-1", "std-2", "std-3"}

    async def test_queries_only_standard_voices(
        self, mock_mongo_collection, mock_r2, r2_config
    ):
        """
        The DB query filter must include is_standard=True.
        If this filter is removed, non-standard character voices could be
        assigned to the narrator — a casting regression.
        """
        manager = _make_manager(mock_mongo_collection, mock_r2, r2_config)

        cursor = MagicMock()
        cursor.to_list = AsyncMock(return_value=[{"_id": "std-1"}])
        mock_mongo_collection.find = MagicMock(return_value=cursor)

        await manager.assign_voice_single(quick=True)

        query_filter = mock_mongo_collection.find.call_args[0][0]
        assert query_filter.get("is_standard") is True

    async def test_raises_when_no_standard_voices_exist(
        self, mock_mongo_collection, mock_r2, r2_config
    ):
        """
        Empty standard pool → clear ValueError, not an IndexError or crash.
        This protects against silent failures when the library is unseeded.
        """
        manager = _make_manager(mock_mongo_collection, mock_r2, r2_config)

        cursor = MagicMock()
        cursor.to_list = AsyncMock(return_value=[])
        mock_mongo_collection.find = MagicMock(return_value=cursor)

        with pytest.raises(ValueError, match="No standard voices"):
            await manager.assign_voice_single(quick=True)


# ---------------------------------------------------------------------------
# assign_voice_single — vector mode
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestAssignVoiceSingleVector:

    async def test_raises_when_character_is_none(
        self, mock_mongo_collection, mock_r2, r2_config
    ):
        """
        quick=False without a character dict must raise ValueError immediately.
        This validates the public API contract of the method.
        """
        manager = _make_manager(mock_mongo_collection, mock_r2, r2_config)

        with pytest.raises(ValueError, match="character"):
            await manager.assign_voice_single(quick=False, character=None)

    async def test_returns_highest_similarity_voice(
        self, mock_mongo_collection, mock_r2, r2_config
    ):
        """
        Given voices with known embeddings, the method must return the voice
        whose embedding is most similar to the character query embedding.
        """
        manager = _make_manager(mock_mongo_collection, mock_r2, r2_config)

        # voice-target has an embedding pointing in the same direction as our query
        # voice-other points in the opposite direction — similarity will be negative
        pool = [
            {"_id": "voice-target", "description": "male deep", "embedding": [1.0, 0.0] + [0.0] * 766, "is_standard": False},
            {"_id": "voice-other",  "description": "female high", "embedding": [-1.0, 0.0] + [0.0] * 766, "is_standard": False},
        ]
        cursor = MagicMock()
        cursor.to_list = AsyncMock(return_value=pool)
        mock_mongo_collection.find = MagicMock(return_value=cursor)

        character = {"name": "Sherlock Holmes", "description": "Brilliant detective, male."}

        with patch.object(manager, "_summarize_character_for_search", new=AsyncMock(return_value="deep male analytical")):
            # Query embedding points toward voice-target
            with patch(
                "app.services.voice_library.AIEmbeddingService.generate_embedding",
                new=AsyncMock(return_value=[1.0, 0.0] + [0.0] * 766),
            ):
                voice_id = await manager.assign_voice_single(quick=False, character=character)

        assert voice_id == "voice-target"

    async def test_falls_back_to_standard_pool_when_no_nonstandard_voices(
        self, mock_mongo_collection, mock_r2, r2_config
    ):
        """
        When the non-standard pool is empty, vector mode must fall back to the
        standard pool rather than raising an error.
        """
        manager = _make_manager(mock_mongo_collection, mock_r2, r2_config)

        standard_pool = [
            {"_id": "std-1", "description": "neutral female", "embedding": [1.0] + [0.0] * 767}
        ]

        call_count = 0
        def side_effect_find(query_filter, *args, **kwargs):
            nonlocal call_count
            cursor = MagicMock()
            if query_filter.get("is_standard") is False:
                cursor.to_list = AsyncMock(return_value=[])  # non-standard pool empty
            else:
                cursor.to_list = AsyncMock(return_value=standard_pool)
            return cursor

        mock_mongo_collection.find = MagicMock(side_effect=side_effect_find)

        with patch.object(manager, "_summarize_character_for_search", new=AsyncMock(return_value="neutral")):
            with patch(
                "app.services.voice_library.AIEmbeddingService.generate_embedding",
                new=AsyncMock(return_value=[1.0] + [0.0] * 767),
            ):
                voice_id = await manager.assign_voice_single(quick=False, character={"name": "Narrator"})

        assert voice_id == "std-1"


# ---------------------------------------------------------------------------
# assign_voice_multiple
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestAssignVoiceMultiple:

    async def test_raises_when_library_empty(
        self, mock_mongo_collection, mock_r2, r2_config
    ):
        manager = _make_manager(mock_mongo_collection, mock_r2, r2_config)

        cursor = MagicMock()
        cursor.to_list = AsyncMock(return_value=[])
        mock_mongo_collection.find = MagicMock(return_value=cursor)

        with pytest.raises(ValueError, match="No non-standard voices"):
            await manager.assign_voice_multiple([{"name": "Alice"}])

    async def test_raises_when_not_enough_voices_for_characters(
        self, mock_mongo_collection, mock_r2, r2_config
    ):
        """
        3 characters but only 2 voices → must raise before attempting assignment.
        The Hungarian algorithm would silently reuse voices; we want an early error.
        """
        manager = _make_manager(mock_mongo_collection, mock_r2, r2_config)

        cursor = MagicMock()
        cursor.to_list = AsyncMock(return_value=[
            {"_id": "v1", "description": "x", "embedding": [0.1] * 768},
            {"_id": "v2", "description": "y", "embedding": [0.2] * 768},
        ])
        mock_mongo_collection.find = MagicMock(return_value=cursor)

        characters = [{"name": "Alice"}, {"name": "Bob"}, {"name": "Charlie"}]

        with pytest.raises(ValueError, match="3 characters"):
            await manager.assign_voice_multiple(characters)

    async def test_returns_dict_with_all_character_names(
        self, mock_mongo_collection, mock_r2, r2_config
    ):
        """
        Every character must appear as a key in the result dict.
        """
        manager = _make_manager(mock_mongo_collection, mock_r2, r2_config)

        voices = [
            {"_id": f"v{i}", "description": "x", "embedding": [float(i)] + [0.0] * 767}
            for i in range(3)
        ]
        cursor = MagicMock()
        cursor.to_list = AsyncMock(return_value=voices)
        mock_mongo_collection.find = MagicMock(return_value=cursor)

        characters = [{"name": "Alice"}, {"name": "Bob"}, {"name": "Charlie"}]

        with patch.object(manager, "_summarize_character_for_search", new=AsyncMock(side_effect=lambda c: c["name"])):
            with patch(
                "app.services.voice_library.AIEmbeddingService.generate_embedding",
                new=AsyncMock(side_effect=lambda t, **kw: [hash(t) % 2] + [0.0] * 767),
            ):
                with patch.object(manager, "_llm_validate_char_assignments", new=AsyncMock(return_value=[])):
                    result = await manager.assign_voice_multiple(characters)

        assert set(result.keys()) == {"Alice", "Bob", "Charlie"}

    async def test_all_assigned_voice_ids_are_unique(
        self, mock_mongo_collection, mock_r2, r2_config
    ):
        """
        Each character must get a DIFFERENT voice. The Hungarian algorithm
        guarantees this — this test is a regression guard ensuring we haven't
        accidentally broken the uniqueness constraint.
        """
        manager = _make_manager(mock_mongo_collection, mock_r2, r2_config)

        voices = [
            {"_id": f"v{i}", "description": "x", "embedding": [float(i) / 10] + [0.0] * 767}
            for i in range(3)
        ]
        cursor = MagicMock()
        cursor.to_list = AsyncMock(return_value=voices)
        mock_mongo_collection.find = MagicMock(return_value=cursor)

        characters = [{"name": "A"}, {"name": "B"}, {"name": "C"}]

        with patch.object(manager, "_summarize_character_for_search", new=AsyncMock(side_effect=lambda c: c["name"])):
            with patch(
                "app.services.voice_library.AIEmbeddingService.generate_embedding",
                new=AsyncMock(side_effect=lambda t, **kw: [0.1, 0.2] + [0.0] * 766),
            ):
                with patch.object(manager, "_llm_validate_char_assignments", new=AsyncMock(return_value=[])):
                    result = await manager.assign_voice_multiple(characters)

        assert len(set(result.values())) == 3  # all voice IDs are distinct


# ---------------------------------------------------------------------------
# _llm_validate_char_assignments
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestLlmValidateCharAssignments:

    async def test_returns_empty_list_when_all_approved(
        self, mock_mongo_collection, mock_r2, r2_config
    ):
        manager = _make_manager(mock_mongo_collection, mock_r2, r2_config)

        assignments = [
            {"char_idx": 0, "voice_idx": 0, "char_name": "Alice",
             "char_bio": "young female", "voice_desc": "young female voice", "voice_id": "v0"}
        ]

        with patch(
            "app.services.voice_library.AITextService.chat",
            new=AsyncMock(return_value='{"rejections": []}'),
        ):
            result = await manager._llm_validate_char_assignments(assignments)

        assert result == []

    async def test_returns_veto_tuple_on_rejection(
        self, mock_mongo_collection, mock_r2, r2_config
    ):
        """
        When the LLM rejects characterId=0, the method must return [(0, voice_idx)].
        This tuple is what the caller uses to penalise that pairing in the cost matrix.
        """
        manager = _make_manager(mock_mongo_collection, mock_r2, r2_config)

        assignments = [
            {"char_idx": 0, "voice_idx": 2, "char_name": "Bob",
             "char_bio": "old male", "voice_desc": "young female voice", "voice_id": "v2"}
        ]

        with patch(
            "app.services.voice_library.AITextService.chat",
            new=AsyncMock(return_value='{"rejections": [0]}'),
        ):
            result = await manager._llm_validate_char_assignments(assignments)

        assert (0, 2) in result