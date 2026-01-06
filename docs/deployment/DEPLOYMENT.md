# Production Deployment Guide - Audiobooker

## 📋 Pre-Deployment Checklist

### 1. Environment Configuration
- [ ] Copy `.env.production.example` to `.env.production`
- [ ] Update all placeholder values with production credentials
- [ ] Generate secure `SECRET_KEY` and `JWT_SECRET_KEY`
- [ ] Configure production database connection
- [ ] Set up Cloudflare R2 production bucket
- [ ] Configure production CORS origins
- [ ] Add TTS API keys (OpenAI or alternative)
- [ ] Set `DEBUG=false` and `ENVIRONMENT=production`

### 2. Infrastructure Requirements
- [ ] PostgreSQL 15+ database server
- [ ] Redis server (for task queue)
- [ ] Cloudflare R2 bucket with appropriate permissions
- [ ] Domain with SSL certificate
- [ ] Reverse proxy (Nginx/Caddy) or Load balancer
- [ ] Container runtime (Docker) or Python 3.9+ environment

### 3. Database Setup
- [ ] Create production database
- [ ] Run database migrations
- [ ] Set up database backups
- [ ] Configure connection pooling
- [ ] Set up monitoring for database performance

### 4. Storage (Cloudflare R2)
- [ ] Create production R2 bucket
- [ ] Configure bucket CORS policy
- [ ] Set up lifecycle rules (optional)
- [ ] Configure custom domain for R2 (optional)
- [ ] Test upload/download/delete operations

### 5. Security
- [ ] Enable HTTPS/TLS
- [ ] Configure rate limiting
- [ ] Set up WAF rules (if available)
- [ ] Review and restrict CORS origins
- [ ] Enable security headers
- [ ] Configure secrets management (AWS Secrets Manager, Vault, etc.)
- [ ] Set up API authentication (if required)

### 6. Monitoring & Logging
- [ ] Configure log aggregation (ELK, CloudWatch, etc.)
- [ ] Set up error tracking (Sentry, Rollbar)
- [ ] Configure application metrics (Prometheus, DataDog)
- [ ] Set up uptime monitoring
- [ ] Configure alerting rules

---

## 🚀 Deployment Options

### Option 1: Docker Deployment (Recommended)

#### Step 1: Build Docker Image
```bash
cd backend
docker build -t audiobooker-api:latest .
```

#### Step 2: Run with Docker Compose
```bash
# Use the provided docker-compose.production.yml
docker-compose -f docker-compose.production.yml up -d
```

#### Step 3: Verify Deployment
```bash
# Check container health
docker ps
docker logs audiobooker-api

# Test health endpoint
curl https://api.yourdomain.com/health
```

### Option 2: Direct Python Deployment

#### Step 1: Set Up Virtual Environment
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate  # Windows

pip install -r requirements.txt
```

#### Step 2: Run with Gunicorn (Production Server)
```bash
# Install gunicorn if not in requirements
pip install gunicorn uvicorn[standard]

# Run with multiple workers
gunicorn main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120 \
  --access-logfile /var/log/audiobooker/access.log \
  --error-logfile /var/log/audiobooker/error.log \
  --log-level info
```

#### Step 3: Set Up Systemd Service
```bash
# Create service file
sudo nano /etc/systemd/system/audiobooker.service
```

```ini
[Unit]
Description=Audiobooker FastAPI Application
After=network.target postgresql.service redis.service

[Service]
Type=notify
User=audiobooker
Group=audiobooker
WorkingDirectory=/opt/audiobooker/backend
Environment="PATH=/opt/audiobooker/backend/venv/bin"
EnvironmentFile=/opt/audiobooker/backend/.env.production
ExecStart=/opt/audiobooker/backend/venv/bin/gunicorn main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable audiobooker
sudo systemctl start audiobooker
sudo systemctl status audiobooker
```

### Option 3: Cloud Platform Deployment

#### AWS Elastic Beanstalk
```bash
# Install EB CLI
pip install awsebcli

