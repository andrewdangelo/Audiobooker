# Troubleshooting Guide

## Common Issues

### Backend Issues

#### 1. Backend Won't Start

**Symptom**: `uvicorn` fails to start or crashes immediately.

**Possible Causes**:
- Port 8000 already in use
- Missing dependencies
- Database connection failure
- Invalid environment variables

**Solutions**:

```bash
# Check if port is in use
netstat -ano | findstr :8000  # Windows
lsof -i :8000                  # macOS/Linux

# Kill process using port
# Windows: Find PID and kill in Task Manager
kill -9 <PID>                  # macOS/Linux

# Reinstall dependencies
cd backend
source venv/Scripts/activate
pip install -r requirements.txt

# Check database connection
python -c "from config.database import engine; engine.connect()"

# Verify environment variables
python -c "from config.settings import settings; print(settings.DATABASE_URL)"
```

#### 2. CORS Errors

**Symptom**: Browser shows "blocked by CORS policy" error.

**Error Message**:
```
Access to XMLHttpRequest at 'http://localhost:8000/api/v1/upload/' from origin 
'http://localhost:5173' has been blocked by CORS policy
```

**Solutions**:

1. **Check CORS configuration in `main.py`**:
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["http://localhost:5173", "http://localhost:3000"],
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

2. **Restart backend server** after making changes

3. **Clear browser cache** and hard reload (Ctrl+Shift+R)

4. **Check frontend is using correct API URL**:
   ```typescript
   // src/config/env.ts
   export const API_BASE_URL = 'http://localhost:8000'
   ```

#### 3. Database Connection Errors

**Symptom**: "Could not connect to database" or similar errors.

**Solutions**:

```bash
# Check PostgreSQL is running
docker-compose ps

# If not running, start it
docker-compose up -d postgres

# Check connection string
# backend/.env
DATABASE_URL=postgresql://audiobooker:password@localhost:5433/audiobooker_db

# Test connection
docker exec -it audiobooker-postgres psql -U audiobooker -d audiobooker_db

# Check logs
docker-compose logs postgres

# Recreate database
docker-compose down -v
docker-compose up -d postgres
# Wait 10 seconds
python -c "from config.database import Base, engine; Base.metadata.create_all(bind=engine)"
```

#### 4. File Upload Fails

**Symptom**: Upload returns 500 error or file not saved.

**Solutions**:

1. **Check upload directory exists**:
   ```bash
   cd backend
   mkdir -p uploads
   chmod 755 uploads
   ```

2. **Check file size limits**:
   ```python
   # config/settings.py
   MAX_UPLOAD_SIZE: int = 52428800  # 50MB
   ```

3. **Check storage service**:
   ```python
   # app/services/storage_service.py
   # Verify use_local is True for development
   self.use_local = not settings.R2_ENDPOINT_URL or \
                   settings.R2_ENDPOINT_URL.startswith("https://<account_id>")
   ```

4. **View detailed error logs**:
   ```bash
   # Run backend in foreground to see errors
   python -m uvicorn main:app --reload
   ```

### Frontend Issues

#### 1. Frontend Won't Start

**Symptom**: `npm run dev` fails or shows errors.

**Solutions**:

```bash
# Delete node_modules and reinstall
cd frontend
rm -rf node_modules package-lock.json
npm install

# Clear npm cache
npm cache clean --force

# Check Node version
node --version  # Should be 18.x or higher

# Try different port if 5173 is in use
npm run dev -- --port 3000
```

#### 2. Module Not Found Errors

**Symptom**: `Cannot find module '@/components/...'` or similar.

**Solutions**:

1. **Check path aliases in `vite.config.ts`**:
   ```typescript
   resolve: {
     alias: {
       "@": path.resolve(__dirname, "./src"),
     },
   }
   ```

2. **Check `tsconfig.json`**:
   ```json
   {
     "compilerOptions": {
       "paths": {
         "@/*": ["./src/*"]
       }
     }
   }
   ```

3. **Restart TypeScript server** in VS Code:
   - Press Ctrl+Shift+P
   - Type "Restart TS Server"

#### 3. Tailwind CSS Not Working

**Symptom**: Styles not applying or classes not found.

**Solutions**:

1. **Check `tailwind.config.js`**:
   ```javascript
   content: [
     "./index.html",
     "./src/**/*.{js,ts,jsx,tsx}",
   ]
   ```

2. **Check `index.css` imports**:
   ```css
   @tailwind base;
   @tailwind components;
   @tailwind utilities;
   ```

3. **Reinstall Tailwind**:
   ```bash
   npm install -D tailwindcss postcss autoprefixer
   npm install -D tailwindcss-animate
   ```

4. **Clear Vite cache**:
   ```bash
   rm -rf node_modules/.vite
   npm run dev
   ```

#### 4. API Calls Failing

**Symptom**: Network errors or 404 on API requests.

**Solutions**:

1. **Check API base URL**:
   ```typescript
   // src/config/env.ts
   console.log('API URL:', API_BASE_URL)
   ```

2. **Check backend is running**:
   ```bash
   curl http://localhost:8000/health
   ```

3. **Check endpoint path**:
   ```typescript
   // Should be /api/v1/upload/ not /upload
   api.post('/api/v1/upload/', formData)
   ```

4. **Check browser console for errors**

5. **Use browser DevTools Network tab** to inspect requests

### Docker Issues

#### 1. Docker Container Won't Start

**Symptom**: `docker-compose up` fails or container exits immediately.

**Solutions**:

