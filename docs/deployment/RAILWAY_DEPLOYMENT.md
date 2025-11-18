# Railway Deployment Guide

Complete guide to deploying Audiobooker to Railway staging/production environment.

## Overview

Railway will host:
- **Backend**: FastAPI application (Python)
- **Database**: PostgreSQL (already configured)
- **Frontend**: React/Vite application (Node.js)
- **Storage**: Cloudflare R2 (external)

**Estimated Cost:** $5-20/month depending on usage

---

## Prerequisites

1. **Railway Account**: Sign up at [railway.app](https://railway.app)
2. **GitHub Repository**: Connected to Railway
3. **Cloudflare R2**: Already configured (bucket: audiobooker)

---

## Deployment Steps

### Step 1: Deploy Backend to Railway

#### 1.1 Create New Project

```bash
# Option A: Using Railway CLI
npm i -g @railway/cli
railway login
railway init

# Option B: Using Railway Dashboard
# Go to https://railway.app/new
# Click "Deploy from GitHub repo"
# Select: andrewdangelo/Audiobooker
```

#### 1.2 Configure Backend Service

1. **Create Service**: New → GitHub Repo → Select backend folder
2. **Set Root Directory**: `backend`
3. **Configure Build**:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --timeout 120`

#### 1.3 Add Environment Variables

In Railway Dashboard → Backend Service → Variables, add:

```bash
# Application
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=<generate-with-openssl-rand-hex-32>
API_V1_PREFIX=/api/v1

# Database (Railway auto-provides DATABASE_URL from PostgreSQL service)
# DATABASE_URL is automatically set - no need to add manually

# Cloudflare R2
R2_ACCOUNT_ID=1049d9c736f1ba301b3a8c76ede09455
R2_ACCESS_KEY_ID=1d6d82ee3822ae2490bcb0b0b4759470
R2_SECRET_ACCESS_KEY=e491a96a668dea6fb464f6e68b7549e7b01e06d659cf30350aa95403b3183ec4
R2_BUCKET_NAME=audiobooker
R2_ENDPOINT_URL=https://1049d9c736f1ba301b3a8c76ede09455.r2.cloudflarestorage.com

# CORS (update after frontend deployment)
CORS_ORIGINS=https://your-frontend.up.railway.app

# File Upload
MAX_UPLOAD_SIZE=52428800
ALLOWED_EXTENSIONS=.pdf

# TTS (optional)
TTS_PROVIDER=openai
TTS_API_KEY=your_openai_api_key
```

**Generate SECRET_KEY:**
```bash
# On your local machine
openssl rand -hex 32
```

#### 1.4 Connect PostgreSQL Database

1. **Add PostgreSQL Plugin**:
   - Railway Dashboard → New → Database → PostgreSQL
   - Railway will automatically create `DATABASE_URL` variable

2. **Link to Backend Service**:
   - Click PostgreSQL service
   - Go to "Variables" tab
   - Copy `DATABASE_URL`
   - Backend service will automatically have access

3. **Initialize Database**:
   ```bash
   # After first deployment, run migrations
   railway run python init_db.py
   
   # Or connect to Railway shell
   railway shell
   python init_db.py
   exit
   ```

#### 1.5 Deploy Backend

```bash
# Option A: Auto-deploy from GitHub
# Push to main/staging branch - Railway auto-deploys

# Option B: Manual deploy via CLI
cd backend
railway up
```

#### 1.6 Verify Backend Deployment

```bash
# Get backend URL
railway domain

# Test health endpoint
curl https://your-backend.up.railway.app/health

# Should return: {"status":"healthy","timestamp":"..."}
```

---

### Step 2: Deploy Frontend to Railway

#### 2.1 Create Frontend Service

1. **New Service**: Railway Dashboard → New → GitHub Repo
2. **Set Root Directory**: `frontend`
3. **Configure Build**:
   - Build Command: `npm ci && npm run build`
   - Start Command: `npm run preview -- --host 0.0.0.0 --port $PORT`

#### 2.2 Add Frontend Environment Variables

```bash
# API URL (use your backend Railway URL)
VITE_API_URL=https://your-backend.up.railway.app

# App Config
VITE_APP_NAME=Audiobooker
VITE_MAX_FILE_SIZE=52428800
VITE_ENVIRONMENT=production
```

#### 2.3 Deploy Frontend

```bash
# Push to GitHub - Railway auto-deploys
git push origin feature/crud_service

# Or manual deploy
cd frontend
railway up
```

#### 2.4 Get Frontend URL

```bash
railway domain

# Your frontend will be at:
# https://your-frontend.up.railway.app
```

---

### Step 3: Update CORS Configuration

Now that you have both URLs, update backend CORS:

1. **Backend Service → Variables**
2. **Update CORS_ORIGINS**:
   ```bash
   CORS_ORIGINS=https://your-frontend.up.railway.app,https://yourdomain.com
   ```
3. **Redeploy backend** (Railway auto-redeploys on variable change)

---

### Step 4: Configure Custom Domains (Optional)

#### 4.1 Add Custom Domain to Backend

1. Railway Dashboard → Backend Service → Settings
2. Click "Generate Domain" or "Custom Domain"
3. Add your domain: `api.audiobooker.com`
4. Update DNS records as instructed

#### 4.2 Add Custom Domain to Frontend

1. Railway Dashboard → Frontend Service → Settings
2. Add your domain: `app.audiobooker.com`
3. Update DNS records

#### 4.3 Update CORS with Custom Domain

```bash
CORS_ORIGINS=https://app.audiobooker.com,https://your-frontend.up.railway.app
```

---

## Post-Deployment Tasks

### 1. Initialize Database

```bash
# Connect to Railway shell
railway shell

# Run database initialization
python init_db.py

# Verify tables created
python test_connection.py

exit
```

### 2. Test Complete Flow

1. **Health Check**:
   ```bash
   curl https://your-backend.up.railway.app/health
   ```

2. **Frontend Access**:
   - Visit: `https://your-frontend.up.railway.app`
   - Upload a test PDF
   - Verify file appears in audiobooks list

3. **Database Check**:
   ```bash
   # Railway Dashboard → PostgreSQL → Data
   # Verify audiobooks table has records
   ```

4. **R2 Storage Check**:
   - Login to Cloudflare R2 dashboard
   - Verify files uploaded to `audiobooker` bucket

### 3. Set Up Monitoring

#### Enable Railway Metrics

- Railway Dashboard → Service → Metrics
- Monitor: CPU, Memory, Response Time, Error Rate

#### Add Custom Logging (Optional)

```python
# Add to main.py
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### 4. Configure Alerts

1. Railway Dashboard → Project Settings → Webhooks
2. Add webhook for deployment notifications
3. Connect to Slack/Discord for alerts

---

## Environment Variables Reference

### Backend Required Variables

| Variable | Example | Description |
|----------|---------|-------------|
| `DATABASE_URL` | Auto-set by Railway | PostgreSQL connection |
| `R2_ACCOUNT_ID` | `1049d9c...` | Cloudflare account |
| `R2_ACCESS_KEY_ID` | `1d6d82e...` | R2 access key |
| `R2_SECRET_ACCESS_KEY` | `e491a96...` | R2 secret |
| `R2_BUCKET_NAME` | `audiobooker` | R2 bucket name |
| `R2_ENDPOINT_URL` | `https://...` | R2 endpoint |
| `SECRET_KEY` | `<random>` | App secret key |
| `CORS_ORIGINS` | `https://...` | Allowed origins |

### Frontend Required Variables

| Variable | Example | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `https://api...` | Backend API URL |
| `VITE_APP_NAME` | `Audiobooker` | App name |
| `VITE_MAX_FILE_SIZE` | `52428800` | Max upload size |

---

## Troubleshooting

### Backend Won't Start

```bash
# Check logs
railway logs

# Common issues:
# 1. Missing environment variables
# 2. Database connection failed
# 3. Port binding issue

# Verify environment
railway variables

# Test locally with Railway env
railway run python main.py
```

### Database Connection Error

```bash
# Verify DATABASE_URL is set
railway variables | grep DATABASE_URL

# Check PostgreSQL service is running
railway status

# Reconnect database
# Railway Dashboard → Backend → Variables → Link PostgreSQL
```

### CORS Errors

```bash
# Update CORS_ORIGINS with frontend URL
railway variables set CORS_ORIGINS=https://your-frontend.up.railway.app

# Check current CORS setting
curl -I https://your-backend.up.railway.app/health
```

### Frontend Build Fails

```bash
# Check Node version
# Railway uses Node 18 by default

# Add .nvmrc to frontend folder
echo "18" > frontend/.nvmrc

# Clear build cache
railway service delete-cache
```

### File Upload Fails

```bash
# Verify R2 credentials
railway run python -c "from storage_sdk import R2Client; R2Client()"

# Check R2 bucket CORS
# Cloudflare Dashboard → R2 → audiobooker → CORS
```

---

## CI/CD Pipeline

### Automatic Deployments

Railway automatically deploys when you push to connected branch:

```bash
# Deploy to staging
git push origin feature/crud_service

# Deploy to production
git push origin main
```

### Manual Deployments

```bash
# Deploy specific service
railway up --service backend

# Deploy all services
railway up
```

### Rollback

```bash
# Railway Dashboard → Service → Deployments
# Click previous deployment → "Redeploy"

# Or via CLI
railway rollback
```

---

## Scaling Configuration

### Vertical Scaling

Railway Dashboard → Service → Settings → Resources:
- **Starter**: 512MB RAM, 1 vCPU ($5/month)
- **Standard**: 2GB RAM, 2 vCPU ($10/month)
- **Pro**: 8GB RAM, 4 vCPU ($20/month)

### Horizontal Scaling

```json
// railway.json
{
  "deploy": {
    "numReplicas": 2
  }
}
```

---

## Cost Optimization

### Current Setup Estimate

| Service | Usage | Cost |
|---------|-------|------|
| Backend | 1 instance | $5/month |
| Frontend | 1 instance | $5/month |
| PostgreSQL | 1GB storage | Free |
| **Total** | | **$10/month** |

### Tips to Reduce Costs

1. **Use single instance** for low traffic
2. **Enable sleep mode** for staging (auto-sleep after 30 min inactivity)
3. **Optimize Docker images** to reduce build time
4. **Use Railway's free tier** ($5 credit/month)

---

## Security Checklist

- [x] `DEBUG=false` in production
- [x] Strong `SECRET_KEY` generated
- [x] CORS limited to specific domains
- [x] HTTPS enabled (automatic on Railway)
- [x] Database credentials in environment variables
- [x] R2 credentials secured
- [ ] Add rate limiting
- [ ] Enable authentication (future)
- [ ] Regular security audits

---

## Maintenance

### Regular Tasks

**Weekly:**
- Check error logs: `railway logs --tail`
- Monitor resource usage: Railway Dashboard → Metrics

**Monthly:**
- Update dependencies: `railway run pip list --outdated`
- Review costs: Railway Dashboard → Usage
- Backup database: `railway run pg_dump > backup.sql`

**Quarterly:**
- Security audit
- Performance optimization
- Cost analysis

---

## Next Steps

1. ✅ Deploy backend to Railway
2. ✅ Connect PostgreSQL
3. ✅ Initialize database
4. ✅ Deploy frontend
5. ✅ Update CORS
6. ✅ Test end-to-end
7. ⏳ Add custom domain
8. ⏳ Set up monitoring
9. ⏳ Configure alerts
10. ⏳ Document for team

---

## Support Resources

- **Railway Docs**: https://docs.railway.app
- **Railway Discord**: https://discord.gg/railway
- **Railway CLI**: https://docs.railway.app/develop/cli
- **Status Page**: https://status.railway.app

---

## Quick Commands Reference

```bash
# Login
railway login

# Link project
railway link

# View logs
railway logs

# Run command
railway run <command>

# Shell access
railway shell

# Set variable
railway variables set KEY=value

# Deploy
railway up

# Status
railway status

# Open dashboard
railway open
```

---

**Last Updated**: 2025-10-29  
**Version**: 1.0.0  
**Environment**: Production/Staging on Railway
