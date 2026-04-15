"""
Seed Script: Sample Books + Store Listings → MongoDB (backend service)

Inserts books into the `books` collection and matching records into
`store_listings` so the store catalog, featured, new-releases, and
bestsellers endpoints all return data.

Usage:
    python seed_books.py              # insert (skip existing titles)
    python seed_books.py --wipe       # drop books + store_listings first
    python seed_books.py --check      # print current counts and exit
"""

import asyncio
import argparse
import logging
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

load_dotenv(Path(__file__).parent / ".env")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
MONGODB_URL  = os.getenv("DATABASE_URL", "mongodb://localhost:27017")
MONGODB_DB   = os.getenv("DATABASE_NAME", "audiobooker_backend_db")
BOOKS_COL    = "books"
LISTINGS_COL = "store_listings"

# Placeholder publisher user_id — swap for a real one if you need
PUBLISHER_ID = "seed_publisher_000000000000"

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cover image placeholders  (800×1200 ratio, genre-coloured via picsum seed)
# ---------------------------------------------------------------------------
def cover(seed: int) -> str:
    return f"https://picsum.photos/seed/{seed}/400/600"

# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------
NOW = datetime.utcnow()

def make_chapters(count: int, avg_minutes: int = 25) -> list:
    chapters = []
    cursor = 0
    for i in range(1, count + 1):
        duration = avg_minutes * 60
        chapters.append({
            "id": str(uuid.uuid4()),
            "title": f"Chapter {i}",
            "start_time": cursor,
            "duration": duration,
            "chapter_number": i,
        })
        cursor += duration
    return chapters


def make_named_chapters(names: list[str], avg_minutes: int = 25) -> list:
    """Build chapters from a list of real titles, varying duration slightly for realism."""
    import random
    rng = random.Random(sum(ord(c) for c in names[0]))  # deterministic seed
    chapters = []
    cursor = 0
    for i, name in enumerate(names, 1):
        # ±20 % jitter around avg so chapters feel different lengths
        duration = int(avg_minutes * 60 * rng.uniform(0.80, 1.20))
        chapters.append({
            "id": str(uuid.uuid4()),
            "title": name,
            "start_time": cursor,
            "duration": duration,
            "chapter_number": i,
        })
        cursor += duration
    return chapters


