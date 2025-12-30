import httpx
import asyncio
import websockets
import json
import base64

async def prepare_job():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8002/api/v1/tts/audio-stitch/prepare",
            json={
                "chunk_ids": ["0", "1", "2", "3", "4", "5"],
                "crossfade_ms": 0,
                "normalize": True,
                "output_format": "mp3"
            }
        )
        result = response.json()
        print(f"Job ID: {result['job_id']}")
        return result['job_id']

# Get the job ID from the prepare endpoint
job_id = asyncio.run(prepare_job())


async def stream_audio(job_id: str):
    """Stream audio and save to file"""
    
    uri = f"ws://localhost:8002/api/v1/tts/audio-stitch/stream"
    async with websockets.connect(uri) as websocket:
        # Send start message
        await websocket.send(json.dumps({
            "action": "start",
            "job_id": job_id,
            "config": {
                "buffer_size": 8192,
                "bitrate": "128k"
            }
        }))
        
        print("Streaming started...")
        audio_data = bytearray()
        
        # Receive messages from websocket
        while True:
            try:
                message = await websocket.recv()
                data = json.loads(message)
                
                if data["type"] == "metadata":
                    print(f"Duration: {data['data']['total_duration']}s")
                    print(f"Format: {data['data']['format']}")
                    print(f"Chunks: {data['data']['chunks_count']}")
                    
                elif data["type"] == "audio_chunk":
                    # Decode base64 audio data
                    chunk = base64.b64decode(data["data"])
                    audio_data.extend(chunk)
                    
            
            except websockets.exceptions.ConnectionClosed:
                break
        
        with open("audio_output/streamed_audio/streamed_audio.mp3", "wb") as f:
            f.write(audio_data)
        
        print(f"Saved to streamed_audio.mp3 ({len(audio_data)} bytes)")

# Run the fucking stream you bitch
asyncio.run(stream_audio(job_id))

