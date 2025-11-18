# Railway Staging Deployment Guide

Quick guide to deploy Audiobooker backend to Railway staging environment.

## Prerequisites

- ✅ Railway account created
- ✅ Railway CLI installed (optional but recommended)
- ✅ Git repository pushed to GitHub
- ✅ Currently on `staging` branch

## Step 1: Install Railway CLI (Optional)

```bash
# Windows (PowerShell)
iwr https://railway.app/install.ps1 | iex

# macOS/Linux
curl -fsSL https://railway.app/install.sh | sh

# Verify installation
railway --version

# Login to Railway
railway login
```

## Step 2: Deploy Backend to Railway

### Option A: Using Railway Dashboard (Recommended for First Deploy)

1. **Go to Railway Dashboard**
   - Visit: https://railway.app/dashboard
   - Click "New Project"

2. **Deploy from GitHub**
   - Select "Deploy from GitHub repo"
   - Choose repository: `andrewdangelo/Audiobooker`
   - **Important**: Select branch `staging`
   - Click "Deploy Now"

3. **Configure Service**
   - Railway will auto-detect the service
   - Click on the service card
   - Go to "Settings"
   - **Root Directory**: Set to `backend`
   - **Branch**: Ensure it's set to `staging`

4. **Configure Build & Deploy**
   - Railway should auto-detect from `railway.json`
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --timeout 120`
   - Python version: 3.9 (from `.python-version`)

### Option B: Using Railway CLI

```bash
# Navigate to backend directory
cd backend

# Initialize Railway project
railway init

# Select "Create new project"
# Name: "audiobooker-staging"

# Link to staging environment
railway environment staging

# Deploy
railway up
```

## Step 3: Add PostgreSQL Database

### Using Railway Dashboard:

1. **Add Database**
   - In your project, click "New" → "Database" → "Add PostgreSQL"
   - Railway automatically creates a PostgreSQL instance
   - Railway auto-injects `DATABASE_URL` into your service

2. **Verify Connection**
   - Go to PostgreSQL service → "Variables"
   - Copy `DATABASE_URL` (for reference)
   - The backend service should automatically have access to this variable

### Using Railway CLI:

```bash
# Add PostgreSQL
railway add --database postgres

# Link services (should be automatic)
railway link
```

## Step 4: Set Environment Variables

### Using Railway Dashboard:

1. **Go to Backend Service**
   - Click on your backend service
   - Go to "Variables" tab

2. **Add Variables** (from `.env.staging`):

```bash
# Application Settings
ENVIRONMENT=staging
DEBUG=false
API_V1_PREFIX=/api/v1

# Secret Key (GENERATE NEW ONE!)
SECRET_KEY=<run: openssl rand -hex 32>

# Cloudflare R2
R2_ACCOUNT_ID=1049d9c736f1ba301b3a8c76ede09455
R2_ACCESS_KEY_ID=1d6d82ee3822ae2490bcb0b0b4759470
R2_SECRET_ACCESS_KEY=e491a96a668dea6fb464f6e68b7549e7b01e06d659cf30350aa95403b3183ec4
R2_BUCKET_NAME=audiobooker
R2_ENDPOINT_URL=https://1049d9c736f1ba301b3a8c76ede09455.r2.cloudflarestorage.com

# CORS (update after frontend deploy)
CORS_ORIGINS=https://audiobooker-staging-frontend.up.railway.app,http://localhost:5173

# File Upload
MAX_UPLOAD_SIZE=52428800
ALLOWED_EXTENSIONS=.pdf

# TTS (optional for staging)
TTS_PROVIDER=openai
TTS_API_KEY=your_api_key_here
```

3. **Generate SECRET_KEY**:
   ```bash
   # Run locally
   openssl rand -hex 32
   
   # Copy the output and paste as SECRET_KEY value
   ```

### Using Railway CLI:

```bash
# Set variables one by one
railway variables set ENVIRONMENT=staging
railway variables set DEBUG=false
railway variables set SECRET_KEY=$(openssl rand -hex 32)
railway variables set R2_ACCOUNT_ID=1049d9c736f1ba301b3a8c76ede09455
railway variables set R2_ACCESS_KEY_ID=1d6d82ee3822ae2490bcb0b0b4759470
railway variables set R2_SECRET_ACCESS_KEY=e491a96a668dea6fb464f6e68b7549e7b01e06d659cf30350aa95403b3183ec4
railway variables set R2_BUCKET_NAME=audiobooker
railway variables set R2_ENDPOINT_URL=https://1049d9c736f1ba301b3a8c76ede09455.r2.cloudflarestorage.com
railway variables set CORS_ORIGINS=http://localhost:5173
railway variables set MAX_UPLOAD_SIZE=52428800
railway variables set ALLOWED_EXTENSIONS=.pdf

# View all variables
railway variables
```

## Step 5: Initialize Database

### Using Railway CLI:

```bash
# Connect to your Railway project
railway link

# Run database initialization
railway run python init_db.py

# Verify connection
railway run python test_connection.py
```

### Using Railway Dashboard Shell:

1. Go to backend service → "Deployments" → Select latest deployment
2. Click "View Logs" then "Shell" tab
3. Run:
   ```bash
   python init_db.py
   python test_connection.py
   ```

## Step 6: Verify Deployment

### 1. Get Backend URL

**Dashboard:**
- Go to backend service → "Settings" → "Domains"
- Copy the Railway-provided URL: `https://your-backend-xxx.up.railway.app`

**CLI:**
```bash
railway domain
```

### 2. Test Health Endpoint

