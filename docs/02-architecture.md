# System Architecture

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Client Layer                         │
│  ┌────────────────────────────────────────────────────┐     │
│  │         React Frontend (localhost:5173)            │     │
│  │  - UI Components (shadcn/ui)                       │     │
│  │  - State Management (React Hooks)                  │     │
│  │  - API Client (Axios)                              │     │
│  └────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ HTTP/REST
                            │ CORS Enabled
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      Application Layer                       │
│  ┌────────────────────────────────────────────────────┐     │
│  │       FastAPI Backend (localhost:8000)             │     │
│  │  ┌──────────────────────────────────────────┐     │     │
│  │  │  API Routes (/api/v1/*)                  │     │     │
│  │  │  - Upload Router                         │     │     │
│  │  │  - Audiobooks Router                     │     │     │
│  │  │  - Conversion Router                     │     │     │
│  │  │  - Health Router                         │     │     │
│  │  └──────────────────────────────────────────┘     │     │
│  │  ┌──────────────────────────────────────────┐     │     │
│  │  │  Business Logic (Services)               │     │     │
│  │  │  - Storage Service                       │     │     │
│  │  │  - Audiobook Service                     │     │     │
│  │  │  - Conversion Service                    │     │     │
│  │  └──────────────────────────────────────────┘     │     │
│  └────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ SQLAlchemy ORM
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                       Data Layer                             │
│  ┌────────────────────────────────────────────────────┐     │
│  │  PostgreSQL Database (localhost:5433)              │     │
│  │  - Audiobooks Table                                │     │
│  │  - Users Table                                     │     │
│  │  - Conversion Jobs Table                           │     │
│  └────────────────────────────────────────────────────┘     │
│  ┌────────────────────────────────────────────────────┐     │
│  │  File Storage                                      │     │
│  │  - Local Filesystem (development)                  │     │
│  │  - Cloudflare R2 (production)                      │     │
│  └────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

## Component Architecture

### Frontend Architecture

```
src/
├── components/           # Reusable UI components
│   ├── ui/              # Base UI components (shadcn)
│   │   ├── button.tsx
│   │   ├── progress.tsx
│   │   └── ...
│   ├── layout/          # Layout components
│   │   ├── Header.tsx
│   │   ├── Footer.tsx
│   │   └── Sidebar.tsx
│   └── upload/          # Upload-specific components
│       ├── FileUpload.tsx
│       └── UploadProgress.tsx
├── pages/               # Route-level components
│   ├── Home.tsx
│   ├── Dashboard.tsx
│   ├── Upload.tsx
│   └── Library.tsx
├── services/            # API communication
│   ├── api.ts          # Axios instance configuration
│   ├── upload.service.ts
│   └── audiobook.service.ts
├── hooks/               # Custom React hooks
│   └── useAudiobooks.ts
├── types/               # TypeScript definitions
│   ├── audiobook.ts
│   └── upload.ts
└── config/              # Configuration
    └── env.ts
```

### Backend Architecture

```
backend/
├── app/
│   ├── models/              # Database models (SQLAlchemy)
│   │   ├── __init__.py
│   │   ├── audiobook.py    # Audiobook model
│   │   ├── user.py         # User model
│   │   └── conversion_job.py
│   ├── schemas/             # Request/Response schemas (Pydantic)
│   │   ├── __init__.py
│   │   ├── audiobook.py
│   │   └── upload.py
│   ├── routers/             # API endpoints
│   │   ├── __init__.py
│   │   ├── upload.py       # POST /upload, GET /upload/:id/status
│   │   ├── audiobooks.py   # CRUD for audiobooks
│   │   ├── conversion.py   # Conversion operations
│   │   └── health.py       # Health check endpoint
│   ├── services/            # Business logic
│   │   ├── __init__.py
│   │   ├── storage_service.py     # File storage operations
│   │   ├── audiobook_service.py   # Audiobook operations
│   │   └── conversion_service.py  # PDF to audio conversion
│   ├── core/                # Core utilities
│   │   ├── __init__.py
│   │   └── security.py
│   └── utils/               # Helper functions
│       ├── __init__.py
│       └── pdf_utils.py
├── config/                  # Configuration
│   ├── __init__.py
│   ├── settings.py         # Application settings
│   └── database.py         # Database configuration
├── tests/                   # Test files
│   ├── __init__.py
│   └── test_upload.py
└── main.py                  # Application entry point
```

## Data Flow

### File Upload Flow

```
1. User Action
   │
   ├─> FileUpload Component (Frontend)
   │   - User drags/selects PDF file
   │   - File validation (type, size)
   │   - Create FormData
   │
   ├─> Upload Service (Frontend)
   │   - POST to /api/v1/upload/
   │   - Track upload progress
   │   - Handle response/errors
   │
   ├─> CORS Middleware (Backend)
   │   - Validate origin
   │   - Add CORS headers
   │
   ├─> Upload Router (Backend)
   │   - Validate file type (.pdf)
   │   - Validate file size (max 50MB)
   │   - Generate unique ID
   │
   ├─> Storage Service (Backend)
   │   - Save to local filesystem OR
   │   - Upload to Cloudflare R2
   │
   ├─> Audiobook Service (Backend)
   │   - Create database record
   │   - Set status to 'pending'
   │
   └─> Response to Frontend
       - Return audiobook ID
       - Return status
       - Display success message
```

### API Request Flow

```
Client Request
    │
    ├─> API Client (Axios)
    │   - Base URL: http://localhost:8000
    │   - Add headers
    │   - Send request
    │
    ├─> FastAPI Application
    │   - CORS Middleware
    │   - Route to appropriate router
    │   - Validate request (Pydantic)
    │
    ├─> Router Handler
    │   - Parse request parameters
    │   - Call service layer
    │   - Handle business logic
    │
    ├─> Service Layer
    │   - Database operations (SQLAlchemy)
    │   - External service calls
    │   - Data transformations
    │
    ├─> Database/Storage
    │   - Execute queries
    │   - Store/retrieve data
    │
    └─> Response
        - Format response (Pydantic)
        - Return JSON
        - Handle errors
```

## Database Schema

### Entity Relationship Diagram

```
┌─────────────────────────┐
│        Users            │
├─────────────────────────┤
│ id (UUID, PK)          │
│ email (String)         │
│ password_hash (String) │
│ created_at (DateTime)  │
└─────────────────────────┘
            │
            │ 1:N
            │
            ▼
┌─────────────────────────┐
│     Audiobooks          │
├─────────────────────────┤
│ id (UUID, PK)          │
│ user_id (UUID, FK)     │
│ title (String)         │
│ original_file_name     │
│ file_size (Integer)    │
│ pdf_path (String)      │
│ audio_path (String)    │
│ status (String)        │
│ created_at (DateTime)  │
│ updated_at (DateTime)  │
└─────────────────────────┘
            │
            │ 1:N
            │
            ▼
┌─────────────────────────┐
│   Conversion Jobs       │
├─────────────────────────┤
│ id (UUID, PK)          │
│ audiobook_id (UUID, FK)│
│ status (String)        │
│ progress (Integer)     │
│ error_message (String) │
│ started_at (DateTime)  │
│ completed_at (DateTime)│
└─────────────────────────┘
```

## Deployment Architecture

### Development Environment

```
Developer Machine
├── Frontend Dev Server (Vite)
│   └── localhost:5173
├── Backend Dev Server (Uvicorn)
│   └── localhost:8000
└── Docker Compose
    └── PostgreSQL
        └── localhost:5433
```

### Production Environment (Planned)

```
Cloud Infrastructure
├── Frontend (Static Hosting)
│   ├── Vercel / Netlify
│   └── CDN Distribution
├── Backend (Container Service)
│   ├── Docker Container
│   ├── Load Balancer
│   └── Auto-scaling
├── Database
│   └── Managed PostgreSQL
└── Storage
    └── Cloudflare R2
```

## Security Architecture

### Authentication Flow (Planned)

```
1. User Login
2. Backend validates credentials
3. Generate JWT token
4. Return token to frontend
5. Store token in localStorage
6. Include token in Authorization header
7. Backend validates token on each request
```

### CORS Configuration

- **Allowed Origins**: `http://localhost:5173`, `http://localhost:3000`
- **Allowed Methods**: All (`*`)
- **Allowed Headers**: All (`*`)
- **Credentials**: Enabled

### File Validation

- **Type**: PDF files only (`.pdf` extension)
- **Size**: Maximum 50MB (52,428,800 bytes)
- **Content Type**: `application/pdf`

## Performance Considerations

### Frontend Optimization
- Code splitting with React Router
- Lazy loading of components
- Optimized build with Vite
- Tailwind CSS purging

### Backend Optimization
- Asynchronous request handling
- Database connection pooling
- File streaming for large uploads
- Background task processing (planned)

### Caching Strategy (Planned)
- Browser caching for static assets
- API response caching
- Database query caching
