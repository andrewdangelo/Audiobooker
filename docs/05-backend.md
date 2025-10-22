# Backend Development Guide

## Overview

The backend is built with FastAPI, providing a modern, fast (high-performance) Python web framework with automatic API documentation and type validation.

## Technology Stack

- **FastAPI 0.104.1**: Modern web framework
- **Python 3.9+**: Programming language
- **SQLAlchemy 2.0.23**: ORM for database operations
- **Pydantic 2.5.0**: Data validation using Python type hints
- **Uvicorn**: ASGI server
- **PostgreSQL**: Relational database
- **psycopg2-binary**: PostgreSQL adapter

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── models/                # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── audiobook.py
│   │   ├── user.py
│   │   └── conversion_job.py
│   ├── schemas/               # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── audiobook.py
│   │   └── upload.py
│   ├── routers/               # API endpoint handlers
│   │   ├── __init__.py
│   │   ├── upload.py
│   │   ├── audiobooks.py
│   │   ├── conversion.py
│   │   └── health.py
│   ├── services/              # Business logic
│   │   ├── __init__.py
│   │   ├── storage_service.py
│   │   ├── audiobook_service.py
│   │   └── conversion_service.py
│   ├── core/                  # Core utilities
│   │   ├── __init__.py
│   │   └── security.py
│   └── utils/                 # Helper functions
│       ├── __init__.py
│       └── pdf_utils.py
├── config/                    # Configuration
│   ├── __init__.py
│   ├── settings.py           # Application settings
│   └── database.py           # Database configuration
├── tests/                     # Test files
│   ├── __init__.py
│   └── test_upload.py
├── uploads/                   # Local file storage (dev)
├── venv/                      # Virtual environment
├── .env                       # Environment variables
├── main.py                    # Application entry point
└── requirements.txt           # Python dependencies
```

## Application Entry Point

**File**: `main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.settings import settings
from app.routers import audiobooks, upload, conversion, health

# Create FastAPI app instance
app = FastAPI(
    title="Audiobooker API",
    description="PDF to Audiobook conversion API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(
    audiobooks.router,
    prefix=f"{settings.API_V1_PREFIX}/audiobooks",
    tags=["Audiobooks"]
)
app.include_router(
    upload.router,
    prefix=f"{settings.API_V1_PREFIX}/upload",
    tags=["Upload"]
)
app.include_router(
    conversion.router,
    prefix=f"{settings.API_V1_PREFIX}/conversion",
    tags=["Conversion"]
)

@app.on_event("startup")
async def startup_event():
    print("🚀 Audiobooker API starting up...")

@app.on_event("shutdown")
async def shutdown_event():
    print("👋 Audiobooker API shutting down...")
```

## Configuration

### Settings

**File**: `config/settings.py`

```python
from pydantic_settings import BaseSettings
from typing import Union
from pydantic import field_validator

class Settings(BaseSettings):
    # Application
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "change-me-in-production"
    API_V1_PREFIX: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = "postgresql://audiobooker:password@localhost:5433/audiobooker_db"
    
    # CORS
    CORS_ORIGINS: Union[list[str], str] = "http://localhost:5173,http://localhost:3000"
    
    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v
    
    # File Upload
    MAX_UPLOAD_SIZE: int = 52428800  # 50MB
    ALLOWED_EXTENSIONS: Union[list[str], str] = ".pdf"
    UPLOAD_DIR: str = "uploads"
    
    # Cloudflare R2
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = "audiobooker-storage"
    R2_ENDPOINT_URL: str = ""
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

### Database Configuration

**File**: `config/database.py`

```python
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config.settings import settings

# Create SQLAlchemy engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class
Base = declarative_base()

# Dependency for getting database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

## Models

### Audiobook Model

**File**: `app/models/audiobook.py`

```python
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from config.database import Base
import uuid

class Audiobook(Base):
    __tablename__ = "audiobooks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    title = Column(String, nullable=False)
    original_file_name = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    pdf_path = Column(String, nullable=False)
    audio_path = Column(String, nullable=True)
    status = Column(String, default="pending")  # pending, processing, completed, failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

## Schemas

### Upload Schema

**File**: `app/schemas/upload.py`

```python
from pydantic import BaseModel
from typing import Optional

class UploadResponse(BaseModel):
    id: str
    filename: str
    size: int
    message: str
    status: str

class UploadStatusResponse(BaseModel):
    id: str
    status: str
    message: str
```

## Routers

### Upload Router

**File**: `app/routers/upload.py`

```python
from fastapi import APIRouter, UploadFile, File, HTTPException, status
import uuid

router = APIRouter()

@router.post("/")
async def upload_pdf(file: UploadFile = File(...)):
    """
    Upload a PDF file for conversion
    
    - **file**: PDF file to upload (max 50MB)
    """
    # Validate file extension
    if not file.filename or not file.filename.endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed"
        )
    
    # Read file content
    content = await file.read()
    file_size = len(content)
    
    # Validate file size (50MB)
    if file_size > 52428800:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum allowed size of 50MB"
        )
    
    # Generate unique ID
    file_id = str(uuid.uuid4())
    
    # Return success response
    return {
        "id": file_id,
        "filename": file.filename,
        "size": file_size,
        "message": "File received successfully!",
        "status": "pending"
    }

@router.get("/{upload_id}/status")
async def get_upload_status(upload_id: str):
    """Get the status of an upload/conversion"""
    return {
        "id": upload_id,
        "status": "pending",
        "message": "This is a test endpoint"
    }
```

