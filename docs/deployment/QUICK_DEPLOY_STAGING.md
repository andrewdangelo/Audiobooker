# 🎯 Railway Staging - Quick Deploy

**Backend is ready for Railway staging deployment!** Follow these steps:

## ⚡ 3-Minute Quick Start

### 1. Open Railway Dashboard
```
https://railway.app/dashboard
```

### 2. Create New Project
- Click "New Project"
- "Deploy from GitHub repo"
- Repository: `andrewdangelo/Audiobooker`
- **Branch**: `staging` ⚠️
- Click "Deploy Now"

### 3. Configure Service
- Click on service → Settings
- **Root Directory**: `backend`
- **Branch**: `staging`

### 4. Add Database
- Click "New" → "Database" → "Add PostgreSQL"
- Wait ~30 seconds

### 5. Set Environment Variables

Click service → Variables tab → Add each:

```bash
ENVIRONMENT=staging
DEBUG=false
SECRET_KEY=<run: openssl rand -hex 32>
API_V1_PREFIX=/api/v1
R2_ACCOUNT_ID=1049d9c736f1ba301b3a8c76ede09455
R2_ACCESS_KEY_ID=1d6d82ee3822ae2490bcb0b0b4759470
R2_SECRET_ACCESS_KEY=e491a96a668dea6fb464f6e68b7549e7b01e06d659cf30350aa95403b3183ec4
R2_BUCKET_NAME=audiobooker
R2_ENDPOINT_URL=https://1049d9c736f1ba301b3a8c76ede09455.r2.cloudflarestorage.com
CORS_ORIGINS=http://localhost:5173
MAX_UPLOAD_SIZE=52428800
ALLOWED_EXTENSIONS=.pdf
```

**Generate SECRET_KEY locally first:**
```bash
openssl rand -hex 32
```

### 6. Initialize Database

**Option A - Railway CLI:**
```bash
railway login
railway link
railway run python init_db.py
```

**Option B - Dashboard:**
- Service → Deployments → Latest → Shell
- Run: `python init_db.py`

### 7. Test Deployment

Get your URL from: Service → Settings → Domains

```bash
# Test health
curl https://your-backend.up.railway.app/health

# Open API docs
https://your-backend.up.railway.app/docs
```

---

## ✅ Success Checklist

- [ ] Service deployed (green checkmark)
- [ ] PostgreSQL connected
- [ ] All env vars set (12 total)
- [ ] Database initialized
- [ ] Health endpoint returns 200
- [ ] API docs loads
- [ ] No errors in logs

---

## 📚 Full Documentation

**New to Railway?** → Start with `STAGING_CHECKLIST.md`  
**Need details?** → See `RAILWAY_STAGING_DEPLOY.md`  
**Troubleshooting?** → Check `RAILWAY_DEPLOYMENT.md`

---

## 🆘 Quick Troubleshooting

**Build Failed?**
- Check root directory = `backend`
- Check branch = `staging`

**Database Error?**
- Verify PostgreSQL service added
- Run `railway run python test_connection.py`

**Service Won't Start?**
- Check logs: Service → Deployments → View Logs
- Verify all env vars set

**Health Check 404?**
- Wait 2-3 minutes for deployment
- Check logs for startup errors

---

**Time Estimate**: ~15 minutes  
**Difficulty**: Easy (follow checklist)  
**Prerequisites**: Railway account, GitHub connected

🚀 **Ready? Open `STAGING_CHECKLIST.md` and start!**
