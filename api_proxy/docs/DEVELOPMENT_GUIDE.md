# API Gateway Development Guide

## Architecture Overview

The API Gateway serves as the central bridge between frontend applications and backend microservices.

```
Frontend Apps (Web UI, Mobile UI)
          ↓
    API Proxy (FastAPI Gateway) ← YOU ARE HERE
          ↓
├── Internal Microservices
│   ├── TTS Service (port 8002)
│   ├── PDF Processing (port 8001)
│   ├── Backend Service (port 8003)
│   └── Auth Service (port 8004)
│
├── Data Storage
│   ├── PostgreSQL (metadata, user data)
│   └── CloudFlare R2 (audio files, PDFs)
│
└── External APIs
    ├── Gutenberg (public domain books)
    └── ElevenLabs (premium TTS)
```

## Project Structure

```
api_proxy/
├── app/
│   ├── routers/          # API route handlers (controllers)
│   │   ├── health.py     # Health check endpoints
│   │   ├── pdf.py        # PDF processing routes
│   │   ├── tts.py        # TTS service routes
│   │   └── auth.py       # Authentication routes
│   │
│   ├── services/         # Business logic & external service clients
│   │   ├── http_client.py    # HTTP client for microservices
│   │   └── cache.py          # Caching layer (if needed)
│   │
│   ├── schemas/          # Pydantic models for request/response
│   │   ├── pdf.py        # PDF-related schemas
│   │   ├── tts.py        # TTS-related schemas
│   │   └── common.py     # Shared schemas
│   │
│   └── middleware/       # Custom middleware
│       ├── auth.py       # Authentication middleware
│       ├── rate_limit.py # Rate limiting
│       └── logging.py    # Request/response logging
│
├── config/
│   └── settings.py       # Configuration & environment variables
│
├── main.py              # Application entry point
├── requirements.txt     # Python dependencies
└── .env                 # Environment variables (not committed)
```

## Adding a New API Route

### Step 1: Create a Router

Create a new file in `app/routers/` for your feature:

```python
# app/routers/audiobooks.py
"""
Audiobooks Router - Manage audiobook operations
"""

from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import List
import logging

from config.settings import settings
from app.services.http_client import http_client
from app.schemas.audiobooks import AudiobookResponse, CreateAudiobookRequest

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_model=List[AudiobookResponse])
async def list_audiobooks(
    limit: int = 20,
    offset: int = 0
):
    """
    List all audiobooks with pagination.
    
    Args:
        limit: Maximum number of items to return
        offset: Number of items to skip
        
    Returns:
        List of audiobooks
    """
    try:
        # Proxy request to backend microservice
        response = await http_client.get(
            f"{settings.BACKEND_SERVICE_URL}/api/v1/audiobooks",
            params={"limit": limit, "offset": offset}
        )
        return response.json()
        
    except Exception as e:
        logger.error(f"Failed to fetch audiobooks: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch audiobooks")


@router.post("/", response_model=AudiobookResponse)
async def create_audiobook(request: CreateAudiobookRequest):
    """
    Create a new audiobook.
    
    Args:
        request: Audiobook creation request
        
    Returns:
        Created audiobook details
    """
    try:
        response = await http_client.post(
            f"{settings.BACKEND_SERVICE_URL}/api/v1/audiobooks",
            json=request.model_dump()
        )
        return response.json()
        
    except Exception as e:
        logger.error(f"Failed to create audiobook: {e}")
        raise HTTPException(status_code=500, detail="Failed to create audiobook")


@router.get("/{audiobook_id}", response_model=AudiobookResponse)
async def get_audiobook(audiobook_id: str):
    """
    Get audiobook details by ID.
    
    Args:
        audiobook_id: Unique audiobook identifier
        
    Returns:
        Audiobook details
    """
    try:
        response = await http_client.get(
            f"{settings.BACKEND_SERVICE_URL}/api/v1/audiobooks/{audiobook_id}"
        )
        
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="Audiobook not found")
            
        return response.json()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch audiobook: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch audiobook")
```

### Step 2: Create Schemas

Define request/response models in `app/schemas/`:

```python
# app/schemas/audiobooks.py
"""
Audiobook Schemas - Request/Response models
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class CreateAudiobookRequest(BaseModel):
    """Request model for creating an audiobook"""
    title: str = Field(..., min_length=1, max_length=255)
    author: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    source_pdf_id: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "The Great Gatsby",
                "author": "F. Scott Fitzgerald",
                "description": "A classic American novel",
                "source_pdf_id": "pdf_123456"
            }
        }


class AudiobookResponse(BaseModel):
    """Response model for audiobook data"""
    id: str
    title: str
    author: str
    description: Optional[str] = None
    status: str
    audio_url: Optional[str] = None
    duration: Optional[float] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "ab_123456",
                "title": "The Great Gatsby",
                "author": "F. Scott Fitzgerald",
                "status": "completed",
                "audio_url": "https://storage.example.com/audiobooks/ab_123456.mp3",
                "duration": 3600.5,
                "created_at": "2025-11-26T10:00:00Z"
            }
        }
```

### Step 3: Register Router in main.py

Add your router to the main application:

```python
# main.py

from app.routers import health, pdf, audiobooks

# ... (other code)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(
    pdf.router,
    prefix=f"{settings.API_V1_PREFIX}/pdf",
    tags=["PDF Processing"]
)
app.include_router(
    audiobooks.router,
    prefix=f"{settings.API_V1_PREFIX}/audiobooks",
    tags=["Audiobooks"]
)
```

