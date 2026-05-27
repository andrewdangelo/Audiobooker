"""
Mock Book Chunks — BookBrain Demo Data
=======================================

Fictional book: "The Iron Letter" — a crime thriller with multiple POV characters.
Designed to stress-test the exact pain points in SpeakerChunker:

  1. Aliases  — "Roz" is Rosalind; "The Captain" is Marcus Vane
  2. First-person narration with a named narrator ("Kane")
  3. Dialogue attribution ambiguity — multiple characters in same scene
  4. A character introduced mid-book who the web-RAG would miss (unknown book)
  5. Scene-level relationship context (who is where with whom)

Each chunk matches the shape that TextChunker / SpeakerChunker produces:
  {"chunk_id": int, "text": str, "page_numbers": [int], "character_count": int,
   "start_char": int, "end_char": int}

The BOOK_TITLE and BOOK_ID are used when calling the BookBrain API.
"""

BOOK_TITLE = "The Iron Letter"
BOOK_ID    = "demo-iron-letter-001"

# ---------------------------------------------------------------------------
# Raw chunk text — written to expose chunker edge cases
# ---------------------------------------------------------------------------

_CHUNK_TEXTS = [
    # Chunk 0 — Opening. Establishes first-person narrator "Kane", setting, introduces Roz.
    """I have been a detective for seventeen years, but I had never seen a case like this one.
My name is Elliot Kane, and the city of Drenholm had taught me most of what I know about
human cruelty. That morning I sat at my desk reading a telegram, which I will reproduce here
in its entirety: COME AT ONCE. THE LETTER HAS BEEN STOLEN. —R.

The R stood for Rosalind Hartwell, the only person in Drenholm who still sent telegrams.
Everyone else called her Roz. I had worked with Roz three years ago on the Farrow Bridge
affair, and she had an instinct for trouble that I had come to respect deeply.

I pocketed the telegram and reached for my coat. Whatever the letter was, someone had
decided it was worth stealing. In my experience, that made it worth finding.""",

    # Chunk 1 — First dialogue. Roz introduced speaking. Alias demonstrated in narration.
    """Roz was waiting at the door of her shop when my cab arrived. She was a small woman with
iron-grey hair and sharp green eyes that missed nothing.

"You took your time," she said, not unkindly.

"The bridge traffic." I stepped inside. The shop smelled of old paper and turpentine.
"Tell me about the letter."

Roz closed the door behind us and crossed to the counter. She kept her voice low, though
we were alone.

"It belonged to a man named Marcus Vane. He brought it to me for appraisal two days ago.
Authenticated correspondence between Lord Aldrick and the colonial governor — 1887. Worth
a great deal of money, but that is not why someone took it."

"Why, then?"

Roz looked at me steadily. "Because of what it proves."

I waited. Roz had a talent for timing.

"Marcus Vane is going to stand trial for sedition next month," she said. "The letter is
evidence that would clear him."
""",

    # Chunk 2 — New character: Marcus Vane. Called "The Captain" by other characters.
    # Introduces his alias and physical description.
    """I found Marcus Vane at the harbour tavern where Roz said he spent his mornings.
He was a large man, broad-shouldered, with a naval officer's posture that years of civilian
life had not erased. The other men at the bar called him "Captain" with the easy familiarity
of old habit.

I introduced myself and set my card on the table in front of him.

The Captain studied my card for a long moment before he looked up. "A private inquiry agent.
Roz sent you."

"She did."

"Then sit down, Mr. Kane." He did not ask — he commanded, the way men who have spent long
years giving orders always do. "I'll tell you what I told the constabulary, which is
everything. I have nothing to hide."

He told me the story of the letter. It had come to him through his late father's estate —
a cache of old documents that the solicitor had overlooked for thirty years. When Marcus had
finally opened the box and read the letter, he had understood immediately what it meant.

"Lord Aldrick ordered the destruction of the settlement records himself," Marcus said.
"That is what the letter proves. The charges against me are built on records that should
not exist."
""",

    # Chunk 3 — Three-way scene. Kane, Roz, and Marcus. Dense dialogue attribution.
    # Tests the chunker's hardest case: who speaks when three people are present.
    """We met that evening in Roz's back room — Marcus, Roz, and I — spreading a map of
the old colonial quarter across the worktable. Someone had entered the shop between eight
and midnight on Tuesday. They had not forced the lock.

"A duplicate key," Marcus said, pressing his finger to the map. "The solicitor's office.
They would have a copy."

Roz shook her head. "Mr. Percival Fenn has been my solicitor for twenty years. He is not
a thief."

"He might not know," I said. "A key can be copied without the owner's knowledge."

Marcus looked at me. "You think someone inside the solicitor's office."

"I think someone with access." I studied the map. "The more interesting question is how
they knew the letter was here at all. You brought it to Roz two days ago. Who knew?"

A silence settled over the room. Roz reached for the lamp and turned the wick higher.

"Three people," Marcus said at last. "Myself. My clerk, Tobias Grint. And my solicitor."

"Then we need to speak with Tobias Grint," I said.

"He won't talk to you," Marcus said. "He doesn't trust inquiry agents."

Roz smiled slightly. "He will talk to me."
""",

    # Chunk 4 — New minor character: Tobias Grint. Roz interviews him. Kane observes.
    # The character never uses his own name — relies on context to attribute his dialogue.
    """Tobias Grint was a nervous young man with ink-stained fingers and a habit of glancing
toward the door. He came to the shop the next morning at Roz's invitation and sat on the
edge of the chair as though prepared to flee at any moment.

Roz poured him tea and set it in front of him with the calm efficiency she brought to
everything.

"You are not in trouble, Mr. Grint," she said. "We only want to understand the movements
of the letter."

He wrapped both hands around the teacup. "The Captain told me not to say anything."

"The Captain told you not to speak to the constabulary. I am not the constabulary."

A pause. He looked at his tea.

"I copied it," he said, very quietly. "The letter. Before the Captain took it for appraisal.
I thought — I don't know what I thought. I was curious. The Captain found an old box of
his father's papers and I helped him sort them and I read it over his shoulder when he
wasn't looking."

"And then?" Roz asked.

"And then nothing. I told no one."

Roz set down her own cup. "You told no one, and yet someone knew the letter existed and
where to find it." She did not phrase it as an accusation. She didn't need to.

Grint's face went pale. "There was a man," he said at last. "He came to the office two days
before the Captain found the letter. Said he was researching the Vane family estate on
behalf of a historical society. I showed him — I showed him the box. I didn't think it
mattered. It was just old papers."
""",

    # Chunk 5 — Climactic scene. Kane confronts the antagonist, never named in this chunk.
    # Relies heavily on context and pronoun resolution. Tests BookBrain's character memory.
    """I found him in the archive room of the colonial records office, three hours before
closing. He was a middle-aged man with a civil servant's grey suit and a civil servant's
careful expression, and he did not seem surprised to see me.

"Mr. Kane," he said. "I wondered when you would find your way here."

"You have something that belongs to Marcus Vane." I kept my voice level.

"I have a document that certain people are very interested in keeping suppressed." He moved
to the window. The harbour was visible below, grey in the afternoon light. "You understand
what would happen if that letter were introduced as evidence. Careers would end. Families
would be ruined."

"A man would be freed," I said. "Who has done nothing wrong."

He was quiet for a moment. Then: "What do you want, Mr. Kane?"

"The letter. And the name of whoever sent you to take it."

He looked at me for a long time. Something moved behind his careful expression — not guilt
exactly. Something older than guilt.

"I took it myself," he said. "No one sent me. Marcus Vane's father was my friend for
forty years. I took that letter to protect him. To protect what remains of him."

I had not expected that. I waited.

"He wrote it," the man said quietly. "Lord Aldrick did not write the letter, Mr. Kane.
Marcus Vane's father did. He destroyed the settlement records, not Aldrick. The letter
proves Marcus's father was a criminal. Marcus Vane is innocent — but not in the way
he believes."
""",
]


