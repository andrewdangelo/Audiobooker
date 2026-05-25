"""CharacterDiscovery helpers that do not require spaCy or HTTP."""

from app.services.character_discovery import CharacterDiscovery


def test_parse_character_json_strips_fences():
    raw = '```json\n{"characters": [{"name": "Jane Doe", "aliases": ["Jane"]}]}\n```'
    out = CharacterDiscovery._parse_character_json(raw)
    assert len(out) == 1
    assert out[0]["name"] == "Jane Doe"


def test_parse_character_json_top_level_list():
    raw = '[{"name": "Bob", "aliases": []}]'
    out = CharacterDiscovery._parse_character_json(raw)
    assert out[0]["name"] == "Bob"


def test_names_corefer_first_name_subset():
    a = CharacterDiscovery._name_parts("Elizabeth Bennet")
    b = CharacterDiscovery._name_parts("Elizabeth")
    assert CharacterDiscovery._names_corefer(a, b) is True
