import asyncio
import io
import os
import sys
import uuid

from tests.client_factory import get_clients
from app.services.voice_library import VoiceLibraryManager

async def test_add_voice_batch():
   # Setup
    openai, hf, collection, r2_session, r2_config = get_clients()
    manager = VoiceLibraryManager(openai, hf, collection, r2_session, r2_config)

    print("🚀 Starting 'Add Voice' Component Test...")

    voices_dir = "voice_samples"
    
    if not os.path.exists(voices_dir):
        print(f"❌ Error: Directory '{voices_dir}' not found.")
        return

    # get .wav sample voices
    voice_files = [f for f in os.listdir(voices_dir) if f.endswith(".wav")]
    
    if not voice_files:
        print(f"Empty directory: No .wav files found in {voices_dir}")
        return

    print(f"🚀 Found {len(voice_files)} voices. Starting batch upload...")

    for filename in voice_files:
        file_path = os.path.join(voices_dir, filename)
        
        print(f"\n--- Processing: {filename} ---")
        # Execution
        try:
            with open(file_path, "rb") as f:
                audio_stream = io.BytesIO(f.read())
                
            print(f"--- Processing audio and generating profile ---")
            voice_id = await manager.add_voice(
                input_audio=audio_stream, 
                filename=f"{filename}",
                start_time="00:00"
            )
            
            print(f"✅ SUCCESS!")
            print(f"Stored Mongo ID: {voice_id}")
            
        except Exception as e:
            print(f"❌ Test Failed: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    # Since the manager is async, we must run it with the asyncio loop
    asyncio.run(test_add_voice_batch())