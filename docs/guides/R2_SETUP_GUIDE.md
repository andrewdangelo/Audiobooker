# Cloudflare R2 Setup Guide

## What Was Updated

I've configured the backend to integrate Cloudflare R2 storage with PostgreSQL. Here's what changed:

### 1. **Enhanced Storage Service** (`backend/app/services/storage_service.py`)
- Added better R2 connection validation
- Improved error handling with automatic local fallback
- Added logging for debugging
- Returns proper R2 URL paths (`r2://bucket-name/filename`)

### 2. **Updated Upload Router** (`backend/app/routers/upload.py`)
- Now integrates `StorageService` to upload files to R2
- Creates database records via `AudiobookService`
- Saves R2 file path in PostgreSQL `audiobooks` table
- Returns complete audiobook record with storage location

### 3. **Environment File** (`backend/.env`)
- Updated with placeholder values that need YOUR credentials

---

## Configuration Steps

### Step 1: Get Your Cloudflare R2 Credentials

1. Log into your Cloudflare Dashboard
2. Go to **R2** section
3. Find your **Account ID** (top of page or in bucket settings)
4. Create an **API Token** if you haven't:
   - Click "Manage R2 API Tokens"
   - Create token with "Object Read & Write" permissions
   - Save the **Access Key ID** and **Secret Access Key**
5. Note your **Bucket Name** (you said it's set up already)

### Step 2: Update `.env` File

Open `backend/.env` and replace these values:

```env
# Replace these with YOUR actual values:
R2_ACCOUNT_ID=your_account_id_here          # Example: abc123def456
R2_ACCESS_KEY_ID=your_access_key_id_here    # Example: f1e2d3c4b5a6
R2_SECRET_ACCESS_KEY=your_secret_key_here   # Example: a1b2c3d4e5f6g7h8i9j0
R2_BUCKET_NAME=audiobooker-storage          # Change if different
R2_ENDPOINT_URL=https://your_account_id_here.r2.cloudflarestorage.com
```

**Important:** 
- The `R2_ENDPOINT_URL` must include your actual Account ID
- Example: If your Account ID is `abc123`, the endpoint is `https://abc123.r2.cloudflarestorage.com`

### Step 3: Restart the Backend

After updating `.env`:

```bash
cd backend
# Stop the current backend (Ctrl+C)
# Start it again:
source venv/Scripts/activate  # or venv\Scripts\activate on Windows
uvicorn main:app --reload
```

---

## Testing the Integration

### Test 1: Check Storage Mode

When you start the backend, check the logs:

- ✅ **R2 Configured**: "Using Cloudflare R2 storage: audiobooker-storage"
- ⚠️ **Local Fallback**: "Using local filesystem storage"

### Test 2: Upload a PDF

1. Go to frontend: http://localhost:5173
2. Upload a PDF file
3. Check the response - it should include `pdf_path`

**Expected Response:**
```json
{
  "id": "uuid-here",
  "title": "Your PDF Name",
  "filename": "yourfile.pdf",
  "size": 12345,
  "pdf_path": "r2://audiobooker-storage/uuid.pdf",  // R2 path
  "status": "pending",
  "created_at": "2024-01-15T10:30:00",
  "message": "File uploaded successfully to storage and database"
}
```

### Test 3: Verify in Cloudflare

1. Go to your R2 bucket in Cloudflare Dashboard
2. You should see the uploaded PDF file with UUID name

### Test 4: Verify in Database

Connect to PostgreSQL and check:

```bash
docker exec -it audiobooker-postgres-1 psql -U audiobooker -d audiobooker_db
```

```sql
SELECT id, title, original_file_name, pdf_path, status, created_at 
FROM audiobooks 
ORDER BY created_at DESC 
LIMIT 5;
```

You should see your uploaded file with the R2 path.

---

## How It Works

### Upload Flow:

1. **Frontend** sends PDF → `POST /api/v1/upload`
2. **Backend** validates file (type, size)
3. **StorageService** uploads to R2 bucket
4. **AudiobookService** creates database record with R2 path
5. **Response** returned to frontend with audiobook details

### Database Schema:

```sql
audiobooks table:
- id (UUID) - Primary key
- title (String) - PDF filename without extension
- original_file_name (String) - Original upload name
- file_size (Integer) - File size in bytes
- pdf_path (String) - R2 location: "r2://bucket/file.pdf"
- audio_path (String) - NULL until conversion (future)
- status (String) - "pending", "processing", "completed", "failed"
- created_at (DateTime)
- updated_at (DateTime)
```

---

## Fallback Behavior

If R2 credentials are **not configured** or **invalid**:

- System automatically falls back to local storage
- Files saved to `backend/uploads/` directory
- `pdf_path` in database shows local file path
- No errors - seamless fallback

This allows development without R2 while production uses R2.

---

## Troubleshooting

### "Using local filesystem storage" (but you want R2)

**Cause:** R2 credentials not configured or invalid

**Fix:**
1. Check `.env` has actual values (not placeholders)
2. Verify Account ID matches in both `R2_ACCOUNT_ID` and `R2_ENDPOINT_URL`
3. Test API token permissions in Cloudflare dashboard
4. Restart backend after changes

### "Failed to connect to R2: NoSuchBucket"

**Cause:** Bucket name incorrect

**Fix:**
- Check bucket name in Cloudflare dashboard
- Update `R2_BUCKET_NAME` in `.env`
- Bucket names are case-sensitive

### "Failed to connect to R2: InvalidAccessKeyId"

**Cause:** Wrong API credentials

**Fix:**
- Regenerate API token in Cloudflare
- Update `R2_ACCESS_KEY_ID` and `R2_SECRET_ACCESS_KEY`
- Ensure token has "Object Read & Write" permissions

### Upload succeeds but file not in R2

**Cause:** System fell back to local storage

**Fix:**
- Check backend logs for connection errors
- Verify all R2 credentials are correct
- Check Cloudflare R2 service status

---

## Next Steps

Once R2 is working:

1. ✅ Files upload to R2
2. ✅ Database stores R2 paths
3. 🔄 **Next:** Implement PDF text extraction
4. 🔄 **Next:** Implement Text-to-Speech conversion
5. 🔄 **Next:** Store audio files in R2 (similar flow)

---

## Security Notes

- ⚠️ **Never commit `.env` to Git** (already in `.gitignore`)
- 🔒 Keep R2 API tokens secure
- 🔒 Use separate tokens for development and production
- 🔒 Rotate tokens periodically

---

## Need Help?

If you encounter issues:

1. Check backend logs for detailed errors
2. Verify R2 dashboard shows your bucket
3. Test API token with Cloudflare's R2 API directly
4. Ensure your Cloudflare plan includes R2 (most do)

---

**Ready to Configure?** 

Just provide your 4 credentials and I'll help you update the `.env` file! 🚀
