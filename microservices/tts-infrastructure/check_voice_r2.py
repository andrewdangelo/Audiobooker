# save as check_voice_r2.py in tts-infrastructure root
import boto3
from botocore.client import Config
from app.core.config_settings import settings

client = boto3.client(
    "s3",
    endpoint_url=settings.R2_ENDPOINT_URL or f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
    aws_access_key_id=settings.R2_ACCESS_KEY_ID,
    aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
    config=Config(signature_version="s3v4"),
    region_name="auto",
)

response = client.list_objects_v2(Bucket=settings.R2_BUCKET_NAME, Prefix="voice_library/")
for obj in response.get("Contents", []):
    print(obj["Key"])