### Health Router

**File**: `app/routers/health.py`

```python
from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}
```

## Services

### Storage Service

**File**: `app/services/storage_service.py`

```python
import os
from pathlib import Path
from typing import Optional
from config.settings import settings

class StorageService:
    """Service for file storage operations"""
    
    def __init__(self):
        # Check if using R2 or local storage
        self.use_local = not settings.R2_ENDPOINT_URL or \
                        settings.R2_ENDPOINT_URL.startswith("https://<account_id>")
        
        if self.use_local:
            # Use local filesystem
            self.storage_path = Path(settings.UPLOAD_DIR)
            self.storage_path.mkdir(exist_ok=True)
    
    async def upload_file(
        self,
        file_content: bytes,
        file_name: str,
        content_type: Optional[str] = None
    ) -> str:
        """Upload a file to storage"""
        if self.use_local:
            # Save to local filesystem
            file_path = self.storage_path / file_name
            with open(file_path, 'wb') as f:
                f.write(file_content)
            return str(file_path)
        else:
            # Upload to Cloudflare R2
            # Implementation for R2 upload
            pass
    
    async def download_file(self, file_key: str) -> bytes:
        """Download a file from storage"""
        if self.use_local:
            with open(file_key, 'rb') as f:
                return f.read()
        else:
            # Download from R2
            pass
    
    async def delete_file(self, file_key: str) -> bool:
        """Delete a file from storage"""
        if self.use_local:
            os.remove(file_key)
            return True
        else:
            # Delete from R2
            pass
```

### Audiobook Service

**File**: `app/services/audiobook_service.py`

```python
from sqlalchemy.orm import Session
from app.models.audiobook import Audiobook
from typing import List, Optional
import uuid

class AudiobookService:
    """Service for audiobook operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, audiobook_data: dict) -> Audiobook:
        """Create a new audiobook record"""
        audiobook = Audiobook(**audiobook_data)
        self.db.add(audiobook)
        self.db.commit()
        self.db.refresh(audiobook)
        return audiobook
    
    def get_by_id(self, audiobook_id: str) -> Optional[Audiobook]:
        """Get audiobook by ID"""
        return self.db.query(Audiobook).filter(
            Audiobook.id == uuid.UUID(audiobook_id)
        ).first()
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[Audiobook]:
        """Get all audiobooks"""
        return self.db.query(Audiobook).offset(skip).limit(limit).all()
    
    def update_status(self, audiobook_id: str, status: str) -> Optional[Audiobook]:
        """Update audiobook status"""
        audiobook = self.get_by_id(audiobook_id)
        if audiobook:
            audiobook.status = status
            self.db.commit()
            self.db.refresh(audiobook)
        return audiobook
    
    def delete(self, audiobook_id: str) -> bool:
        """Delete an audiobook"""
        audiobook = self.get_by_id(audiobook_id)
        if audiobook:
            self.db.delete(audiobook)
            self.db.commit()
            return True
        return False
```

## Database Operations

### Create Tables

```python
from config.database import Base, engine

# Create all tables
Base.metadata.create_all(bind=engine)
```

### Database Session Usage

```python
from fastapi import Depends
from sqlalchemy.orm import Session
from config.database import get_db

@router.get("/audiobooks")
async def get_audiobooks(db: Session = Depends(get_db)):
    audiobooks = db.query(Audiobook).all()
    return audiobooks
```

## Error Handling

### Custom Exceptions

```python
from fastapi import HTTPException, status

# Bad Request
raise HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail="Invalid file type"
)

# Not Found
raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Audiobook not found"
)

# Internal Server Error
raise HTTPException(
    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    detail="Failed to process file"
)
```

### Global Exception Handler

```python
from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)}
    )
```

## Testing

### Setup pytest

```bash
pip install pytest pytest-asyncio httpx
```

### Example Test

**File**: `tests/test_upload.py`

```python
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_upload_valid_pdf():
    files = {"file": ("test.pdf", b"fake pdf content", "application/pdf")}
    response = client.post("/api/v1/upload/", files=files)
    assert response.status_code == 200
    assert "id" in response.json()
```

## Running the Application

### Development Mode

```bash
# Activate virtual environment
source venv/Scripts/activate  # Windows
source venv/bin/activate      # macOS/Linux

# Run with auto-reload
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode

```bash
# Run with multiple workers
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Documentation

FastAPI automatically generates interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## Best Practices

### 1. Type Hints

```python
from typing import List, Optional

def get_audiobooks(skip: int = 0, limit: int = 100) -> List[Audiobook]:
    pass
```

### 2. Dependency Injection

```python
from fastapi import Depends

def get_current_user(token: str = Depends(oauth2_scheme)):
    pass

@router.get("/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user
```

### 3. Async/Await

```python
@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    content = await file.read()
    # Process content
```

### 4. Response Models

```python
from pydantic import BaseModel

class AudiobookResponse(BaseModel):
    id: str
    title: str
    status: str

@router.get("/audiobooks/{id}", response_model=AudiobookResponse)
async def get_audiobook(id: str):
    pass
```

## Common Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run server
python -m uvicorn main:app --reload

# Run tests
pytest

# Format code
black .

# Lint code
flake8 .

# Type check
mypy .
```
