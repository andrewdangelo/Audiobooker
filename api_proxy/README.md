# API Gateway

FastAPI-based API Gateway that serves as the bridge between frontend applications (Web UI, Mobile UI) and backend microservices.

## Architecture

```
Frontend Apps (Web UI, Mobile UI)
          ↓
    API Gateway (FastAPI) ← YOU ARE HERE
          ↓
├── Internal Microservices
│   ├── TTS Service (port 8002)
│   ├── PDF Processing (port 8001)
│   ├── Backend Service (port 8003)
│   └── Storage Service (port 8004)
│
├── Data Storage
│   ├── PostgreSQL
│   └── CloudFlare R2
│
└── External APIs
    ├── Gutenberg API
    └── ElevenLabs API
```

## Quick Start

### 1. Setup Virtual Environment

From the project root:
```bash
# The virtual environment is in the root directory
source ../venv/Scripts/activate  # Windows
# or
source ../venv/bin/activate  # Linux/Mac
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your configuration
# Update microservice URLs and CORS origins
```

### 4. Run the Server

Development mode (auto-reload):
```bash
uvicorn main:app --reload --port 8000
```

Production mode:
```bash
python main.py
```

## Available Endpoints

### Core Endpoints
- `GET /` - API Gateway information
- `GET /health` - Basic health check
- `GET /health/services` - Check all microservices health
- `GET /docs` - Swagger UI API documentation
- `GET /redoc` - ReDoc API documentation

### API Routes
- `POST /api/v1/pdf/upload` - Upload PDF for processing
- `POST /api/v1/pdf/process/{job_id}` - Start PDF processing
- `GET /api/v1/pdf/status/{job_id}` - Check processing status
- `GET /api/v1/pdf/download/{job_id}` - Download extracted text

## Documentation

- **[Development Guide](docs/DEVELOPMENT_GUIDE.md)** - Learn how to add new routes and features
- **[Production Deployment](docs/PRODUCTION_GUIDE.md)** - Deploy to Railway or Docker
- **[API Documentation](http://localhost:8000/docs)** - Interactive API docs (when server is running)

## Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `ENVIRONMENT` | Environment name (development/production) | `development` | No |
| `DEBUG` | Enable debug mode | `true` | No |
| `PORT` | Server port | `8000` | No |
| `CORS_ORIGINS` | Allowed CORS origins (comma-separated) | `http://localhost:5173,http://localhost:3000` | Yes |
| `PDF_PROCESSOR_URL` | PDF processing microservice URL | `http://localhost:8001` | Yes |
| `TTS_SERVICE_URL` | TTS microservice URL | `http://localhost:8002` | Yes |
| `BACKEND_SERVICE_URL` | Backend service URL | `http://localhost:8003` | Yes |
| `STORAGE_SERVICE_URL` | Storage service URL | `http://localhost:8004` | Yes |
| `REQUEST_TIMEOUT` | HTTP request timeout (seconds) | `30` | No |
| `UPLOAD_TIMEOUT` | File upload timeout (seconds) | `120` | No |
| `RATE_LIMIT_REQUESTS` | Max requests per period | `100` | No |
| `RATE_LIMIT_PERIOD` | Rate limit period (seconds) | `60` | No |

## Project Structure

```
api_proxy/
├── app/
│   ├── routers/          # API route handlers
│   │   ├── health.py     # Health check endpoints
│   │   └── pdf.py        # PDF processing routes
│   │
│   ├── services/         # Business logic & external clients
│   │   └── http_client.py
│   │
│   ├── schemas/          # Pydantic models
│   └── middleware/       # Custom middleware
│
├── config/
│   └── settings.py       # Configuration management
│
├── docs/
│   ├── DEVELOPMENT_GUIDE.md
│   └── PRODUCTION_GUIDE.md
│
├── main.py              # Application entry point
├── requirements.txt     # Python dependencies
├── Procfile            # Railway deployment
├── Dockerfile          # Docker deployment
└── .env                # Environment variables (local)
```

## Development

### Adding a New Route

See the [Development Guide](docs/DEVELOPMENT_GUIDE.md) for detailed instructions on:
- Creating new routers
- Defining request/response schemas
- Connecting to microservices
- Error handling
- Testing

### Testing

```bash
# Install test dependencies
pip install pytest httpx

# Run tests
pytest

# Run with coverage
pytest --cov=app tests/
```

### Code Quality

```bash
# Format code
black .

# Lint
flake8 .

# Type checking
mypy .
```

## Deployment

### Railway (Recommended)

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login and deploy
railway login
railway init
railway up
```

See [Production Guide](docs/PRODUCTION_GUIDE.md) for complete deployment instructions.

### Docker

```bash
# Build image
docker build -t audiobooker-api-gateway .

# Run container
docker run -p 8000:8000 --env-file .env audiobooker-api-gateway
```

## Monitoring

### Health Checks

```bash
# Basic health
curl http://localhost:8000/health

# All services health
curl http://localhost:8000/health/services
```

### Logs

Development:
```bash
# Logs are printed to console
uvicorn main:app --reload
```

Production (Railway):
```bash
railway logs --follow
```

## Troubleshooting

### Common Issues

**Import errors when starting**
- Ensure virtual environment is activated
- Run `pip install -r requirements.txt`

**CORS errors in browser**
- Check `CORS_ORIGINS` in `.env` includes your frontend URL
- Verify frontend URL format (no trailing slash)

**Microservice connection errors**
- Verify microservices are running
- Check URLs in `.env` are correct
- Test with `/health/services` endpoint

**Port already in use**
- Change `PORT` in `.env`
- Or kill process: `lsof -ti:8000 | xargs kill`

## Support

- **Documentation**: Check `/docs` folder
- **API Docs**: http://localhost:8000/docs (when running)
- **Issues**: Report bugs in the project repository

## License

[Your License Here]

