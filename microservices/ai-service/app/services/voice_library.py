import io
import base64
import random
import librosa
import soundfile as sf
from typing import List, Dict, Optional, Tuple
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from scipy.optimize import linear_sum_assignment
import json
import uuid
import httpx

from app.services.ai_text_service import AITextService
from app.services.ai_emb_service import AIEmbeddingService
from app.services.ai_model_factory import ModelProvider

from app.core.config_settings import Settings, settings as default_settings

class VoiceLibraryManager:
    def __init__(
        self,
        mongo_collection,
        r2_session,
        r2_config: Dict,
        text_provider: ModelProvider = ModelProvider.CF,
        text_preset: Optional[str] = "chat-basic",
        emb_provider: ModelProvider = ModelProvider.CF,
        emb_preset: Optional[str] = "embedding-768",
        settings: Settings = default_settings,  # injected, falls back to global
    ):
        self.collection = mongo_collection
        self.r2_session = r2_session
        self.r2_config = r2_config
        self.target_sr = 24000
        self.settings = settings

        self._text_provider = text_provider
        self._text_preset = text_preset
        self._emb_provider = emb_provider
        self._emb_preset = emb_preset

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_voice_description(self, audio_buffer: io.BytesIO) -> str:
        audio_buffer.seek(0)
        audio_bytes = audio_buffer.read()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.cloudflare.com/client/v4/accounts"
                f"/{self.settings.MATT_CF_ACCOUNT_ID}/ai/run/@cf/openai/whisper",
                headers={
                    "Authorization": f"Bearer {self.settings.MATT_CF_AI_TOKEN}",
                    "Content-Type": "application/octet-stream",
                },
                content=audio_bytes,
                timeout=60,
            )

        if response.status_code != 200:
            raise RuntimeError(f"Whisper error {response.status_code}: {response.text}")

        transcript = response.json()["result"]["text"].strip()
        print(f"   Transcript: {transcript[:80]}...")

        return await AITextService.chat_with_system(
            system=(
                "You are a voice analyst. Based on a speech transcript, infer the "
                "speaker's voice traits. Output ONLY a comma-separated list covering: "
                "pitch, tone, accent, character, gender, age. No extra words. You are not allowed to put unknown for any field. Just omit that unknown term in the string"
            ),
            user=f"Transcript of the voice clip:\n\n{transcript}",
            provider=self._text_provider,
            preset=self._text_preset,
        )

    def _clean_audio(
        self,
        audio_stream: io.BytesIO,
        start_time_str: str = "00:00",
        duration_sec: int = 12,
    ) -> Tuple[io.BytesIO, float]:
        """
        Resample, clip, and export audio to a WAV buffer.
        Returns (processed_buffer, actual_duration_seconds).
        """
        audio, sr = librosa.load(audio_stream, sr=None, mono=True)

        minutes, seconds = map(int, start_time_str.split(":"))
        start_sample = int((minutes * 60 + seconds) * sr)
        end_sample = start_sample + int(duration_sec * sr)
        clip = audio[start_sample : min(end_sample, len(audio))]

        if sr != self.target_sr:
            clip = librosa.resample(clip, orig_sr=sr, target_sr=self.target_sr)
            sr = self.target_sr

        out_buffer = io.BytesIO()
        sf.write(out_buffer, clip, sr, format="WAV", subtype="PCM_16")
        out_buffer.seek(0)

        return out_buffer, len(clip) / sr

    async def _upload_to_r2(self, buffer: io.BytesIO, voice_id: str) -> None:
        """Upload processed audio buffer to R2."""
        buffer.seek(0)
        async with self.r2_session.client(
            "s3",
            endpoint_url=(
                f"https://{self.r2_config['account_id']}.r2.cloudflarestorage.com"
            ),
            aws_access_key_id=self.r2_config["access_key"],
            aws_secret_access_key=self.r2_config["secret_key"],
        ) as s3:
            await s3.put_object(
                Bucket=self.r2_config["bucket"],
                Key=f"voice_library/{voice_id}.wav",
                Body=buffer.read(),
                ContentType="audio/wav",
            )

    async def _delete_from_r2(self, voice_id: str) -> None:
        """Delete audio file from R2."""
        async with self.r2_session.client(
            "s3",
            endpoint_url=(
                f"https://{self.r2_config['account_id']}.r2.cloudflarestorage.com"
            ),
            aws_access_key_id=self.r2_config["access_key"],
            aws_secret_access_key=self.r2_config["secret_key"],
        ) as s3:
            await s3.delete_object(
                Bucket=self.r2_config["bucket"],
                Key=f"voice_library/{voice_id}.wav",
            )

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def add_voice(
        self,
        input_audio: io.BytesIO,
        filename: str,
        start_time: str = "00:00",
        is_standard: bool = False,
    ) -> str:
        """
        Process → Describe → Embed → Upload to R2 → Save to Mongo.
        Returns the new voice_id string.

        Args:
            is_standard: Mark True for safe/neutral voices eligible for
                         quick narrator assignment (assign_voice_single quick mode).
        """
        processed_buffer, duration = self._clean_audio(input_audio, start_time)
        description = await self._get_voice_description(processed_buffer)
        embedding = await AIEmbeddingService.generate_embedding(
            description,
            provider=self._emb_provider,
            preset=self._emb_preset,
        )

        voice_id = str(uuid.uuid4())
        await self._upload_to_r2(processed_buffer, voice_id)
        await self.collection.insert_one({
            "_id": voice_id,
            "original_filename": filename,
            "description": description,
            "embedding": embedding,
            "duration": duration,
            "is_standard": is_standard,
        })
        return voice_id

    async def delete_voice_by_id(self, voice_id: str) -> bool:
        """
        Delete a voice from both Mongo and R2.
        Returns True if the document existed and was deleted, False if not found.
        R2 deletion is best-effort — a storage error will not raise.
        """
        result = await self.collection.delete_one({"_id": voice_id})
        if result.deleted_count == 0:
            return False

        try:
            await self._delete_from_r2(voice_id)
        except Exception as e:
            print(f"⚠️  R2 delete failed for {voice_id}: {e}")

        return True

    # ------------------------------------------------------------------
    # Assignment — single voice
    # ------------------------------------------------------------------

    async def assign_voice_single(
        self,
        quick: bool = True,
        character: Optional[Dict] = None,
    ) -> str:
        """
        Assign a single voice (e.g. narrator or lone character).

        quick=True  (default / POC mode)
            Random pick from the is_standard=True pool.
            Zero LLM calls, no character info needed.

        quick=False  (vector search mode)
            Requires a `character` dict.
            Runs HyDE → embed → cosine similarity against the is_standard=False
            pool (falls back to standard pool if no non-standard voices exist).
            Same pipeline as assign_voice_multiple but for one result.

        Returns the voice_id string.
        """
        if quick:
            return await self._assign_single_quick()
        if character is None:
            raise ValueError("character dict is required when quick=False")
        return await self._assign_single_vector(character)

    async def _assign_single_quick(self) -> str:
        """Random pick from the is_standard=True shortlist."""
        cursor = self.collection.find({"is_standard": True}, {"_id": 1})
        pool = await cursor.to_list(length=100)

        if not pool:
            raise ValueError(
                "No standard voices found. "
                "Re-seed with add_voice(..., is_standard=True)."
            )

        chosen_id = str(random.choice(pool)["_id"])
        print(f"✅ Quick assign → {chosen_id}")
        return chosen_id

    async def _assign_single_vector(self, character: Dict) -> str:
        """
        Embed a character profile and return the closest non-standard voice.
        Falls back to the standard pool when no non-standard voices exist.
        """
        cursor = self.collection.find(
            {"is_standard": False},
            {"_id": 1, "description": 1, "embedding": 1},
        )
        pool = await cursor.to_list(length=1000)

        if not pool:
            print("⚠️  No non-standard voices — falling back to standard pool.")
            cursor = self.collection.find(
                {"is_standard": True},
                {"_id": 1, "description": 1, "embedding": 1},
            )
            pool = await cursor.to_list(length=1000)

        if not pool:
            raise ValueError("Voice library is empty.")

        bio = await self._summarize_character_for_search(character)
        query_emb = await AIEmbeddingService.generate_embedding(
            bio,
            provider=self._emb_provider,
            preset=self._emb_preset,
        )

        pool_embs = np.array([v["embedding"] for v in pool])
        scores = cosine_similarity(np.array(query_emb).reshape(1, -1), pool_embs)[0]
        best_idx = int(np.argmax(scores))
        chosen = pool[best_idx]

        print(
            f"✅ Vector assign → {chosen['_id']} "
            f"| score {scores[best_idx]:.3f} "
            f"| {chosen.get('description', '')[:60]}…"
        )
        return str(chosen["_id"])

    # ------------------------------------------------------------------
    # Assignment — multiple voices (full cast)
    # ------------------------------------------------------------------

    async def assign_voice_multiple(self, characters: List[Dict]) -> Dict[str, str]:
        """
        Optimised voice assignment for a full cast.
        Draws only from the is_standard=False pool so standard narrator
        voices are never consumed by character assignment.

        Pipeline: HyDE summary → embed → Hungarian algorithm → LLM veto loop.
        Returns {character_name: voice_id}.
        """
        cursor = self.collection.find(
            {"is_standard": False},
            {"_id": 1, "description": 1, "embedding": 1},
        )
        all_voices = await cursor.to_list(length=1000)

        if not all_voices:
            raise ValueError(
                "No non-standard voices in the library for character assignment. "
                "Add voices with is_standard=False."
            )
        if len(all_voices) < len(characters):
            raise ValueError(
                f"Library has {len(all_voices)} non-standard voices but "
                f"{len(characters)} characters need unique assignment."
            )

        library_ids = [str(v["_id"]) for v in all_voices]
        library_embs = np.array([v["embedding"] for v in all_voices])

        char_data = []
        for char in characters:
            bio = await self._summarize_character_for_search(char)
            emb = await AIEmbeddingService.generate_embedding(
                bio, provider=self._emb_provider, preset=self._emb_preset,
            )
            char_data.append({"name": char["name"], "bio": bio, "embedding": emb})

        cost_matrix = 1.0 - cosine_similarity(
            np.array([c["embedding"] for c in char_data]), library_embs
        )

        current_assignments: List[Dict] = []
        for attempt in range(5):
            char_indices, voice_indices = linear_sum_assignment(cost_matrix)
            current_assignments = [
                {
                    "char_idx": int(ci),
                    "voice_idx": int(vi),
                    "char_name": char_data[ci]["name"],
                    "char_bio": char_data[ci]["bio"],
                    "voice_desc": all_voices[vi]["description"],
                    "voice_id": library_ids[vi],
                }
                for ci, vi in zip(char_indices, voice_indices)
            ]

            vetoes = await self._llm_validate_char_assignments(current_assignments)
            if not vetoes:
                print(f"✅ Voice selection approved on attempt {attempt + 1}")
                break

            for c_idx, v_idx in vetoes:
                cost_matrix[c_idx, v_idx] = 99.9
            print(f"LLM vetoed {len(vetoes)} choices — re-solving…")

        return {a["char_name"]: a["voice_id"] for a in current_assignments}

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    async def manual_vector_search(
        self, query_embedding: List[float], limit: int = 5
    ) -> List[Dict]:
        """
        In-memory cosine-similarity search across the full library.
        Returns top-k voices (without embedding arrays) sorted by score desc.
        """
        cursor = self.collection.find({}, {"_id": 1, "description": 1, "embedding": 1})
        all_voices = await cursor.to_list(length=1000)

        if not all_voices:
            return []

        scores = cosine_similarity(
            np.array(query_embedding).reshape(1, -1),
            np.array([v["embedding"] for v in all_voices]),
        )[0]

        for i, voice in enumerate(all_voices):
            voice["score"] = float(scores[i])
            del voice["embedding"]

        all_voices.sort(key=lambda x: x["score"], reverse=True)
        return all_voices[:limit]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _llm_validate_char_assignments(
        self, voice_assignments: List[Dict], chunk_size: int = 5
    ) -> List[Tuple[int, int]]:
        """
        Ask the LLM to veto impossible character↔voice pairings.
        Returns list of (char_idx, voice_idx) tuples to reject.
        """
        all_veto_tuples: List[Tuple[int, int]] = []

        for i in range(0, len(voice_assignments), chunk_size):
            chunk = voice_assignments[i : i + chunk_size]
            prompt_rows = "\n".join(
                f"CharacterId: {c['char_idx']}\n"
                f"Character: {c['char_name']} (Bio: {c['char_bio']})\n"
                f"Assigned Voice: {c['voice_desc']}\n---"
                for c in chunk
            )
            prompt = (
                "You are an Audiobook Casting Director. Review these character↔voice assignments:\n\n"
                f"{prompt_rows}\n\n"
                "Identify 'Impossible' matches: wrong gender, wildly wrong age, "
                "or tone that directly contradicts the character.\n"
                'Return ONLY a JSON object: {"rejections": [<characterId>, ...]}\n'
                'If all are fine: {"rejections": []}\n'
                "No other words."
            )

            raw = await AITextService.chat(
                prompt_messages=[["user", prompt]],
                provider=self._text_provider,
                preset=self._text_preset,
            )
            print(f"🚀 VETOS: {raw}")

            data = json.loads(raw)
            for char_id in data.get("rejections", []):
                for c in chunk:
                    if c["char_idx"] == char_id:
                        all_veto_tuples.append((c["char_idx"], c["voice_idx"]))

        return all_veto_tuples

    async def _summarize_character_for_search(self, character_json: Dict) -> str:
        """HyDE: generate the ideal voice description for a character before embedding."""
        return await AITextService.chat_with_system(
            system=(
                "You output ONLY a comma-separated list of voice traits that would "
                "suit this character. No extra words."
            ),
            user=(
                "Convert this character profile into a concise voice description:\n"
                f"{json.dumps(character_json)}"
            ),
            provider=self._text_provider,
            preset=self._text_preset,
        )