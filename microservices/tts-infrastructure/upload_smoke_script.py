"""
Upload a minimal smoke test script JSON to R2.
Run from tts-infrastructure root: python upload_smoke_script.py
"""

import boto3
import json
from botocore.client import Config

from app.core.config_settings import settings

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
            "source_chunk_ids": [0],
            "emotion": "narrative, calm",
            "emotion_strength": 0.5
        },
        {
            "speaker": "Narrator",
            "text": "The old house stood at the end of the lane.",
            "page_numbers": [1],
            "source_chunk_ids": [0],
            "emotion": "narrative, calm",
            "emotion_strength": 0.5
        },
        {
            "speaker": "Narrator",
            "text": "Nobody had lived there for thirty years.",
            "page_numbers": [2],
            "source_chunk_ids": [1],
            "emotion": "narrative, calm",
            "emotion_strength": 0.5
        }
    ]
}

client = boto3.client(
    "s3",
    endpoint_url=settings.R2_ENDPOINT_URL or f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
    aws_access_key_id=settings.R2_ACCESS_KEY_ID,
    aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
    config=Config(signature_version="s3v4"),
    region_name="auto",
)

client.put_object(
    Bucket=settings.R2_BUCKET_NAME,
    Key=SCRIPT_R2_KEY,
    Body=json.dumps(script).encode("utf-8"),
    ContentType="application/json",
)

print(f"Uploaded to R2: {SCRIPT_R2_KEY}")