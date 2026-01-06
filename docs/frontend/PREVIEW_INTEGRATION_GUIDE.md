# Integration Guide: Upload to Preview Flow

## Overview
This guide shows how to integrate the audiobook preview page with your existing upload functionality.

## Step 1: Modify Upload Page

After a successful file upload, redirect to the preview page with the preview ID.

```typescript
// In your Upload.tsx or similar component

import { useNavigate } from 'react-router-dom';

function Upload() {
  const navigate = useNavigate();
  
  const handleUploadComplete = async (file: File, creditType: CreditType) => {
    try {
      // 1. Upload the file
      const formData = new FormData();
      formData.append('file', file);
      formData.append('creditType', creditType);
      
      const uploadResponse = await fetch('/api/uploads', {
        method: 'POST',
        body: formData
      });
      
      const { uploadId } = await uploadResponse.json();
      
      // 2. Create preview request
      const previewResponse = await fetch('/api/previews', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          uploadId,
          creditType
        })
      });
      
      const { previewId } = await previewResponse.json();
      
      // 3. Redirect to preview page
      navigate(`/preview/${previewId}`);
      
    } catch (error) {
      console.error('Upload failed:', error);
      // Handle error
    }
  };
  
  return (
    // Your upload UI
    <div>
      {/* Upload form */}
    </div>
  );
}
```

## Step 2: Backend API Implementation

### Create Preview Endpoint

```python
# Python/FastAPI example

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

class PreviewCreateRequest(BaseModel):
    upload_id: str
    credit_type: str  # 'basic', 'premium', 'author_publisher'

@router.post("/api/previews")
async def create_preview(request: PreviewCreateRequest):
    """
    Create a new preview and start TTS processing
    """
    # 1. Validate upload exists
    upload = await get_upload(request.upload_id)
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    
    # 2. Create preview record
    preview = await db.previews.create({
        "upload_id": request.upload_id,
        "audiobook_id": upload.audiobook_id,
        "credit_type": request.credit_type,
        "processing_status": "processing",
        "processing_progress": 0
    })
    
    # 3. Queue TTS processing job
    await queue_tts_job(preview.id, request.credit_type)
    
    # 4. Return preview ID
    return {"preview_id": preview.id}
```

### Get Preview Data Endpoint

```python
@router.get("/api/previews/{preview_id}")
async def get_preview(preview_id: str):
    """
    Get preview data including processing status and voice options
    """
    preview = await db.previews.get(preview_id)
    if not preview:
        raise HTTPException(status_code=404, detail="Preview not found")
    
    # Get available voices from voice service
    available_voices = await voice_service.get_available_voices()
    
    return {
        "id": preview.id,
        "audiobookId": preview.audiobook_id,
        "creditType": preview.credit_type,
        "processingStatus": preview.processing_status,
        "processingProgress": preview.processing_progress,
        "basicVoicePreviewUrl": preview.basic_voice_url,
        "characterVoices": preview.character_voices,
        "availableVoices": available_voices,
        "estimatedCompletionTime": preview.estimated_time,
        "createdAt": preview.created_at,
        "updatedAt": preview.updated_at
    }
```

### Status Polling Endpoint

```python
@router.get("/api/previews/{preview_id}/status")
async def get_preview_status(preview_id: str):
    """
    Get current processing status (for polling)
    """
    preview = await db.previews.get(preview_id)
    if not preview:
        raise HTTPException(status_code=404, detail="Preview not found")
    
    return {
        "status": preview.processing_status,
        "progress": preview.processing_progress,
        "estimatedTime": preview.estimated_time,
        "errorMessage": preview.error_message
    }
```

## Step 3: TTS Processing Job

```python
# Background job for TTS processing

async def process_tts_preview(preview_id: str, credit_type: str):
    """
    Process TTS preview based on credit type
    """
    try:
        preview = await db.previews.get(preview_id)
        audiobook = await db.audiobooks.get(preview.audiobook_id)
        
        # Update status
        await db.previews.update(preview_id, {
            "processing_status": "processing",
            "processing_progress": 10
        })
        
        # Extract text sample (first chapter or 1000 words)
        text_sample = await extract_text_sample(audiobook.file_path)
        
        if credit_type == "basic":
            # Generate single voice preview
            audio_url = await tts_service.generate_audio(
                text=text_sample,
                voice_id="default_narrator"
            )
            
            await db.previews.update(preview_id, {
                "basic_voice_url": audio_url,
                "processing_progress": 100,
                "processing_status": "completed"
            })
            
        elif credit_type == "premium":
            # Detect characters and assign voices
            characters = await detect_characters(text_sample)
            
            character_voices = []
            for i, character in enumerate(characters):
                progress = 20 + (i * 60 / len(characters))
                await db.previews.update(preview_id, {
                    "processing_progress": progress
                })
                
                # Generate audio for this character
                audio_url = await tts_service.generate_character_audio(
                    text=character.sample_text,
                    voice_id=character.assigned_voice_id
                )
                
                character_voices.append({
                    "characterName": character.name,
                    "characterDescription": character.description,
                    "selectedVoiceId": character.assigned_voice_id,
                    "previewUrl": audio_url
                })
            
            await db.previews.update(preview_id, {
                "character_voices": character_voices,
                "processing_progress": 100,
                "processing_status": "completed"
            })
            
        elif credit_type == "author_publisher":
            # Similar to premium but allow customization
            characters = await detect_characters(text_sample)
            
            # Generate previews with default voices
            character_voices = []
            for character in characters:
                audio_url = await tts_service.generate_character_audio(
                    text=character.sample_text,
                    voice_id="default_voice"
                )
                
                character_voices.append({
                    "characterName": character.name,
                    "characterDescription": character.description,
                    "selectedVoiceId": "default_voice",
                    "previewUrl": audio_url
                })
            
            await db.previews.update(preview_id, {
                "character_voices": character_voices,
                "processing_progress": 100,
                "processing_status": "completed"
            })
        
    except Exception as e:
        await db.previews.update(preview_id, {
            "processing_status": "failed",
            "error_message": str(e)
        })
```

