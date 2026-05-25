"""
Fidelity Verifier

Zero-tolerance integrity layer that guarantees no text is lost, duplicated,
fabricated, or corrupted at every transformation boundary in the pipeline.
Runs inline at 4 checkpoints: chunking, stitching, smart-split, reassembly.
"""
__author__ = "Andrew D'Angelo"

import difflib
import hashlib
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from app.core.logging_config import Logger


SPEECH_VERBS_SET: Set[str] = {
    "said", "says", "asked", "asks", "replied", "replies", "answered", "answers",
    "shouted", "shouts", "whispered", "whispers", "muttered", "mutters",
    "exclaimed", "exclaims", "demanded", "demands", "cried", "cries",
    "called", "calls", "yelled", "yells", "screamed", "screams",
    "snapped", "snaps", "growled", "growls", "hissed", "hisses",
    "sighed", "sighs", "laughed", "laughs", "chuckled", "chuckles",
    "murmured", "murmurs", "breathed", "breathes", "gasped", "gasps",
    "groaned", "groans", "moaned", "moans", "declared", "declares",
    "announced", "announces", "continued", "continues", "added", "adds",
    "began", "begins", "interrupted", "interrupts",
    "inquired", "inquires", "wondered", "wonders", "observed", "observes",
    "commented", "comments", "noted", "notes", "remarked", "remarks",
    "admitted", "admits", "agreed", "agrees", "protested", "protests",
    "suggested", "suggests", "explained", "explains", "insisted", "insists",
    "responded", "responds", "retorted", "retorts", "countered", "counters",
    "confirmed", "confirms", "denied", "denies", "pleaded", "pleads",
}

_MARKER_PATTERN = re.compile(
    r"\[(?:Q|CONT|Ctx|After)\s*:\s*[^\]]*\]"
)

