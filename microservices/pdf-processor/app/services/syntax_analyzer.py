"""
Syntax Analyzer

spaCy-based dependency parsing for dialogue tag analysis.
Determines who is speaking by analyzing English syntax: subjects of speech
verbs, passive voice agents, action beats, pronouns, and alternation patterns.
"""
__author__ = "Andrew D'Angelo"

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from app.core.logging_config import Logger


# ---------------------------------------------------------------------------
# Speech verb set (lemmatized for spaCy lookup)
# ---------------------------------------------------------------------------

SPEECH_VERB_LEMMAS: Set[str] = {
    "say", "ask", "reply", "answer", "shout", "whisper", "mutter",
    "exclaim", "demand", "cry", "call", "yell", "scream",
    "snap", "growl", "hiss", "sigh", "laugh", "chuckle",
    "murmur", "breathe", "gasp", "groan", "moan", "declare",
    "announce", "continue", "add", "begin", "interrupt",
    "inquire", "wonder", "observe", "comment", "note", "remark",
    "admit", "agree", "protest", "suggest", "explain", "insist",
    "respond", "retort", "counter", "confirm", "deny", "plead",
}

# Surface forms for regex-based fallback
SPEECH_VERBS_PATTERN = re.compile(
    r"\b(said|says|asked|asks|replied|replies|answered|answers|"
    r"shouted|shouts|whispered|whispers|muttered|mutters|"
    r"exclaimed|exclaims|demanded|demands|cried|cries|"
    r"called|calls|yelled|yells|screamed|screams|"
    r"snapped|snaps|growled|growls|hissed|hisses|"
    r"sighed|sighs|laughed|laughs|chuckled|chuckles|"
    r"murmured|murmurs|breathed|breathes|gasped|gasps|"
    r"groaned|groans|moaned|moans|declared|declares|"
    r"announced|announces|continued|continues|added|adds|"
    r"began|begins|interrupted|interrupts|"
    r"inquired|inquires|wondered|wonders|observed|observes|"
    r"commented|comments|noted|notes|remarked|remarks|"
    r"admitted|admits|agreed|agrees|protested|protests|"
    r"suggested|suggests|explained|explains|insisted|insists|"
    r"responded|responds|retorted|retorts|countered|counters|"
    r"confirmed|confirms|denied|denies|pleaded|pleads)\b",
    re.IGNORECASE,
)


# Module-level spaCy singleton
_nlp = None


def _get_nlp():
    global _nlp
    if _nlp is not None:
        return _nlp
    try:
        import spacy
        _nlp = spacy.load("en_core_web_md", disable=["lemmatizer", "textcat"])
        return _nlp
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class DialogueTagAnalysis:
    speaker_candidates: List[str]
    speech_verb: Optional[str] = None
    tag_position: Optional[str] = None
    voice: str = "none"
    is_addressee_pattern: bool = False
    addressee: Optional[str] = None
    confidence: float = 0.0
    method: str = "none"


@dataclass
class SpeakerContext:
    last_speakers: List[str] = field(default_factory=list)
    active_participants: Set[str] = field(default_factory=set)
    last_named_male: Optional[str] = None
    last_named_female: Optional[str] = None
    chapter_id: Optional[int] = None

    def reset_for_new_chapter(self):
        self.last_speakers.clear()
        self.active_participants.clear()
        self.last_named_male = None
        self.last_named_female = None

    def update_after_attribution(self, speaker: str, gender: str):
        self.last_speakers.insert(0, speaker)
        if len(self.last_speakers) > 10:
            self.last_speakers.pop()
        self.active_participants.add(speaker)
        if gender == "male":
            self.last_named_male = speaker
        elif gender == "female":
            self.last_named_female = speaker

    def update_from_narration(self, narration_text: str, alias_map: Dict[str, str], character_genders: Dict[str, str]):
        narration_lower = narration_text.lower()
        for name_lower, canonical in alias_map.items():
            if len(name_lower) >= 3 and name_lower in narration_lower:
                self.active_participants.add(canonical)
                gender = character_genders.get(canonical)
                if gender == "male":
                    self.last_named_male = canonical
                elif gender == "female":
                    self.last_named_female = canonical


# ---------------------------------------------------------------------------
# SyntaxAnalyzer
# ---------------------------------------------------------------------------

