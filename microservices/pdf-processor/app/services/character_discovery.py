"""
Character Discovery

Hybrid character and alias detection using spaCy NER + LLM validation.
Three-tier pipeline: NER extraction -> LLM enrichment -> text evidence validation.
"""
__author__ = "Andrew D'Angelo"

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from app.core.logging_config import Logger


SPEECH_VERBS = (
    r"said|says|asked|asks|replied|replies|answered|answers|"
    r"shouted|shouts|whispered|whispers|muttered|mutters|"
    r"exclaimed|exclaims|demanded|demands|cried|cries|"
    r"called|calls|yelled|yells|screamed|screams|"
    r"snapped|snaps|growled|growls|hissed|hisses|"
    r"sighed|sighs|laughed|laughs|chuckled|chuckles|"
    r"murmured|murmurs|breathed|breathes|gasped|gasps|"
    r"groaned|groans|moaned|moans|declared|declares|"
    r"announced|announces|continued|continues|added|adds|"
    r"began|begins|went on|interrupted|interrupts|"
    r"inquired|inquires|wondered|wonders|observed|observes|"
    r"commented|comments|noted|notes|remarked|remarks|"
    r"admitted|admits|agreed|agrees|protested|protests|"
    r"suggested|suggests|explained|explains|insisted|insists|"
    r"responded|responds|retorted|retorts|countered|counters|"
    r"confirmed|confirms|denied|denies|pleaded|pleads"
)

_SPEECH_VERB_RE = re.compile(rf"\b({SPEECH_VERBS})\b", re.IGNORECASE)

_FALSE_POSITIVE_RE = [
    re.compile(r"^(chapter|prologue|epilogue|book|part|introduction|foreword|afterword|preface)(\s+\d+)?$", re.IGNORECASE),
    re.compile(r"^(the\s+)?pattern$", re.IGNORECASE),
]

_TITLE_PREFIXES = {"mr", "mrs", "ms", "dr", "professor", "prof", "sir", "lady", "lord", "miss", "master", "captain", "capt", "colonel", "col", "general", "gen", "sergeant", "sgt", "king", "queen", "prince", "princess", "duke", "duchess", "count", "countess", "baron", "baroness"}

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
class Character:
    name: str
    gender: str
    description: str
    mentioned_count: int = 0
    aliases: List[str] = field(default_factory=list)
    is_speaking_character: bool = True
    discovery_method: str = "ner"
    confidence: float = 0.0


@dataclass
class CharacterRegistry:
    characters: List[Character]
    alias_to_canonical: Dict[str, str]
    narrator_name: str = "Narrator"
    pov: str = "Third Person"


# ---------------------------------------------------------------------------
# CharacterDiscovery
# ---------------------------------------------------------------------------

