"""
Unit Tests — AI Generation Router (ai_generation.py)
======================================================
Tests the HTTP layer: routing, request validation, response shape, and error
handling. Uses FastAPI's TestClient (synchronous) and AsyncClient for async
routes.

What we test here vs. in test_ai_text_service.py:
  - HERE:  Does the endpoint parse the request body correctly?
           Does it return the right HTTP status codes?
           Does it format the JSON response correctly?
           Does a service exception become a 500 with a useful detail field?
  - THERE: Does the service itself do the right thing internally?

This separation means a broken service test doesn't mask a broken routing test
and vice versa.
"""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI


# ---------------------------------------------------------------------------
# App fixture — mounts only the router under test, no other dependencies
# ---------------------------------------------------------------------------

@pytest.fixture
def app():
    """
    Create a minimal FastAPI app with only the AI generation router mounted.
    This is faster than booting the full app and avoids startup side effects
    (DB connections, etc.).
    """
    from app.routers.ai_generation import router
    test_app = FastAPI()
    test_app.include_router(router)
    return test_app


@pytest.fixture
def client(app):
    return TestClient(app)


# ---------------------------------------------------------------------------
# POST /chat
# ---------------------------------------------------------------------------

class TestChatEndpoint:

    def test_returns_200_with_answer_key(self, client):
        with patch(
            "app.routers.ai_generation.AITextService.chat",
            new=AsyncMock(return_value="Mocked LLM answer"),
        ):
            response = client.post("/chat", json={
                "prompt_messages": [["user", "Hello"]],
                "provider": "cf",
                "preset": "chat-basic",
            })

        assert response.status_code == 200
        assert response.json()["answer"] == "Mocked LLM answer"

    def test_returns_500_when_service_raises(self, client):
        """
        If AITextService.chat raises, the endpoint must return 500 with the
        exception message in the detail field — not a generic crash.
        """
        with patch(
            "app.routers.ai_generation.AITextService.chat",
            new=AsyncMock(side_effect=RuntimeError("Cloudflare timeout")),
        ):
            response = client.post("/chat", json={
                "prompt_messages": [["user", "Hi"]],
                "provider": "cf",
            })

        assert response.status_code == 500
        assert "Cloudflare timeout" in response.json()["detail"]

    def test_422_when_prompt_messages_missing(self, client):
        """
        prompt_messages is required. Missing it must return 422 Unprocessable
        Entity (FastAPI/Pydantic validation), not a 500 crash.
        """
        response = client.post("/chat", json={"provider": "cf"})
        assert response.status_code == 422

    def test_default_provider_is_cf(self, client):
        """
        Provider defaults to CF. A request without an explicit provider must
        still succeed and call the service (not crash on a missing enum value).
        """
        with patch(
            "app.routers.ai_generation.AITextService.chat",
            new=AsyncMock(return_value="ok"),
        ) as mock_chat:
            response = client.post("/chat", json={
                "prompt_messages": [["user", "Hello"]],
            })

        assert response.status_code == 200
        call_kwargs = mock_chat.call_args.kwargs
        from app.services.ai_model_factory import ModelProvider
        assert call_kwargs["provider"] == ModelProvider.CF


# ---------------------------------------------------------------------------
# POST /chat/web-rag
# ---------------------------------------------------------------------------

class TestRagChatEndpoint:

    def test_returns_answer_and_context(self, client):
        fake_snippets = [{"title": "T", "body": "B", "url": "http://x.com"}]

        with patch(
            "app.routers.ai_generation.AITextService.chat_rag_web_context",
            new=AsyncMock(return_value=("RAG answer", fake_snippets)),
        ):
            response = client.post("/chat/web-rag", json={
                "prompt_messages": [["user", "What is AI?"]],
                "provider": "cf",
            })

        assert response.status_code == 200
        body = response.json()
        assert body["answer"] == "RAG answer"
        assert body["context"] == fake_snippets

    def test_passes_search_query_template_to_service(self, client):
        with patch(
            "app.routers.ai_generation.AITextService.chat_rag_web_context",
            new=AsyncMock(return_value=("answer", [])),
        ) as mock_rag:
            client.post("/chat/web-rag", json={
                "prompt_messages": [["user", "hi"]],
                "provider": "cf",
                "search_query_template": "latest AI news",
            })

        call_kwargs = mock_rag.call_args.kwargs
        assert call_kwargs["search_query_template"] == "latest AI news"


# ---------------------------------------------------------------------------
# POST /embedding
# ---------------------------------------------------------------------------

class TestEmbeddingEndpoint:

    def test_returns_embedding_list(self, client):
        fake_vector = [0.1, 0.2, 0.3]

        with patch(
            "app.routers.ai_generation.AIEmbeddingService.generate_embedding",
            new=AsyncMock(return_value=fake_vector),
        ):
            response = client.post("/embedding", json={
                "text": "The Outsiders is a novel.",
                "provider": "cf",
                "preset": "embedding-768",
            })

        assert response.status_code == 200
        assert response.json()["embedding"] == fake_vector

    def test_422_when_text_missing(self, client):
        response = client.post("/embedding", json={"provider": "cf"})
        assert response.status_code == 422

    def test_returns_500_when_embedding_fails(self, client):
        with patch(
            "app.routers.ai_generation.AIEmbeddingService.generate_embedding",
            new=AsyncMock(side_effect=RuntimeError("Embedding endpoint down")),
        ):
            response = client.post("/embedding", json={
                "text": "test",
                "provider": "cf",
            })

        assert response.status_code == 500
        assert "Embedding endpoint down" in response.json()["detail"]