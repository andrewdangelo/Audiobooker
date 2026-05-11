# Smoke Test Guide — Book Generation Pipeline
## Testing via /docs with no pdf-processor involvement

---

## What you need before starting

| Requirement | Where it lives | Status |
|---|---|---|
| One `is_standard=True` voice in MongoDB | ai-service voice_library collection | ✅ Check first (step 1) |
| That voice's WAV file in R2 | `voice_library/{voice_id}.wav` | ✅ Check first (step 1) |
| A script JSON uploaded to R2 | `processed_audiobooks/smoke_test_script.json` | 🔧 You create this (step 2) |
| ai-service running | localhost:8000 (or your PORT) | 🔧 Terminal 1 |
| tts-infrastructure running | localhost:8003 (or your PORT) | 🔧 Terminal 2 |

---

## Step 1 — Verify your voice data

Open ai-service /docs and call:

```
GET /api/v1/ai/voice-library/voices
```

Look at the response. You need at least one entry where `is_standard` is `true`.

**If all your voices have `is_standard: false`**, pick one voice_id from the list and call:

```
PATCH /api/v1/ai/voice-library/voices/{voice_id}
Body: { "is_standard": true }
```

Pick whichever voice you want to use as the narrator for the test.

Now confirm the WAV file exists in R2. The path the service looks for is:

```
voice_library/{voice_id}.wav
```

> ⚠️  IMPORTANT: There is a path mismatch in the older test_tts_chunks.py POC —
> it looked for `voice_library/processed_voice_clips/{voice_id}.wav`.
> The actual upload path in VoiceLibraryManager._upload_to_r2() is
> `voice_library/{voice_id}.wav` (no `processed_voice_clips` subfolder).
> The new book_generation_service.py uses the correct path.
> If your voices were added via add_voice(), they are at the correct path already.

---

## Step 2 — Upload a smoke test script JSON to R2

You need a script file at a known R2 key. The easiest way is a small Python script.
Run this once from anywhere that has your R2 credentials (e.g. the ai-service dir):

```python
# save as: upload_smoke_script.py
# run with: python upload_smoke_script.py

import boto3
import json
from botocore.client import Config

# Fill these in from your .env
R2_ACCOUNT_ID      = "your_account_id"
R2_ACCESS_KEY_ID   = "your_access_key_id"
R2_SECRET_ACCESS_KEY = "your_secret_access_key"
R2_BUCKET_NAME     = "your_bucket_name"

SCRIPT_R2_KEY = "processed_audiobooks/smoke_test_script.json"

script = {
    "characters": [
        {"name": "Narrator", "description": "Narration", "gender": "NEUTRAL"}
    ],
    "script": [
        {
            "speaker": "Narrator",
            "text": "It was a dark and stormy night.",
            "page_numbers": [1],
            "source_chunk_ids": [0]
        },
        {
            "speaker": "Narrator",
            "text": "The old house stood at the end of the lane.",
            "page_numbers": [1],
            "source_chunk_ids": [0]
        },
        {
            "speaker": "Narrator",
            "text": "Nobody had lived there for thirty years.",
            "page_numbers": [2],
            "source_chunk_ids": [1]
        }
    ]
}

client = boto3.client(
    "s3",
    endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
    aws_access_key_id=R2_ACCESS_KEY_ID,
    aws_secret_access_key=R2_SECRET_ACCESS_KEY,
    config=Config(signature_version="s3v4"),
    region_name="auto",
)

client.put_object(
    Bucket=R2_BUCKET_NAME,
    Key=SCRIPT_R2_KEY,
    Body=json.dumps(script).encode("utf-8"),
    ContentType="application/json",
)

print(f"Uploaded to R2: {SCRIPT_R2_KEY}")
```

Run it:
```bash
python upload_smoke_script.py
```

Keep a note of the key: `processed_audiobooks/smoke_test_script.json`

---

## Step 3 — Start the services