### Step 4: Update Configuration

Add any new microservice URLs to `config/settings.py`:

```python
class Settings(BaseSettings):
    # ... existing settings ...
    
    # Add new microservice URL
    BACKEND_SERVICE_URL: str = "http://localhost:8003"
    AUDIOBOOK_SERVICE_URL: str = "http://localhost:8005"
```

And update `.env`:

```bash
# .env
BACKEND_SERVICE_URL=http://localhost:8003
AUDIOBOOK_SERVICE_URL=http://localhost:8005
```

### Step 5: Test Your Route

1. Start the API Gateway:
```bash
uvicorn main:app --reload --port 8000
```

2. Visit the auto-generated documentation:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

3. Test the endpoint:
```bash
# List audiobooks
curl http://localhost:8000/api/v1/audiobooks

# Get specific audiobook
curl http://localhost:8000/api/v1/audiobooks/ab_123456

# Create audiobook
curl -X POST http://localhost:8000/api/v1/audiobooks \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Book", "author": "Test Author"}'
```

## Working with Microservices

### Using the HTTP Client

The `http_client` service handles all communication with microservices:

```python
from app.services.http_client import http_client

# GET request
response = await http_client.get(
    "http://localhost:8001/api/endpoint",
    params={"key": "value"}
)

# POST request with JSON
response = await http_client.post(
    "http://localhost:8001/api/endpoint",
    json={"data": "value"}
)

# POST with file upload
with open("file.pdf", "rb") as f:
    response = await http_client.post_file(
        "http://localhost:8001/api/upload",
        file=f,
        filename="document.pdf",
        additional_data={"metadata": "value"}
    )
```

### Error Handling

Always handle errors from microservices gracefully:

```python
@router.get("/resource/{id}")
async def get_resource(id: str):
    try:
        response = await http_client.get(f"{settings.SERVICE_URL}/resource/{id}")
        
        # Handle specific status codes
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="Resource not found")
        elif response.status_code == 500:
            raise HTTPException(status_code=502, detail="Service temporarily unavailable")
            
        return response.json()
        
    except httpx.TimeoutException:
        logger.error(f"Timeout calling service for resource {id}")
        raise HTTPException(status_code=504, detail="Service timeout")
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
```

## Best Practices

### 1. Use Dependency Injection

```python
from fastapi import Depends
from app.services.auth import get_current_user

@router.get("/protected")
async def protected_route(user = Depends(get_current_user)):
    """Route that requires authentication"""
    return {"message": f"Hello {user.username}"}
```

### 2. Add Request Validation

```python
from pydantic import BaseModel, Field, validator

class CreateRequest(BaseModel):
    email: str = Field(..., regex=r"^[\w\.-]+@[\w\.-]+\.\w+$")
    age: int = Field(..., ge=0, le=150)
    
    @validator('email')
    def email_must_be_lowercase(cls, v):
        return v.lower()
```

### 3. Use Background Tasks for Long Operations

```python
from fastapi import BackgroundTasks

def process_in_background(data: dict):
    # Long-running task
    pass

@router.post("/process")
async def start_processing(
    data: dict,
    background_tasks: BackgroundTasks
):
    background_tasks.add_task(process_in_background, data)
    return {"message": "Processing started"}
```

### 4. Add Response Models

```python
@router.get("/items", response_model=List[ItemResponse])
async def list_items():
    # Response will be validated against ItemResponse schema
    return items
```

### 5. Document Your Endpoints

```python
@router.post(
    "/create",
    response_model=ItemResponse,
    status_code=201,
    summary="Create a new item",
    description="Creates a new item in the system with the provided data",
    responses={
        201: {"description": "Item created successfully"},
        400: {"description": "Invalid request data"},
        500: {"description": "Internal server error"}
    }
)
async def create_item(request: CreateItemRequest):
    """
    Create a new item with all metadata.
    
    - **title**: Item title (required)
    - **description**: Detailed description (optional)
    - **category**: Item category (required)
    """
    pass
```

## Testing

### Unit Testing Routes

```python
# tests/test_audiobooks.py
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_list_audiobooks():
    response = client.get("/api/v1/audiobooks")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_audiobook():
    response = client.get("/api/v1/audiobooks/test_id")
    assert response.status_code in [200, 404]
```

## Debugging

Enable debug mode in `.env`:

```bash
DEBUG=true
ENVIRONMENT=development
```

This will:
- Enable auto-reload on code changes
- Show detailed error messages
- Add debug logging
- Enable FastAPI debug mode

## Common Patterns

### Pagination

```python
from typing import Generic, TypeVar, List
from pydantic import BaseModel

T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int
    
@router.get("/items", response_model=PaginatedResponse[ItemResponse])
async def list_items(page: int = 1, page_size: int = 20):
    # Implementation
    pass
```

### File Uploads

```python
@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a file to the microservice"""
    contents = await file.read()
    
    response = await http_client.post_file(
        f"{settings.SERVICE_URL}/upload",
        file=contents,
        filename=file.filename
    )
    return response.json()
```

### Caching

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_cached_data(key: str):
    # Expensive operation
    return data

@router.get("/data/{key}")
async def get_data(key: str):
    return get_cached_data(key)
```

## Next Steps

1. Review the [API Documentation](http://localhost:8000/docs) after starting the server
2. Check [Production Deployment Guide](./PRODUCTION_GUIDE.md) for deployment instructions
3. Read [Security Best Practices](./SECURITY.md) for securing your routes
4. See [Monitoring Guide](./MONITORING.md) for observability setup
