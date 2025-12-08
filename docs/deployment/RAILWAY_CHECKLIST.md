# Railway Deployment Checklist

Quick reference for deploying Audiobooker to Railway.

## Pre-Deployment

- [ ] All code committed to Git
- [ ] Tests passing
- [ ] Environment variables documented
- [ ] Database schema finalized

## Backend Deployment

### 1. Create Backend Service
- [ ] Railway Dashboard → New → GitHub Repo
- [ ] Select repository: `andrewdangelo/Audiobooker`
- [ ] Set root directory: `backend`

### 2. Configure Build
- [ ] Build command: `pip install -r requirements.txt`
- [ ] Start command: Auto-detected from `Procfile`
- [ ] Python version: 3.9 (from `.python-version`)

### 3. Add PostgreSQL
- [ ] New → Database → PostgreSQL
- [ ] Verify `DATABASE_URL` variable created
- [ ] Note: Railway auto-links to backend service

### 4. Set Environment Variables
```bash
# Required
- [ ] R2_ACCOUNT_ID=1049d9c736f1ba301b3a8c76ede09455
- [ ] R2_ACCESS_KEY_ID=1d6d82ee3822ae2490bcb0b0b4759470
- [ ] R2_SECRET_ACCESS_KEY=e491a96a668dea6fb464f6e68b7549e7b01e06d659cf30350aa95403b3183ec4
- [ ] R2_BUCKET_NAME=audiobooker
- [ ] R2_ENDPOINT_URL=https://1049d9c736f1ba301b3a8c76ede09455.r2.cloudflarestorage.com
- [ ] SECRET_KEY=<generate-with-openssl-rand-hex-32>

# Application
- [ ] ENVIRONMENT=production
- [ ] DEBUG=false
- [ ] API_V1_PREFIX=/api/v1

# Will update after frontend deployment
- [ ] CORS_ORIGINS=https://your-frontend.up.railway.app

# Optional
- [ ] TTS_PROVIDER=openai
- [ ] TTS_API_KEY=<your-key>
```

### 5. Generate SECRET_KEY
```bash
# Run locally
openssl rand -hex 32
# Copy output to Railway
```

### 6. Deploy Backend
- [ ] Push to GitHub or click "Deploy" in Railway
- [ ] Wait for build to complete
- [ ] Check logs for errors

### 7. Initialize Database
```bash
# Option A: Railway CLI
railway shell
python init_db.py
exit

# Option B: One-liner
railway run python init_db.py
```

### 8. Test Backend
```bash
# Get URL from Railway Dashboard
- [ ] Copy backend URL: https://________.up.railway.app
- [ ] Test health: curl https://________.up.railway.app/health
- [ ] Should return: {"status":"healthy","timestamp":"..."}
```

## Frontend Deployment

### 1. Create Frontend Service
- [ ] Railway Dashboard → New → GitHub Repo
- [ ] Select same repository
- [ ] Set root directory: `frontend`

### 2. Configure Build
- [ ] Build command: `npm ci && npm run build`
- [ ] Start command: Auto-detected from `railway.json`

### 3. Set Environment Variables
```bash
- [ ] VITE_API_URL=https://________.up.railway.app (your backend URL)
- [ ] VITE_APP_NAME=Audiobooker
- [ ] VITE_MAX_FILE_SIZE=52428800
- [ ] VITE_ENVIRONMENT=production
```

### 4. Deploy Frontend
- [ ] Push to GitHub or click "Deploy"
- [ ] Wait for build to complete
- [ ] Check logs for errors

### 5. Test Frontend
```bash
- [ ] Copy frontend URL: https://________.up.railway.app
- [ ] Open in browser
- [ ] Verify page loads
- [ ] Check browser console for errors
```

## Update CORS

### 1. Add Frontend URL to Backend CORS
- [ ] Go to Backend Service → Variables
- [ ] Update `CORS_ORIGINS`: 
  ```
  https://your-frontend-url.up.railway.app
  ```
- [ ] Railway will auto-redeploy

### 2. Wait for Redeploy
- [ ] Check deployment logs
- [ ] Verify no errors

## End-to-End Testing

### 1. Test Complete Flow
- [ ] Open frontend URL in browser
- [ ] Upload a test PDF file
- [ ] Verify upload succeeds (no CORS errors)
- [ ] Check audiobook appears in list
- [ ] Try downloading PDF (presigned URL)

