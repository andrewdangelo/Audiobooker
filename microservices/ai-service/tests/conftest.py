"""
conftest.py — Shared pytest fixtures
=====================================
pytest automatically loads this file for every test in the directory.
Fixtures defined here are available to ALL test files without importing.

Key concepts used here:
  - AsyncMock  : a Mock that can be awaited (for async functions)
  - MagicMock  : a regular Mock for sync objects/classes
  - patch      : temporarily replaces a real object with a Mock for the duration
                 of a test, then restores it automatically
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Reusable fake LLM response builder
# ---------------------------------------------------------------------------

def make_openai_response(content: str) -> MagicMock:
    """
    Builds a fake openai ChatCompletion response object.
    Mirrors the shape your code actually accesses:
        response.choices[0].message.content
    """
    message = MagicMock()
    message.content = content

    choice = MagicMock()
    choice.message = message
    choice.delta = message   # used in streaming

    response = MagicMock()
    response.choices = [choice]
    return response


def make_async_openai_client(response_content: str = "mocked response") -> MagicMock:
    """
    Returns a fake AsyncOpenAI client whose .chat.completions.create()
    is an AsyncMock returning a fake response.

    Usage in a test:
        client = make_async_openai_client("Hello!")
        # client.chat.completions.create(...) -> fake response with "Hello!"
    """
    client = MagicMock()
    client.chat = MagicMock()
    client.chat.completions = MagicMock()
    client.chat.completions.create = AsyncMock(
        return_value=make_openai_response(response_content)
    )
    return client


# ---------------------------------------------------------------------------
# Fixtures: ModelFactory patch
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_model_factory():
    """
    Patches ModelFactory.get_model so no network call is ever made.
    Returns a (client, model_name) tuple just like the real factory.

    Use this in any test that exercises code which calls ModelFactory.
    """
    fake_client = make_async_openai_client("mocked LLM response")
    with patch(
        "app.services.ai_model_factory.ModelFactory.get_model",
        new=AsyncMock(return_value=(fake_client, "@cf/openai/gpt-oss-20b")),
    ) as mock:
        yield mock, fake_client


@pytest.fixture
def mock_embedding_service():
    """
    Patches AIEmbeddingService.generate_embedding.
    Returns a fixed 768-dim zero vector so tests never hit the embedding endpoint.
    """
    fake_vector = [0.0] * 768
    with patch(
        "app.services.ai_emb_service.AIEmbeddingService.generate_embedding",
        new=AsyncMock(return_value=fake_vector),
    ) as mock:
        yield mock


@pytest.fixture
def mock_tavily():
    """
    Patches AsyncTavilyClient.search so RAG tests never hit the internet.
    Returns two canned search snippets.
    """
    fake_results = {
        "results": [
            {"title": "Fake Article 1", "content": "Fusion energy breakthrough.", "url": "http://fake1.com"},
            {"title": "Fake Article 2", "content": "Scientists say progress.", "url": "http://fake2.com"},
        ]
    }
    with patch(
        "app.services.ai_text_service.AsyncTavilyClient",
    ) as MockTavily:
        instance = MockTavily.return_value
        instance.search = AsyncMock(return_value=fake_results)
        yield instance


# ---------------------------------------------------------------------------
# Fixtures: MongoDB mock collection
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_mongo_collection():
    """
    A fake Motor async MongoDB collection.
    Covers the subset of collection methods used by VoiceLibraryManager:
        find_one, find, insert_one, delete_one
    """
    collection = MagicMock()

    # find_one → async, returns a single document
    collection.find_one = AsyncMock(return_value=None)

    # insert_one → async
    collection.insert_one = AsyncMock(return_value=MagicMock(inserted_id="fake-id"))

    # delete_one → async, simulates found + deleted
    delete_result = MagicMock()
    delete_result.deleted_count = 1
    collection.delete_one = AsyncMock(return_value=delete_result)

    # find → returns a chainable cursor mock
    cursor = MagicMock()
    cursor.to_list = AsyncMock(return_value=[])
    collection.find = MagicMock(return_value=cursor)

    return collection


@pytest.fixture
def mock_r2():
    """
    Fake aioboto3 session + S3 client.
    Prevents any actual R2 / S3 calls in tests.
    """
    s3_client = AsyncMock()
    s3_client.put_object = AsyncMock()
    s3_client.delete_object = AsyncMock()

    # Simulate async context manager: `async with session.client(...) as s3`
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=s3_client)
    cm.__aexit__ = AsyncMock(return_value=False)

    session = MagicMock()
    session.client = MagicMock(return_value=cm)

    return session, s3_client


@pytest.fixture
def r2_config():
    return {
        "account_id": "test-account",
        "access_key": "test-key",
        "secret_key": "test-secret",
        "bucket": "test-bucket",
    }