```bash
# Replace with your actual URL
curl https://your-backend-xxx.up.railway.app/health

# Expected response:
# {"status":"healthy","timestamp":"..."}
```

### 3. Test API Documentation

Open in browser:
```
https://your-backend-xxx.up.railway.app/docs
```

Should see FastAPI Swagger UI.

### 4. Check Logs

**Dashboard:**
- Backend service → "Deployments" → Latest deployment → "View Logs"

**CLI:**
```bash
railway logs
```

Look for:
- ✅ "Uvicorn running on http://0.0.0.0:8000"
- ✅ "🚀 Audiobooker API starting up..."
- ❌ No errors

## Step 7: Update CORS (After Frontend Deploy)

Once you deploy the frontend and get its URL:

### Using Dashboard:

1. Go to backend service → "Variables"
2. Update `CORS_ORIGINS`:
   ```
   https://your-frontend-staging.up.railway.app,http://localhost:5173
   ```
3. Railway will auto-redeploy

### Using CLI:

```bash
railway variables set CORS_ORIGINS=https://your-frontend-staging.up.railway.app,http://localhost:5173
```

## Step 8: Configure Custom Domain (Optional)

### Using Dashboard:

1. Backend service → "Settings" → "Domains"
2. Click "Custom Domain"
3. Add: `api-staging.yourdomain.com`
4. Update your DNS with provided CNAME record
5. Wait for SSL certificate (automatic)

### Using CLI:

```bash
railway domain add api-staging.yourdomain.com
```

## Troubleshooting

### Build Failures

**Check logs:**
```bash
railway logs --deployment
```

**Common issues:**
- ❌ Missing dependencies → Check `requirements.txt`
- ❌ Python version mismatch → Verify `.python-version`
- ❌ Wrong root directory → Set to `backend` in settings

**Fix:**
```bash
# Rebuild
railway up --detach
```

### Database Connection Failed

**Verify DATABASE_URL:**
```bash
railway variables | grep DATABASE_URL
```

**Test connection:**
```bash
railway run python test_connection.py
```

**Common issues:**
- ❌ DATABASE_URL not set → Add PostgreSQL service
- ❌ Service not linked → Check service linking in dashboard

### Application Won't Start

**Check start command:**
```bash
# Should be in Procfile and railway.json
gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT
```

**Check logs for errors:**
```bash
railway logs --tail
```

**Common issues:**
- ❌ Missing gunicorn → Check `requirements.txt`
- ❌ PORT not bound correctly → Verify `main.py` uses `os.getenv("PORT", 8000)`

### CORS Errors

**Verify CORS_ORIGINS:**
```bash
railway variables | grep CORS_ORIGINS
```

**Update and redeploy:**
```bash
railway variables set CORS_ORIGINS=https://your-frontend.up.railway.app
```

### R2 Upload Failures

**Check R2 credentials:**
```bash
railway variables | grep R2
```

**Test R2 connection:**
```bash
railway run python -c "from storage_sdk import R2Client; print('R2 OK')"
```

## Monitoring & Maintenance

### View Metrics

**Dashboard:**
- Service → "Metrics" tab
- View CPU, Memory, Network usage

### View Logs

```bash
# Real-time logs
railway logs --tail

# Recent logs
railway logs
```

### Restart Service

**Dashboard:**
- Service → "Settings" → "Restart"

**CLI:**
```bash
railway restart
```

### Redeploy

```bash
# From backend directory
railway up

# Or trigger from dashboard
# Service → "Deployments" → "Redeploy"
```

## Environment Management

### Create Staging Environment

```bash
# If not already created
railway environment create staging

# Switch to staging
railway environment staging
```

### List Environments

```bash
railway environment list
```

### Switch Environments

```bash
# Switch to production
railway environment production

# Switch to staging
railway environment staging
```

## Quick Reference Commands

```bash
# Login
railway login

# Link project
railway link

# Deploy
railway up

# View logs
railway logs --tail

# Set variable
railway variables set KEY=value

# Run command
railway run <command>

# Open dashboard
railway open

# Shell access
railway shell

# View status
railway status

# Restart service
railway restart
```

## Success Checklist

Before considering staging deployment complete:

- [ ] Backend deployed successfully
- [ ] PostgreSQL database added and linked
- [ ] All environment variables set (from `.env.staging`)
- [ ] SECRET_KEY generated and set (unique, secure)
- [ ] Database initialized (`init_db.py` run successfully)
- [ ] Health endpoint returns 200: `/health`
- [ ] API docs accessible: `/docs`
- [ ] Logs show no errors
- [ ] R2 credentials configured
- [ ] CORS will be updated after frontend deploy
- [ ] Backend URL documented: `https://________.up.railway.app`

## Next Steps

1. ✅ Backend deployed to staging
2. 📋 Deploy frontend to staging
3. 🔄 Update CORS_ORIGINS with frontend URL
4. 🧪 Test end-to-end file upload
5. ✅ Verify database records
6. ✅ Verify R2 storage
7. 📊 Monitor logs and metrics
8. 🚀 Ready for production deployment

## Support

**Railway Issues:**
- Docs: https://docs.railway.app
- Discord: https://discord.gg/railway
- Status: https://status.railway.app

**Application Issues:**
- Check logs: `railway logs --tail`
- Review main deployment guide: `RAILWAY_DEPLOYMENT.md`
- Check checklist: `RAILWAY_CHECKLIST.md`

---

**Deployment Date**: _______________  
**Deployed By**: _______________  
**Backend Staging URL**: _______________  
**Database**: Railway PostgreSQL (staging)  
**Status**: ⏸️ Pending / ✅ Complete
