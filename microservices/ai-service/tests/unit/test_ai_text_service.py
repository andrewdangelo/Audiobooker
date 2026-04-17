"""
Unit Tests — AITextService
===========================
Tests every public method of AITextService in complete isolation.

What "isolation" means here:
  - ModelFactory.get_model is patched → no Cloudflare calls, no network
  - AsyncTavilyClient is patched     → no web searches
  - Tests run in milliseconds and cost $0

Why these tests matter:
  - They verify YOUR logic: message formatting, cache behaviour, error handling,
    context injection, streaming chunk handling.
  - If Cloudflare changes their API tomorrow, these tests still pass because
    they're testing *your* code, not Cloudflare's.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from tests.conftest import make_async_openai_client, make_openai_response


# ---------------------------------------------------------------------------
# _to_openai_messages  (pure function — no mocking needed)
# ---------------------------------------------------------------------------

class TestToOpenaiMessages:
    """
    _to_openai_messages is a pure function: same input → same output, no side
    effects, no dependencies. These are the simplest possible tests to write
    and they still provide real value: if someone refactors the function and
    breaks the format, this catches it immediately.
    """

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
        assert result["max_tokens"] == 2048

    def test_caller_can_override_temperature(self):
        from app.services.ai_text_service import _base_params
        result = _base_params({"temperature": 0.9})
        assert result["temperature"] == 0.9
        # default max_tokens is preserved
        assert result["max_tokens"] == 2048

    def test_caller_can_override_max_tokens(self):
        from app.services.ai_text_service import _base_params
        result = _base_params({"max_tokens": 512})
        assert result["max_tokens"] == 512

    def test_caller_can_add_extra_params(self):
        from app.services.ai_text_service import _base_params
        result = _base_params({"top_p": 0.95})
        assert result["top_p"] == 0.95
        # defaults still present
        assert "temperature" in result


# ---------------------------------------------------------------------------
# AITextService.chat
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestChat:

    async def test_returns_assistant_text(self):
        """
        Core contract: given a mocked LLM that returns "Hello!", chat() must
        return exactly that string.
        """
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
        """
        The LLM call must receive dicts, NOT the [[role, content]] list format.
        """
        from app.services.ai_text_service import AITextService
        from app.services.ai_model_factory import ModelProvider

        fake_client = make_async_openai_client("ok")
        AITextService._model_cache.clear()

        with patch.object(AITextService, "_get_client", new=AsyncMock(return_value=(fake_client, "model"))):
            await AITextService.chat(
                prompt_messages=[["system", "Be helpful"], ["user", "Hello"]],
                provider=ModelProvider.CF,
            )

        # Verify the actual messages sent to the API
        call_kwargs = fake_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["messages"] == [
            {"role": "system", "content": "Be helpful"},
            {"role": "user", "content": "Hello"},
        ]

    async def test_inputs_override_defaults(self):
        """
        When a caller passes inputs={"temperature": 0.9}, that value must
        reach the API call, not the default 0.2.
        """
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
        _get_client (and therefore ModelFactory.get_model) should be called
        once and the result cached. A second call with the same key must NOT
        hit the factory again.
        This is a regression guard: if someone accidentally removes the cache,
        every request would reinitialise the client, causing latency spikes.
        """
        from app.services.ai_text_service import AITextService
        from app.services.ai_model_factory import ModelProvider

        fake_client = make_async_openai_client("ok")
        AITextService._model_cache.clear()

        mock_factory = AsyncMock(return_value=(fake_client, "model"))

        with patch(
            "app.services.ai_model_factory.ModelFactory.get_model",
            new=mock_factory,
        ):
            await AITextService.chat([["user", "a"]], provider=ModelProvider.CF, preset="chat-basic")
            await AITextService.chat([["user", "b"]], provider=ModelProvider.CF, preset="chat-basic")

        # Factory must only have been initialised once
        assert mock_factory.call_count == 1


