# LLM Speaker Chunking - Quick Start Guide

## What Was Added

Your PDF processor now automatically converts processed PDFs into speaker-attributed scripts using OpenAI's GPT-4o. After the standard chunking, the text is analyzed by an LLM to identify characters, separate dialogue from narration, and create a structured script ready for text-to-speech processing.

## Installation

1. **Install the new dependency:**
   ```bash
   cd microservices/pdf-processor
   pip install openai
   ```

2. **Configure your environment:**
   
   Create or update your `.env` file with:
   ```bash
   # Required
   OPENAI_API_KEY=sk-your-openai-api-key-here
   
   # Optional (defaults provided)
   ENABLE_LLM_CHUNKING=true
   LLM_MODEL=gpt-4o
   LLM_CONCURRENCY=5
   ```

3. **Restart the service:**
   ```bash
   uvicorn main:app --reload
   ```

## How It Works

### Before (Standard Processing):
```
PDF → Extract Text → Chunk → Upload *_processed.json to R2
```

### After (With LLM Chunking):
```
PDF → Extract Text → Chunk → Upload *_processed.json to R2
                             ↓
            Discover Characters ← Send to OpenAI GPT-4o
                             ↓
            Parse into Script Lines (Speaker + Text)
                             ↓
            Upload *_script.json to R2
```

## Output Files

For each processed PDF, you'll get **two files** in R2:

1. **`*_processed.json`** - Standard chunks (unchanged)
2. **`*_script.json`** - NEW! Speaker-attributed script

### Example Script Output:
```json
{
  "characters": [
    {
      "name": "Narrator",
      "description": "Narration / description",
      "gender": "NEUTRAL"
    },
    {
      "name": "Sarah",
      "description": "Main protagonist",
      "gender": "FEMALE",
      "suggestedVoiceId": "female-mature-warm"
    }
  ],
  "script": [
    {
      "speaker": "Narrator",
      "text": "Sarah walked into the room...",
      "page_numbers": [5],
      "source_chunk_ids": [12]
    },
    {
      "speaker": "Sarah",
      "text": "Hello, is anyone here?",
      "page_numbers": [5],
      "source_chunk_ids": [12]
    }
  ]
}
```

## Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | None | **Required** - Your OpenAI API key |
| `ENABLE_LLM_CHUNKING` | false | Enable/disable automatic processing |
| `LLM_MODEL` | gpt-4o | OpenAI model (gpt-4o recommended) |
| `LLM_CONCURRENCY` | 5 | Parallel API requests (1-10) |
| `LLM_MAX_CHARS_PER_WINDOW` | 35000 | Max chars per LLM window |
| `LLM_DISCOVERY_CHARS` | 30000 | Chars for character discovery |

## Cost Estimate

For a typical 300-page novel (~100,000 words):
- **Processing time:** 2-5 minutes
- **API calls:** ~15-25 requests
- **Estimated cost:** $1.00 - $3.00 (with gpt-4o)

Costs scale with document length.

## Testing

Process a sample PDF and check the R2 bucket:

```bash
# You should see both files:
processed_audiobooks/
  job_abc123_processed.json  ✓
  job_abc123_script.json     ✓ NEW!
```

## Disable If Needed

To turn off LLM chunking (save costs):

```bash
# In .env file
ENABLE_LLM_CHUNKING=false
```

Or simply omit `OPENAI_API_KEY` - the system will skip LLM processing gracefully.

## Files Modified

- ✅ `app/services/llm_speaker_chunker.py` - NEW service
- ✅ `app/services/pdf_processor_service.py` - Integrated LLM step
- ✅ `app/core/config_settings.py` - Added LLM settings
- ✅ `requirements.txt` - Added openai package
- ✅ `docs/LLM_SPEAKER_CHUNKING.md` - Full documentation
- ✅ `.env.example` - Configuration template

## Need Help?

See the full documentation: [`docs/LLM_SPEAKER_CHUNKING.md`](./LLM_SPEAKER_CHUNKING.md)