class SyntaxAnalyzer(Logger):

    def __init__(self):
        self._nlp = _get_nlp()
        if self._nlp is None:
            self.logger.warning("spaCy model not available; syntax analysis will use regex fallback only")

    def analyze_quote(
        self,
        quote_unit,
        surrounding_units: List,
        character_registry,
        context: SpeakerContext,
    ) -> DialogueTagAnalysis:
        alias_map = character_registry.alias_to_canonical
        char_genders = self._build_character_genders(character_registry)

        # Continuation quotes: same speaker as previous
        cont = self._check_continuation(quote_unit, context)
        if cont:
            return cont

        before_narr, after_narr = self._extract_surrounding_narration(quote_unit, surrounding_units)

        # Check for addressee pattern in the quote text
        addressee = self._detect_addressee(quote_unit.text, alias_map)

        # Try spaCy-based analysis if available
        if self._nlp and (before_narr.strip() or after_narr.strip()):
            result = self._spacy_analyze(before_narr, after_narr, quote_unit.text, alias_map, addressee)
            if result and result.confidence >= 0.5:
                return result

        # Regex fallback for speech verb patterns
        regex_result = self._regex_speech_verb(before_narr, after_narr, alias_map)
        if regex_result and regex_result.confidence >= 0.5:
            if addressee:
                regex_result.is_addressee_pattern = True
                regex_result.addressee = addressee
            return regex_result

        # Action beat: named subject in adjacent narration
        action = self._find_action_beat_regex(before_narr, after_narr, alias_map)
        if action:
            if addressee:
                action.is_addressee_pattern = True
                action.addressee = addressee
            return action

        # Pronoun resolution
        pronoun_result = self._try_pronoun_from_narration(before_narr + " " + after_narr, context, char_genders)
        if pronoun_result:
            if addressee:
                pronoun_result.is_addressee_pattern = True
                pronoun_result.addressee = addressee
            return pronoun_result

        # Alternation heuristic
        alt = self._check_alternation(context)
        if alt:
            if addressee:
                alt.is_addressee_pattern = True
                alt.addressee = addressee
            return alt

        return DialogueTagAnalysis(
            speaker_candidates=[],
            confidence=0.0,
            method="none",
            is_addressee_pattern=bool(addressee),
            addressee=addressee,
        )

    # ---------------------------------------------------------------
    # spaCy-based analysis
    # ---------------------------------------------------------------

    def _spacy_analyze(
        self,
        before_narr: str,
        after_narr: str,
        quote_text: str,
        alias_map: Dict[str, str],
        addressee: Optional[str],
    ) -> Optional[DialogueTagAnalysis]:
        # Parse narration after the quote first (dialogue tags more commonly follow)
        for narr_text, position in [(after_narr, "after_quote"), (before_narr, "before_quote")]:
            if not narr_text.strip():
                continue
            doc = self._nlp(narr_text)
            result = self._find_speech_verb_in_doc(doc, alias_map, position)
            if result:
                if addressee:
                    result.is_addressee_pattern = True
                    result.addressee = addressee
                return result

        # Try action beat with spaCy
        for narr_text, position in [(after_narr, "after_quote"), (before_narr, "before_quote")]:
            if not narr_text.strip():
                continue
            doc = self._nlp(narr_text)
            result = self._find_action_beat_in_doc(doc, alias_map, position)
            if result:
                if addressee:
                    result.is_addressee_pattern = True
                    result.addressee = addressee
                return result

        return None

    def _find_speech_verb_in_doc(
        self, doc, alias_map: Dict[str, str], position: str,
    ) -> Optional[DialogueTagAnalysis]:
        for token in doc:
            if token.lemma_.lower() not in SPEECH_VERB_LEMMAS:
                continue

            # Active voice: look for nsubj
            for child in token.children:
                if child.dep_ in ("nsubj", "nsubjpass"):
                    speaker = self._resolve_token_to_character(child, doc, alias_map)
                    if speaker:
                        is_passive = child.dep_ == "nsubjpass"
                        return DialogueTagAnalysis(
                            speaker_candidates=[speaker],
                            speech_verb=token.text,
                            tag_position=position,
                            voice="passive" if is_passive else "active",
                            confidence=0.92 if not is_passive else 0.88,
                            method="speech_verb",
                        )

            # Passive voice: look for agent (pobj of "by")
            for child in token.children:
                if child.dep_ == "agent":
                    for grandchild in child.children:
                        if grandchild.dep_ == "pobj":
                            speaker = self._resolve_token_to_character(grandchild, doc, alias_map)
                            if speaker:
                                return DialogueTagAnalysis(
                                    speaker_candidates=[speaker],
                                    speech_verb=token.text,
                                    tag_position=position,
                                    voice="passive",
                                    confidence=0.85,
                                    method="speech_verb",
                                )

        return None

    def _find_action_beat_in_doc(
        self, doc, alias_map: Dict[str, str], position: str,
    ) -> Optional[DialogueTagAnalysis]:
        # Find the root verb and its subject
        for token in doc:
            if token.dep_ == "ROOT" and token.pos_ == "VERB":
                for child in token.children:
                    if child.dep_ == "nsubj":
                        speaker = self._resolve_token_to_character(child, doc, alias_map)
                        if speaker:
                            return DialogueTagAnalysis(
                                speaker_candidates=[speaker],
                                speech_verb=None,
                                tag_position="action_beat",
                                voice="active",
                                confidence=0.55,
                                method="action_beat",
                            )
        return None

    def _resolve_token_to_character(
        self, token, doc, alias_map: Dict[str, str],
    ) -> Optional[str]:
        # Try the full entity span first
        if token.ent_type_ == "PERSON":
            # Get the full entity text
            for ent in doc.ents:
                if ent.start <= token.i < ent.end:
                    canonical = alias_map.get(ent.text.lower())
                    if canonical:
                        return canonical
                    canonical = alias_map.get(ent.text.split()[0].lower())
                    if canonical:
                        return canonical

        # Try token text directly
        canonical = alias_map.get(token.text.lower())
        if canonical:
            return canonical

        # Try compound name (token + next token)
        if token.i + 1 < len(doc):
            compound = f"{token.text} {doc[token.i + 1].text}"
            canonical = alias_map.get(compound.lower())
            if canonical:
                return canonical

        # Check if it's a pronoun we can't resolve here
        if token.pos_ == "PRON":
            return None

        return None

    # ---------------------------------------------------------------
    # Regex fallback
    # ---------------------------------------------------------------

    def _regex_speech_verb(
        self,
        before_narr: str,
        after_narr: str,
        alias_map: Dict[str, str],
    ) -> Optional[DialogueTagAnalysis]:
        sorted_names = sorted(alias_map.keys(), key=len, reverse=True)
        if not sorted_names:
            return None
        name_pattern = "|".join(re.escape(n) for n in sorted_names if len(n) >= 2)
        if not name_pattern:
            return None

        # "Name said" or "said Name" patterns
        pattern = re.compile(
            rf"(?:\b({name_pattern})\b\s+({SPEECH_VERBS_PATTERN.pattern[2:-2]})\b"
            rf"|({SPEECH_VERBS_PATTERN.pattern[2:-2]})\b\s+\b({name_pattern})\b)",
            re.IGNORECASE,
        )

        # Check after narration first
        for text, position in [(after_narr, "after_quote"), (before_narr, "before_quote")]:
            match = pattern.search(text)
            if match:
                name_raw = (match.group(1) or match.group(4) or "").strip()
                verb = (match.group(2) or match.group(3) or "").strip()
                canonical = alias_map.get(name_raw.lower())
                if canonical:
                    return DialogueTagAnalysis(
                        speaker_candidates=[canonical],
                        speech_verb=verb,
                        tag_position=position,
                        voice="active",
                        confidence=0.85,
                        method="speech_verb",
                    )

        return None

    def _find_action_beat_regex(
        self,
        before_narr: str,
        after_narr: str,
        alias_map: Dict[str, str],
    ) -> Optional[DialogueTagAnalysis]:
        sorted_names = sorted(alias_map.keys(), key=len, reverse=True)
        if not sorted_names:
            return None
        name_pattern = "|".join(re.escape(n) for n in sorted_names if len(n) >= 2)
        if not name_pattern:
            return None

        # Name at the start of a sentence in adjacent narration
        pattern = re.compile(rf"(?:^|\.\s+)\b({name_pattern})\b", re.IGNORECASE)

        for text, position in [(after_narr, "after_quote"), (before_narr, "before_quote")]:
            match = pattern.search(text)
            if match:
                name_raw = match.group(1).strip()
                canonical = alias_map.get(name_raw.lower())
                if canonical:
                    return DialogueTagAnalysis(
                        speaker_candidates=[canonical],
                        tag_position="action_beat",
                        voice="active",
                        confidence=0.5,
                        method="action_beat",
                    )

        return None

    # ---------------------------------------------------------------
    # Pronoun resolution
    # ---------------------------------------------------------------

    def _try_pronoun_from_narration(
        self,
        narration: str,
        context: SpeakerContext,
        char_genders: Dict[str, str],
    ) -> Optional[DialogueTagAnalysis]:
        narr_lower = narration.lower()

        # "he said" / "she said" patterns
        he_match = re.search(rf"\bhe\s+({SPEECH_VERBS_PATTERN.pattern[2:-2]})\b", narr_lower)
        she_match = re.search(rf"\bshe\s+({SPEECH_VERBS_PATTERN.pattern[2:-2]})\b", narr_lower)

        if he_match and context.last_named_male:
            return DialogueTagAnalysis(
                speaker_candidates=[context.last_named_male],
                speech_verb=he_match.group(1),
                tag_position="after_quote",
                voice="active",
                confidence=0.75,
                method="pronoun",
            )

        if she_match and context.last_named_female:
            return DialogueTagAnalysis(
                speaker_candidates=[context.last_named_female],
                speech_verb=she_match.group(1),
                tag_position="after_quote",
                voice="active",
                confidence=0.75,
                method="pronoun",
            )

        # Non-speech-verb pronoun patterns: "he turned", "she looked"
        he_action = re.search(r"\bhe\s+\w+", narr_lower)
        she_action = re.search(r"\bshe\s+\w+", narr_lower)

        if he_action and context.last_named_male:
            return DialogueTagAnalysis(
                speaker_candidates=[context.last_named_male],
                tag_position="action_beat",
                voice="active",
                confidence=0.45,
                method="pronoun",
            )

        if she_action and context.last_named_female:
            return DialogueTagAnalysis(
                speaker_candidates=[context.last_named_female],
                tag_position="action_beat",
                voice="active",
                confidence=0.45,
                method="pronoun",
            )

        return None

    # ---------------------------------------------------------------
    # Addressee detection
    # ---------------------------------------------------------------

    def _detect_addressee(self, quote_text: str, alias_map: Dict[str, str]) -> Optional[str]:
        stripped = quote_text.strip().lstrip('""\u201c\u201d\'')
        if not stripped:
            return None

        # "Name, ..." pattern at the start of the quote
        sorted_names = sorted(alias_map.keys(), key=len, reverse=True)
        for name in sorted_names:
            if len(name) < 2:
                continue
            pattern = re.compile(rf"^{re.escape(name)}\s*,", re.IGNORECASE)
            if pattern.match(stripped):
                return alias_map.get(name.lower(), name)

        return None

    # ---------------------------------------------------------------
    # Alternation / continuation
    # ---------------------------------------------------------------

    def _check_alternation(self, context: SpeakerContext) -> Optional[DialogueTagAnalysis]:
        if len(context.last_speakers) >= 2:
            last = context.last_speakers[0]
            second_last = context.last_speakers[1]
            if last != second_last:
                return DialogueTagAnalysis(
                    speaker_candidates=[second_last],
                    confidence=0.5,
                    method="alternation",
                )
        return None

    def _check_continuation(self, quote_unit, context: SpeakerContext) -> Optional[DialogueTagAnalysis]:
        is_continuation = getattr(quote_unit, "continuation_quote", False)
        if is_continuation and context.last_speakers:
            return DialogueTagAnalysis(
                speaker_candidates=[context.last_speakers[0]],
                confidence=0.9,
                method="continuation",
            )
        return None

    # ---------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------

    def _extract_surrounding_narration(
        self,
        quote_unit,
        surrounding_units: List,
        window: int = 3,
    ) -> Tuple[str, str]:
        quote_uid = getattr(quote_unit, "uid", None)
        if quote_uid is None:
            return "", ""

        before_parts: List[str] = []
        after_parts: List[str] = []
        found_quote = False

        for u in surrounding_units:
            uid = getattr(u, "uid", None)
            is_quote = getattr(u, "is_quote", False)

            if uid == quote_uid:
                found_quote = True
                continue

            if is_quote:
                if found_quote:
                    break  # Stop at the next quote after ours
                before_parts.clear()  # Only keep narration since last quote
                continue

            text = getattr(u, "text", "").strip()
            if not text:
                continue

            if not found_quote:
                before_parts.append(text)
                if len(before_parts) > window:
                    before_parts.pop(0)
            else:
                after_parts.append(text)
                if len(after_parts) >= window:
                    break

        return " ".join(before_parts), " ".join(after_parts)

    @staticmethod
    def _build_character_genders(registry) -> Dict[str, str]:
        result: Dict[str, str] = {}
        for char in registry.characters:
            result[char.name] = char.gender
        return result
