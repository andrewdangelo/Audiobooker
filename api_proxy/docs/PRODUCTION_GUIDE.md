# Production Deployment Guide

## Pre-Deployment Checklist

### 1. Environment Configuration

Create a production `.env` file with proper values:

```bash
# Environment
ENVIRONMENT=production
DEBUG=false

# Server
HOST=0.0.0.0
PORT=${PORT}  # Railway will inject this

# CORS - Update with your actual frontend URLs
CORS_ORIGINS=https://your-frontend.railway.app,https://your-custom-domain.com

# Microservice URLs - Update with actual production URLs
PDF_PROCESSOR_URL=https://pdf-processor.railway.app
TTS_SERVICE_URL=https://tts-service.railway.app
BACKEND_SERVICE_URL=https://backend-service.railway.app
STORAGE_SERVICE_URL=https://storage-service.railway.app

# Timeouts (increase for production)
REQUEST_TIMEOUT=60
UPLOAD_TIMEOUT=300

# Rate Limiting
RATE_LIMIT_REQUESTS=1000
RATE_LIMIT_PERIOD=60

# Logging
LOG_LEVEL=INFO
```

### 2. Update requirements.txt

Ensure all dependencies are pinned to specific versions:

```bash
# Generate requirements with exact versions
pip freeze > requirements.txt
```

Current production dependencies:
```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0
httpx==0.25.1
python-multipart==0.0.6
python-dotenv==1.0.0
```

### 3. Security Hardening

Update `config/settings.py` for production:

```python
class Settings(BaseSettings):
    # ... existing settings ...
    
    # Security
    ALLOWED_HOSTS: List[str] = ["your-domain.com", "*.railway.app"]
    SECRET_KEY: str  # For JWT/session management
    
    # Add security headers
    ENABLE_SECURITY_HEADERS: bool = True
    
    # Rate limiting
    RATE_LIMIT_ENABLED: bool = True
```

### 4. Database Connections

If using PostgreSQL for session/cache management:

```python
# config/settings.py
DATABASE_URL: Optional[str] = None
REDIS_URL: Optional[str] = None  # For caching/rate limiting
```

## Railway Deployment

### Step 1: Create Railway Project

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Initialize project
railway init
```

### Step 2: Create Procfile

```bash
# Procfile
web: uvicorn main:app --host 0.0.0.0 --port ${PORT}
```

### Step 3: Create railway.json

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "numReplicas": 1,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

### Step 4: Set Environment Variables

In Railway dashboard, set these variables:

```
ENVIRONMENT=production
DEBUG=false
CORS_ORIGINS=https://your-frontend-url.com
PDF_PROCESSOR_URL=https://pdf-processor-service.railway.app
TTS_SERVICE_URL=https://tts-service.railway.app
BACKEND_SERVICE_URL=https://backend-service.railway.app
STORAGE_SERVICE_URL=https://storage-service.railway.app
```

### Step 5: Deploy

```bash
# Deploy to Railway
railway up

# Or link to GitHub for auto-deployments
railway link
git push origin main
```

### Step 6: Verify Deployment

```bash
# Get deployment URL
railway open

# Check health
curl https://your-api-gateway.railway.app/health
curl https://your-api-gateway.railway.app/health/services
```

## Docker Deployment (Alternative)

### Create Dockerfile

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Create .dockerignore

```.dockerignore
__pycache__
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
.env
.git
.gitignore
*.md
.vscode
.idea
```

### Build and Run

```bash
# Build image
docker build -t audiobooker-api-gateway .

# Run locally
docker run -p 8000:8000 \
  -e ENVIRONMENT=production \
  -e DEBUG=false \
  --env-file .env.production \
  audiobooker-api-gateway

# Push to registry
docker tag audiobooker-api-gateway:latest your-registry/audiobooker-api-gateway:latest
docker push your-registry/audiobooker-api-gateway:latest
```

## Production Optimizations

### 1. Enable Workers

For better performance, use multiple workers:

```python
# main.py
if __name__ == "__main__":
    import uvicorn
    
    workers = 4 if settings.ENVIRONMENT == "production" else 1
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        workers=workers,
        log_level="info",
        access_log=True,
    )
```

Or in Procfile:
```
web: uvicorn main:app --host 0.0.0.0 --port ${PORT} --workers 4
```

### 2. Add Connection Pooling

For better microservice communication:

```python
# app/services/http_client.py
import httpx

# Create a persistent client with connection pooling
client = httpx.AsyncClient(
    timeout=httpx.Timeout(30.0),
    limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
)
```

### 3. Implement Caching

```python
# app/middleware/cache.py
from fastapi import Request, Response
from functools import wraps
import hashlib
import json

cache_store = {}