# ---------------------------------------------------------------------------
# Public: build the chunks list in the SpeakerChunker-compatible format
# ---------------------------------------------------------------------------

def build_mock_chunks() -> list[dict]:
    """
    Returns a list of chunk dicts matching the shape TextChunker produces:
        chunk_id, text, page_numbers, character_count, start_char, end_char
    """
    chunks = []
    offset = 0
    for i, text in enumerate(_CHUNK_TEXTS):
        chunks.append({
            "chunk_id":        i + 1,
            "text":            text,
            "page_numbers":    [i * 3 + 1, i * 3 + 2],
            "character_count": len(text),
            "start_char":      offset,
            "end_char":        offset + len(text),
        })
        offset += len(text)
    return chunks


# ---------------------------------------------------------------------------
# Expected outputs — used to validate BookBrain results in the demo
# ---------------------------------------------------------------------------

EXPECTED_CHARACTERS = [
    {"name": "Elliot Kane",    "aliases": ["Kane"],        "role": "First-person narrator, private detective"},
    {"name": "Rosalind Hartwell", "aliases": ["Roz"],     "role": "Antiquarian, ally of Kane"},
    {"name": "Marcus Vane",    "aliases": ["The Captain", "Captain"], "role": "Naval officer, defendant in sedition trial"},
    {"name": "Tobias Grint",   "aliases": ["Grint"],       "role": "Marcus's clerk, minor character"},
]

EXPECTED_SETTINGS = [
    "Drenholm (city)",
    "Roz's antiquarian shop",
    "Harbour tavern",
    "Colonial records office",
]

# Queries that test BookBrain retrieval — each should surface the right entry type
DEMO_SEARCH_QUERIES = [
    ("Who is The Captain?",                      "character"),
    ("What evidence is Marcus on trial for?",    "plot"),
    ("Where does Roz work?",                     "setting"),
    ("What is the significance of the letter?",  "theme"),
    ("Who is Tobias Grint and what did he do?",  "character"),
]
