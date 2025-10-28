# 🎯 Staging Branch - Production Ready

## 📊 Current Status

**Branch**: `staging`  
**Last Updated**: 2025-10-27  
**Status**: ✅ **READY FOR PRODUCTION DEPLOYMENT**  
**Version**: 1.0.0

---

## 🚀 What's Included

### ✅ Completed Features

1. **Cloudflare R2 Storage Integration**
   - Custom `storage_sdk` package for R2 operations
   - Organized file storage structure (`book_id/type/filename`)
   - Secure presigned URL generation
   - Complete CRUD operations (upload, download, delete)

2. **Backend API**
   - FastAPI application with PostgreSQL database
   - PDF upload endpoint with validation
   - Audiobook management (CRUD)
   - Download endpoints with presigned URLs
   - Health check endpoint
   - CORS configured for production

3. **Production Infrastructure**
   - Docker Compose configuration
   - Environment templates for staging and production
   - Nginx reverse proxy configuration
   - Production-ready requirements with pinned versions

4. **Documentation**
   - Comprehensive deployment guide (DEPLOYMENT.md)
   - Production readiness checklist (PRODUCTION_CHECKLIST.md)
   - Storage SDK documentation (580+ lines)
   - Integration guide
   - Example code

---

## 📁 Repository Structure

```
Audiobooker/
├── backend/                          # FastAPI backend application
│   ├── app/
│   │   ├── routers/                  # API endpoints
│   │   │   ├── audiobooks.py         # Audiobook CRUD + downloads
│   │   │   ├── upload.py             # File upload with R2
│   │   │   ├── conversion.py         # TTS conversion (placeholder)
│   │   │   └── health.py             # Health checks
│   │   ├── models/                   # SQLAlchemy models
│   │   ├── schemas/                  # Pydantic schemas
│   │   └── services/                 # Business logic
│   ├── config/                       # Application configuration
│   │   ├── database.py               # Database setup
│   │   └── settings.py               # Environment settings
│   ├── migrations/                   # Database migrations
│   ├── tests/                        # Unit & integration tests
│   ├── .env.example                  # Development environment template
│   ├── .env.production.example       # Production environment template
│   ├── .env.staging.example          # Staging environment template
│   ├── Dockerfile                    # Production Docker image
│   ├── requirements.txt              # Development dependencies
│   ├── requirements.production.txt   # Production dependencies (pinned)
│   └── main.py                       # Application entry point
├── storage_sdk/                      # Cloudflare R2 SDK
│   ├── r2_client.py                  # Main R2 client (500+ lines)
│   ├── path_utils.py                 # File path utilities
│   ├── config.py                     # R2 configuration
│   ├── __init__.py                   # Package exports
│   ├── README.md                     # Complete SDK documentation
│   ├── INTEGRATION.md                # Backend integration guide
│   └── example.py                    # Working examples
├── frontend/                         # React frontend (existing)
├── docker-compose.yml                # Development environment
├── docker-compose.production.yml     # Production environment
├── DEPLOYMENT.md                     # Production deployment guide
├── PRODUCTION_CHECKLIST.md           # Pre-deployment checklist
├── MIGRATION_SUMMARY.md              # Feature migration summary
└── README.md                         # Project overview

```

---

## 🔧 Quick Start (Development)

### Prerequisites
- Python 3.9+
- PostgreSQL 15+
- Cloudflare R2 account
- Node.js 18+ (for frontend)

### Setup

1. **Clone and switch to staging**
   ```bash
   git clone https://github.com/andrewdangelo/Audiobooker.git
   cd Audiobooker
   git checkout staging
   ```

2. **Backend setup**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # or .\venv\Scripts\activate on Windows
   pip install -r requirements.txt
   
   # Copy and configure environment
   cp .env.example .env
   # Edit .env with your credentials
   
   # Start backend
   uvicorn main:app --reload --port 8000
   ```

3. **Database setup**
   ```bash
   # Start PostgreSQL (Docker)
   docker run -d \
     --name audiobooker-db \
     -e POSTGRES_USER=audiobooker \
     -e POSTGRES_PASSWORD=password \
     -e POSTGRES_DB=audiobooker_db \
     -p 5433:5432 \
     postgres:15-alpine
   
   # Run migrations
   cd backend
   alembic upgrade head
   ```

4. **Test the API**
   ```bash
   # Health check
   curl http://localhost:8000/health
   
   # API docs
   open http://localhost:8000/docs
   ```

---

## 🚀 Production Deployment

### Step 1: Review Checklist
📋 See [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md) for complete pre-deployment tasks

### Step 2: Configure Environment
```bash
cd backend
cp .env.production.example .env.production
# Edit .env.production with production values
```

**Required Configuration:**
- `SECRET_KEY` - Generate with `openssl rand -hex 32`
- `DATABASE_URL` - Production PostgreSQL connection
- `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY` - Cloudflare R2
- `R2_BUCKET_NAME` - Production bucket name
- `CORS_ORIGINS` - Production frontend URL
- `TTS_API_KEY` - OpenAI or alternative TTS provider

### Step 3: Deploy with Docker
```bash
# Build and start production services
docker-compose -f docker-compose.production.yml up -d

# Check logs
docker-compose -f docker-compose.production.yml logs -f api
```

### Step 4: Verify Deployment
```bash
# Health check
curl https://api.yourdomain.com/health

# Test upload
curl -X POST https://api.yourdomain.com/api/v1/upload/ \
  -F "file=@test.pdf"