# ---------------------------------------------------------------------------
# AITextService.chat_with_system
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestChatWithSystem:

    async def test_builds_correct_message_structure(self):
        """
        chat_with_system is a convenience wrapper. Its only responsibility is
        to build the [[system, ...], [user, ...]] list and delegate to chat().
        We verify the delegation, not the LLM call.
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
        called_messages = mock_chat.call_args.kwargs["prompt_messages"]
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

    async def test_raises_value_error_on_invalid_json(self):
        """
        If the model returns prose instead of JSON, chat_json must raise
        ValueError — not silently return garbage.
        """
        from app.services.ai_text_service import AITextService
        from app.services.ai_model_factory import ModelProvider

        fake_client = make_async_openai_client("Sorry, I cannot answer that.")
        AITextService._model_cache.clear()

        with patch.object(AITextService, "_get_client", new=AsyncMock(return_value=(fake_client, "model"))):
            with pytest.raises(ValueError, match="valid JSON"):
                await AITextService.chat_json(
                    prompt_messages=[["user", "Give me JSON"]],
                    provider=ModelProvider.CF,
                )

    async def test_sends_json_object_response_format(self):
        """
        The API call must include response_format={"type": "json_object"}.
        Without this, the model won't reliably return JSON.
        """
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
# AITextService.chat_rag_web_context  (context injection logic)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestChatRagWebContext:

    async def test_injects_snippets_into_existing_system_message(self, mock_tavily):
        """
        When prompt_messages already has a system message, the web context
        must be PREPENDED to it — not added as a new message.
        """
        from app.services.ai_text_service import AITextService
        from app.services.ai_model_factory import ModelProvider

        fake_client = make_async_openai_client("Answer using context.")
        AITextService._model_cache.clear()

        with patch.object(AITextService, "_get_client", new=AsyncMock(return_value=(fake_client, "model"))):
            with patch.object(AITextService, "_derive_search_query", new=AsyncMock(return_value="fusion energy")):
                answer, snippets = await AITextService.chat_rag_web_context(
                    prompt_messages=[
                        ["system", "You are a science assistant."],
                        ["user", "What is fusion?"],
                    ],
                    provider=ModelProvider.CF,
                )

        # The system message sent to the API must contain BOTH the context AND original system content
        sent_messages = fake_client.chat.completions.create.call_args.kwargs["messages"]
        assert sent_messages[0]["role"] == "system"
        assert "Search results" in sent_messages[0]["content"]
        assert "You are a science assistant." in sent_messages[0]["content"]

    async def test_creates_system_message_when_none_exists(self, mock_tavily):
        """
        When there's no system message, a new one must be prepended with context.
        The original user message must remain at index 1.
        """
        from app.services.ai_text_service import AITextService
        from app.services.ai_model_factory import ModelProvider

        fake_client = make_async_openai_client("Here is what I found.")
        AITextService._model_cache.clear()

        with patch.object(AITextService, "_get_client", new=AsyncMock(return_value=(fake_client, "model"))):
            with patch.object(AITextService, "_derive_search_query", new=AsyncMock(return_value="fusion")):
                await AITextService.chat_rag_web_context(
                    prompt_messages=[["user", "What is fusion?"]],
                    provider=ModelProvider.CF,
                )

        sent_messages = fake_client.chat.completions.create.call_args.kwargs["messages"]
        assert sent_messages[0]["role"] == "system"
        assert "Search results" in sent_messages[0]["content"]
        assert sent_messages[1] == {"role": "user", "content": "What is fusion?"}

    async def test_returns_snippets_alongside_answer(self, mock_tavily):
        """
        The method returns a tuple (answer, snippets).
        Snippets must contain the canned Tavily results from the fixture.
        """
        from app.services.ai_text_service import AITextService
        from app.services.ai_model_factory import ModelProvider

        fake_client = make_async_openai_client("Great question.")
        AITextService._model_cache.clear()

        with patch.object(AITextService, "_get_client", new=AsyncMock(return_value=(fake_client, "model"))):
            with patch.object(AITextService, "_derive_search_query", new=AsyncMock(return_value="fusion")):
                answer, snippets = await AITextService.chat_rag_web_context(
                    prompt_messages=[["user", "Fusion?"]],
                    provider=ModelProvider.CF,
                )

        assert answer == "Great question."
        assert len(snippets) == 2
        assert snippets[0]["title"] == "Fake Article 1"


# ---------------------------------------------------------------------------
# AITextService._derive_search_query
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestDeriveSearchQuery:

    async def test_uses_template_directly_without_llm_call(self):
        """
        When a template string is provided, the method must use it directly
        and NOT make any LLM call. This is a performance contract.
        """
        from app.services.ai_text_service import AITextService

        fake_client = make_async_openai_client("should not be called")

        result = await AITextService._derive_search_query(
            client=fake_client,
            model="any-model",
            prompt_messages=[["user", "What is fusion?"]],
            template="latest fusion energy news",
        )

        assert result == "latest fusion energy news"
        # The client must NOT have been called
        fake_client.chat.completions.create.assert_not_called()

    async def test_calls_llm_when_no_template(self):
        """
        Without a template, the method must call the LLM to derive a query.
        """
        from app.services.ai_text_service import AITextService

        fake_client = make_async_openai_client("fusion energy breakthroughs")

        result = await AITextService._derive_search_query(
            client=fake_client,
            model="some-model",
            prompt_messages=[["user", "Tell me about fusion energy"]],
            template=None,
        )

        assert result == "fusion energy breakthroughs"
        fake_client.chat.completions.create.assert_called_once()