SEED_BOOKS = [
    # ── Fantasy ──────────────────────────────────────────────────────────────
    {
        "title": "The Ember Throne",
        "author": "Lyra Ashwood",
        "narrator": "Marcus Cole",
        "description": "A young fire-mage must reclaim a stolen throne before the kingdom burns.",
        "synopsis": (
            "When Kael discovers he can control fire without a focus stone, the Empire labels him "
            "a threat. Hunted across three kingdoms, he stumbles upon the truth behind the Ember "
            "Throne — and the ancient pact that could either save or doom every living soul."
        ),
        "genre": "Fantasy",
        "categories": ["Fantasy", "Adventure", "Magic"],
        "published_year": 2021,
        "price": 14.99,
        "credits_required": 1,
        "rating": 4.7,
        "review_count": 412,
        "cover_image_url": cover(101),
        "chapters": make_named_chapters([
            "The Boy Without a Stone",
            "Embers in the Market Square",
            "A Price on Ash",
            "The Three Kingdoms Treaty",
            "Flight Through the Cinderpines",
            "The Smuggler's Bargain",
            "Whispers of the Old Pact",
            "Blood on the Hearthstone",
            "The Battle of Irongate",
            "What the Flame Remembers",
            "Into the Obsidian Vault",
            "The False King's Court",
            "Trial by Inferno",
            "Ashes of Betrayal",
            "The Pact Reborn",
            "A Throne of Cooling Embers",
            "The New Fire",
            "Epilogue: Long May It Burn",
        ], avg_minutes=28),
        "is_store_item": True,
        "created_at": NOW - timedelta(days=90),
    },
    {
        "title": "Shadows of the Forgotten Sea",
        "author": "Daniela Moreno",
        "narrator": "Eleanor Voss",
        "description": "A marine archaeologist uncovers an underwater civilisation with a dark secret.",
        "synopsis": (
            "Dr. Sable Renn's routine dive expedition turns into a fight for survival when her "
            "team breaches a sealed vault 3,000 metres below the surface. Inside: living history, "
            "and a warning written in a language that predates humanity."
        ),
        "genre": "Fantasy",
        "categories": ["Fantasy", "Mystery", "Archaeology"],
        "published_year": 2022,
        "price": 12.99,
        "credits_required": 1,
        "rating": 4.4,
        "review_count": 289,
        "cover_image_url": cover(202),
        "chapters": make_named_chapters([
            "The Dive That Changed Everything",
            "Anomaly at Grid Seven",
            "Pressure",
            "Languages Older Than Script",
            "The Sealed Door",
            "What Breathes in the Dark",
            "Surface — Too Late",
            "The Warning Translated",
            "Who Built the Vault",
            "Deep Current",
            "Racing the Tide",
            "The Last Dive",
            "Silence at 3,000 Metres",
            "Epilogue: Open Water",
        ], avg_minutes=30),
        "is_store_item": True,
        "created_at": NOW - timedelta(days=60),
    },

    # ── Science Fiction ───────────────────────────────────────────────────────
    {
        "title": "Pale Signal",
        "author": "Renn Takahashi",
        "narrator": "David Osei",
        "description": "First contact was not what humanity expected — or wanted.",
        "synopsis": (
            "When deep-space probe Artemis-9 returns 40 years early carrying a single passenger "
            "who refuses to speak, linguist Dr. Yuki Mara is tasked with breaking the silence. "
            "What she deciphers will rewrite every assumption about the universe."
        ),
        "genre": "Science Fiction",
        "categories": ["Sci-Fi", "First Contact", "Thriller"],
        "published_year": 2023,
        "price": 15.99,
        "credits_required": 1,
        "rating": 4.8,
        "review_count": 673,
        "cover_image_url": cover(303),
        "chapters": make_named_chapters([
            "Artemis-9 Returns",
            "The Passenger Has No Name",
            "Protocol Zero",
            "Forty Years in Transit",
            "Dr. Mara's First Session",
            "Cognition Without Language",
            "The Shape of an Idea",
            "What the Signal Said",
            "Quarantine Breach",
            "The Third Conversation",
            "Every Star Has a Memory",
            "The UN Emergency Session",
            "Truth in the Frequency",
            "What They Built Before Us",
            "Pale Signal Decoded",
            "Choice at the Edge of the Solar System",
            "Departure",
            "Transmission",
            "The Answer We Weren't Ready For",
            "Epilogue: First Words",
        ], avg_minutes=25),
        "is_store_item": True,
        "created_at": NOW - timedelta(days=14),
    },
    {
        "title": "The Recursion Engine",
        "author": "Priya Nair",
        "narrator": "James Holden",
        "description": "A programmer discovers the simulation crack that could free — or delete — reality.",
        "synopsis": (
            "Mira's debugging session takes a fatal turn when a memory-allocation error reveals "
            "coordinates that shouldn't exist. Following the trail, she finds herself at the edge "
            "of a recursive loop that someone very powerful wants to keep running."
        ),
        "genre": "Science Fiction",
        "categories": ["Sci-Fi", "Cyberpunk", "Philosophical"],
        "published_year": 2022,
        "price": 13.99,
        "credits_required": 1,
        "rating": 4.5,
        "review_count": 331,
        "cover_image_url": cover(404),
        "chapters": make_named_chapters([
            "Stack Overflow at 3 a.m.",
            "The Impossible Address",
            "Memory Leak",
            "Who Owns Root",
            "The Loop That Didn't End",
            "Mira Goes Offline",
            "Two Realities, Same Bug",
            "The Architect's Comment",
            "Fork",
            "Collision Detection",
            "Runtime Error",
            "The Last Debug Session",
            "Kill Command",
            "Pull Request: Delete World",
            "Merge",
            "Epilogue: Patch Notes",
        ], avg_minutes=27),
        "is_store_item": True,
        "created_at": NOW - timedelta(days=45),
    },

    # ── Thriller / Mystery ────────────────────────────────────────────────────
    {
        "title": "Forty-Eight Hours",
        "author": "Carter Walsh",
        "narrator": "Sofia Reyes",
        "description": "A detective has two days to stop a copycat killer who's always one step ahead.",
        "synopsis": (
            "The Clockwork Killer vanished ten years ago. Now Detective Lena Holt receives a "
            "ticking package: forty-eight hours to solve a cold case, or the original killer "
            "walks — and the copycat strikes again."
        ),
        "genre": "Thriller",
        "categories": ["Thriller", "Mystery", "Crime"],
        "published_year": 2020,
        "price": 11.99,
        "credits_required": 1,
        "rating": 4.6,
        "review_count": 518,
        "cover_image_url": cover(505),
        "chapters": make_named_chapters([
            "The Package on Her Desk",
            "Hour Zero",
            "Cold Case Files",
            "The Clockwork Pattern",
            "A Copycat Has Rules",
            "Hour Eight: The First Victim",
            "What the Scene Didn't Show",
            "Forensics and Gut Instinct",
            "The Watcher in the Crowd",
            "Hour Sixteen: Closing In",
            "Wrong Turn",
            "The Original Confession",
            "Hour Twenty-Four: Everything Changes",
            "The Real Target",
            "Hour Thirty-Six: Race to Stop It",
            "The Clock Strikes",
            "Hour Forty-Seven",
            "The Last Minute",
            "Aftermath",
            "Epilogue: The Next Package",
            "Author's Note on the Clockwork Cases",
            "Bonus Chapter: Lena's First Case",
        ], avg_minutes=20),
        "is_store_item": True,
        "created_at": NOW - timedelta(days=30),
    },
    {
        "title": "The Glass Informant",
        "author": "Nina Blackwood",
        "narrator": "Thomas Grant",
        "description": "An intelligence analyst realises the mole she's hunting is herself.",
        "synopsis": (
            "Claire Ashby has spent six months hunting a leak inside MI-7. The evidence is "
            "irrefutable, the suspect profile a perfect match. The only problem: it points "
            "directly at her. Now she must clear her name before the agency erases her."
        ),
        "genre": "Thriller",
        "categories": ["Thriller", "Espionage", "Conspiracy"],
        "published_year": 2023,
        "price": 12.99,
        "credits_required": 1,
        "rating": 4.3,
        "review_count": 244,
        "cover_image_url": cover(606),
        "chapters": make_named_chapters([
            "Six Months in the Dark",
            "The Suspect Profile",
            "Mirror, Mirror",
            "Who Do You Trust in MI-7",
            "Burn Notice",
            "The Safe House That Wasn't Safe",
            "Every Leak Has a Source",
            "Running Without a Cover",
            "The Double",
            "Glass Evidence",
            "Defection or Manipulation",
            "The Real Handler",
            "Breaking Cover to Save It",
            "Clearance",
            "Epilogue: New Assignment",
            "Classified Appendix",
            "Reading Group Guide",
            "Interview with Nina Blackwood",
            "Bonus Content: The Moscow Files",
        ], avg_minutes=22),
        "is_store_item": True,
        "created_at": NOW - timedelta(days=7),
    },

    # ── Historical Fiction ────────────────────────────────────────────────────
    {
        "title": "Letters from Carthage",
        "author": "Amara Okonjo",
        "narrator": "Fatima Hassan",
        "description": "A slave translator holds the fate of two civilisations in her words.",
        "synopsis": (
            "Set during the final days of the Punic Wars, Tanit works as a translator between "
            "Roman commanders and Carthaginian elders. Both sides trust her. Both sides are wrong. "
            "A sweeping story of loyalty, language, and survival."
        ),
        "genre": "Historical Fiction",
        "categories": ["Historical", "War", "Drama"],
        "published_year": 2019,
        "price": 13.49,
        "credits_required": 1,
        "rating": 4.9,
        "review_count": 782,
        "cover_image_url": cover(707),
        "chapters": make_named_chapters([
            "The Auction Block, 149 BC",
            "Two Masters, One Tongue",
            "The Roman Commander's Questions",
            "What Survives in Language",
            "The Elder Council's Silence",
            "A Letter That Cannot Be Sent",
            "Fire at the Harbour",
            "The Words She Chose Not to Translate",
            "Treachery or Mercy",
            "The Siege Begins",
            "What the Romans Don't Know",
            "A Door Left Open",
            "The Final Council",
            "Flames and Ink",
            "One Word Left Out",
            "The Survivor's Journal",
            "Ash",
            "The Last Letter",
            "Historical Note",
            "Glossary of Latin and Punic Terms",
            "Recommended Reading",
            "Author's Personal Connection to Carthage",
            "Bonus: The Commander's Private Record",
            "Epilogue: Alexandria, 130 BC",
        ], avg_minutes=32),
        "is_store_item": True,
        "created_at": NOW - timedelta(days=120),
    },

    # ── Romance ───────────────────────────────────────────────────────────────
    {
        "title": "The Second Time in Paris",
        "author": "Celeste Dubois",
        "narrator": "Isabelle Laurent",
        "description": "A decade after their first goodbye, two architects meet on the same bridge.",
        "synopsis": (
            "Nadia never expected to see Jules again. He left without a word; she rebuilt without "
            "him. Now they're both commissioned for the same renovation project in the 7th "
            "arrondissement, and the blueprints for keeping their distance are already crumbling."
        ),
        "genre": "Romance",
        "categories": ["Romance", "Contemporary", "Drama"],
        "published_year": 2021,
        "price": 10.99,
        "credits_required": 1,
        "rating": 4.5,
        "review_count": 903,
        "cover_image_url": cover(808),
        "chapters": make_named_chapters([
            "The Bridge at Pont de l'Alma",
            "Ten Years of Forgetting",
            "The Commission",
            "Shared Office, Separate Silences",
            "The Blueprint Disagreement",
            "What He Left Unsaid",
            "Site Visit, Rue du Bac",
            "Coffee and Old Arguments",
            "The Foundation Crack",
            "What Nadia Built Without Him",
            "Jules Explains — Too Late?",
            "The Night Before the Deadline",
            "Renovation Complete",
            "Epilogue: The Same Bridge",
            "Bonus Scene: Ten Years Earlier",
        ], avg_minutes=24),
        "is_store_item": True,
        "created_at": NOW - timedelta(days=50),
    },

    # ── Non-fiction / Self-help ───────────────────────────────────────────────
    {
        "title": "Deep Systems: How Experts Really Think",
        "author": "Dr. Owen Park",
        "narrator": "Owen Park",
        "description": "The cognitive science behind elite decision-making — and how to acquire it.",
        "synopsis": (
            "Drawing on 15 years of research with surgeons, chess grandmasters, and combat pilots, "
            "Dr. Park reveals the hidden mental models that separate competent from exceptional. "
            "Practical frameworks you can start applying today."
        ),
        "genre": "Non-Fiction",
        "categories": ["Self-Help", "Psychology", "Productivity"],
        "published_year": 2020,
        "price": 16.99,
        "credits_required": 2,
        "rating": 4.7,
        "review_count": 1204,
        "cover_image_url": cover(909),
        "chapters": make_named_chapters([
            "Introduction: The Gap Between Competent and Expert",
            "Part I — What Mental Models Actually Are",
            "The Chess Grandmaster's Secret",
            "How Surgeons Decide in Three Seconds",
            "Combat Pilots and the OODA Loop",
            "Part II — Building Your Own System",
            "Pattern Recognition Is a Skill, Not a Gift",
            "The Deliberate Mistake: Learning at Edge Cases",
            "Stress-Testing Your Assumptions",
            "Part III — Organisations That Think",
            "When Systems Fail: A Case Study",
            "Psychological Safety Is Not Comfort",
            "Epilogue: The Lifelong Learner",
        ], avg_minutes=35),
        "is_store_item": True,
        "created_at": NOW - timedelta(days=200),
    },

    # ── Horror ────────────────────────────────────────────────────────────────
    {
        "title": "What the Walls Remember",
        "author": "Silas Crane",
        "narrator": "Gregory Mast",
        "description": "The house was sold five times in ten years. Each family left in the middle of the night.",
        "synopsis": (
            "When journalist Petra Halm investigates the Voss Estate for a true-crime podcast, "
            "she expects urban legend. What she records instead dismantles everything she believes "
            "about the boundary between memory and presence."
        ),
        "genre": "Horror",
        "categories": ["Horror", "Paranormal", "Mystery"],
        "published_year": 2022,
        "price": 11.49,
        "credits_required": 1,
        "rating": 4.4,
        "review_count": 367,
        "cover_image_url": cover(1010),
        "chapters": make_named_chapters([
            "The Estate Listing",
            "Episode One: First Night in the Voss House",
            "The Neighbours Don't Look Up",
            "Tape 3: A Sound Behind the Wallpaper",
            "The Previous Families — What Records Survive",
            "Episode Two: The Locked Room Opens",
            "The Voice on the Recording",
            "Who Was Elsa Voss",
            "Static",
            "Episode Three: Petra Doesn't Leave",
            "What the Walls Remember",
            "The Archive Photograph",
            "Tape 11: The Confession",
            "Episode Four (Incomplete)",
            "Transcript — Final Broadcast",
            "Found Audio",
            "Epilogue: The New Owners",
        ], avg_minutes=26),
        "is_store_item": True,
        "created_at": NOW - timedelta(days=21),
    },

    # ── Children's ────────────────────────────────────────────────────────────
    {
        "title": "The Last Lighthouse Keeper",
        "author": "Maeve Sullivan",
        "narrator": "Alice Chen",
        "description": "A girl, a lighthouse, and the sea-creature no one else believes in.",
        "synopsis": (
            "Ten-year-old Finn has spent her whole life in the lighthouse while her father keeps "
            "the light. When a storm washes something enormous onto the rocks, she's the only one "
            "brave enough — or small enough — to help it home."
        ),
        "genre": "Children's",
        "categories": ["Children's", "Adventure", "Fantasy"],
        "published_year": 2020,
        "price": 8.99,
        "credits_required": 1,
        "rating": 4.9,
        "review_count": 1587,
        "cover_image_url": cover(1111),
        "chapters": make_named_chapters([
            "Finn and the Keeper's Light",
            "The Storm Before Breakfast",
            "Something on the Rocks",
            "Dad Says It's Just a Seal",
            "Blue Eyes the Size of Dinner Plates",
            "Feeding a Secret",
            "The Harbour Master's Questions",
            "Low Tide Agreement",
            "The Name She Gave It",
            "When It Was Time",
        ], avg_minutes=18),
        "is_store_item": True,
        "created_at": NOW - timedelta(days=180),
    },

    # ── Premium (Theatrical) ──────────────────────────────────────────────────
    # These books have is_premium=True: every named character is voiced by a
    # dedicated AI narrator, creating an immersive full-cast experience.
    {
        "title": "Courts of the Crimson Crown",
        "author": "Seraphina Vale",
        "narrator": "Full Cast",  # theatrical — many voices
        "description": (
            "Six noble houses. One empty throne. Everyone is lying — "
            "and every voice sounds different."
        ),
        "synopsis": (
            "When King Aldric dies without an heir, the six noble houses of Verenthal each send "
            "a champion to the Crimson Courts. The negotiations are civil. The assassinations are "
            "not. Told through the eyes of six rivals who each believe they are the hero of this "
            "story, this theatrical audiobook gives every major character their own distinct voice "
            "— bringing the politics, betrayals, and forbidden alliances to vivid life."
        ),
        "genre": "Fantasy",
        "categories": ["Fantasy", "Political", "Drama", "Premium"],
        "published_year": 2024,
        "price": 14.99,
        "credits_required": 1,
        "is_premium": True,
        "premium_price": 24.99,
        "premium_credits": 2,
        "rating": 4.8,
        "review_count": 541,
        "cover_image_url": cover(2001),
        "chapters": make_named_chapters([
            "Prologue: The King is Dead",
            "House Valdris Arrives — Voice of Lord Edric",
            "House Morrow Arrives — Voice of Lady Sable",
            "House Kestrel Arrives — Voice of Commander Thane",
            "House Vael Arrives — Voice of Ambassador Lirien",
            "House Dusk Arrives — Voice of the Spymaster",
            "House Crane Arrives — Voice of Scholar Petra",
            "The First Banquet: Six Perspectives",
            "Back Channels — Lord Edric and Lady Sable",
            "The Map Room — Commander Thane Alone",
            "What the Spymaster Knows",
            "Scholar Petra Finds the Old Law",
            "The First Vote: Three Ayes, Three Nays",
            "Night of Knives",
            "The Morning After — Who Is Missing",
            "Lirien Makes a Deal",
            "The Spymaster Chooses a Side",
            "The Second Vote: Treachery on the Floor",
            "Blood on the Crimson Dais",
            "The Survivor Speaks — All Voices, One Room",
            "Epilogue: The New Throne",
        ], avg_minutes=27),
        "is_store_item": True,
        "created_at": NOW - timedelta(days=10),
    },
    {
        "title": "Nine Voices",
        "author": "Ivan Marsh",
        "narrator": "Full Cast",
        "description": (
            "A murder. Nine witnesses. Nine completely different stories — "
            "each narrated by the person who lived it."
        ),
        "synopsis": (
            "Detective Rowan Adler has nine witnesses to the same event. The problem: no two "
            "accounts agree on a single detail. Structured as nine consecutive first-person "
            "narrations — each voiced by a unique performer — *Nine Voices* is a psychological "
            "thriller designed specifically for the theatrical audio format. The truth emerges "
            "only in the silences between stories."
        ),
        "genre": "Thriller",
        "categories": ["Thriller", "Psychological", "Mystery", "Premium"],
        "published_year": 2024,
        "price": 12.99,
        "credits_required": 1,
        "is_premium": True,
        "premium_price": 21.99,
        "premium_credits": 2,
        "rating": 4.9,
        "review_count": 883,
        "cover_image_url": cover(2002),
        "chapters": make_named_chapters([
            "Detective Adler Opens the Case",
            "Voice One: The Neighbour Who Saw Nothing",
            "Voice Two: The Business Partner",
            "Voice Three: The Estranged Sister",
            "Voice Four: The Night-Shift Nurse",
            "Voice Five: The Delivery Driver",
            "Voice Six: The Ex-Lover",
            "Voice Seven: The Child Upstairs",
            "Voice Eight: The Second Detective",
            "Voice Nine: The Victim — Recorded Before",
            "Adler Reviews the Transcripts",
            "The One Lie All Nine Voices Told",
            "Confrontation",
            "The Tenth Voice",
            "Epilogue: Adler Closes the File",
        ], avg_minutes=30),
        "is_store_item": True,
        "created_at": NOW - timedelta(days=5),
    },
    {
        "title": "The Kepler Accord",
        "author": "Dr. Yuki Tanaka",
        "narrator": "Full Cast",
        "description": (
            "Humanity's first deep-space crew must negotiate peace with a civilisation that "
            "communicates entirely through emotional tone — not words."
        ),
        "synopsis": (
            "The ISV Kepler carries twelve specialists, twelve worldviews, and one mission: "
            "establish contact with the Aryn — a species whose language has no vocabulary, only "
            "feeling. Each crew member narrates their own experience of the same moments aboard "
            "the ship, creating a multi-layered portrait of courage, fear, and the universal "
            "terror of being misunderstood. Engineered for theatrical audio: twelve performers, "
            "one story."
        ),
        "genre": "Science Fiction",
        "categories": ["Sci-Fi", "First Contact", "Drama", "Premium"],
        "published_year": 2025,
        "price": 16.99,
        "credits_required": 1,
        "is_premium": True,
        "premium_price": 26.99,
        "premium_credits": 2,
        "rating": 4.7,
        "review_count": 317,
        "cover_image_url": cover(2003),
        "chapters": make_named_chapters([
            "Mission Briefing: Commander Chen",
            "Launch Day — Twelve Separate Journals",
            "Month Three: The Linguist Disagrees",
            "Month Three: The Engineer Disagrees Differently",
            "First Aryn Signal — Crew Reactions",
            "The Diplomat Attempts Protocol",
            "The Xenobiologist Feels Something",
            "What Fear Sounds Like at 0.3c",
            "The Ship's Counsellor Logs a Warning",
            "Aryn Vessel at Fifty Kilometres",
            "The Communication Attempt — Ten Voices at Once",
            "Silence After the Broadcast",
            "What They Sent Back",
            "Commander Chen Makes the Call",
            "The Accord — Every Voice, One Moment",
            "Return Transit: Letters Home",
            "Epilogue: What Earth Heard",
        ], avg_minutes=29),
        "is_store_item": True,
        "created_at": NOW - timedelta(days=2),
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _total_duration(chapters: list) -> int:
    return sum(c["duration"] for c in chapters)


async def wipe(db):
    r1 = await db[BOOKS_COL].delete_many({"is_store_item": True})
    r2 = await db[LISTINGS_COL].delete_many({})
    log.info(f"Wiped {r1.deleted_count} books and {r2.deleted_count} listings")


async def seed(db, books: list) -> tuple[int, int]:
    inserted = skipped = 0
    for book in books:
        existing = await db[BOOKS_COL].find_one({"title": book["title"]})
        if existing:
            log.info(f"  SKIP  '{book['title']}' (already exists)")
            skipped += 1
            continue

        book_id = str(uuid.uuid4())
        now = book.get("created_at", NOW)

        # ── Insert into books collection ────────────────────────────────────
        book_doc = {
            "_id": book_id,
            "id": book_id,
            "title": book["title"],
            "author": book["author"],
            "narrator": book.get("narrator"),
            "description": book.get("description"),
            "synopsis": book.get("synopsis"),
            "duration": _total_duration(book["chapters"]),
            "cover_image_url": book.get("cover_image_url"),
            "audio_url": None,
            "sample_audio_url": None,
            "genre": book.get("genre"),
            "categories": book.get("categories", []),
            "rating": book.get("rating", 0.0),
            "review_count": book.get("review_count", 0),
            "price": book.get("price"),
            "credits_required": book.get("credits_required", 1),
            "published_year": book.get("published_year"),
            "is_store_item": True,
            # Premium (theatrical) edition fields
            "is_premium": book.get("is_premium", False),
            "premium_price": book.get("premium_price"),
            "premium_credits": book.get("premium_credits", 2),
            "chapters": book["chapters"],
            "created_at": now,
            "updated_at": now,
        }
        await db[BOOKS_COL].insert_one(book_doc)

        # ── Insert matching store listing ───────────────────────────────────
        listing_id = str(uuid.uuid4())
        listing_doc = {
            "_id": listing_id,
            "id": listing_id,
            "user_id": PUBLISHER_ID,
            "book_id": book_id,
            "title": book["title"],
            "price": book.get("price"),
            "status": "published",
            "total_sales": book.get("review_count", 0) // 3,  # rough estimate
            "revenue": round((book.get("price", 0) or 0) * (book.get("review_count", 0) // 3), 2),
            "rating": book.get("rating", 0.0),
            "description": book.get("description"),
            "cover_image_url": book.get("cover_image_url"),
            "admin_feedback": None,
            "published_at": now,
            "created_at": now,
            "updated_at": now,
        }
        await db[LISTINGS_COL].insert_one(listing_doc)

        log.info(f"  INSERT '{book['title']}' [{book.get('genre')}] ${book.get('price')}")
        inserted += 1

    return inserted, skipped


async def check(db):
    books_count = await db[BOOKS_COL].count_documents({"is_store_item": True})
    listings_count = await db[LISTINGS_COL].count_documents({})
    log.info(f"Store books : {books_count}")
    log.info(f"Listings    : {listings_count}")
    log.info("\nBooks by genre:")
    pipeline = [
        {"$match": {"is_store_item": True}},
        {"$group": {"_id": "$genre", "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}}
    ]
    async for doc in db[BOOKS_COL].aggregate(pipeline):
        log.info(f"  {doc['_id']:25s} {doc['count']}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main(wipe_first: bool, check_only: bool):
    client = AsyncIOMotorClient(MONGODB_URL, serverSelectionTimeoutMS=5000)
    try:
        await client.admin.command("ping")
        log.info(f"Connected to MongoDB: {MONGODB_URL}  db={MONGODB_DB}")
    except Exception as e:
        log.error(f"Cannot connect to MongoDB: {e}")
        sys.exit(1)

    db = client[MONGODB_DB]

    if check_only:
        await check(db)
        client.close()
        return

    if wipe_first:
        await wipe(db)

    inserted, skipped = await seed(db, SEED_BOOKS)
    log.info(f"\nDone — {inserted} inserted, {skipped} skipped")
    client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed sample books into backend MongoDB")
    parser.add_argument("--wipe",  action="store_true", help="Remove existing store books first")
    parser.add_argument("--check", action="store_true", help="Print current counts and exit")
    args = parser.parse_args()

    asyncio.run(main(wipe_first=args.wipe, check_only=args.check))