### 2. Verify Backend
```bash
- [ ] Check backend logs: railway logs --service backend
- [ ] Verify upload logged
- [ ] No errors in logs
```

### 3. Verify Database
```bash
- [ ] Railway Dashboard → PostgreSQL → Data
- [ ] Check audiobooks table has record
- [ ] Verify PDF path contains R2 URL
```

### 4. Verify R2 Storage
- [ ] Login to Cloudflare R2 dashboard
- [ ] Open `audiobooker` bucket
- [ ] Verify file uploaded with correct path: `{book_id}/pdf/{filename}`

## Post-Deployment

### 1. Document URLs
```
Backend URL: https://________.up.railway.app
Frontend URL: https://________.up.railway.app
Database: (Railway internal)
```

### 2. Save to Team Documentation
- [ ] Share URLs with team
- [ ] Update README with production URLs
- [ ] Document environment variables

### 3. Set Up Monitoring
- [ ] Railway Dashboard → Metrics (enabled by default)
- [ ] Optional: Add Sentry for error tracking
- [ ] Optional: Set up uptime monitoring

### 4. Configure Alerts (Optional)
- [ ] Railway → Project Settings → Webhooks
- [ ] Add Discord/Slack webhook for deployment notifications

## Custom Domain (Optional)

### 1. Backend Custom Domain
- [ ] Railway Dashboard → Backend → Settings → Domains
- [ ] Click "Custom Domain"
- [ ] Add: `api.audiobooker.com`
- [ ] Update DNS with provided CNAME
- [ ] Wait for SSL certificate (automatic)

### 2. Frontend Custom Domain
- [ ] Railway Dashboard → Frontend → Settings → Domains
- [ ] Add: `app.audiobooker.com`
- [ ] Update DNS with provided CNAME
- [ ] Wait for SSL certificate

### 3. Update CORS Again
- [ ] Backend Variables → Update CORS_ORIGINS
  ```
  https://app.audiobooker.com,https://your-frontend.up.railway.app
  ```

## Troubleshooting

### Backend Issues
```bash
# View logs
railway logs --service backend

# Check variables
railway variables --service backend

# Restart service
railway restart --service backend

# Shell access
railway shell --service backend
```

### Frontend Issues
```bash
# View logs
railway logs --service frontend

# Check build output
railway logs --deployment <deployment-id>

# Verify env vars loaded
railway variables --service frontend
```

### Database Issues
```bash
# Check connection
railway run python test_connection.py

# View PostgreSQL logs
railway logs --service PostgreSQL

# Connect to database
railway connect PostgreSQL
```

### CORS Issues
- [ ] Verify CORS_ORIGINS matches frontend URL exactly
- [ ] Check both http:// and https://
- [ ] No trailing slashes
- [ ] Backend redeployed after CORS update

## Rollback Procedure

### If Deployment Fails
1. [ ] Railway Dashboard → Service → Deployments
2. [ ] Find previous working deployment
3. [ ] Click "..." → "Redeploy"

### If Data Issues
1. [ ] Don't panic - R2 files are safe
2. [ ] Check database backup
3. [ ] Restore from backup if needed

## Success Criteria

- [x] Backend health check returns 200
- [x] Frontend loads without errors
- [x] File upload works end-to-end
- [x] Database records created
- [x] R2 files stored correctly
- [x] No CORS errors
- [x] No console errors

---

## Quick Reference Commands

```bash
# Login to Railway
railway login

# Link to project
railway link

# View all services
railway status

# Deploy specific service
railway up --service backend

# View logs
railway logs --tail

# Run command
railway run python init_db.py

# Shell access
railway shell

# Set variable
railway variables set KEY=value

# Restart service
railway restart

# Open dashboard
railway open
```

---

## Support

**Railway Issues:**
- Docs: https://docs.railway.app
- Discord: https://discord.gg/railway
- Status: https://status.railway.app

**Application Issues:**
- Check logs: `railway logs`
- Review deployment guide: `RAILWAY_DEPLOYMENT.md`

---

**Deployment Date**: _______________  
**Deployed By**: _______________  
**Backend URL**: _______________  
**Frontend URL**: _______________  
**Status**: ⏸️ Pending / ✅ Complete
