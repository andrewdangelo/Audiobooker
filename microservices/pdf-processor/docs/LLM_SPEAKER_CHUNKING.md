# LLM Speaker Chunking Integration

## Overview

The PDF processor now includes automatic LLM-based speaker chunking functionality. After processing a PDF and creating the standard chunk-based JSON output, the system can optionally send the processed data through an OpenAI-powered speaker attribution pipeline that converts prose into speaker-attributed script lines.

## How It Works

1. **Standard PDF Processing**: PDF is downloaded from R2, text is extracted, and chunks are created
2. **Upload Processed JSON**: The chunked JSON is uploaded to R2 as `*_processed.json`
3. **LLM Speaker Chunking** (if enabled): The processed JSON is analyzed by an LLM to:
   - Discover characters from the text
   - Parse prose into dialogue and narration
   - Attribute each line to a specific speaker
   - Create chapter markers
4. **Upload Script JSON**: The speaker-attributed script is uploaded to R2 as `*_script.json`

## Configuration

Add these environment variables to your `.env` file:

```bash
# Required for LLM chunking
OPENAI_API_KEY=sk-your-api-key-here

# Optional - customize LLM behavior
ENABLE_LLM_CHUNKING=true           # Enable/disable automatic LLM chunking
LLM_MODEL=gpt-4o                   # OpenAI model to use
LLM_CONCURRENCY=5                  # Number of concurrent API requests
LLM_MAX_CHARS_PER_WINDOW=35000    # Max chars per LLM window
LLM_DISCOVERY_CHARS=30000         # Chars to analyze for character discovery
```

## Output Format

### Processed JSON (`*_processed.json`)
Standard PDF processing output with chunks:
```json
{
  "r2_key": "...",
  "total_pages": 100,
  "total_chunks": 50,
  "chunks": [
    {
      "chunk_id": 1,
      "text": "Chapter content...",
      "page_numbers": [1, 2],
      "character_count": 1000
    }
  ]
}
```

### Script JSON (`*_script.json`)
LLM-processed speaker-attributed script:
```json
{
  "characters": [
    {
      "name": "Narrator",
      "description": "Narration / description",
      "gender": "NEUTRAL",
      "suggestedVoiceId": "professional-narrator"
    },
    {
      "name": "John",
      "description": "Main character, young man",
      "gender": "MALE",
      "suggestedVoiceId": "male-young-energetic"
    }
  ],
  "script": [
    {
      "speaker": "Chapter",
      "text": "Chapter One: The Beginning",
      "page_numbers": [1],
      "source_chunk_ids": [1]
    },
    {
      "speaker": "Narrator",
      "text": "It was a dark and stormy night...",
      "page_numbers": [1],
      "source_chunk_ids": [1]
    },
    {
      "speaker": "John",
      "text": "I can't believe this is happening!",
      "page_numbers": [1, 2],
      "source_chunk_ids": [1, 2]
    }
  ],
  "meta": {
    "source_total_pdf_chunks": 50,
    "llm_windows": 10,
    "model": "gpt-4o",
    "processing_time": 45.2,
    "total_script_lines": 250,
    "total_characters": 8
  }
}
```

## Usage

### Automatic Processing (via Job Queue)

When you submit a PDF processing job, if `ENABLE_LLM_CHUNKING=true`, the system will automatically:

1. Process the PDF normally
2. Upload `*_processed.json` to R2
3. Run LLM speaker chunking
4. Upload `*_script.json` to R2

The job status will show:
- Progress: 85% - "Processing speaker attribution with LLM"
- Progress: 90% - "LLM speaker chunking completed"
- Progress: 100% - "Processing completed successfully"

Job result will include both output keys:
```json
{
  "status": "completed",
  "result": {
    "output_key": "processed_audiobooks/job_123_processed.json",
    "script_output_key": "processed_audiobooks/job_123_script.json",
    "llm_chunking_enabled": true,
    "total_chunks": 50,
    "total_pages": 100
  }
}
```

### Manual Processing (via Code)

You can also use the speaker chunker directly:

```python
from app.services.llm_speaker_chunker import SpeakerChunker
from app.core.config_settings import settings

# Initialize
chunker = SpeakerChunker(
    api_key=settings.OPENAI_API_KEY,
    model="gpt-4o"
)

# Process already-chunked data
script_result = await chunker.chunk_by_speaker_from_processed_data(
    processed_data=your_processed_json_dict,
    discovery_chars=30000,
    max_chars_per_window=35000,
    concurrency=5
)

# Result contains characters and script
print(f"Found {len(script_result['characters'])} characters")
print(f"Generated {len(script_result['script'])} script lines")
```

## Features

### Character Discovery
- Automatically identifies main characters from the text
- Always includes a "Narrator" character
- Provides descriptions and gender for each character
- Suggests voice IDs for TTS integration

### Speaker Attribution
- Converts prose into dialogue and narration
- Attributes each line to a specific speaker
- Handles chapter markers specially (speaker: "Chapter")
- Maintains page number and chunk ID provenance

### Concurrency & Performance
- Processes multiple text windows in parallel
- Configurable concurrency level (default: 5)
- Automatic retry logic with exponential backoff
- Continues processing even if LLM chunking fails

### Error Handling
- If LLM chunking fails, standard processing still completes
- Errors are logged but don't fail the entire job
- Job result indicates whether LLM chunking was successful

## R2 Storage Layout

After processing a PDF with LLM chunking enabled:

```
R2 Bucket:
  audiobook_uploads/
    original_file.pdf              # Original upload
  processed_audiobooks/
    job_123_processed.json         # Standard chunks
    job_123_script.json            # LLM speaker-attributed script
```

## Cost Considerations

LLM chunking uses OpenAI's API and incurs costs based on:
- Model used (gpt-4o is recommended)
- Amount of text processed
- Number of API calls (depends on concurrency and window size)

For a typical novel (~100k words):
- Estimated API calls: 10-20 windows
- Estimated cost: $0.50-$2.00 (with gpt-4o)

Set `ENABLE_LLM_CHUNKING=false` to disable and avoid costs.

## Dependencies

The following package must be installed:

```bash
pip install openai
```

Already added to `requirements.txt`.

## Files Modified

1. **New Service**: `app/services/llm_speaker_chunker.py` - Complete LLM chunking implementation
2. **Updated Service**: `app/services/pdf_processor_service.py` - Integrated LLM chunking into pipeline
3. **Updated Config**: `app/core/config_settings.py` - Added LLM configuration settings
4. **Updated Requirements**: `requirements.txt` - Added `openai` package

## Next Steps

To enable LLM chunking:

1. Set your OpenAI API key in `.env`:
   ```bash
   OPENAI_API_KEY=sk-your-key-here
   ENABLE_LLM_CHUNKING=true
   ```

2. Restart the PDF processor service:
   ```bash
   cd microservices/pdf-processor
   uvicorn main:app --reload
   ```

3. Submit a PDF processing job - the script will be automatically generated!
