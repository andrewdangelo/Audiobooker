"""Unit tests for FidelityVerifier (text completeness, chunk de-overlap, final gate)."""

import pytest

from app.services.fidelity_verifier import FidelityVerifier


@pytest.fixture
def fv() -> FidelityVerifier:
    return FidelityVerifier()


def test_normalize_text_collapses_whitespace(fv: FidelityVerifier):
    assert fv.normalize_text("  a\n\nb\tc  ") == "a b c"


def test_hash_text_stable(fv: FidelityVerifier):
    h1 = fv.hash_text("same")
    h2 = fv.hash_text("same")
    assert h1 == h2 and len(h1) == 64


def test_verify_text_completeness_pass_identical(fv: FidelityVerifier):
    r = fv.verify_text_completeness("one two", ["one two"], "unit")
    assert r.passed is True
    assert r.confidence_score == 1.0
    assert r.missing_spans == []


def test_verify_chunking_single_chunk_round_trip(fv: FidelityVerifier):
    original = "abcdefghij"
    chunks = [{"text": original, "start_char": 0, "end_char": len(original)}]
    r = fv.verify_chunking(original, chunks, overlap=200)
    assert r.passed is True
    assert r.confidence_score == 1.0


def test_verify_no_marker_contamination_detects_q_tag(fv: FidelityVerifier):
    segs = [{"text": 'He spoke. [Q: 0] "Hi."', "speaker": "Narrator"}]
    w = fv.verify_no_marker_contamination(segs)
    assert len(w) == 1
    assert "pipeline marker" in w[0].lower()


def test_verify_speaker_names_unknown_warning(fv: FidelityVerifier):
    segs = [{"speaker": "TotallyUnknownPerson", "text": "x"}]
    issues = fv.verify_speaker_names(segs, {"Narrator"}, {})
    assert len(issues) == 1
    assert issues[0].reason == "unknown_character"


def test_run_final_gate_pass_clean_text(fv: FidelityVerifier):
    original = "The cat sat."
    segments = [
        {"speaker": "Narrator", "text": "The ", "is_quote": False},
        {"speaker": "Narrator", "text": "cat sat.", "is_quote": False},
    ]
    out, report = fv.run_final_gate(
        original_text=original,
        segments=list(segments),
        known_characters={"Narrator"},
        alias_map={},
        narrator_name="Narrator",
        pov="Third Person",
    )
    assert report.passed is True
    assert report.confidence_score >= 0.98
    d = fv.generate_report_dict(report)
    assert d["overall_status"] in ("PASS", "PASS_WITH_WARNINGS")


def test_alternation_sanity_flags_three_same_speaker_quotes(fv: FidelityVerifier):
    segs = [
        {"speaker": "Bob", "text": '"a"', "is_quote": True},
        {"speaker": "Bob", "text": '"b"', "is_quote": True},
        {"speaker": "Bob", "text": '"c"', "is_quote": True},
    ]
    anomalies = fv._check_alternation_sanity(segs)
    assert any(a.reason == "impossible_alternation" for a in anomalies)
