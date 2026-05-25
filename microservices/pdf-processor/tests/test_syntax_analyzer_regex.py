"""SyntaxAnalyzer regex fallback (no spaCy model required)."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.services.character_discovery import Character, CharacterRegistry
from app.services.syntax_analyzer import SpeakerContext, SyntaxAnalyzer


@pytest.fixture
def registry() -> CharacterRegistry:
    return CharacterRegistry(
        characters=[
            Character("Alice", "female", "Protagonist", mentioned_count=50),
        ],
        alias_to_canonical={"alice": "Alice"},
        narrator_name="Narrator",
        pov="Third Person",
    )


def test_regex_speech_verb_after_quote(registry: CharacterRegistry):
    with patch("app.services.syntax_analyzer._get_nlp", return_value=None):
        sa = SyntaxAnalyzer()

    n0 = SimpleNamespace(uid=0, text="Intro line.", is_quote=False)
    q1 = SimpleNamespace(uid=1, text='\u201cHello.\u201d', is_quote=True, continuation_quote=False)
    n2 = SimpleNamespace(uid=2, text="Alice said nothing more.", is_quote=False)

    ctx = SpeakerContext()
    res = sa.analyze_quote(q1, [n0, q1, n2], registry, ctx)
    assert res.speaker_candidates == ["Alice"]
    assert res.confidence >= 0.5
    assert res.method == "speech_verb"


def test_continuation_uses_context_last_speaker(registry: CharacterRegistry):
    with patch("app.services.syntax_analyzer._get_nlp", return_value=None):
        sa = SyntaxAnalyzer()

    ctx = SpeakerContext()
    ctx.last_speakers = ["Bob"]

    q = SimpleNamespace(
        uid=5,
        text='"continued"',
        is_quote=True,
        continuation_quote=True,
    )
    res = sa.analyze_quote(q, [q], registry, ctx)
    assert res.method == "continuation"
    assert res.speaker_candidates == ["Bob"]