def cache_response(expire_seconds: int = 300):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Create cache key
            key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            cache_key = hashlib.md5(key.encode()).hexdigest()
            
            # Check cache
            if cache_key in cache_store:
                cached_data, timestamp = cache_store[cache_key]
                if time.time() - timestamp < expire_seconds:
                    return cached_data
            
            # Call function
            result = await func(*args, **kwargs)
            
            # Store in cache
            cache_store[cache_key] = (result, time.time())
            
            return result
        return wrapper
    return decorator
```

### 4. Add Rate Limiting

```python
# app/middleware/rate_limit.py
from fastapi import Request, HTTPException
from collections import defaultdict
import time

request_counts = defaultdict(list)

async def rate_limit_middleware(request: Request, call_next):
    """Simple rate limiting by IP"""
    client_ip = request.client.host
    now = time.time()
    
    # Clean old requests
    request_counts[client_ip] = [
        req_time for req_time in request_counts[client_ip]
        if now - req_time < 60  # 1 minute window
    ]
    
    # Check limit
    if len(request_counts[client_ip]) >= 100:  # 100 requests per minute
        raise HTTPException(status_code=429, detail="Too many requests")
    
    # Record request
    request_counts[client_ip].append(now)
    
    response = await call_next(request)
    return response
```

### 5. Add Monitoring

```python
# main.py
from prometheus_fastapi_instrumentator import Instrumentator

# Add Prometheus metrics
Instrumentator().instrument(app).expose(app)
```

## Monitoring & Logging

### 1. Structured Logging

```python
# config/logging.py
import logging
import sys
from pythonjsonlogger import jsonlogger

def setup_logging():
    logger = logging.getLogger()
    handler = logging.StreamHandler(sys.stdout)
    
    if settings.ENVIRONMENT == "production":
        formatter = jsonlogger.JsonFormatter(
            '%(asctime)s %(name)s %(levelname)s %(message)s'
        )
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
```

### 2. Health Checks

Railway automatically monitors `/health` endpoint. Ensure it returns 200:

```python
@router.get("/health")
async def health_check():
    """Kubernetes/Railway health probe"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
```

### 3. Error Tracking

Integrate Sentry for error tracking:

```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[FastApiIntegration()],
        environment=settings.ENVIRONMENT,
        traces_sample_rate=0.1,
    )
```

## Database Migrations

If using databases:

```bash
# Install alembic
pip install alembic

# Initialize
alembic init migrations

# Create migration
alembic revision --autogenerate -m "Initial migration"

# Run migrations
alembic upgrade head
```

Add to Procfile:
```
release: alembic upgrade head
web: uvicorn main:app --host 0.0.0.0 --port ${PORT}
```

## Rollback Strategy

### Railway Rollback

```bash
# View deployments
railway deployments

# Rollback to previous
railway rollback
```

### Database Rollback

```bash
# Rollback one migration
alembic downgrade -1

# Rollback to specific version
alembic downgrade <revision_id>
```

## Performance Tuning

### 1. Connection Limits

```python
# config/settings.py
MAX_DB_CONNECTIONS: int = 20
MAX_HTTP_CONNECTIONS: int = 100
HTTP_KEEPALIVE_CONNECTIONS: int = 20
```

### 2. Timeout Configuration

```python
REQUEST_TIMEOUT: int = 60
UPLOAD_TIMEOUT: int = 300
DB_COMMAND_TIMEOUT: int = 30
```

### 3. Response Compression

Already enabled with `GZipMiddleware` in main.py.

## Security Best Practices

1. **Never commit `.env` files** - Use Railway's environment variables
2. **Use HTTPS only** - Railway provides automatic SSL
3. **Validate all inputs** - Use Pydantic models
4. **Implement rate limiting** - Prevent abuse
5. **Add authentication** - Protect sensitive endpoints
6. **Enable CORS properly** - Only allow trusted origins
7. **Keep dependencies updated** - Regular security updates
8. **Use secrets management** - For API keys and credentials

## Troubleshooting

### Common Issues

**502 Bad Gateway**
- Check if service is running: `railway logs`
- Verify PORT environment variable is used
- Check microservice URLs are correct

**Slow Response Times**
- Review timeout settings
- Check microservice health
- Enable connection pooling
- Add caching for frequent requests

**Memory Issues**
- Reduce number of workers
- Implement request streaming for large files
- Add memory limits in railway.json

**Database Connection Errors**
- Verify DATABASE_URL is correct
- Check connection pool settings
- Ensure migrations are run

## Post-Deployment

1. **Test all endpoints** - Use the `/docs` page
2. **Monitor logs** - `railway logs --follow`
3. **Check metrics** - Response times, error rates
4. **Set up alerts** - For downtime or errors
5. **Document API** - Keep API documentation updated
6. **Load testing** - Use tools like Apache Bench or Locust

## Support

- Railway Docs: https://docs.railway.app
- FastAPI Docs: https://fastapi.tiangolo.com
- Project Issues: [Your GitHub repo]
