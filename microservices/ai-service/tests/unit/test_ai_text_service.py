"""
Unit Tests — AITextService
===========================
Tests every public method of AITextService in complete isolation.

What "isolation" means here:
  - ModelFactory.get_model is patched → no Cloudflare calls, no network
  - AsyncTavilyClient is patched     → no web searches
  - Tests run in milliseconds and cost $0

Why these tests matter:
  - They verify YOUR logic: message formatting, cache behaviour, error
    handling, context injection, word limit injection, JSON repair.
  - If Cloudflare changes their API tomorrow, these tests still pass because
    they are testing *your* code, not Cloudflare's.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from tests.conftest import make_async_openai_client, make_openai_response


# ---------------------------------------------------------------------------
# _to_openai_messages  (pure function)
# ---------------------------------------------------------------------------

class TestToOpenaiMessages:

    def test_single_user_message(self):
        from app.services.ai_text_service import _to_openai_messages
        result = _to_openai_messages([["user", "Hello"]])
        assert result == [{"role": "user", "content": "Hello"}]

    def test_system_and_user(self):
        from app.services.ai_text_service import _to_openai_messages
        result = _to_openai_messages([
            ["system", "You are helpful."],
            ["user", "Tell me a joke"],
        ])
        assert result == [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Tell me a joke"},
        ]

    def test_preserves_order(self):
        from app.services.ai_text_service import _to_openai_messages
        messages = [["user", "a"], ["assistant", "b"], ["user", "c"]]
        result = _to_openai_messages(messages)
        assert [m["role"] for m in result] == ["user", "assistant", "user"]

    def test_empty_list(self):
        from app.services.ai_text_service import _to_openai_messages
        assert _to_openai_messages([]) == []


# ---------------------------------------------------------------------------
# _base_params  (pure function)
# ---------------------------------------------------------------------------

class TestBaseParams:

    def test_defaults_when_no_inputs(self):
        from app.services.ai_text_service import _base_params
        result = _base_params(None)
        assert result["temperature"] == 0.2
        assert result["max_tokens"] == 8192

    def test_caller_can_override_temperature(self):
        from app.services.ai_text_service import _base_params
        result = _base_params({"temperature": 0.9})
        assert result["temperature"] == 0.9
        assert result["max_tokens"] == 8192

    def test_caller_can_override_max_tokens(self):
        from app.services.ai_text_service import _base_params
        result = _base_params({"max_tokens": 512})
        assert result["max_tokens"] == 512

    def test_caller_can_add_extra_params(self):
        from app.services.ai_text_service import _base_params
        result = _base_params({"top_p": 0.95})
        assert result["top_p"] == 0.95
        assert "temperature" in result


# ---------------------------------------------------------------------------
# _repair_json  (pure function)
# ---------------------------------------------------------------------------

class TestRepairJson:
    """
    _repair_json has three resolution stages. Each stage gets its own test
    so a regression in one stage does not hide behind another passing stage.
    """

    def test_valid_json_passes_straight_through(self):
        from app.services.ai_text_service import _repair_json
        result = _repair_json('{"name": "Harry", "age": 11}')
        assert result == {"name": "Harry", "age": 11}

    def test_strips_markdown_json_fence(self):
        """Model wraps output in ```json ... ``` — very common with instruct models."""
        from app.services.ai_text_service import _repair_json
        raw = '```json\n{"name": "Harry"}\n```'
        assert _repair_json(raw) == {"name": "Harry"}

    def test_strips_plain_markdown_fence(self):
        """Model uses ``` without the json tag."""
        from app.services.ai_text_service import _repair_json
        raw = '```\n{"name": "Harry"}\n```'
        assert _repair_json(raw) == {"name": "Harry"}

    def test_extracts_json_from_preamble(self):
        """Model adds prose before the JSON object."""
        from app.services.ai_text_service import _repair_json
        raw = 'Here is the JSON you requested:\n{"name": "Harry"}'
        assert _repair_json(raw) == {"name": "Harry"}

    def test_extracts_json_array(self):
        """Brace extractor must also handle arrays, not just objects."""
        from app.services.ai_text_service import _repair_json
        raw = 'Result: [{"id": 1}, {"id": 2}]'
        assert _repair_json(raw) == [{"id": 1}, {"id": 2}]

    def test_raises_value_error_on_hopeless_input(self):
        """Completely unparseable prose must raise ValueError."""
        from app.services.ai_text_service import _repair_json
        with pytest.raises(ValueError, match="Could not extract valid JSON"):
            _repair_json("Sorry, I cannot answer that.")

    def test_raises_on_empty_string(self):
        from app.services.ai_text_service import _repair_json
        with pytest.raises(ValueError):
            _repair_json("")


# ---------------------------------------------------------------------------
# _word_limit_from_preset  (pure function)
# ---------------------------------------------------------------------------

class TestWordLimitFromPreset:
    """
    Uses the real ai_defaults.json via _get_registry() — appropriate because
    that file is static checked-in data, not a live dependency.
    """

    def test_returns_75_percent_of_output_tokens_for_known_preset(self):
        """chat-basic has max_output_tokens: 32768. Expected = int(32768 * 0.75)."""
        from app.services.ai_text_service import _word_limit_from_preset
        result = _word_limit_from_preset("chat-basic")
        assert result == int(32768 * 0.75)

    def test_respects_custom_ratio(self):
        from app.services.ai_text_service import _word_limit_from_preset
        result = _word_limit_from_preset("chat-basic", ratio=0.5)
        assert result == int(32768 * 0.5)

    def test_returns_none_for_unknown_preset(self):
        from app.services.ai_text_service import _word_limit_from_preset
        assert _word_limit_from_preset("this-preset-does-not-exist") is None

    def test_returns_none_when_preset_is_none(self):
        from app.services.ai_text_service import _word_limit_from_preset
        assert _word_limit_from_preset(None) is None

    def test_embedding_preset_returns_none(self):
        """
        Embedding presets have max_output_tokens: null in the JSON.
        Must return None rather than crashing on int(None * 0.75).
        """
        from app.services.ai_text_service import _word_limit_from_preset
        assert _word_limit_from_preset("embedding-768") is None


# ---------------------------------------------------------------------------
# _inject_word_limit  (pure function)
# ---------------------------------------------------------------------------

class TestInjectWordLimit:

    def test_appends_to_existing_system_message(self):
        from app.services.ai_text_service import _inject_word_limit
        messages = [["system", "You are helpful."], ["user", "Hi"]]
        result = _inject_word_limit(messages, 500)
        assert "Limit your response to 500 words." in result[0][1]
        assert "You are helpful." in result[0][1]

    def test_prepends_new_system_message_when_none_exists(self):
        from app.services.ai_text_service import _inject_word_limit
        messages = [["user", "Hi"]]
        result = _inject_word_limit(messages, 500)
        assert result[0][0] == "system"
        assert "500 words" in result[0][1]
        assert result[1] == ["user", "Hi"]

    def test_does_not_mutate_original_list(self):
        """
        _inject_word_limit must copy — mutating the caller's list would cause
        the word limit instruction to bleed into subsequent calls that reuse
        the same message list.
        """
        from app.services.ai_text_service import _inject_word_limit
        original = [["system", "Be helpful."], ["user", "Hi"]]
        original_system_content = original[0][1]
        _inject_word_limit(original, 500)
        assert original[0][1] == original_system_content

    def test_original_user_message_preserved(self):
        from app.services.ai_text_service import _inject_word_limit
        messages = [["system", "sys"], ["user", "Tell me everything"]]
        result = _inject_word_limit(messages, 200)
        assert result[1] == ["user", "Tell me everything"]


# ---------------------------------------------------------------------------
# AITextService.chat
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestChat:

    async def test_returns_assistant_text(self):
        from app.services.ai_text_service import AITextService
        from app.services.ai_model_factory import ModelProvider

        fake_client = make_async_openai_client("Hello!")
        AITextService._model_cache.clear()

        with patch.object(AITextService, "_get_client", new=AsyncMock(return_value=(fake_client, "some-model"))):
            result = await AITextService.chat(
                prompt_messages=[["user", "Hi"]],
                provider=ModelProvider.CF,
            )

        assert result == "Hello!"

    async def test_messages_are_converted_before_api_call(self):
        from app.services.ai_text_service import AITextService
        from app.services.ai_model_factory import ModelProvider

        fake_client = make_async_openai_client("ok")
        AITextService._model_cache.clear()

        with patch.object(AITextService, "_get_client", new=AsyncMock(return_value=(fake_client, "model"))):
            await AITextService.chat(
                prompt_messages=[["system", "Be helpful"], ["user", "Hello"]],
                provider=ModelProvider.CF,
            )

        call_kwargs = fake_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["messages"] == [
            {"role": "system", "content": "Be helpful"},
            {"role": "user", "content": "Hello"},
        ]

    async def test_inputs_override_defaults(self):
        from app.services.ai_text_service import AITextService
        from app.services.ai_model_factory import ModelProvider

        fake_client = make_async_openai_client("ok")
        AITextService._model_cache.clear()

        with patch.object(AITextService, "_get_client", new=AsyncMock(return_value=(fake_client, "model"))):
            await AITextService.chat(
                prompt_messages=[["user", "Hi"]],
                provider=ModelProvider.CF,
                inputs={"temperature": 0.9, "max_tokens": 100},
            )

        call_kwargs = fake_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["temperature"] == 0.9
        assert call_kwargs["max_tokens"] == 100

    async def test_client_is_cached_on_second_call(self):
        """
        ModelFactory.get_model should only be called once. A second call with
        the same cache key must reuse the existing client.
        """
        from app.services.ai_text_service import AITextService
        from app.services.ai_model_factory import ModelProvider

        fake_client = make_async_openai_client("ok")
        AITextService._model_cache.clear()

        mock_factory = AsyncMock(return_value=(fake_client, "model"))

        with patch("app.services.ai_model_factory.ModelFactory.get_model", new=mock_factory):
            await AITextService.chat([["user", "a"]], provider=ModelProvider.CF, preset="chat-basic")
            await AITextService.chat([["user", "b"]], provider=ModelProvider.CF, preset="chat-basic")

        assert mock_factory.call_count == 1


# ---------------------------------------------------------------------------
# AITextService.chat_with_system
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestChatWithSystem:

    async def test_builds_correct_message_structure(self):
        """
        chat_with_system delegates to chat() with positional args.
        We verify the first positional arg (messages) has the right structure.
        """
        from app.services.ai_text_service import AITextService
        from app.services.ai_model_factory import ModelProvider

        AITextService._model_cache.clear()

        with patch.object(AITextService, "chat", new=AsyncMock(return_value="answer")) as mock_chat:
            result = await AITextService.chat_with_system(
                system="You are a tester.",
                user="Run the tests.",
                provider=ModelProvider.CF,
            )

        assert result == "answer"
        # chat() is called with messages as the first positional arg
        called_messages = mock_chat.call_args.args[0]
        assert called_messages[0] == ["system", "You are a tester."]
        assert called_messages[1] == ["user", "Run the tests."]


# ---------------------------------------------------------------------------
# AITextService.chat_json
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestChatJson:

    async def test_parses_valid_json_response(self):
        from app.services.ai_text_service import AITextService
        from app.services.ai_model_factory import ModelProvider

        fake_client = make_async_openai_client('{"name": "Harry", "age": 11}')
        AITextService._model_cache.clear()

        with patch.object(AITextService, "_get_client", new=AsyncMock(return_value=(fake_client, "model"))):
            result = await AITextService.chat_json(
                prompt_messages=[["user", "Give me JSON"]],
                provider=ModelProvider.CF,
            )

        assert result == {"name": "Harry", "age": 11}

    async def test_repairs_markdown_fenced_json(self):
        """
        chat_json must succeed even when the model wraps output in ```json fences.
        Previously this would raise ValueError — now _repair_json handles it.
        """
        from app.services.ai_text_service import AITextService
        from app.services.ai_model_factory import ModelProvider

        fake_client = make_async_openai_client('```json\n{"name": "Harry"}\n```')
        AITextService._model_cache.clear()

        with patch.object(AITextService, "_get_client", new=AsyncMock(return_value=(fake_client, "model"))):
            result = await AITextService.chat_json(
                prompt_messages=[["user", "Give me JSON"]],
                provider=ModelProvider.CF,
            )

        assert result == {"name": "Harry"}

    async def test_raises_value_error_on_completely_invalid_response(self):
        """Prose with no JSON anywhere must still raise ValueError."""
        from app.services.ai_text_service import AITextService
        from app.services.ai_model_factory import ModelProvider

        fake_client = make_async_openai_client("Sorry, I cannot answer that.")
        AITextService._model_cache.clear()

        with patch.object(AITextService, "_get_client", new=AsyncMock(return_value=(fake_client, "model"))):
            with pytest.raises(ValueError, match="Could not extract valid JSON"):
                await AITextService.chat_json(
                    prompt_messages=[["user", "Give me JSON"]],
                    provider=ModelProvider.CF,
                )

    async def test_sends_json_object_response_format(self):
        """The API call must include response_format={"type": "json_object"}."""
        from app.services.ai_text_service import AITextService
        from app.services.ai_model_factory import ModelProvider

        fake_client = make_async_openai_client('{"ok": true}')
        AITextService._model_cache.clear()

        with patch.object(AITextService, "_get_client", new=AsyncMock(return_value=(fake_client, "model"))):
            await AITextService.chat_json(
                prompt_messages=[["user", "JSON please"]],
                provider=ModelProvider.CF,
            )

        call_kwargs = fake_client.chat.completions.create.call_args.kwargs
        assert call_kwargs.get("response_format") == {"type": "json_object"}


# ---------------------------------------------------------------------------
# AITextService.chat_rag_web_context
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestChatRagWebContext:

    async def test_injects_snippets_into_existing_system_message(self, mock_tavily):
        from app.services.ai_text_service import AITextService
        from app.services.ai_model_factory import ModelProvider

        fake_client = make_async_openai_client("Answer using context.")
        AITextService._model_cache.clear()

        with patch.object(AITextService, "_get_client", new=AsyncMock(return_value=(fake_client, "model"))):
            with patch.object(AITextService, "_derive_search_query", new=AsyncMock(return_value="fusion energy")):
                with patch("app.services.ai_text_service._word_limit_from_preset", return_value=None):
                    await AITextService.chat_rag_web_context(
                        prompt_messages=[
                            ["system", "You are a science assistant."],
                            ["user", "What is fusion?"],
                        ],
                        provider=ModelProvider.CF,
                    )

        sent_messages = fake_client.chat.completions.create.call_args.kwargs["messages"]
        assert sent_messages[0]["role"] == "system"
        assert "Search results" in sent_messages[0]["content"]
        assert "You are a science assistant." in sent_messages[0]["content"]

    async def test_creates_system_message_when_none_exists(self, mock_tavily):
        from app.services.ai_text_service import AITextService
        from app.services.ai_model_factory import ModelProvider

        fake_client = make_async_openai_client("Here is what I found.")
        AITextService._model_cache.clear()

        with patch.object(AITextService, "_get_client", new=AsyncMock(return_value=(fake_client, "model"))):
            with patch.object(AITextService, "_derive_search_query", new=AsyncMock(return_value="fusion")):
                with patch("app.services.ai_text_service._word_limit_from_preset", return_value=None):
                    await AITextService.chat_rag_web_context(
                        prompt_messages=[["user", "What is fusion?"]],
                        provider=ModelProvider.CF,
                    )

        sent_messages = fake_client.chat.completions.create.call_args.kwargs["messages"]
        assert sent_messages[0]["role"] == "system"
        assert "Search results" in sent_messages[0]["content"]
        assert sent_messages[1] == {"role": "user", "content": "What is fusion?"}

    async def test_returns_snippets_alongside_answer(self, mock_tavily):
        from app.services.ai_text_service import AITextService
        from app.services.ai_model_factory import ModelProvider

        fake_client = make_async_openai_client("Great question.")
        AITextService._model_cache.clear()

        with patch.object(AITextService, "_get_client", new=AsyncMock(return_value=(fake_client, "model"))):
            with patch.object(AITextService, "_derive_search_query", new=AsyncMock(return_value="fusion")):
                with patch("app.services.ai_text_service._word_limit_from_preset", return_value=None):
                    answer, snippets = await AITextService.chat_rag_web_context(
                        prompt_messages=[["user", "Fusion?"]],
                        provider=ModelProvider.CF,
                    )

        assert answer == "Great question."
        assert len(snippets) == 2
        assert snippets[0]["title"] == "Fake Article 1"

    async def test_word_limit_injected_when_preset_has_token_count(self, mock_tavily):
        """
        When the preset resolves to a known word limit, the system message
        sent to the API must contain the word limit instruction.
        """
        from app.services.ai_text_service import AITextService
        from app.services.ai_model_factory import ModelProvider

        fake_client = make_async_openai_client("Answer.")
        AITextService._model_cache.clear()

        with patch.object(AITextService, "_get_client", new=AsyncMock(return_value=(fake_client, "model"))):
            with patch.object(AITextService, "_derive_search_query", new=AsyncMock(return_value="q")):
                with patch("app.services.ai_text_service._word_limit_from_preset", return_value=500):
                    await AITextService.chat_rag_web_context(
                        prompt_messages=[["system", "You are helpful."], ["user", "Hi"]],
                        provider=ModelProvider.CF,
                        preset="chat-basic",
                    )

        sent_messages = fake_client.chat.completions.create.call_args.kwargs["messages"]
        assert "500 words" in sent_messages[0]["content"]

    async def test_word_limit_not_injected_when_preset_unknown(self, mock_tavily):
        """
        When _word_limit_from_preset returns None, no word limit instruction
        should appear in the system message.
        """
        from app.services.ai_text_service import AITextService
        from app.services.ai_model_factory import ModelProvider

        fake_client = make_async_openai_client("Answer.")
        AITextService._model_cache.clear()

        with patch.object(AITextService, "_get_client", new=AsyncMock(return_value=(fake_client, "model"))):
            with patch.object(AITextService, "_derive_search_query", new=AsyncMock(return_value="q")):
                with patch("app.services.ai_text_service._word_limit_from_preset", return_value=None):
                    await AITextService.chat_rag_web_context(
                        prompt_messages=[["system", "You are helpful."], ["user", "Hi"]],
                        provider=ModelProvider.CF,
                    )

        sent_messages = fake_client.chat.completions.create.call_args.kwargs["messages"]
        assert "words" not in sent_messages[0]["content"]


# ---------------------------------------------------------------------------
# AITextService._derive_search_query
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestDeriveSearchQuery:

    async def test_uses_query_text_directly_without_llm_call(self):
        """
        When search_query_text is provided, it is used as-is and the LLM
        must NOT be called. This is both a correctness and a cost contract.
        """
        from app.services.ai_text_service import AITextService

        fake_client = make_async_openai_client("should not be called")

        result = await AITextService._derive_search_query(
            client=fake_client,
            model="any-model",
            prompt_messages=[["user", "What is fusion?"]],
            search_query_text="latest fusion energy news",
        )

        assert result == "latest fusion energy news"
        fake_client.chat.completions.create.assert_not_called()

    async def test_calls_llm_when_no_query_text(self):
        """
        When search_query_text is None, the LLM must be called to derive a query.
        """
        from app.services.ai_text_service import AITextService

        fake_client = make_async_openai_client("fusion energy breakthroughs")

        result = await AITextService._derive_search_query(
            client=fake_client,
            model="some-model",
            prompt_messages=[["user", "Tell me about fusion energy"]],
            search_query_text=None,
        )

        assert result == "fusion energy breakthroughs"
        fake_client.chat.completions.create.assert_called_once()

    async def test_falls_back_to_last_user_message_on_empty_llm_response(self):
        """
        If the LLM returns an empty string, fall back to the raw last user
        message rather than sending a blank search query to Tavily.
        """
        from app.services.ai_text_service import AITextService

        fake_client = make_async_openai_client("")

        result = await AITextService._derive_search_query(
            client=fake_client,
            model="some-model",
            prompt_messages=[["user", "Tell me about fusion energy"]],
            search_query_text=None,
        )

        assert result == "Tell me about fusion energy"