## Step 4: Update Character Voice Selection

```python
@router.put("/api/previews/{preview_id}/character-voices")
async def update_character_voice(
    preview_id: str,
    request: dict
):
    """
    Update voice selection for a character
    """
    character_name = request.get("characterName")
    voice_id = request.get("voiceId")
    
    preview = await db.previews.get(preview_id)
    if not preview:
        raise HTTPException(status_code=404, detail="Preview not found")
    
    # Find character in preview
    character_voices = preview.character_voices
    for cv in character_voices:
        if cv["characterName"] == character_name:
            # Update voice selection
            cv["selectedVoiceId"] = voice_id
            
            # Regenerate preview with new voice
            new_audio_url = await tts_service.generate_character_audio(
                text=cv["sampleText"],
                voice_id=voice_id
            )
            cv["previewUrl"] = new_audio_url
            break
    
    await db.previews.update(preview_id, {
        "character_voices": character_voices
    })
    
    return {"success": True}
```

## Step 5: Confirm and Start Full Conversion

```python
@router.post("/api/previews/{preview_id}/confirm")
async def confirm_preview(preview_id: str):
    """
    Confirm voice selections and start full audiobook conversion
    """
    preview = await db.previews.get(preview_id)
    if not preview:
        raise HTTPException(status_code=404, detail="Preview not found")
    
    # Create full conversion job
    conversion = await db.conversions.create({
        "audiobook_id": preview.audiobook_id,
        "credit_type": preview.credit_type,
        "voice_selections": preview.character_voices,
        "status": "queued"
    })
    
    # Queue full TTS conversion
    await queue_full_conversion(conversion.id)
    
    return {"conversion_id": conversion.id}
```

## Example Flow Diagram

```
User uploads file
      ↓
POST /api/uploads
      ↓
Upload ID returned
      ↓
POST /api/previews
      ↓
Preview ID returned
      ↓
Navigate to /preview/{previewId}
      ↓
GET /api/previews/{previewId} (initial load)
      ↓
Display processing status
      ↓
Poll GET /api/previews/{previewId}/status
      ↓
Processing completes
      ↓
Display voice previews
      ↓
[Author/Publisher only] Select voices
      ↓
PUT /api/previews/{previewId}/character-voices
      ↓
User confirms
      ↓
POST /api/previews/{previewId}/confirm
      ↓
Full conversion starts
      ↓
Navigate to /library
```

## Environment Variables

Add these to your `.env` file:

```bash
# TTS Service
TTS_API_URL=https://your-tts-service.com
TTS_API_KEY=your_api_key

# Preview Settings
PREVIEW_SAMPLE_LENGTH=1000  # words
PREVIEW_GENERATION_TIMEOUT=300  # seconds
MAX_PREVIEW_DURATION=120  # seconds of audio

# Voice Options
DEFAULT_NARRATOR_VOICE=voice-narrator-01
AVAILABLE_VOICES=voice-1,voice-2,voice-3
```

## Testing

Test the complete flow:

```bash
# 1. Upload a file
curl -X POST http://localhost:3000/api/uploads \
  -F "file=@test-book.pdf" \
  -F "creditType=premium"

# 2. Create preview
curl -X POST http://localhost:3000/api/previews \
  -H "Content-Type: application/json" \
  -d '{"uploadId": "upload-123", "creditType": "premium"}'

# 3. Check status
curl http://localhost:3000/api/previews/preview-456/status

# 4. Get preview data
curl http://localhost:3000/api/previews/preview-456

# 5. Update character voice
curl -X PUT http://localhost:3000/api/previews/preview-456/character-voices \
  -H "Content-Type: application/json" \
  -d '{"characterName": "John Doe", "voiceId": "voice-2"}'

# 6. Confirm and start conversion
curl -X POST http://localhost:3000/api/previews/preview-456/confirm
```

---

**Note:** This is a simplified integration guide. Adjust paths, authentication, and error handling based on your specific backend architecture.
