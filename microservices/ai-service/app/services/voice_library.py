import io
import base64
import librosa
import soundfile as sf
from typing import List, Dict, Tuple
from openai import AsyncOpenAI
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from scipy.optimize import linear_sum_assignment 
import json
from app.services.huggingface_service import HuggingFaceService
import uuid

from ai_emb_service import AIEmbeddingService   # Use this to generate embeddings

class VoiceLibraryManager:
    def __init__(self, openai_client: AsyncOpenAI, text_service: AITextService, embedding_service: AIEmbeddingService, mongo_collection, r2_session, r2_config: Dict):
        # self.openai = openai_client
        # self.hf = hf_service
        self.embedding_service = embedding_service
        self.text_service = text_service
        self.collection = mongo_collection
        self.r2_session = r2_session
        self.r2_config = r2_config
        self.bucket = r2_config
        self.target_sr = 24000

    async def _get_voice_description(self, audio_buffer: io.BytesIO) -> str:
        """
        Call speech-to-text model 
        """
        audio_buffer.seek(0)
        audio_data = audio_buffer.read()
        audio_b64 = base64.b64encode(audio_data).decode('utf-8')

        # Replace with cloudflare-deployed model
        response = await self.openai.chat.completions.create(
            model="gpt-4o-audio-preview",
            modalities=["text"],
            messages=[
                {
                    "role": "system",
                    "content": "Analyze the audio. Provide an accurate and useful concise description of: pitch, tone, accent, character, gender, and age. Output is a comma separated list of each key-value as natural text. Nothing else. No extra words. Just the traits."
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Characterize this voice clip."},
                        {"type": "input_audio", "input_audio": {"data": audio_b64, "format": "wav"}}
                    ]
                }
            ]
        )

        # Flatten into string format optimized for vector search
        return response.choices[0].message.content

    # Obsolete - for OpenAI
    async def _get_embedding(self, text: str) -> List[float]:
        """
        Generates a vector embedding for the text description.
        """
        # TODO: Replace with huggingface
        response = await self.openai.embeddings.create(
            input=text,
            model="text-embedding-3-small"
        )
        return response.data[0].embedding

    # Considering removing this and making sure the audio is already tweaked and adjusted beforehand
    def _clean_audio(self, audio_stream: io.BytesIO, start_time_str: str = "00:00", duration_sec: int = 12) -> Tuple[io.BytesIO, float]:
        """
        Resamples, clips, and prepares audio for the library.
        Returns: (Processed Buffer, actual duration)
        """
        # Load audio (automatically converts to mono)
        audio, sr = librosa.load(audio_stream, sr=None, mono=True)

        # Extract segment
        minutes, seconds = map(int, start_time_str.split(':'))
        start_sample = int((minutes * 60 + seconds) * sr)
        end_sample = start_sample + int(duration_sec * sr)
        
        # Guard against short audio
        clip = audio[start_sample:min(end_sample, len(audio))]

        # Resample to target SR
        if sr != self.target_sr:
            clip = librosa.resample(clip, orig_sr=sr, target_sr=self.target_sr)
            sr = self.target_sr

        # Export to Buffer
        out_buffer = io.BytesIO()
        sf.write(out_buffer, clip, sr, format='WAV', subtype='PCM_16')
        out_buffer.seek(0)
        
        duration = len(clip) / sr
        return out_buffer, duration

<<<<<<< Updated upstream
    async def add_voice(self, input_audio: io.BytesIO, filename: str, start_time: str = "00:00"):
