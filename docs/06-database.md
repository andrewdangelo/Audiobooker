# Database Schema

## Overview

The database uses PostgreSQL for production and can use SQLite for local development. The schema is managed by SQLAlchemy ORM.

## Connection Configuration

### PostgreSQL (Production/Docker)

```properties
DATABASE_URL=postgresql://audiobooker:password@localhost:5433/audiobooker_db
```

### SQLite (Local Development)

```properties
DATABASE_URL=sqlite:///./audiobooker.db
```

## Tables

### Users Table

Stores user account information.

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    is_superuser BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_users_email ON users(email);
```

**SQLAlchemy Model** (`app/models/user.py`):

```python
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from config.database import Base
import uuid

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

### Audiobooks Table

Stores audiobook metadata and processing status.

```sql
CREATE TABLE audiobooks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    original_file_name VARCHAR(500) NOT NULL,
    file_size INTEGER NOT NULL,
    pdf_path VARCHAR(1000) NOT NULL,
    audio_path VARCHAR(1000),
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_audiobooks_user_id ON audiobooks(user_id);
CREATE INDEX idx_audiobooks_status ON audiobooks(status);
CREATE INDEX idx_audiobooks_created_at ON audiobooks(created_at DESC);
```

**Status Values**:
- `pending`: Uploaded, waiting for processing
- `processing`: Currently being converted
- `completed`: Conversion successful
- `failed`: Conversion failed

**SQLAlchemy Model** (`app/models/audiobook.py`):

```python
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from config.database import Base
import uuid

class Audiobook(Base):
    __tablename__ = "audiobooks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    title = Column(String(500), nullable=False)
    original_file_name = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    pdf_path = Column(String(1000), nullable=False)
    audio_path = Column(String(1000), nullable=True)
    status = Column(String(50), default="pending", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="audiobooks")
    conversion_jobs = relationship("ConversionJob", back_populates="audiobook", cascade="all, delete-orphan")
```

### Conversion Jobs Table

Tracks individual conversion job status and progress.

```sql
CREATE TABLE conversion_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    audiobook_id UUID REFERENCES audiobooks(id) ON DELETE CASCADE,
    status VARCHAR(50) DEFAULT 'queued',
    progress INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_conversion_jobs_audiobook_id ON conversion_jobs(audiobook_id);
CREATE INDEX idx_conversion_jobs_status ON conversion_jobs(status);
```

**Status Values**:
- `queued`: Waiting to start
- `running`: Currently processing
- `completed`: Successfully completed
- `failed`: Failed with error

**SQLAlchemy Model** (`app/models/conversion_job.py`):

```python
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from config.database import Base
import uuid

class ConversionJob(Base):
    __tablename__ = "conversion_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audiobook_id = Column(UUID(as_uuid=True), ForeignKey("audiobooks.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(50), default="queued", index=True)
    progress = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    audiobook = relationship("Audiobook", back_populates="conversion_jobs")
```

## Entity Relationships

```
┌─────────────┐
│    Users    │
└──────┬──────┘
       │
       │ 1:N
       │
       ▼
┌─────────────┐
│ Audiobooks  │
└──────┬──────┘
       │
       │ 1:N
       │
       ▼
┌─────────────┐
│Conversion   │
│   Jobs      │
└─────────────┘
```

## Database Initialization

### Create All Tables

```python
from config.database import Base, engine

# Create all tables
Base.metadata.create_all(bind=engine)
```

### Drop All Tables (Caution!)

```python
from config.database import Base, engine

# Drop all tables - USE WITH CAUTION
Base.metadata.drop_all(bind=engine)
```

## Migrations (Future Enhancement)

### Using Alembic

```bash
# Install Alembic
pip install alembic

# Initialize Alembic
alembic init alembic

# Create migration
alembic revision --autogenerate -m "Create initial tables"

# Apply migration
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

## Common Queries

### Get Audiobooks for User

```python
from app.models.audiobook import Audiobook

audiobooks = db.query(Audiobook)\
    .filter(Audiobook.user_id == user_id)\
    .order_by(Audiobook.created_at.desc())\
    .all()