# Initialize EB
eb init -p python-3.9 audiobooker

# Create environment
eb create audiobooker-production

# Deploy
eb deploy
```

#### Google Cloud Run
```bash
# Build and push to GCR
gcloud builds submit --tag gcr.io/PROJECT_ID/audiobooker

# Deploy to Cloud Run
gcloud run deploy audiobooker \
  --image gcr.io/PROJECT_ID/audiobooker \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

#### Azure App Service
```bash
# Login to Azure
az login

# Create resource group
az group create --name audiobooker-rg --location eastus

# Create App Service plan
az appservice plan create --name audiobooker-plan \
  --resource-group audiobooker-rg \
  --sku B1 --is-linux

# Create web app
az webapp create --resource-group audiobooker-rg \
  --plan audiobooker-plan \
  --name audiobooker \
  --runtime "PYTHON:3.9"

# Deploy
az webapp up --name audiobooker
```

---

## 🔧 Post-Deployment Configuration

### 1. Nginx Reverse Proxy Configuration

```nginx
# /etc/nginx/sites-available/audiobooker
upstream audiobooker_api {
    server 127.0.0.1:8000;
    # Add more servers for load balancing
    # server 127.0.0.1:8001;
    # server 127.0.0.1:8002;
}

server {
    listen 80;
    server_name api.yourdomain.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Logging
    access_log /var/log/nginx/audiobooker-access.log;
    error_log /var/log/nginx/audiobooker-error.log;

    # File upload size
    client_max_body_size 50M;
    client_body_timeout 300s;

    # Proxy settings
    location / {
        proxy_pass http://audiobooker_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://audiobooker_api/health;
        access_log off;
    }
}
```

```bash
# Enable site and reload Nginx
sudo ln -s /etc/nginx/sites-available/audiobooker /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 2. SSL Certificate (Let's Encrypt)

```bash
# Install Certbot
sudo apt-get update
sudo apt-get install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d api.yourdomain.com

# Auto-renewal is handled by cron/systemd timer
sudo certbot renew --dry-run
```

### 3. Database Migrations

```bash
# Run Alembic migrations
cd backend
alembic upgrade head

# Or if not using Alembic, run SQL directly
psql -h your-db-host -U audiobooker -d audiobooker_db -f migrations/init.sql
```

### 4. Create R2 Bucket and Configure CORS

```bash
# Using Wrangler CLI
npm install -g wrangler
wrangler login

# Create bucket
wrangler r2 bucket create audiobooker-production

# Set CORS policy
cat > r2-cors.json << EOF
{
  "CORSRules": [
    {
      "AllowedOrigins": ["https://yourdomain.com"],
      "AllowedMethods": ["GET", "PUT", "POST", "DELETE"],
      "AllowedHeaders": ["*"],
      "MaxAgeSeconds": 3600
    }
  ]
}
EOF

# Apply CORS (via Cloudflare Dashboard or API)
```

---

## 🔍 Verification Steps

### 1. Health Checks
```bash
# API health
curl https://api.yourdomain.com/health

# Expected response:
# {"status": "healthy", "timestamp": "2025-10-27T..."}
```

### 2. API Endpoints
```bash
# Test upload endpoint
curl -X POST https://api.yourdomain.com/api/v1/upload/ \
  -F "file=@test.pdf"

# Test audiobooks list
curl https://api.yourdomain.com/api/v1/audiobooks/

# Test download endpoint
curl https://api.yourdomain.com/api/v1/audiobooks/{id}/download
```

### 3. Database Connection
```bash
# From backend container/server
python -c "
from config.database import engine
from sqlalchemy import text
with engine.connect() as conn:
    result = conn.execute(text('SELECT 1'))
    print('Database connection: OK')
"
```

### 4. R2 Storage
```bash
# Test R2 connection
python -c "
from storage_sdk import R2Client
client = R2Client()
print('R2 connection: OK')
print(f'Bucket: {client.bucket_name}')
"
```

---

## 📊 Monitoring Setup

### 1. Application Metrics
```python
# Add to main.py for Prometheus metrics
from prometheus_fastapi_instrumentator import Instrumentator

