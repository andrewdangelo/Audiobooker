# PDF Processor Microservice

FastAPI-based microservice for processing PDFs from R2 storage with text extraction, chunking, and **LLM-powered speaker attribution**.

## Features

✅ **PDF Text Extraction** - Extract text from PDFs with automatic OCR for scanned documents  
✅ **Intelligent Chunking** - Split text into manageable chunks with overlap  
✅ **R2 Storage Integration** - Download/upload from Cloudflare R2  
✅ **Job Queue System** - Track processing jobs with Redis  
✅ **Database Integration** - Store audiobook metadata in PostgreSQL  
✅ **🆕 LLM Speaker Chunking** - Convert prose to speaker-attributed scripts using OpenAI GPT-4o  

## 🆕 LLM Speaker Chunking

The PDF processor now includes intelligent speaker attribution powered by OpenAI's GPT-4o. After standard processing, the text is analyzed to:

- 🎭 **Discover Characters** - Automatically identify characters from the text
- 💬 **Separate Dialogue** - Distinguish between dialogue and narration
- 🗣️ **Attribute Speakers** - Assign each line to a specific character
- 📚 **Detect Chapters** - Identify and mark chapter boundaries
- 🎤 **Suggest Voices** - Recommend voice types for TTS

### Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Add OpenAI API key to .env
echo "OPENAI_API_KEY=sk-your-key-here" >> .env
echo "ENABLE_LLM_CHUNKING=true" >> .env

# 3. Run the service
uvicorn main:app --reload
```

See [QUICKSTART_LLM_CHUNKING.md](./QUICKSTART_LLM_CHUNKING.md) for details.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      PDF Processing Flow                     │
└─────────────────────────────────────────────────────────────┘

1. Upload PDF to R2
   │
   ▼
2. Create Processing Job (Redis)
   │
   ▼
3. Extract Text (PyMuPDF + OCR)
   │
   ▼
4. Standard Chunking (character-based)
   │
   ▼
5. Upload *_processed.json to R2
   │
   ▼
6. 🆕 LLM Speaker Chunking (if enabled)
   │
   ├─► Discover Characters (GPT-4o)
   ├─► Parse Windows into Script Lines
   └─► Merge Results
   │
   ▼
7. Upload *_script.json to R2
   │
   ▼
8. Create Database Record
   │
   ▼
9. Complete Job ✓
```

## Output Files

For each processed PDF:

1. **`*_processed.json`** - Standard character-based chunks
   ```json
   {
     "chunks": [
       {"chunk_id": 1, "text": "...", "page_numbers": [1]}
     ]
   }
   ```

2. **`*_script.json`** (NEW!) - Speaker-attributed script
   ```json
   {
     "characters": [
       {"name": "Narrator", "gender": "NEUTRAL"},
       {"name": "Alice", "gender": "FEMALE"}
     ],
     "script": [
       {"speaker": "Narrator", "text": "Alice opened the door..."},
       {"speaker": "Alice", "text": "Hello?"}
     ]
   }
   ```

## API Endpoints

### Health Check
```http
GET /api/v1/pdf/health
```

### Process PDF
```http
POST /api/v1/pdf/pdf_processor/process
```

### Get Job Status
```http
GET /api/v1/pdf/pdf_processor/job/{job_id}
```

## Environment Variables

See [.env.example](./.env.example) for complete configuration options.

### Required
```bash
DATABASE_URL=postgresql://...
R2_ACCOUNT_ID=...
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
R2_BUCKET_NAME=...
```

### LLM Chunking (Optional)
```bash
OPENAI_API_KEY=sk-...
ENABLE_LLM_CHUNKING=true
LLM_MODEL=gpt-4o
```

## Documentation

- 📖 [LLM Speaker Chunking Guide](./QUICKSTART_LLM_CHUNKING.md)
- 📚 [Full LLM Documentation](./docs/LLM_SPEAKER_CHUNKING.md)
- 🔧 [Configuration Reference](./.env.example)

## Technologies

- **FastAPI** - Web framework
- **PyMuPDF** - PDF text extraction
- **Tesseract/EasyOCR** - OCR for scanned PDFs
- **OpenAI GPT-4o** - LLM speaker chunking
- **Redis** - Job queue
- **PostgreSQL** - Database
- **Cloudflare R2** - Object storage

## Author

Mohammad Saifan
