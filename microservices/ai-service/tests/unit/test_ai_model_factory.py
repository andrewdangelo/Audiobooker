"""
Unit Tests — ModelFactory
==========================
Tests the routing/resolution logic in ModelFactory without ever hitting a
real endpoint. The factory's job is:

  1. Given a preset/provider/task, pick the right endpoint config
  2. Build the right client type (AsyncOpenAI, HFEmbeddingClient, etc.)
  3. In dev mode: use the preset registry shortcut
  4. In prod mode: hit the live deployment list

We test (1) and (3) heavily because that logic lives entirely in your code.
(2) and (4) are thin wrappers around third-party clients — less valuable to
unit-test since you'd just be asserting that AsyncOpenAI() was called.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# ModelProvider / ModelTask enum parsing
# ---------------------------------------------------------------------------

class TestModelProviderEnum:
    """
    The enums support shorthand aliases ("cf", "hf").
    If that mapping breaks, every request using shorthand strings would fail.
    """

    def test_cf_lowercase_resolves(self):
        from app.services.ai_model_factory import ModelProvider
        assert ModelProvider("cf") == ModelProvider.CF

    def test_hf_uppercase_resolves(self):
        from app.services.ai_model_factory import ModelProvider
        assert ModelProvider("HF") == ModelProvider.HF

    def test_unknown_value_returns_none(self):
        from app.services.ai_model_factory import ModelProvider
        assert ModelProvider._missing_("garbage") is None


class TestModelTaskEnum:
    def test_text_generation_hf_alias(self):
        from app.services.ai_model_factory import ModelTask
        assert ModelTask("text-generation") == ModelTask.TXT

    def test_sentence_similarity_hf_alias(self):
        from app.services.ai_model_factory import ModelTask
        assert ModelTask("sentence-similarity") == ModelTask.EMB

    def test_try_parse_valid(self):
        from app.services.ai_model_factory import ModelTask
        assert ModelTask.try_parse("txt") == ModelTask.TXT

    def test_try_parse_invalid_returns_none(self):
        from app.services.ai_model_factory import ModelTask
        assert ModelTask.try_parse("not-a-task") is None


# ---------------------------------------------------------------------------
# _PresetRegistry
# ---------------------------------------------------------------------------

class TestPresetRegistry:
    """
    Tests the registry that wraps ai_defaults.json.
    Uses the real file (it's static data) — this is an appropriate exception
    to the "no real dependencies" rule because the JSON is checked into the
    repo and never changes at runtime.
    """

    @pytest.fixture
    def registry(self):
        import os
        from app.services.ai_model_factory import _PresetRegistry
        json_path = os.path.join(
            os.path.dirname(__file__), "..", "app", "data", "ai_defaults.json"
        )
        return _PresetRegistry(json_path)

    def test_chat_basic_preset_exists(self, registry):
        assert registry.get("chat-basic") is not None

    def test_embedding_preset_exists(self, registry):
        assert registry.get("embedding-768") is not None

    def test_unknown_preset_returns_none(self, registry):
        assert registry.get("this-does-not-exist") is None

    def test_entry_has_correct_provider(self, registry):
        from app.services.ai_model_factory import ModelProvider
        entry = registry.get("chat-basic")
        assert entry.provider == ModelProvider.CF

    def test_entry_has_deployment_name(self, registry):
        entry = registry.get("chat-basic")
        assert entry.deployment_name  # non-empty string

    def test_values_for_provider_filters_correctly(self, registry):
        from app.services.ai_model_factory import ModelProvider
        cf_entries = registry.values_for_provider(ModelProvider.CF)
        assert all(e.provider == ModelProvider.CF for e in cf_entries)
        assert len(cf_entries) > 0

    def test_contains_operator(self, registry):
        assert "chat-basic" in registry
        assert "nonexistent" not in registry


# ---------------------------------------------------------------------------
# _choose_valid_deployment
# ---------------------------------------------------------------------------

class TestChooseValidDeployment:
    """
    This static method contains non-trivial selection logic with three
    fallback levels. Each level gets its own test.
    """

    def _make_entry(self, name, task_str, repository=None):
        """Helper to build a minimal fake endpoint object."""
        entry = MagicMock()
        entry.name = name
        entry.task = task_str
        entry.repository = repository or name
        return entry

    def test_exact_deployment_name_wins(self):
        from app.services.ai_model_factory import ModelFactory, ModelTask
        entries = {
            "model-a": self._make_entry("model-a", "txt"),
            "model-b": self._make_entry("model-b", "txt"),
        }
        result = ModelFactory._choose_valid_deployment(entries, ModelTask.TXT, deployment_name="model-a")
        assert result.name == "model-a"

    def test_repository_match_as_fallback(self):
        from app.services.ai_model_factory import ModelFactory, ModelTask
        entries = {
            "ep-1": self._make_entry("ep-1", "txt", repository="gpt-4"),
        }
        result = ModelFactory._choose_valid_deployment(entries, ModelTask.TXT, model_name="gpt-4")
        assert result.name == "ep-1"

    def test_raises_when_no_deployments_for_task(self):
        from app.services.ai_model_factory import ModelFactory, ModelTask
        entries = {
            "emb-1": self._make_entry("emb-1", "emb"),
        }
        with pytest.raises(ValueError, match="No valid deployments"):
            ModelFactory._choose_valid_deployment(entries, ModelTask.TXT)

    def test_raises_when_name_not_found(self):
        from app.services.ai_model_factory import ModelFactory, ModelTask
        entries = {
            "model-a": self._make_entry("model-a", "txt"),
        }
        with pytest.raises(ValueError, match="No valid deployments"):
            ModelFactory._choose_valid_deployment(
                entries, ModelTask.TXT, deployment_name="model-that-does-not-exist"
            )

    def test_task_filtering_excludes_wrong_task(self):
        """
        An embedding model should never be returned for a TXT task,
        even if it's the only model in the list.
        """
        from app.services.ai_model_factory import ModelFactory, ModelTask
        entries = {
            "emb-only": self._make_entry("emb-only", "emb"),
        }
        with pytest.raises(ValueError):
            ModelFactory._choose_valid_deployment(entries, ModelTask.TXT)


# ---------------------------------------------------------------------------
# ModelFactory._resolve_endpoint  (dev mode preset shortcut)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestResolveEndpointDevMode:

    async def test_dev_mode_returns_preset_without_network_call(self):
        """
        In dev mode with a valid preset, _resolve_endpoint must return
        immediately from the registry and never call _get_deployments.
        """
        from app.services.ai_model_factory import ModelFactory, ModelProvider, ModelTask

        with patch("app.services.ai_model_factory._is_dev", return_value=True):
            with patch.object(
                ModelFactory, "_get_deployments_and_pick", new=AsyncMock()
            ) as mock_live:
                result = await ModelFactory._resolve_endpoint(
                    provider=ModelProvider.CF,
                    model_task=ModelTask.TXT,
                    deployment_name=None,
                    model_name=None,
                    preset="chat-basic",
                )

        # Live lookup was never called
        mock_live.assert_not_called()
        assert result.name == "chat-basic"

    async def test_dev_mode_raises_on_unknown_preset(self):
        from app.services.ai_model_factory import ModelFactory, ModelProvider, ModelTask

        with patch("app.services.ai_model_factory._is_dev", return_value=True):
            with pytest.raises(ValueError, match="not found in ai_defaults.json"):
                await ModelFactory._resolve_endpoint(
                    provider=ModelProvider.CF,
                    model_task=ModelTask.TXT,
                    deployment_name=None,
                    model_name=None,
                    preset="this-preset-does-not-exist",
                )

    async def test_dev_mode_raises_on_provider_mismatch(self):
        """
        If a preset belongs to CF but HF is requested, raise clearly.
        Silent provider confusion would lead to wrong credentials being used.
        """
        from app.services.ai_model_factory import ModelFactory, ModelProvider, ModelTask

        with patch("app.services.ai_model_factory._is_dev", return_value=True):
            with pytest.raises(ValueError, match="provider"):
                await ModelFactory._resolve_endpoint(
                    provider=ModelProvider.HF,   # wrong provider for a CF preset
                    model_task=ModelTask.TXT,
                    deployment_name=None,
                    model_name=None,
                    preset="chat-basic",          # chat-basic is CF
                )

    async def test_prod_mode_ignores_preset_and_hits_live(self):
        """
        In production, preset is ignored and _get_deployments_and_pick is used.
        """
        from app.services.ai_model_factory import ModelFactory, ModelProvider, ModelTask

        fake_entry = MagicMock()
        fake_entry.name = "live-deployment"

        with patch("app.services.ai_model_factory._is_dev", return_value=False):
            with patch.object(
                ModelFactory, "_get_deployments_and_pick", new=AsyncMock(return_value=fake_entry)
            ) as mock_live:
                result = await ModelFactory._resolve_endpoint(
                    provider=ModelProvider.CF,
                    model_task=ModelTask.TXT,
                    deployment_name="live-deployment",
                    model_name=None,
                    preset="chat-basic",  # should be ignored in prod
                )

        mock_live.assert_called_once()
        assert result.name == "live-deployment"