=======
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
                Key=f"voice_library/processed_voice_clips/{voice_id}.wav",
                Body=buffer.read(),
                ContentType="audio/wav"
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
                Key=f"voice_library/processed_voice_clips/{voice_id}.wav"
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
>>>>>>> Stashed changes
        """
        Orchestrates: Process -> Describe -> Embed -> Upload -> Save
        """
        # Audio Processing
        processed_buffer, duration = self._clean_audio(input_audio, start_time)
        
        # Extract voice profile -> use OpenAI For now
        description = await self._get_voice_description(processed_buffer)
        
        # Generate embedding
        # embedding = await self._get_embedding(description)
        embedding = await self.hf.get_embedding(description)

        voice_id = str(uuid.uuid4())
        
        # Upload to R2
        r2_path = f"voice_library/{voice_id}.wav"
        processed_buffer.seek(0)
        
        # You MUST create a client from the session like this:
        async with self.r2_session.client(
            "s3",
            endpoint_url=f"https://{self.r2_config['account_id']}.r2.cloudflarestorage.com",
            aws_access_key_id=self.r2_config['access_key'],
            aws_secret_access_key=self.r2_config['secret_key']
        ) as s3_client:
            # We use put_object for a BytesIO buffer in R2 async flows
            await s3_client.put_object(
                Bucket=self.r2_config['bucket'],
                Key=r2_path,
                Body=processed_buffer.read(),
                ContentType="audio/wav"
            )
        
        # 5. Persist to Mongo (Async)
        doc = {
            "_id": voice_id,
            "original_filename": filename,
            "description": description, # Search-friendly description of the voice
            "embedding": embedding,
            # "r2_path": r2_path,   # Redundant. We know the path from the directory + id
            "duration": duration
        }
        result = await self.collection.insert_one(doc)
        return str(result.inserted_id)
    
    
    # Singular lookup utility
    async def manual_vector_search(self, query_embedding: List[float], limit: int=5 ) -> List[Dict]:
        """
        Perform vector search against voice library in-memory
        """
        cursor = self.collection.find({}, {"_id": 1, "description": 1, "embedding": 1})     # Use description for LLM validation later 
        all_voices = await cursor.to_list(length=1000)

        if not all_voices:
            return []
        
        # Prepare row vectors for similarity
        emb_samples = np.array([v["embedding"] for v in all_voices])
        query_vec = np.array(query_embedding).reshape(1, -1)

        # similarity calculation - array (1, n voices)
        sim_scores = cosine_similarity(query_vec, emb_samples)[0]

        # Sort best matches
        for i, voice in enumerate(all_voices):
            voice['score'] = float(sim_scores[i])
            del voice['embedding']  # Don't need this in memory anymore

        all_voices.sort(key=lambda x: x['score'], reverse=True) # sort descendinhg

        # Return top k samples
        return all_voices[:limit]
    

    async def assign_voice_multiple(self, characters: List[Dict]) -> str:
        """
        Assign voices to multiple characters
        Considers multiple characters at a time to determine optimized best fit
        """

        # Get voice_library collection
        cursor = self.collection.find({}, {"_id": 1, "description": 1, "embedding": 1})     # Use description for LLM validation later 
        all_voices = await cursor.to_list(length=1000)

        if not all_voices:
            return []
        
        if len(all_voices) < len(characters):
            raise Exception("Library size smaller than character count. Unique assignment impossible.")

        # Prepare library samples
        library_ids = [str(v["_id"]) for v in all_voices]
        library_embs = np.array([v["embedding"] for v in all_voices])
        
        # Prepare unassigned character samples
        char_data = []
        for char in characters:
            bio = await self._summarize_character_for_search(char)
            emb = await self.hf.get_embedding(bio)
            char_data.append({
                "name": char['name'],
                "bio": bio, # Search-friendly version of the character description
                "embedding": emb,
                "raw": char
            }) 

        # build similarity matrix
        query_embs = np.array([c["embedding"] for c in char_data])
        sim_matrix = cosine_similarity(query_embs, library_embs)    # (n_chars, K_library_profiles)
        cost_matrix = 1.0 - sim_matrix

        # Iterative Optimization Loop
        final_mapping = {}

        max_attempts = 5
        for attempt in range(max_attempts):
            # Linear Assignment Optimization - calculate best fit for voice profiles without overlap
            char_indices, voice_indices = linear_sum_assignment(cost_matrix)

            current_assignments = []
            for c_idx, v_idx in zip(char_indices, voice_indices):
                current_assignments.append({
                    "char_idx": int(c_idx),
                    "voice_idx": int(v_idx),
                    "char_name": char_data[c_idx]['name'],
                    "char_bio": char_data[c_idx]['bio'],  # LLM-generated description of charater, search friendly 
                    "voice_desc": all_voices[v_idx]['description'],
                    "voice_id": library_ids[v_idx]
                })

            # check for mismatches using LLM
            vetoes = await self._llm_validate_char_assignments(current_assignments)

            if not vetoes:
                print(f"Voice Selection approved on attempt {attempt + 1}")
                return {a['char_name']: a['voice_id'] for a in current_assignments}
            
            # Apply vetos (Set cost to infinity for rejected pairs)
            for c_idx, v_idx in vetoes:  # Loop over list of tuples with Ids
                cost_matrix[c_idx, v_idx] = 99.9
            
            # Re-solve if we got vetos
            print(f"LLM Vetoed {len(vetoes)} choices. Re-solving...")

        return {c['char_name']: c['voice_id'] for c in current_assignments}


    async def _llm_validate_char_assignments(self, voice_assignments: List[Dict], chunk_size=5) -> List[Tuple[int, int]]:
        """
        LLM reviews the total cast list. 
        Returns a list of (char_idx, voice_idx) tuples to REJECT.
        """

        all_veto_tuples = []

        for i in range(0, len(voice_assignments)):
            chunk = voice_assignments[i : i + chunk_size]

            prompt_chunk = "\n".join([
                f"Character: {c['char_name']} (Bio: {c['char_bio']})\n"
                f"Assigned Voice: {c['voice_desc']}\n---"
                f"CharacterId: {c['char_idx']}\n---" 
                for c in chunk
            ])

            prompt = f"""
            You are an Audiobook Casting Director. Review this assignment for the current cast of characters and their assigned voice descriptions :
            {prompt_chunk}

            Identify any 'Impossible' matches. 
            A match is impossible if the gender is wrong, age is wildly off, 
            or the tone contradicts the core character.

            Return ONLY ONE SINGLE JSON object with a 'rejections' key containing a list of character IDs.
            Return JSON EXAMPLE: {{"rejections": ["1", "2"]}}
            If all are good, return {{"rejections": []}}.
            You shall not return any other info or explanations or words. I only want the json object with the rejections ids.
            """

            messages = [{"role": "user", "content": prompt}]
            content = await self.hf.chat_completion(messages)

            print(f"🚀VETOS🚀: {content}")


            data = json.loads(content)
            rejected_ids = data.get("rejections", [])

            # Map character names back to (char_idx, voice_idx) for the matrix
            for char_id in rejected_ids:
                for c in voice_assignments:
                    if c['char_idx'] == char_id:
                        all_veto_tuples.append((c['char_idx'], c['voice_idx']))
        
        return all_veto_tuples

    # HyDE -> generate ideal voice we are expecting before embedding
    async def _summarize_character_for_search(self, character_json: Dict) -> str:
        prompt = f"Convert this character profile into a concise description of their ideal voice. Output is a comma separated list of each key-value as natural text. Here is the profile: {json.dumps(character_json)}"
        messages = [{"role": "user", "content": prompt}]

        return await self.hf.chat_completion(messages)