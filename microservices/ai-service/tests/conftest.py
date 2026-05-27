"""
conftest.py — Shared pytest fixtures
=====================================
pytest automatically loads this file for every test in the directory.
Fixtures and helpers defined here are available to ALL test files without
importing.

Key decisions:
  - Settings are mocked at import time via a module-level patch so tests
    never depend on a real .env file existing. This makes the suite runnable
    in CI, on a colleague's machine, or anywhere without credentials.
  - All external I/O (Cloudflare, MongoDB, R2, Tavily) is mocked so unit
    tests cost $0 and run in milliseconds.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from types import SimpleNamespace


# ---------------------------------------------------------------------------
# Settings mock — must happen before any app.* import
#
# settings = Settings() runs at module level in config_settings.py, which
# means the moment any test imports anything from app/, Pydantic tries to
# load your .env file and validate every required field. If the file is
# missing (CI, fresh clone, colleague's machine) the entire test suite
# crashes before a single test runs.
#
# We intercept it here by patching the Settings class to return a
# SimpleNamespace with fake-but-valid values for every field the app code
# actually reads during tests.
# ---------------------------------------------------------------------------

FAKE_SETTINGS = SimpleNamespace(
    ENVIRONMENT="development",
    PORT=8002,
    LOG_LEVEL="INFO",
    DEBUG=True,
    TEST_VERSION="test",
    API_V1_PREFIX="/api/v1",
    MONGODB_URL="mongodb://fake:27017",
    R2_ACCOUNT_ID="fake-r2-account",
    R2_ACCESS_KEY_ID="fake-r2-key",
    R2_SECRET_ACCESS_KEY="fake-r2-secret",
    R2_BUCKET_NAME="fake-bucket",
    R2_ENDPOINT_URL=None,
    CORS_ORIGINS=["http://localhost:3000"],
    REDIS_HOST="localhost",
    REDIS_PORT=6379,
    REDIS_DB=0,
    REDIS_PASSWORD=None,
    DEFAULT_CHUNK_SIZE=1000,
    DEFAULT_CHUNK_OVERLAP=200,
    MAX_FILE_SIZE_MB=100,
    ENABLE_LLM_CHUNKING=True,
    HF_ENDPOINT_URL="https://fake-hf-endpoint.example.com",
    HF_TOKEN="fake-hf-token",
    HF_WRITE_TOKEN="fake-hf-write-token",
    HF_NAMESPACE="fake-namespace",
    LLM_SERVERLESS=True,
    LLM_MODEL="fake/model",
    LLM_CONCURRENCY=10,
    LLM_MAX_CHARS_PER_WINDOW=20000,
    LLM_DISCOVERY_CHARS=17000,
    LLM_DELAY_BETWEEN_REQUESTS=2.0,
    LLM_ENDPOINT_NAME="fake-endpoint-001",
    TTS_CONCURRENCY=1,
    MATT_CF_ACCOUNT_ID="fake-cf-account",
    MATT_CF_AI_TOKEN="fake-cf-token",
    TAVILY_API_KEY="fake-tavily-key",
    # Properties
    is_production=False,
    is_development=True,
)

# Patch at module level — this runs once when conftest is loaded, before
# any test file imports app code.
patch("app.core.config_settings.Settings", return_value=FAKE_SETTINGS).start()
patch("app.core.config_settings.settings", FAKE_SETTINGS).start()


# ---------------------------------------------------------------------------
# Reusable fake LLM response builders
# ---------------------------------------------------------------------------

def make_openai_response(content: str) -> MagicMock:
    """
    Builds a fake openai ChatCompletion response object.
    Mirrors the shape the code actually accesses:
        response.choices[0].message.content
    """
    message = MagicMock()
    message.content = content

    choice = MagicMock()
    choice.message = message
    choice.delta = message  # used in streaming

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
    Patches AsyncTavilyClient so RAG tests never hit the internet.
    Returns two canned search snippets that match the shape _fetch_web_snippets
    expects from Tavily's response.
    """
    fake_results = {
        "results": [
            {
                "title": "Fake Article 1",
                "content": "Fusion energy breakthrough.",
                "url": "http://fake1.com",
            },
            {
                "title": "Fake Article 2",
                "content": "Scientists say progress.",
                "url": "http://fake2.com",
            },
        ]
    }
    with patch("app.services.ai_text_service.AsyncTavilyClient") as MockTavily:
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

    collection.find_one = AsyncMock(return_value=None)
    collection.insert_one = AsyncMock(return_value=MagicMock(inserted_id="fake-id"))

    delete_result = MagicMock()
    delete_result.deleted_count = 1
    collection.delete_one = AsyncMock(return_value=delete_result)

    cursor = MagicMock()
    cursor.to_list = AsyncMock(return_value=[])
    collection.find = MagicMock(return_value=cursor)

    return collection


# ---------------------------------------------------------------------------
# Fixtures: R2 / S3 mock
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_r2():
    """
    Fake aioboto3 session + S3 client.
    Prevents any actual R2 / S3 calls in tests.
    """
    s3_client = AsyncMock()
    s3_client.put_object = AsyncMock()
    s3_client.delete_object = AsyncMock()
    s3_client.get_object = AsyncMock()

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