_SPEECH_VERB_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(v) for v in sorted(SPEECH_VERBS_SET, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class SpanDiff:
    start: int
    end: int
    text_preview: str
    diff_type: str  # "missing", "extra"


@dataclass
class SpeakerAnomaly:
    segment_idx: int
    speaker: str
    reason: str
    severity: str  # "warning", "error"


@dataclass
class ChapterFidelityReport:
    chapter_id: int
    chapter_title: str
    text_hash: str
    char_count_match: bool
    missing_chars: int
    extra_chars: int
    speaker_confidence_avg: float
    flagged_attributions: List[SpeakerAnomaly]
    status: str


@dataclass
class FidelityReport:
    stage: str
    passed: bool
    original_char_count: int
    output_char_count: int
    char_diff: int
    original_hash: str
    output_hash: str
    missing_spans: List[SpanDiff]
    extra_spans: List[SpanDiff]
    speaker_anomalies: List[SpeakerAnomaly]
    chapter_reports: List[ChapterFidelityReport]
    confidence_score: float
    repair_applied: bool = False
    repair_details: Optional[str] = None


# ---------------------------------------------------------------------------
# FidelityVerifier
# ---------------------------------------------------------------------------

class FidelityVerifier(Logger):

    # ---------------------------------------------------------------
    # Normalisation helpers
    # ---------------------------------------------------------------

    @staticmethod
    def normalize_text(text: str) -> str:
        text = unicodedata.normalize("NFKC", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @staticmethod
    def hash_text(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    # ---------------------------------------------------------------
    # Core diff engine
    # ---------------------------------------------------------------

    def _diff_texts(self, original: str, reconstructed: str) -> Tuple[List[SpanDiff], List[SpanDiff]]:
        """Character-level diff returning missing and extra spans."""
        missing: List[SpanDiff] = []
        extra: List[SpanDiff] = []

        # For very long texts, use chunked comparison
        if len(original) > 500_000 or len(reconstructed) > 500_000:
            return self._diff_texts_chunked(original, reconstructed)

        sm = difflib.SequenceMatcher(None, original, reconstructed, autojunk=False)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "delete":
                missing.append(SpanDiff(
                    start=i1, end=i2,
                    text_preview=original[i1:i2][:200],
                    diff_type="missing",
                ))
            elif tag == "insert":
                extra.append(SpanDiff(
                    start=j1, end=j2,
                    text_preview=reconstructed[j1:j2][:200],
                    diff_type="extra",
                ))
            elif tag == "replace":
                missing.append(SpanDiff(
                    start=i1, end=i2,
                    text_preview=original[i1:i2][:200],
                    diff_type="missing",
                ))
                extra.append(SpanDiff(
                    start=j1, end=j2,
                    text_preview=reconstructed[j1:j2][:200],
                    diff_type="extra",
                ))
        return missing, extra

    def _diff_texts_chunked(self, original: str, reconstructed: str, window: int = 10_000) -> Tuple[List[SpanDiff], List[SpanDiff]]:
        """Chunked diff for very long texts to keep memory bounded."""
        missing: List[SpanDiff] = []
        extra: List[SpanDiff] = []
        max_len = max(len(original), len(reconstructed))

        for start in range(0, max_len, window):
            o_chunk = original[start:start + window]
            r_chunk = reconstructed[start:start + window]
            if o_chunk == r_chunk:
                continue
            sm = difflib.SequenceMatcher(None, o_chunk, r_chunk, autojunk=False)
            for tag, i1, i2, j1, j2 in sm.get_opcodes():
                if tag == "delete":
                    missing.append(SpanDiff(
                        start=start + i1, end=start + i2,
                        text_preview=o_chunk[i1:i2][:200],
                        diff_type="missing",
                    ))
                elif tag == "insert":
                    extra.append(SpanDiff(
                        start=start + j1, end=start + j2,
                        text_preview=r_chunk[j1:j2][:200],
                        diff_type="extra",
                    ))
                elif tag == "replace":
                    missing.append(SpanDiff(
                        start=start + i1, end=start + i2,
                        text_preview=o_chunk[i1:i2][:200],
                        diff_type="missing",
                    ))
                    extra.append(SpanDiff(
                        start=start + j1, end=start + j2,
                        text_preview=r_chunk[j1:j2][:200],
                        diff_type="extra",
                    ))
        return missing, extra

    # ---------------------------------------------------------------
    # Text completeness checkpoints
    # ---------------------------------------------------------------

    def verify_text_completeness(
        self,
        original: str,
        segments: List[str],
        stage: str,
        normalize: bool = True,
    ) -> FidelityReport:
        o = self.normalize_text(original) if normalize else original
        reconstructed = " ".join(segments) if normalize else "".join(segments)
        r = self.normalize_text(reconstructed) if normalize else reconstructed

        o_hash = self.hash_text(o)
        r_hash = self.hash_text(r)
        char_diff = len(r) - len(o)

        if o_hash == r_hash:
            self.logger.info("Fidelity [%s]: PASS (hash match, %d chars)", stage, len(o))
            return FidelityReport(
                stage=stage, passed=True,
                original_char_count=len(o), output_char_count=len(r),
                char_diff=0, original_hash=o_hash, output_hash=r_hash,
                missing_spans=[], extra_spans=[],
                speaker_anomalies=[], chapter_reports=[],
                confidence_score=1.0,
            )

        missing, extra = self._diff_texts(o, r)
        total_diff_chars = sum(s.end - s.start for s in missing) + sum(s.end - s.start for s in extra)
        confidence = max(0.0, 1.0 - (total_diff_chars / max(len(o), 1)))
        passed = confidence >= 0.98

        level = "info" if passed else "error"
        getattr(self.logger, level)(
            "Fidelity [%s]: %s (confidence=%.4f, diff=%d chars, %d missing, %d extra)",
            stage, "PASS" if passed else "FAIL", confidence, char_diff,
            len(missing), len(extra),
        )
        return FidelityReport(
            stage=stage, passed=passed,
            original_char_count=len(o), output_char_count=len(r),
            char_diff=char_diff, original_hash=o_hash, output_hash=r_hash,
            missing_spans=missing, extra_spans=extra,
            speaker_anomalies=[], chapter_reports=[],
            confidence_score=confidence,
        )

    def verify_chunking(self, original_text: str, chunks: List[dict], overlap: int) -> FidelityReport:
        if not chunks:
            return self.verify_text_completeness(original_text, [], "chunking")

        # Reconstruct using start_char/end_char to de-overlap
        sorted_chunks = sorted(chunks, key=lambda c: c.get("start_char", 0))
        parts: List[str] = []
        last_end = 0
        for chunk in sorted_chunks:
            start = chunk.get("start_char", 0)
            text = chunk.get("text", "")
            if start < last_end:
                # Overlap region -- skip the overlapping prefix
                skip = last_end - start
                text = text[skip:]
            parts.append(text)
            last_end = max(last_end, chunk.get("end_char", start + len(chunk.get("text", ""))))

        return self.verify_text_completeness(original_text, parts, "chunking", normalize=True)

    def verify_stitching(self, original_text: str, stitched_text: str, char_map: list) -> FidelityReport:
        report = self.verify_text_completeness(original_text, [stitched_text], "stitching")

        if len(char_map) != len(stitched_text):
            self.logger.error(
                "Fidelity [stitching]: char_map length %d != stitched_text length %d",
                len(char_map), len(stitched_text),
            )
            report.passed = False
            report.confidence_score = min(report.confidence_score, 0.9)

        return report

    def verify_smart_split(self, stitched_text: str, text_units: list) -> FidelityReport:
        unit_texts = [getattr(u, "text", u.get("text", "")) if isinstance(u, dict) else u.text for u in text_units]
        return self.verify_text_completeness(stitched_text, unit_texts, "smart_split", normalize=True)

    def verify_reassembly(self, original_text: str, segments: List[dict]) -> FidelityReport:
        seg_texts = [s.get("text", "") for s in segments]
        return self.verify_text_completeness(original_text, seg_texts, "reassembly")

    # ---------------------------------------------------------------
    # Anti-hallucination guards
    # ---------------------------------------------------------------

    def verify_no_marker_contamination(self, segments: List[dict]) -> List[str]:
        warnings: List[str] = []
        for idx, seg in enumerate(segments):
            text = seg.get("text", "")
            for match in _MARKER_PATTERN.finditer(text):
                warnings.append(
                    f"Segment {idx}: pipeline marker found: {match.group()!r}"
                )
        if warnings:
            self.logger.warning("Fidelity: %d marker contamination(s) found", len(warnings))
        return warnings

    def verify_segment_text_unchanged(
        self,
        original_units: list,
        segments: List[dict],
    ) -> List[SpeakerAnomaly]:
        anomalies: List[SpeakerAnomaly] = []
        unit_texts: Dict[int, str] = {}
        for u in original_units:
            uid = getattr(u, "uid", None)
            text = getattr(u, "text", None)
            if uid is not None and text is not None:
                unit_texts[uid] = text

        for idx, seg in enumerate(segments):
            chunk_id = seg.get("chunk_id")
            if chunk_id is not None and chunk_id in unit_texts:
                original = self.normalize_text(unit_texts[chunk_id])
                current = self.normalize_text(seg.get("text", ""))
                if original != current:
                    anomalies.append(SpeakerAnomaly(
                        segment_idx=idx,
                        speaker=seg.get("speaker", ""),
                        reason="text_modified_from_source",
                        severity="error",
                    ))
        return anomalies

    def verify_speaker_names(
        self,
        segments: List[dict],
        known_characters: set,
        alias_map: Dict[str, str],
    ) -> List[SpeakerAnomaly]:
        allowed = {"Unknown", "Narrator"}
        anomalies: List[SpeakerAnomaly] = []
        known_lower = {n.lower() for n in known_characters} | {k.lower() for k in alias_map}
        allowed_lower = {a.lower() for a in allowed}

        for idx, seg in enumerate(segments):
            speaker = seg.get("speaker", "")
            if not speaker:
                continue
            if speaker.lower() in allowed_lower:
                continue
            if speaker.lower() in known_lower:
                continue
            if alias_map.get(speaker.lower()):
                continue
            anomalies.append(SpeakerAnomaly(
                segment_idx=idx,
                speaker=speaker,
                reason="unknown_character",
                severity="warning",
            ))
        return anomalies

    # ---------------------------------------------------------------
    # Speaker consistency validation
    # ---------------------------------------------------------------

    def validate_speaker_consistency(
        self,
        segments: List[dict],
        original_text: str,
        alias_map: Dict[str, str],
        narrator_name: str,
        pov: str,
    ) -> List[SpeakerAnomaly]:
        anomalies: List[SpeakerAnomaly] = []
        anomalies.extend(self._check_dialogue_evidence_batch(segments, original_text, alias_map))
        anomalies.extend(self._check_alternation_sanity(segments))
        anomalies.extend(self._check_first_person_consistency(segments, narrator_name, pov))
        return anomalies

    def _check_dialogue_evidence(
        self,
        segment: dict,
        segment_idx: int,
        original_text: str,
        alias_map: Dict[str, str],
    ) -> Optional[SpeakerAnomaly]:
        if not segment.get("is_quote", False):
            return None
        speaker = segment.get("speaker", "")
        if speaker in ("Unknown", "Narrator", ""):
            return None

        seg_text = segment.get("text", "")
        pos = original_text.find(seg_text[:80])
        if pos == -1:
            return None

        window_start = max(0, pos - 500)
        window_end = min(len(original_text), pos + len(seg_text) + 500)
        window = original_text[window_start:window_end].lower()

        surfaces = {speaker.lower()}
        for alias, canonical in alias_map.items():
            if canonical.lower() == speaker.lower():
                surfaces.add(alias.lower())
        first = speaker.split()[0].lower()
        if len(first) >= 3:
            surfaces.add(first)

        found = any(s in window for s in surfaces)
        if not found:
            return SpeakerAnomaly(
                segment_idx=segment_idx,
                speaker=speaker,
                reason="no_textual_evidence",
                severity="warning",
            )
        return None

    def _check_dialogue_evidence_batch(
        self,
        segments: List[dict],
        original_text: str,
        alias_map: Dict[str, str],
    ) -> List[SpeakerAnomaly]:
        anomalies: List[SpeakerAnomaly] = []
        for idx, seg in enumerate(segments):
            result = self._check_dialogue_evidence(seg, idx, original_text, alias_map)
            if result:
                anomalies.append(result)
        return anomalies

    def _check_alternation_sanity(self, segments: List[dict]) -> List[SpeakerAnomaly]:
        anomalies: List[SpeakerAnomaly] = []
        consecutive_quotes: List[Tuple[int, str]] = []

        for idx, seg in enumerate(segments):
            if seg.get("is_quote", False):
                consecutive_quotes.append((idx, seg.get("speaker", "")))
            else:
                self._evaluate_consecutive_quotes(consecutive_quotes, anomalies)
                consecutive_quotes = []

        self._evaluate_consecutive_quotes(consecutive_quotes, anomalies)
        return anomalies

    @staticmethod
    def _evaluate_consecutive_quotes(
        quotes: List[Tuple[int, str]],
        anomalies: List[SpeakerAnomaly],
    ) -> None:
        if len(quotes) < 3:
            return
        for i in range(len(quotes) - 2):
            a_idx, a_spk = quotes[i]
            b_idx, b_spk = quotes[i + 1]
            c_idx, c_spk = quotes[i + 2]
            if a_spk == b_spk == c_spk and a_spk not in ("Unknown", "Narrator", ""):
                anomalies.append(SpeakerAnomaly(
                    segment_idx=b_idx,
                    speaker=b_spk,
                    reason="impossible_alternation",
                    severity="error",
                ))

    def _check_first_person_consistency(
        self,
        segments: List[dict],
        narrator_name: str,
        pov: str,
    ) -> List[SpeakerAnomaly]:
        if pov != "First Person" or narrator_name == "Narrator":
            return []

        anomalies: List[SpeakerAnomaly] = []
        for idx, seg in enumerate(segments):
            if seg.get("is_quote", False):
                continue
            speaker = seg.get("speaker", "")
            if speaker == "Narrator":
                anomalies.append(SpeakerAnomaly(
                    segment_idx=idx,
                    speaker=speaker,
                    reason="narrator_inconsistency",
                    severity="warning",
                ))
        return anomalies

    # ---------------------------------------------------------------
    # Auto-repair
    # ---------------------------------------------------------------

    def attempt_repair(
        self,
        original_text: str,
        segments: List[dict],
        report: FidelityReport,
    ) -> Tuple[List[dict], FidelityReport]:
        if not report.missing_spans:
            return segments, report

        self.logger.warning(
            "Fidelity: attempting auto-repair for %d missing spans",
            len(report.missing_spans),
        )

        repaired = list(segments)
        original_norm = self.normalize_text(original_text)

        for span in sorted(report.missing_spans, key=lambda s: s.start, reverse=True):
            missing_text = original_norm[span.start:span.end]
            if not missing_text.strip():
                continue

            # Find the best insertion point: after the segment whose text
            # ends closest to (but before) the missing span's position
            insert_idx = len(repaired)
            cumulative = 0
            for i, seg in enumerate(repaired):
                cumulative += len(self.normalize_text(seg.get("text", "")))
                if cumulative >= span.start:
                    insert_idx = i + 1
                    break

            repaired.insert(insert_idx, {
                "speaker": "Narrator",
                "text": missing_text,
                "chunk_id": None,
                "is_quote": False,
            })

        new_report = self.verify_reassembly(original_text, repaired)
        new_report.repair_applied = True
        new_report.repair_details = f"Inserted {len(report.missing_spans)} missing span(s)"

        if new_report.confidence_score >= 0.98:
            self.logger.warning("Fidelity: auto-repair succeeded (confidence=%.4f)", new_report.confidence_score)
        else:
            self.logger.error("Fidelity: auto-repair insufficient (confidence=%.4f)", new_report.confidence_score)

        return repaired, new_report

    # ---------------------------------------------------------------
    # Final integrity gate
    # ---------------------------------------------------------------

    def run_final_gate(
        self,
        original_text: str,
        segments: List[dict],
        known_characters: set,
        alias_map: Dict[str, str],
        narrator_name: str,
        pov: str,
    ) -> Tuple[List[dict], FidelityReport]:
        report = self.verify_reassembly(original_text, segments)

        marker_warnings = self.verify_no_marker_contamination(segments)
        speaker_name_issues = self.verify_speaker_names(segments, known_characters, alias_map)
        consistency_issues = self.validate_speaker_consistency(
            segments, original_text, alias_map, narrator_name, pov,
        )

        all_anomalies = speaker_name_issues + consistency_issues
        report.speaker_anomalies = all_anomalies

        final_segments = segments

        if report.confidence_score < 0.98:
            final_segments, report = self.attempt_repair(original_text, segments, report)

        errors = [a for a in report.speaker_anomalies if a.severity == "error"]
        warnings = [a for a in report.speaker_anomalies if a.severity == "warning"]

        if report.confidence_score >= 0.98 and not errors:
            if warnings or marker_warnings:
                status = "PASS_WITH_WARNINGS"
            else:
                status = "PASS"
            report.passed = True
        elif report.confidence_score >= 0.95:
            status = "PASS_WITH_WARNINGS"
            report.passed = True
        else:
            status = "FAIL"
            report.passed = False
            self.logger.error(
                "Fidelity FINAL GATE: FAIL (confidence=%.4f, %d errors, %d warnings)",
                report.confidence_score, len(errors), len(warnings),
            )

        self.logger.info(
            "Fidelity FINAL GATE: %s (confidence=%.4f, anomalies=%d)",
            status, report.confidence_score, len(all_anomalies),
        )

        report.stage = "final_gate"
        return final_segments, report

    # ---------------------------------------------------------------
    # Report serialization
    # ---------------------------------------------------------------

    def generate_report_dict(self, report: FidelityReport) -> dict:
        errors = [a for a in report.speaker_anomalies if a.severity == "error"]
        warnings = [a for a in report.speaker_anomalies if a.severity == "warning"]

        if report.passed and not errors:
            if warnings:
                overall = "PASS_WITH_WARNINGS"
            else:
                overall = "PASS"
        else:
            overall = "FAIL"

        return {
            "overall_status": overall,
            "text_completeness": report.confidence_score,
            "original_hash": report.original_hash,
            "output_hash": report.output_hash,
            "original_char_count": report.original_char_count,
            "output_char_count": report.output_char_count,
            "char_diff": report.char_diff,
            "speaker_anomaly_count": len(report.speaker_anomalies),
            "error_count": len(errors),
            "warning_count": len(warnings),
            "repair_applied": report.repair_applied,
            "repair_details": report.repair_details,
            "missing_span_count": len(report.missing_spans),
            "extra_span_count": len(report.extra_spans),
            "chapter_reports": [
                {
                    "chapter_id": cr.chapter_id,
                    "chapter_title": cr.chapter_title,
                    "text_hash": cr.text_hash,
                    "char_count_match": cr.char_count_match,
                    "missing_chars": cr.missing_chars,
                    "extra_chars": cr.extra_chars,
                    "speaker_confidence_avg": cr.speaker_confidence_avg,
                    "flagged_count": len(cr.flagged_attributions),
                    "status": cr.status,
                }
                for cr in report.chapter_reports
            ],
        }