```bash
# View container logs
docker-compose logs postgres

# Check container status
docker-compose ps

# Remove and recreate containers
docker-compose down
docker-compose up -d

# Check Docker daemon is running
docker ps

# Restart Docker Desktop (if on Windows/Mac)
```

#### 2. Port Already in Use

**Symptom**: "port is already allocated" error.

**Solutions**:

```bash
# Change port in docker-compose.yml
ports:
  - "5434:5432"  # Use different host port

# Or find and stop process using the port
# Windows:
netstat -ano | findstr :5433
# Then kill in Task Manager

# macOS/Linux:
lsof -i :5433
kill -9 <PID>
```

#### 3. Database Data Lost

**Symptom**: Data disappears after stopping containers.

**Solutions**:

```bash
# Don't use -v flag when stopping
docker-compose down  # Preserves volumes
# NOT: docker-compose down -v  # Deletes volumes

# Backup database before stopping
docker exec audiobooker-postgres pg_dump -U audiobooker audiobooker_db > backup.sql

# Restore if needed
docker exec -i audiobooker-postgres psql -U audiobooker -d audiobooker_db < backup.sql
```

### Development Environment Issues

#### 1. Python Virtual Environment Issues

**Symptom**: Wrong Python version or packages not found.

**Solutions**:

```bash
# Recreate virtual environment
cd backend
rm -rf venv
python -m venv venv
source venv/Scripts/activate  # Windows Git Bash
source venv/bin/activate      # macOS/Linux
pip install -r requirements.txt

# Verify correct Python
which python
python --version

# Verify packages
pip list
```

#### 2. Git Issues

**Symptom**: Can't push, merge conflicts, etc.

**Solutions**:

```bash
# Discard local changes
git restore .

# Resolve merge conflicts
git status  # See conflicted files
# Edit files to resolve conflicts
git add .
git commit -m "Resolve merge conflicts"

# Reset to remote
git fetch origin
git reset --hard origin/master

# Clean untracked files
git clean -fd
```

#### 3. Environment Variables Not Loading

**Symptom**: Application uses default values instead of `.env`.

**Solutions**:

1. **Check `.env` file exists**:
   ```bash
   ls -la backend/.env
   ls -la frontend/.env
   ```

2. **Check `.env` syntax** (no quotes needed):
   ```properties
   # Correct
   DATABASE_URL=postgresql://user:pass@localhost:5433/db

   # Incorrect
   DATABASE_URL="postgresql://user:pass@localhost:5433/db"
   ```

3. **Restart servers after changing `.env`**

4. **Check Python loads env**:
   ```python
   from config.settings import settings
   print(settings.DATABASE_URL)
   ```

5. **Check Vite loads env** (must start with `VITE_`):
   ```typescript
   console.log(import.meta.env.VITE_API_URL)
   ```

## Error Messages

### Backend Error Messages

#### "ModuleNotFoundError: No module named 'X'"

```bash
# Install missing package
pip install <package-name>

# Or reinstall all dependencies
pip install -r requirements.txt
```

#### "sqlalchemy.exc.OperationalError: could not connect to server"

```bash
# Check PostgreSQL is running
docker-compose ps

# Check connection string
echo $DATABASE_URL

# Test connection
psql -U audiobooker -h localhost -p 5433 -d audiobooker_db
```

#### "FastAPI: 422 Unprocessable Entity"

- Request body doesn't match Pydantic schema
- Check request data types
- View detailed error in response body

### Frontend Error Messages

#### "Failed to resolve import"

```bash
# Clear cache and reinstall
rm -rf node_modules/.vite
npm install
```

#### "Unexpected token '<'"

- JavaScript file served instead of JSON (usually 404)
- Check API endpoint exists
- Check backend is running

#### "Network Error" / "ERR_NETWORK"

- Backend not running
- Wrong API URL
- CORS not configured
- Firewall blocking connection

## Performance Issues

### Backend Slow

```python
# Add logging to identify slow operations
import time
import logging

logger = logging.getLogger(__name__)

@router.post("/upload")
async def upload(file: UploadFile):
    start = time.time()
    
    # Your code
    
    duration = time.time() - start
    logger.info(f"Upload took {duration:.2f}s")
```

### Frontend Slow

```typescript
// Use React DevTools Profiler
// Check Network tab for slow API calls
// Use Lighthouse for performance audit
```

### Database Slow

```sql
-- Check slow queries
SELECT * FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;

-- Add indexes
CREATE INDEX idx_audiobooks_status ON audiobooks(status);
```

## Getting Help

### Check Logs

```bash
# Backend logs
python -m uvicorn main:app --reload

# Frontend logs
npm run dev

# Docker logs
docker-compose logs -f

# PostgreSQL logs
docker-compose logs postgres
```

### Debug Mode

```python
# backend/main.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

```typescript
// frontend - Check browser console
console.log('Debug info:', data)
```

### Report an Issue

Include:
1. Error message (full stack trace)
2. Steps to reproduce
3. Environment (OS, Python version, Node version)
4. Relevant code snippets
5. Logs from backend/frontend/docker

### Useful Commands

```bash
# Check all services status
docker-compose ps
curl http://localhost:8000/health
curl http://localhost:5173

# View all ports in use
netstat -ano | findstr LISTENING  # Windows
lsof -i -P | grep LISTEN           # macOS/Linux

# Restart everything
docker-compose down
docker-compose up -d postgres
cd backend && source venv/Scripts/activate && uvicorn main:app --reload
cd frontend && npm run dev
```