Terminal 1 — ai-service:
```bash
cd microservices/ai-service
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Watch for this line in the logs before proceeding:
```
VoiceLibraryManager initialised
```

Terminal 2 — tts-infrastructure:
```bash
cd microservices/tts-infrastructure
uvicorn main:app --host 127.0.0.1 --port 8003 --reload
```

Watch for:
```
Redis connected: localhost:6379
```

---

## Step 4 — Trigger the generation job

Open tts-infrastructure /docs at:
```
http://localhost:8003/docs
```

Find and expand:
```
POST /api/v1/tts/book-generation/start
```

Click **Try it out**, paste this body (use any UUID for book_id):

```json
{
  "book_id": "11111111-1111-1111-1111-111111111111",
  "script_r2_key": "processed_audiobooks/smoke_test_script.json",
  "user_id": "test-user-001"
}
```

Hit **Execute**.

Expected response (202):
```json
{
  "job_id": "some-uuid-here",
  "status": "accepted",
  "message": "Audio generation job queued"
}
```

Copy the `job_id`.

---

## Step 5 — Poll job status

In the same /docs page, find:
```
GET /api/v1/tts/book-generation/job/{job_id}
```

Paste your job_id and hit Execute. Refresh every few seconds.

**What you should see as it progresses:**

| progress | pipeline_stage | message |
|---|---|---|
| 5 | downloading_script | Downloading script from R2 |
| 10 | voice_selection | Selecting narrator voice |
| 15 | downloading_voice | Downloading voice sample |
| ~30–90 | tts_generation | Generating audio: 1/3 chunks |
| 100 | completed | Audio generation complete: 3/3 chunks |

**Completed response looks like:**
```json
{
  "job_id": "...",
  "status": "completed",
  "progress": 100,
  "pipeline_stage": "completed",
  "total_chunks": 3,
  "chunks_completed": 3,
  "chunks_failed": 0,
  "voice_id": "the-voice-id-that-was-picked",
  "result": {
    "book_id": "11111111-1111-1111-1111-111111111111",
    "total_chunks": 3,
    "chunks_completed": 3,
    "chunks_failed": 0,
    "chunk_r2_keys": [
      "audiobook_chunks/11111111-1111-1111-1111-111111111111/0.wav",
      "audiobook_chunks/11111111-1111-1111-1111-111111111111/1.wav",
      "audiobook_chunks/11111111-1111-1111-1111-111111111111/2.wav"
    ],
    "voice_id": "the-voice-id-that-was-picked"
  }
}
```

---

## What a failure looks like and what it means

**status: failed, pipeline_stage: voice_selection**
→ No `is_standard=True` voice in MongoDB. Go back to Step 1 and PATCH one.

**status: failed, pipeline_stage: downloading_script**
→ The script JSON key doesn't exist in R2. Re-run upload_smoke_script.py.

**status: failed, pipeline_stage: downloading_voice**
→ The voice WAV is missing from R2 at `voice_library/{voice_id}.wav`.
  This means the voice exists in MongoDB but the R2 upload failed when it
  was originally added. Re-add it via POST /voice-library/voices.

**status: failed, pipeline_stage: tts_generation (chunks_failed > 0)**
→ HF inference endpoint is down or rejecting requests. Check the
  tts-infrastructure terminal logs — the error from ai-service will be
  printed there with the full HTTP response.

**job not found (404 on GET /job/{job_id})**
→ Redis TTL expired (48 hours) or Redis restarted. Just re-trigger.

---

## Verifying the output in R2

After a successful run, confirm the chunk WAVs exist. Quick check using boto3:

```python
# save as: check_r2_chunks.py

import boto3
from botocore.client import Config

R2_ACCOUNT_ID        = "your_account_id"
R2_ACCESS_KEY_ID     = "your_access_key_id"
R2_SECRET_ACCESS_KEY = "your_secret_access_key"
R2_BUCKET_NAME       = "your_bucket_name"
BOOK_ID              = "11111111-1111-1111-1111-111111111111"

client = boto3.client(
    "s3",
    endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
    aws_access_key_id=R2_ACCESS_KEY_ID,
    aws_secret_access_key=R2_SECRET_ACCESS_KEY,
    config=Config(signature_version="s3v4"),
    region_name="auto",
)

response = client.list_objects_v2(
    Bucket=R2_BUCKET_NAME,
    Prefix=f"audiobook_chunks/{BOOK_ID}/",
)

objects = response.get("Contents", [])
if not objects:
    print("No chunks found — generation may not have completed.")
else:
    for obj in objects:
        print(f"{obj['Key']}  ({obj['Size']:,} bytes)")
```

Run it:
```bash
python check_r2_chunks.py
```

If you see three `.wav` files with non-zero sizes, the pipeline is working end to end.