```

### Get Audiobooks by Status

```python
pending_audiobooks = db.query(Audiobook)\
    .filter(Audiobook.status == "pending")\
    .all()
```

### Get Audiobook with Conversion Jobs

```python
from sqlalchemy.orm import joinedload

audiobook = db.query(Audiobook)\
    .options(joinedload(Audiobook.conversion_jobs))\
    .filter(Audiobook.id == audiobook_id)\
    .first()
```

### Update Audiobook Status

```python
audiobook = db.query(Audiobook).filter(Audiobook.id == audiobook_id).first()
if audiobook:
    audiobook.status = "completed"
    audiobook.audio_path = "/path/to/audio.mp3"
    db.commit()
```

### Delete Audiobook (Cascade Delete)

```python
audiobook = db.query(Audiobook).filter(Audiobook.id == audiobook_id).first()
if audiobook:
    db.delete(audiobook)
    db.commit()
    # This will also delete associated conversion_jobs due to cascade
```

## Database Management

### PostgreSQL CLI Access

```bash
# Access PostgreSQL in Docker container
docker exec -it audiobooker-postgres psql -U audiobooker -d audiobooker_db

# List tables
\dt

# Describe table
\d audiobooks

# Query data
SELECT * FROM audiobooks;

# Exit
\q
```

### Backup Database

```bash
# Backup
docker exec -t audiobooker-postgres pg_dump -U audiobooker audiobooker_db > backup.sql

# Restore
docker exec -i audiobooker-postgres psql -U audiobooker -d audiobooker_db < backup.sql
```

### Reset Database

```bash
# Stop and remove container with volumes
docker-compose down -v

# Start container (creates fresh database)
docker-compose up -d postgres

# Wait for database to be ready
sleep 5

# Create tables
cd backend
source venv/Scripts/activate
python -c "from config.database import Base, engine; Base.metadata.create_all(bind=engine)"
```

## Performance Optimization

### Indexes

All foreign keys and commonly queried fields have indexes:
- `users.email`
- `audiobooks.user_id`
- `audiobooks.status`
- `audiobooks.created_at`
- `conversion_jobs.audiobook_id`
- `conversion_jobs.status`

### Connection Pooling

```python
# config/database.py
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,      # Verify connections before using
    pool_size=10,            # Number of connections to maintain
    max_overflow=20          # Maximum overflow connections
)
```

### Query Optimization

```python
# Use joinedload to prevent N+1 queries
from sqlalchemy.orm import joinedload

audiobooks = db.query(Audiobook)\
    .options(joinedload(Audiobook.user))\
    .filter(Audiobook.status == "completed")\
    .all()

# Use pagination for large result sets
def get_paginated_audiobooks(db, page=1, per_page=20):
    return db.query(Audiobook)\
        .offset((page - 1) * per_page)\
        .limit(per_page)\
        .all()
```

## Data Integrity

### Constraints

- **Primary Keys**: UUID for all tables
- **Foreign Keys**: Cascade delete for child records
- **NOT NULL**: Required fields enforced
- **UNIQUE**: Email addresses must be unique
- **DEFAULT VALUES**: Timestamps and status fields

### Transactions

```python
from sqlalchemy.orm import Session

def create_audiobook_with_job(db: Session, audiobook_data: dict):
    try:
        # Create audiobook
        audiobook = Audiobook(**audiobook_data)
        db.add(audiobook)
        db.flush()  # Get audiobook.id before commit
        
        # Create conversion job
        job = ConversionJob(audiobook_id=audiobook.id)
        db.add(job)
        
        # Commit transaction
        db.commit()
        return audiobook
    except Exception as e:
        # Rollback on error
        db.rollback()
        raise e
```

## Schema Validation

Pydantic schemas ensure data validation before database operations:

```python
from pydantic import BaseModel, UUID4
from datetime import datetime

class AudiobookCreate(BaseModel):
    title: str
    original_file_name: str
    file_size: int
    pdf_path: str

class AudiobookResponse(BaseModel):
    id: UUID4
    title: str
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True
```
