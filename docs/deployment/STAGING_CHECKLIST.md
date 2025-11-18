# ✅ Railway Staging Deployment Checklist

Quick checklist for deploying to Railway staging environment.

## Pre-Deployment Verification

- [ ] Currently on `staging` branch
- [ ] All code committed and pushed to GitHub
- [ ] Railway account created
- [ ] `.env.staging` reviewed (don't commit!)
- [ ] Backend files ready:
  - [ ] `railway.json` exists
  - [ ] `Procfile` exists
  - [ ] `.python-version` exists
  - [ ] `requirements.txt` includes `gunicorn==21.2.0`

## Railway Project Setup

### 1. Create Railway Project
- [ ] Go to https://railway.app/dashboard
- [ ] Click "New Project"
- [ ] Select "Deploy from GitHub repo"
- [ ] Choose: `andrewdangelo/Audiobooker`
- [ ] **Select branch**: `staging` ⚠️
- [ ] Click "Deploy Now"

### 2. Configure Backend Service
- [ ] Click on backend service card
- [ ] Settings → **Root Directory**: `backend`
- [ ] Settings → **Branch**: `staging`
- [ ] Verify build/start commands detected from `railway.json`

### 3. Add PostgreSQL Database
- [ ] Click "New" → "Database" → "Add PostgreSQL"
- [ ] Wait for database provisioning
- [ ] Verify `DATABASE_URL` auto-injected to backend service

## Environment Variables Setup

### Generate Secret Key First
```bash
# Run this locally
openssl rand -hex 32
```
Copy the output ⬆️

### Set Variables in Railway Dashboard

Navigate to: Backend Service → Variables tab

#### Required Variables:
```bash
ENVIRONMENT=staging
DEBUG=false
SECRET_KEY=<paste-generated-key-here>
API_V1_PREFIX=/api/v1

# R2 Configuration
R2_ACCOUNT_ID=1049d9c736f1ba301b3a8c76ede09455
R2_ACCESS_KEY_ID=1d6d82ee3822ae2490bcb0b0b4759470
R2_SECRET_ACCESS_KEY=e491a96a668dea6fb464f6e68b7549e7b01e06d659cf30350aa95403b3183ec4
R2_BUCKET_NAME=audiobooker
R2_ENDPOINT_URL=https://1049d9c736f1ba301b3a8c76ede09455.r2.cloudflarestorage.com

# CORS (will update after frontend)
CORS_ORIGINS=http://localhost:5173

# File Upload
MAX_UPLOAD_SIZE=52428800
ALLOWED_EXTENSIONS=.pdf
```

#### Optional Variables:
```bash
TTS_PROVIDER=openai
TTS_API_KEY=your_key_here
```

### Variable Checklist
- [ ] `ENVIRONMENT=staging`
- [ ] `DEBUG=false`
- [ ] `SECRET_KEY` (generated & unique)
- [ ] `API_V1_PREFIX=/api/v1`
- [ ] `R2_ACCOUNT_ID`
- [ ] `R2_ACCESS_KEY_ID`
- [ ] `R2_SECRET_ACCESS_KEY`
- [ ] `R2_BUCKET_NAME`
- [ ] `R2_ENDPOINT_URL`
- [ ] `CORS_ORIGINS` (temporary, will update)
- [ ] `MAX_UPLOAD_SIZE=52428800`
- [ ] `ALLOWED_EXTENSIONS=.pdf`
- [ ] `DATABASE_URL` (auto-injected by Railway) ✓

## Database Initialization

### Option 1: Railway CLI
```bash
# Install CLI if needed
curl -fsSL https://railway.app/install.sh | sh

# Login
railway login

# Link to project
railway link

# Run database setup
railway run python init_db.py

# Test connection
railway run python test_connection.py
```

- [ ] CLI installed and logged in
- [ ] Project linked
- [ ] `init_db.py` executed successfully
- [ ] Connection test passed

### Option 2: Railway Dashboard
- [ ] Service → Deployments → Latest → Shell
- [ ] Run: `python init_db.py`
- [ ] Run: `python test_connection.py`
- [ ] Verify: "✅ Connected" message

## Deployment Verification

### 1. Get Backend URL
- [ ] Service → Settings → Domains
- [ ] Copy Railway URL: `https://______________.up.railway.app`
- [ ] Document URL: ___________________________________

### 2. Test Endpoints

```bash
# Replace with your actual URL
BACKEND_URL=https://your-backend.up.railway.app

# Test health
curl $BACKEND_URL/health
# Expected: {"status":"healthy","timestamp":"..."}

# Open API docs in browser
# https://your-backend.up.railway.app/docs
```

- [ ] Health endpoint returns 200
- [ ] API docs page loads
- [ ] Swagger UI displays all endpoints

### 3. Check Logs
- [ ] Service → Deployments → Latest → View Logs
- [ ] Look for: "🚀 Audiobooker API starting up..."
- [ ] Look for: "Uvicorn running on http://0.0.0.0:8000"
- [ ] No error messages

### 4. Check Metrics
- [ ] Service → Metrics tab
- [ ] CPU usage normal
- [ ] Memory usage normal
- [ ] Service responding

## Post-Deployment Tasks

### Document Deployment
```
Deployment Date: _______________
Deployed By: _______________
Backend URL: https://_______________
Database: Railway PostgreSQL (staging)
Branch: staging
Status: ⏸️ Pending / ✅ Complete
```

### Update Team Documentation
- [ ] Add staging backend URL to README
- [ ] Share URL with team
- [ ] Update project documentation

## Frontend Deployment (Next)

After backend is verified:

- [ ] Deploy frontend to Railway staging
- [ ] Get frontend URL: `https://_______________`
- [ ] Update backend `CORS_ORIGINS`:
  ```
  CORS_ORIGINS=https://your-frontend-staging.up.railway.app,http://localhost:5173
  ```
- [ ] Backend will auto-redeploy with new CORS

## End-to-End Testing (After Frontend Deploy)

- [ ] Open frontend URL
- [ ] Upload test PDF file
- [ ] Verify upload succeeds (no CORS errors)
- [ ] Check backend logs for upload request
- [ ] Verify database record created
- [ ] Verify file in R2 bucket
- [ ] Test download/presigned URL

## Troubleshooting

### Build Failed
```bash
# Check logs
railway logs --deployment

# Common fixes:
# - Verify requirements.txt
# - Check .python-version
# - Verify root directory = backend

# Rebuild
railway up
```

### Database Connection Failed
```bash
# Check DATABASE_URL exists
railway variables | grep DATABASE_URL

# Test connection
railway run python test_connection.py

# Check PostgreSQL service running
# Dashboard → PostgreSQL service → Status
```

### Application Won't Start
```bash
# Check logs
railway logs --tail

# Verify Procfile command
# Check port binding in main.py
# Verify gunicorn in requirements.txt
```

### Health Check Fails
```bash
# Check if service is up
railway status

# Check logs
railway logs

# Verify health endpoint exists
# backend/app/routers/health.py
```

## Rollback Procedure

If deployment fails:

1. [ ] Dashboard → Service → Deployments
2. [ ] Find previous working deployment
3. [ ] Click "..." → "Redeploy"
4. [ ] Monitor logs for successful startup

## Success Criteria

All must be ✅ before proceeding:

- [x] Backend deployed without errors
- [x] PostgreSQL database connected
- [x] All environment variables set
- [x] Database tables initialized
- [x] Health endpoint returns 200
- [x] API docs accessible
- [x] Logs show no errors
- [x] Service metrics normal
- [x] Backend URL documented

## Quick Commands Reference

```bash
# Login to Railway
railway login

# Link project
railway link

# View logs
railway logs --tail

# Set variable
railway variables set KEY=value

# Run command
railway run python init_db.py

# Shell access
railway shell

# Deploy
railway up

# Restart
railway restart

# Open dashboard
railway open
```

## Support Resources

- **Railway Docs**: https://docs.railway.app
- **Full Deployment Guide**: `RAILWAY_STAGING_DEPLOY.md`
- **Main Railway Guide**: `RAILWAY_DEPLOYMENT.md`
- **Railway Discord**: https://discord.gg/railway
- **Status Page**: https://status.railway.app

---

## Next Steps After Completion

1. ✅ Backend staging deployed
2. 📋 Deploy frontend staging
3. 🔄 Update CORS_ORIGINS
4. 🧪 End-to-end testing
5. 📊 Monitor for 24-48 hours
6. 🚀 Ready for production deployment

**Status**: ⏸️ Not Started / 🔄 In Progress / ✅ Complete