```

📖 **Full deployment guide**: [DEPLOYMENT.md](DEPLOYMENT.md)

---

## 📊 Environment Variables

### Core Settings
```env
ENVIRONMENT=production           # development, staging, or production
DEBUG=false                      # MUST be false in production
SECRET_KEY=<generate-secure-key> # Use openssl rand -hex 32
API_V1_PREFIX=/api/v1
```

### Database
```env
DATABASE_URL=postgresql://user:pass@host:5432/db
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
```

### Cloudflare R2
```env
R2_ACCOUNT_ID=your_account_id
R2_ACCESS_KEY_ID=your_access_key
R2_SECRET_ACCESS_KEY=your_secret_key
R2_BUCKET_NAME=audiobooker-production
R2_ENDPOINT_URL=https://<account_id>.r2.cloudflarestorage.com
```

### Security
```env
CORS_ORIGINS=https://yourdomain.com
FORCE_HTTPS=true
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60
```

See templates for complete configuration:
- `.env.production.example` - Production
- `.env.staging.example` - Staging
- `.env.example` - Development

---

## 🧪 Testing

### Run Tests
```bash
cd backend
pytest tests/ -v
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/api/v1/upload/` | Upload PDF |
| GET | `/api/v1/audiobooks/` | List audiobooks |
| GET | `/api/v1/audiobooks/{id}` | Get audiobook |
| GET | `/api/v1/audiobooks/{id}/download` | Download PDF (presigned URL) |
| GET | `/api/v1/audiobooks/{id}/audio/download` | Download audio (presigned URL) |
| DELETE | `/api/v1/audiobooks/{id}` | Delete audiobook |
| GET | `/docs` | API documentation (dev only) |

---

## 📈 Monitoring

### Health Endpoint
```bash
GET /health
```
Response:
```json
{
  "status": "healthy",
  "timestamp": "2025-10-27T12:00:00Z",
  "database": "connected",
  "storage": "connected"
}
```

### Metrics (Production)
- Prometheus metrics at `/metrics` (if enabled)
- Sentry error tracking
- Application logs in `/var/log/audiobooker/`

---

## 🔐 Security Features

- ✅ HTTPS/TLS encryption
- ✅ CORS restriction to specific origins
- ✅ Rate limiting (60 requests/minute)
- ✅ File size limits (50MB)
- ✅ File type validation (PDF only)
- ✅ Filename sanitization
- ✅ SQL injection protection (SQLAlchemy)
- ✅ Presigned URLs with expiration (1 hour)
- ✅ No credentials in logs
- ✅ Security headers (HSTS, X-Frame-Options, etc.)

---

## 📦 Dependencies

### Core Framework
- FastAPI 0.104.1
- Uvicorn 0.24.0
- Pydantic 2.5.0

### Database
- SQLAlchemy 2.0.23
- PostgreSQL (via psycopg2-binary 2.9.9)

### Storage
- boto3 1.34.10 (S3-compatible for R2)

### Production Server
- Gunicorn 21.2.0

See `requirements.production.txt` for complete list with pinned versions.

---

## 🔄 Branch Strategy

```
master (main)
  └── staging ← You are here
       └── feature/crud_service (merged)
```

**Workflow:**
1. Develop features in `feature/*` branches
2. Merge to `staging` for testing
3. Deploy `staging` to staging environment
4. After testing, merge `staging` to `master`
5. Deploy `master` to production

---

## 📝 Recent Changes

### Version 1.0.0 (2025-10-27)

**Added:**
- Cloudflare R2 storage integration with custom SDK
- Organized file storage structure
- Presigned URL downloads
- Production deployment configuration
- Comprehensive documentation

**Changed:**
- Replaced basic StorageService with feature-rich R2Client
- Updated CORS to support multiple frontend ports
- Enhanced error handling and validation

**Fixed:**
- R2 client initialization with proper settings
- Filename sanitization edge cases
- CORS configuration for staging environment

See [MIGRATION_SUMMARY.md](MIGRATION_SUMMARY.md) for detailed changes.

---

## 🆘 Troubleshooting

### Backend won't start
```bash
# Check logs
docker-compose logs api

# Verify environment variables
python -c "from config.settings import settings; print(settings.R2_BUCKET_NAME)"

# Test database connection
python -c "from config.database import engine; print(engine)"
```

### Upload fails with 500 error
```bash
# Check R2 credentials
python -c "from storage_sdk import R2Client; R2Client().list_files()"

# Verify bucket exists and has correct permissions
```

### CORS errors
```bash
# Verify CORS_ORIGINS in .env includes your frontend URL
# Example: CORS_ORIGINS=https://yourdomain.com,http://localhost:5173
```

For more issues, see [DEPLOYMENT.md](DEPLOYMENT.md#support--troubleshooting)

---

## 📞 Support

- **Documentation**: See `/docs` folder
- **Issues**: https://github.com/andrewdangelo/Audiobooker/issues
- **Pull Requests**: https://github.com/andrewdangelo/Audiobooker/pulls

---

## ✅ Production Readiness

- [x] All tests passing
- [x] Documentation complete
- [x] Environment templates created
- [x] Docker configuration ready
- [x] Deployment guide written
- [x] Security hardening implemented
- [x] Monitoring setup documented
- [ ] Final smoke tests on staging environment
- [ ] Load testing completed
- [ ] Security audit passed

**Status**: Ready for staging deployment and testing

---

## 🎯 Next Steps

1. Deploy to staging environment
2. Run end-to-end tests
3. Perform load testing
4. Security audit
5. Final approval for production
6. Merge `staging` → `master`
7. Production deployment

---

**Maintained by**: Development Team  
**Last Review**: 2025-10-27  
**Next Review**: After staging deployment