@app.on_event("startup")
async def startup():
    Instrumentator().instrument(app).expose(app)
```

### 2. Log Aggregation
```bash
# Install Filebeat for log shipping
sudo apt-get install filebeat

# Configure Filebeat
sudo nano /etc/filebeat/filebeat.yml

# Point to your log aggregation service
# (Elasticsearch, CloudWatch, etc.)
```

### 3. Error Tracking (Sentry)
```bash
# Install Sentry SDK
pip install sentry-sdk

# Add to main.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    environment=os.getenv("ENVIRONMENT"),
    integrations=[FastApiIntegration()],
    traces_sample_rate=1.0,
)
```

---

## 🔄 Backup & Recovery

### Database Backups
```bash
# Automated daily backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/audiobooker"
DB_NAME="audiobooker_db"

# Create backup
pg_dump -h localhost -U audiobooker $DB_NAME | gzip > \
  $BACKUP_DIR/backup_${DATE}.sql.gz

# Keep only last 30 days
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +30 -delete

# Upload to S3/R2 for off-site storage
aws s3 cp $BACKUP_DIR/backup_${DATE}.sql.gz \
  s3://audiobooker-backups/db/
```

### R2 Backup
```bash
# Replicate R2 bucket to another region/provider
# Using rclone
rclone sync cloudflare-r2:audiobooker-production \
  s3-backup:audiobooker-backup
```

---

## 🚨 Rollback Procedure

### Quick Rollback
```bash
# If using Docker
docker-compose down
docker pull audiobooker-api:previous-version
docker-compose up -d

# If using systemd
sudo systemctl stop audiobooker
cd /opt/audiobooker
git checkout previous-release-tag
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl start audiobooker

# Database rollback (if needed)
alembic downgrade -1
```

---

## 📞 Support & Troubleshooting

### Common Issues

**Issue: 500 errors on upload**
```bash
# Check logs
tail -f /var/log/audiobooker/error.log

# Verify R2 credentials
python -c "from storage_sdk import R2Client; R2Client().list_files()"

# Check file permissions
ls -la /tmp/uploads
```

**Issue: Database connection timeout**
```bash
# Check connection pool
# Increase DB_POOL_SIZE in .env.production

# Check database server
psql -h db-host -U audiobooker -d audiobooker_db
```

**Issue: High memory usage**
```bash
# Reduce worker count
# Update WORKERS in .env.production

# Monitor memory
htop
# or
docker stats audiobooker-api
```

---

## 📝 Maintenance Tasks

### Weekly
- [ ] Review error logs
- [ ] Check disk space
- [ ] Monitor database size
- [ ] Review API metrics

### Monthly
- [ ] Update dependencies
- [ ] Review and optimize database
- [ ] Audit security settings
- [ ] Test backup restoration

### Quarterly
- [ ] Security audit
- [ ] Performance optimization
- [ ] Cost optimization review
- [ ] Disaster recovery test

---

## 🎯 Performance Optimization

### Database Indexing
```sql
-- Add indexes for common queries
CREATE INDEX idx_audiobooks_status ON audiobooks(status);
CREATE INDEX idx_audiobooks_created_at ON audiobooks(created_at DESC);
CREATE INDEX idx_audiobooks_user_id ON audiobooks(user_id);
```

### Caching Strategy
```python
# Add Redis caching for frequently accessed data
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend

@app.on_event("startup")
async def startup():
    redis = aioredis.from_url(os.getenv("REDIS_URL"))
    FastAPICache.init(RedisBackend(redis), prefix="audiobooker-cache")
```

### CDN for R2
```bash
# Configure Cloudflare CDN in front of R2
# This provides caching and faster global delivery
```

---

**Deployment Date**: _______________  
**Deployed By**: _______________  
**Version**: _______________  
**Sign-off**: _______________