class CharacterDiscovery(Logger):

    def __init__(self, llm_api=None):
        self._llm_api = llm_api
        self._nlp = _get_nlp()
        if self._nlp is None:
            self.logger.warning("spaCy model not available; character discovery will rely on LLM only")

    # ---------------------------------------------------------------
    # Main entry point
    # ---------------------------------------------------------------

    def discover(self, full_text: str, book_title: str = "Unknown Book") -> CharacterRegistry:
        self.logger.info("Starting character discovery for '%s' (%d chars)", book_title, len(full_text))

        # Tier 1: NER
        ner_candidates = self._ner_extract(full_text) if self._nlp else []
        self.logger.info("Tier 1 (NER): %d candidates", len(ner_candidates))

        # Tier 2: LLM enrichment
        if self._llm_api:
            enriched = self._llm_enrich(ner_candidates, book_title, full_text)
            self.logger.info("Tier 2 (LLM): %d enriched candidates", len(enriched))
        else:
            enriched = ner_candidates
            self.logger.info("Tier 2 (LLM): skipped (no API)")

        # Tier 3: text evidence validation
        characters = self._validate_with_text_evidence(enriched, full_text)
        self.logger.info("Tier 3 (validation): %d validated characters", len(characters))

        # POV + narrator
        pov, narrator_name = self._detect_pov_and_narrator(full_text, characters)

        alias_map = self._build_alias_map(characters)

        registry = CharacterRegistry(
            characters=characters,
            alias_to_canonical=alias_map,
            narrator_name=narrator_name,
            pov=pov,
        )

        for c in characters[:15]:
            alias_str = f" aliases={c.aliases}" if c.aliases else ""
            self.logger.info("  -> %s (%s, %dx, conf=%.2f)%s", c.name, c.gender, c.mentioned_count, c.confidence, alias_str)

        return registry

    # ---------------------------------------------------------------
    # Tier 1: spaCy NER
    # ---------------------------------------------------------------

    def _ner_extract(self, text: str, max_chars: int = 100_000) -> List[Dict]:
        if self._nlp is None:
            return []

        samples = self._sample_text(text, max_chars)
        entity_counts: Dict[str, int] = {}
        entity_positions: Dict[str, List[int]] = {}

        for sample_text in samples:
            doc = self._nlp(sample_text)
            for ent in doc.ents:
                if ent.label_ != "PERSON":
                    continue
                name = ent.text.strip()
                if len(name) < 2 or any(c.isdigit() for c in name):
                    continue
                if not re.match(r"^[A-Za-z\s\-\.\']+$", name):
                    continue
                entity_counts[name] = entity_counts.get(name, 0) + 1
                entity_positions.setdefault(name, []).append(ent.start_char)

        candidates = [
            {"name": name, "count": count, "positions": entity_positions.get(name, []), "possible_aliases": []}
            for name, count in entity_counts.items()
            if count >= 1
        ]

        candidates = self._group_coreferring_names(candidates)
        return candidates

    def _sample_text(self, text: str, max_chars: int) -> List[str]:
        if len(text) <= max_chars:
            return [text]

        samples = [text[:30_000]]
        mid = len(text) // 2
        samples.append(text[mid:mid + 20_000])
        two_thirds = (2 * len(text)) // 3
        samples.append(text[two_thirds:two_thirds + 20_000])
        samples.append(text[-20_000:])
        return samples

    # ---------------------------------------------------------------
    # Name co-reference grouping
    # ---------------------------------------------------------------

    def _group_coreferring_names(self, entities: List[Dict]) -> List[Dict]:
        sorted_ents = sorted(entities, key=lambda e: len(e["name"]), reverse=True)
        groups: List[Dict] = []
        absorbed: Set[str] = set()

        for ent in sorted_ents:
            name = ent["name"]
            if name in absorbed:
                continue

            group = {
                "name": name,
                "count": ent["count"],
                "positions": list(ent.get("positions", [])),
                "possible_aliases": [],
            }

            name_parts = self._name_parts(name)

            for other in sorted_ents:
                other_name = other["name"]
                if other_name == name or other_name in absorbed:
                    continue

                other_parts = self._name_parts(other_name)

                # Same surname or first name match
                if self._names_corefer(name_parts, other_parts):
                    group["possible_aliases"].append(other_name)
                    group["count"] += other["count"]
                    group["positions"].extend(other.get("positions", []))
                    absorbed.add(other_name)

            groups.append(group)
            absorbed.add(name)

        return groups

    @staticmethod
    def _name_parts(name: str) -> Dict[str, str]:
        words = name.split()
        result: Dict[str, str] = {"full": name}

        # Strip title prefix
        if words and words[0].lower().rstrip(".") in _TITLE_PREFIXES:
            result["title"] = words[0]
            words = words[1:]

        if words:
            result["first"] = words[0]
        if len(words) > 1:
            result["last"] = words[-1]
        result["bare_words"] = words
        return result

    @staticmethod
    def _names_corefer(a: Dict, b: Dict) -> bool:
        a_words = a.get("bare_words", [])
        b_words = b.get("bare_words", [])
        if not a_words or not b_words:
            return False

        # Exact first name match (with different lengths -> one is a full name)
        if a_words[0].lower() == b_words[0].lower() and len(a_words) != len(b_words):
            return True

        # Surname match when both have surnames
        a_last = a.get("last", "").lower()
        b_last = b.get("last", "").lower()
        if a_last and b_last and a_last == b_last:
            return True

        # Single word matches the first or last name of a multi-word name
        if len(b_words) == 1 and len(a_words) > 1:
            single = b_words[0].lower()
            if single == a_words[0].lower() or single == a_words[-1].lower():
                return True

        return False

    # ---------------------------------------------------------------
    # Tier 2: LLM enrichment
    # ---------------------------------------------------------------

    def _llm_enrich(self, ner_candidates: List[Dict], book_title: str, full_text: str) -> List[Dict]:
        if not self._llm_api:
            return ner_candidates

        # Build candidate summary for prompt
        candidate_lines = []
        for c in sorted(ner_candidates, key=lambda x: x["count"], reverse=True)[:40]:
            aliases_str = f" (also: {', '.join(c['possible_aliases'])})" if c["possible_aliases"] else ""
            candidate_lines.append(f"- {c['name']} ({c['count']}x){aliases_str}")

        candidates_text = "\n".join(candidate_lines) if candidate_lines else "(no NER candidates found)"
        # Escape braces for LangChain
        candidates_text = candidates_text.replace("{", "{{").replace("}", "}}")

        system_msg = (
            "You are a literary analysis assistant. "
            "Given a list of character name candidates extracted from a book, "
            "validate and enrich each one.\n\n"
            "RULES:\n"
            "1. Canonical name must be the character's REAL full name.\n"
            "2. aliases MUST include common short names and nicknames.\n"
            "3. NEVER use non-English characters.\n"
            "4. Reject candidates that are not actual character names.\n"
            "5. Add any important characters missing from the list.\n\n"
            "Return ONLY valid JSON:\n"
            '{{\"characters\": [{{\"name\": \"string\", \"aliases\": [\"string\"], '
            '\"gender\": \"male|female|unknown\", \"description\": \"1 sentence\", '
            '\"confirmed\": true}}]}}'
        )

        user_msg = (
            f"Book: '{book_title}'\n\n"
            f"Candidates found by NER:\n{candidates_text}\n\n"
            "Validate, enrich with aliases/gender/description, add missing characters. "
            "Return ONLY the JSON."
        )

        try:
            answer = self._llm_api.sync_chat(
                prompt_messages=[["system", system_msg], ["user", user_msg]],
                inputs={},
                timeout=120,
            )
            parsed = self._parse_character_json(answer)
            if parsed:
                # Merge LLM results with NER counts
                ner_lookup = {c["name"].lower(): c for c in ner_candidates}
                for p in parsed:
                    key = p.get("name", "").lower()
                    if key in ner_lookup:
                        p["count"] = ner_lookup[key]["count"]
                        p.setdefault("possible_aliases", [])
                        existing_aliases = set(a.lower() for a in p.get("aliases", []))
                        for a in ner_lookup[key].get("possible_aliases", []):
                            if a.lower() not in existing_aliases:
                                p.setdefault("aliases", []).append(a)
                    else:
                        p.setdefault("count", full_text.lower().count(p.get("name", "").lower().split()[0]))
                return parsed
        except Exception as e:
            self.logger.warning("LLM enrichment failed: %s", e)

        return ner_candidates

    @staticmethod
    def _parse_character_json(raw: str) -> List[Dict]:
        clean = re.sub(r"```(?:json)?|```", "", raw).strip()
        try:
            parsed = json.loads(clean)
            if isinstance(parsed, list):
                return parsed
            return parsed.get("characters", [])
        except json.JSONDecodeError:
            recovered = []
            for m in re.finditer(r'\{[^{}]*"name"[^{}]*\}', clean, re.DOTALL):
                try:
                    obj = json.loads(m.group(0))
                    if obj.get("name"):
                        recovered.append(obj)
                except json.JSONDecodeError:
                    continue
            return recovered

    # ---------------------------------------------------------------
    # Tier 3: text evidence validation
    # ---------------------------------------------------------------

    def _validate_with_text_evidence(self, candidates: List[Dict], full_text: str) -> List[Character]:
        full_lower = full_text.lower()
        validated: List[Character] = []
        seen: Set[str] = set()

        for c in candidates:
            name = c.get("name", "").strip()
            if not name or len(name) < 2:
                continue

            # False positive filter
            if any(p.match(name) for p in _FALSE_POSITIVE_RE):
                continue
            if not re.match(r"^[A-Za-z\s\-\.\']+$", name):
                continue
            # Strip embedded nicknames like "Dallas 'Dally' Winston"
            name = re.sub(r"\s*['\"].*?['\"]\s*", " ", name).strip()
            name = re.sub(r"\s+", " ", name)

            key = name.lower()
            if key in seen:
                continue
            seen.add(key)

            # Count mentions
            first_name = name.split()[0]
            name_mentions = full_lower.count(first_name.lower())
            raw_aliases = c.get("aliases", c.get("possible_aliases", []))
            clean_aliases = [
                a.strip() for a in raw_aliases
                if isinstance(a, str)
                and len(a.strip()) >= 2
                and re.match(r"^[A-Za-z\s\-\.\']+$", a.strip())
                and a.strip().lower() != name.lower()
            ]

            # Auto-add first name as alias if multi-word
            if len(name.split()) > 1 and len(first_name) >= 3:
                if first_name not in clean_aliases and first_name.lower() not in seen:
                    clean_aliases.append(first_name)

            total_mentions = name_mentions + sum(full_lower.count(a.lower()) for a in clean_aliases)
            if total_mentions == 0:
                continue

            # Check if character appears near speech verbs
            is_speaking = False
            all_surfaces = [name.lower(), first_name.lower()] + [a.lower() for a in clean_aliases]
            for surface in all_surfaces:
                pattern = re.compile(
                    rf"\b{re.escape(surface)}\b.{{0,200}}\b({SPEECH_VERBS})\b"
                    rf"|\b({SPEECH_VERBS})\b.{{0,200}}\b{re.escape(surface)}\b",
                    re.IGNORECASE | re.DOTALL,
                )
                if pattern.search(full_text[:100_000]):
                    is_speaking = True
                    break

            # Confidence scoring
            method = "both" if c.get("confirmed") else ("llm" if "description" in c and c["description"] else "ner")
            confidence = 0.5
            if total_mentions >= 10:
                confidence += 0.2
            elif total_mentions >= 3:
                confidence += 0.1
            if is_speaking:
                confidence += 0.2
            if method == "both":
                confidence += 0.1
            confidence = min(confidence, 1.0)

            validated.append(Character(
                name=name,
                gender=c.get("gender", "unknown"),
                description=c.get("description", ""),
                mentioned_count=total_mentions,
                aliases=clean_aliases,
                is_speaking_character=is_speaking,
                discovery_method=method,
                confidence=confidence,
            ))

        # Deduplicate: absorb shorter names into longer ones
        validated.sort(key=lambda ch: len(ch.name), reverse=True)
        final: List[Character] = []
        absorbed_keys: Set[str] = set()

        for char in validated:
            if char.name.lower() in absorbed_keys:
                continue
            final.append(char)
            for other in validated:
                if other.name != char.name and other.name.lower() not in absorbed_keys:
                    if re.match(rf"(?i)^{re.escape(other.name)}\b", char.name):
                        absorbed_keys.add(other.name.lower())
                        if other.name not in char.aliases:
                            char.aliases.append(other.name)

        # Resolve alias conflicts
        alias_owners: Dict[str, List[Character]] = {}
        for char in final:
            for alias in char.aliases:
                alias_owners.setdefault(alias.lower(), []).append(char)
        for alias, owners in alias_owners.items():
            if len(owners) > 1:
                owners.sort(key=lambda ch: ch.mentioned_count, reverse=True)
                for loser in owners[1:]:
                    loser.aliases = [a for a in loser.aliases if a.lower() != alias]

        # Ensure Narrator exists
        if not any(c.name == "Narrator" for c in final):
            final.insert(0, Character("Narrator", "neutral", "The narrative voice", 0, discovery_method="system", confidence=1.0))

        final.sort(key=lambda ch: ch.mentioned_count, reverse=True)
        return final

    # ---------------------------------------------------------------
    # Alias map
    # ---------------------------------------------------------------

    def _build_alias_map(self, characters: List[Character]) -> Dict[str, str]:
        alias_map: Dict[str, str] = {}
        conflicts: Dict[str, List[str]] = {}

        for char in characters:
            alias_map[char.name.lower()] = char.name
            for alias in char.aliases:
                key = alias.lower()
                if key in alias_map and alias_map[key] != char.name:
                    conflicts.setdefault(key, []).append(char.name)
                else:
                    alias_map[key] = char.name

            # Auto-add first name if unambiguous
            first = char.name.split()[0].lower()
            if len(first) >= 3 and first not in alias_map:
                alias_map[first] = char.name

        # Resolve conflicts: most-mentioned wins
        char_mentions = {c.name: c.mentioned_count for c in characters}
        for key, competing in conflicts.items():
            all_names = [alias_map.get(key, "")] + competing
            winner = max(all_names, key=lambda n: char_mentions.get(n, 0))
            alias_map[key] = winner

        return alias_map

    # ---------------------------------------------------------------
    # POV / narrator detection
    # ---------------------------------------------------------------

    def _detect_pov_and_narrator(
        self,
        full_text: str,
        characters: List[Character],
        llm_api=None,
    ) -> Tuple[str, str]:
        intro = full_text[:10_000]

        first_person_re = re.compile(rf"\bI\s+({SPEECH_VERBS})\b", re.IGNORECASE)
        fp_count = len(first_person_re.findall(intro))

        # Also check for "I was", "I had", "I knew" as narrative indicators
        fp_narrative = len(re.findall(r"\bI\s+(was|had|knew|felt|saw|heard|thought|wanted|needed)\b", intro, re.IGNORECASE))

        is_first_person = (fp_count >= 3) or (fp_count >= 1 and fp_narrative >= 5)

        if not is_first_person:
            return "Third Person", "Narrator"

        # Find the narrator's name by looking for characters addressing someone
        narrator_name = "Narrator"
        best_count = 0
        for char in characters:
            if char.name == "Narrator":
                continue
            first = char.name.split()[0].lower()
            # Look for patterns like '"Ponyboy," he said' or 'called me Ponyboy'
            address_count = len(re.findall(
                rf'["\u201c]\s*{re.escape(char.name.split()[0])}\b',
                intro, re.IGNORECASE,
            ))
            mention_count = intro.lower().count(first)
            score = address_count * 3 + mention_count
            if score > best_count and mention_count >= 3:
                best_count = score
                narrator_name = char.name

        if narrator_name == "Narrator" and self._llm_api:
            try:
                intro_escaped = intro[:6000].replace("{", "{{").replace("}", "}}")
                answer = self._llm_api.sync_chat(
                    prompt_messages=[
                        ["system", (
                            "This book is written in first person. "
                            "Who is the narrator? Return ONLY the character's full name."
                        )],
                        ["user", f"Opening text:\n\n{intro_escaped}"],
                    ],
                    inputs={},
                    timeout=60,
                )
                name = answer.strip().strip('"').strip("'")
                if name and len(name) < 100 and re.match(r"^[A-Za-z\s\-\.]+$", name):
                    narrator_name = name
            except Exception as e:
                self.logger.warning("LLM narrator detection failed: %s", e)

        self.logger.info("POV: First Person, narrator: '%s'", narrator_name)
        return "First Person", narrator_name
