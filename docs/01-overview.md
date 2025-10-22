# Project Overview

## Introduction

Audiobooker is a full-stack web application that converts PDF documents into audiobooks. The system allows users to upload PDF files, processes the text content, and generates audio files using text-to-speech technology.

## Technology Stack

### Frontend
- **Framework**: React 18
- **Language**: TypeScript
- **Build Tool**: Vite 5.0.8
- **Styling**: Tailwind CSS 3.3.6
- **UI Components**: shadcn/ui
- **HTTP Client**: Axios
- **Routing**: React Router 6.20.1

### Backend
- **Framework**: FastAPI 0.104.1
- **Language**: Python 3.9+
- **ORM**: SQLAlchemy 2.0.23
- **Validation**: Pydantic 2.5.0
- **PDF Processing**: PyPDF2 3.0.1
- **Cloud Storage**: boto3 1.34.10 (Cloudflare R2)
- **Database Driver**: psycopg2-binary 2.9.9

### Database
- **Development**: PostgreSQL 15 (Docker)
- **Production**: PostgreSQL (Docker Compose)

### Infrastructure
- **Containerization**: Docker & Docker Compose
- **Version Control**: Git

## Project Structure

```
Audiobooker/
├── backend/                 # FastAPI backend application
│   ├── app/                # Application code
│   │   ├── models/        # SQLAlchemy models
│   │   ├── routers/       # API route handlers
│   │   ├── schemas/       # Pydantic schemas
│   │   └── services/      # Business logic
│   ├── config/            # Configuration files
│   ├── tests/             # Backend tests
│   ├── venv/              # Python virtual environment
│   ├── main.py            # Application entry point
│   └── .env               # Environment variables
├── frontend/              # React frontend application
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── pages/        # Page components
│   │   ├── services/     # API services
│   │   ├── hooks/        # Custom React hooks
│   │   ├── types/        # TypeScript type definitions
│   │   └── config/       # Frontend configuration
│   ├── public/           # Static assets
│   └── package.json      # NPM dependencies
├── docs/                 # Project documentation
├── docker-compose.yml    # Docker services configuration
└── README.md            # Project README

```

## Key Features

### 1. File Upload
- Drag-and-drop interface
- File type validation (PDF only)
- File size validation (max 50MB)
- Real-time upload progress tracking

### 2. PDF Processing
- Text extraction from PDF documents
- Content parsing and cleaning
- Metadata extraction

### 3. Audio Conversion
- Text-to-Speech conversion
- Multiple voice options (planned)
- Audio quality settings (planned)

### 4. Storage
- Local filesystem (development)
- Cloudflare R2 (production)
- Database record management

### 5. API
- RESTful API design
- OpenAPI documentation
- CORS enabled for frontend communication

## Design Principles

### Modularity
The application is designed with clear separation of concerns:
- Frontend and backend are independent
- Services are loosely coupled
- Configuration is externalized

### Scalability
- Database-driven architecture
- Asynchronous processing support
- Docker-based deployment

### Developer Experience
- Hot module reloading (Vite)
- Auto-reload on code changes (Uvicorn)
- Type safety (TypeScript, Pydantic)
- Comprehensive documentation

### Security
- CORS configuration
- Environment-based secrets
- File validation
- Size limits

## Development Philosophy

The project follows modern development best practices:
- **Type Safety**: TypeScript on frontend, Pydantic on backend
- **Code Organization**: Clear directory structure with single responsibility
- **Configuration Management**: Environment variables for all config
- **Testing**: Test infrastructure in place
- **Documentation**: Comprehensive inline and external docs
- **Version Control**: Git with clear commit messages

## Use Cases

1. **Students**: Convert textbooks and study materials to audio format
2. **Professionals**: Listen to reports and documents while multitasking
3. **Accessibility**: Provide audio versions for visually impaired users
4. **Content Creators**: Generate audiobook versions of written content

## Future Roadmap

1. **Phase 1** (Current): Basic file upload and processing
2. **Phase 2**: Text extraction and TTS integration
3. **Phase 3**: User authentication and management
4. **Phase 4**: Queue system for batch processing
5. **Phase 5**: Advanced features (voice selection, speed control, etc.)
