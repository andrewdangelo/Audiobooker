# API Reference

## Base URL

**Development**: `http://localhost:8000`

**API Version**: `/api/v1`

## Authentication

Currently, the API does not require authentication. This will be added in a future update.

## Endpoints

### Health Check

#### GET /health

Check if the API is running.

**Request**:
```http
GET /health HTTP/1.1
Host: localhost:8000
```

**Response**:
```json
{
  "status": "healthy"
}
```

**Status Codes**:
- `200 OK`: API is healthy

---

### File Upload

#### POST /api/v1/upload/

Upload a PDF file for conversion to audiobook.

**Request**:
```http
POST /api/v1/upload/ HTTP/1.1
Host: localhost:8000
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary

------WebKitFormBoundary
Content-Disposition: form-data; name="file"; filename="document.pdf"
Content-Type: application/pdf

[PDF file content]
------WebKitFormBoundary--
```

**Parameters**:
- `file` (form-data, required): PDF file to upload
  - Type: `application/pdf`
  - Max size: 50 MB
  - Extension: `.pdf`

**Response** (200 OK):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "document.pdf",
  "size": 1048576,
  "message": "File received successfully!",
  "status": "pending"
}
```

**Error Responses**:

400 Bad Request - Invalid file type:
```json
{
  "detail": "Only PDF files are allowed"
}
```

400 Bad Request - File too large:
```json
{
  "detail": "File size exceeds maximum allowed size of 50MB"
}
```

**cURL Example**:
```bash
curl -X POST "http://localhost:8000/api/v1/upload/" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/document.pdf"
```

**JavaScript Example**:
```javascript
const formData = new FormData()
formData.append('file', pdfFile)

const response = await fetch('http://localhost:8000/api/v1/upload/', {
  method: 'POST',
  body: formData
})

const result = await response.json()
console.log(result)
```

---

#### GET /api/v1/upload/{upload_id}/status

Get the status of an uploaded file.

**Request**:
```http
GET /api/v1/upload/550e8400-e29b-41d4-a716-446655440000/status HTTP/1.1
Host: localhost:8000
```

**Path Parameters**:
- `upload_id` (string, required): UUID of the upload

**Response** (200 OK):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "This is a test endpoint"
}
```

**cURL Example**:
```bash
curl "http://localhost:8000/api/v1/upload/550e8400-e29b-41d4-a716-446655440000/status"
```

---

### Audiobooks

#### GET /api/v1/audiobooks/

Get a list of all audiobooks.

**Request**:
```http
GET /api/v1/audiobooks/ HTTP/1.1
Host: localhost:8000
```

**Query Parameters**:
- `skip` (integer, optional): Number of records to skip. Default: `0`
- `limit` (integer, optional): Maximum number of records to return. Default: `100`

**Response** (200 OK):
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "My Document",
    "original_file_name": "document.pdf",
    "file_size": 1048576,
    "pdf_path": "uploads/550e8400-e29b-41d4-a716-446655440000.pdf",
    "audio_path": null,
    "status": "pending",
    "created_at": "2025-10-22T19:30:00Z",
    "updated_at": "2025-10-22T19:30:00Z"
  }
]
```

**cURL Example**:
```bash
curl "http://localhost:8000/api/v1/audiobooks/?skip=0&limit=10"
```

---

#### GET /api/v1/audiobooks/{audiobook_id}

Get details of a specific audiobook.

**Request**:
```http
GET /api/v1/audiobooks/550e8400-e29b-41d4-a716-446655440000 HTTP/1.1
Host: localhost:8000
```

**Path Parameters**:
- `audiobook_id` (string, required): UUID of the audiobook

**Response** (200 OK):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "My Document",
  "original_file_name": "document.pdf",
  "file_size": 1048576,
  "pdf_path": "uploads/550e8400-e29b-41d4-a716-446655440000.pdf",
  "audio_path": "uploads/550e8400-e29b-41d4-a716-446655440000.mp3",
  "status": "completed",
  "created_at": "2025-10-22T19:30:00Z",
  "updated_at": "2025-10-22T19:35:00Z"
}
```

**Error Response** (404 Not Found):
```json
{
  "detail": "Audiobook not found"
}
```

---

#### DELETE /api/v1/audiobooks/{audiobook_id}

Delete an audiobook.

**Request**:
```http
DELETE /api/v1/audiobooks/550e8400-e29b-41d4-a716-446655440000 HTTP/1.1
Host: localhost:8000
```

**Path Parameters**:
- `audiobook_id` (string, required): UUID of the audiobook

**Response** (200 OK):
```json
{
  "message": "Audiobook deleted successfully"
}
```

**Error Response** (404 Not Found):
```json
{
  "detail": "Audiobook not found"
}
```

---

### Conversion

#### POST /api/v1/conversion/start

Start conversion of a PDF to audiobook.

**Request**:
```http
POST /api/v1/conversion/start HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "audiobook_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response** (200 OK):
```json
{
  "job_id": "660e8400-e29b-41d4-a716-446655440000",
  "audiobook_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "message": "Conversion job started"
}
```

---

#### GET /api/v1/conversion/{job_id}/status

Get the status of a conversion job.

**Request**:
```http
GET /api/v1/conversion/660e8400-e29b-41d4-a716-446655440000/status HTTP/1.1
Host: localhost:8000
```

**Path Parameters**:
- `job_id` (string, required): UUID of the conversion job

**Response** (200 OK):
```json
{
  "job_id": "660e8400-e29b-41d4-a716-446655440000",
  "status": "running",
  "progress": 45,
  "started_at": "2025-10-22T19:30:00Z"
}
```

**Status Values**:
- `queued`: Waiting to start
- `running`: Currently processing
- `completed`: Successfully completed
- `failed`: Failed with error

---

## Response Schemas

### UploadResponse

```typescript
{
  id: string          // UUID of the upload
  filename: string    // Original filename
  size: number        // File size in bytes
  message: string     // Success message
  status: string      // Upload status
}
```

### AudiobookResponse

```typescript
{
  id: string                  // UUID
  title: string               // Audiobook title
  original_file_name: string  // Original PDF filename
  file_size: number           // File size in bytes
  pdf_path: string            // Path to PDF file
  audio_path: string | null   // Path to audio file (null if not converted)
  status: string              // pending | processing | completed | failed
  created_at: string          // ISO 8601 datetime
  updated_at: string          // ISO 8601 datetime
}
```

### ConversionJobResponse

```typescript
{
  job_id: string              // UUID of conversion job
  audiobook_id: string        // UUID of audiobook
  status: string              // queued | running | completed | failed
  progress: number            // 0-100
  error_message: string | null // Error details if failed
  started_at: string | null   // ISO 8601 datetime
  completed_at: string | null // ISO 8601 datetime
}
```

### ErrorResponse

```typescript
{
  detail: string  // Error message
}
```

---

## Status Codes

| Code | Description |
|------|-------------|
| 200 | OK - Request successful |
| 201 | Created - Resource created successfully |
| 400 | Bad Request - Invalid request parameters |
| 401 | Unauthorized - Authentication required |
| 404 | Not Found - Resource not found |
| 422 | Unprocessable Entity - Validation error |
| 500 | Internal Server Error - Server error |

---

## Rate Limiting

Currently, there are no rate limits. This will be implemented in a future update.

---

## CORS

The API allows cross-origin requests from:
- `http://localhost:5173` (Vite dev server)
- `http://localhost:3000` (Alternative dev server)

All HTTP methods and headers are allowed.

---

## Interactive Documentation

The API provides interactive documentation:

### Swagger UI
Visit `http://localhost:8000/docs` for an interactive API explorer where you can:
- View all endpoints
- See request/response schemas
- Try out API calls directly
- Download OpenAPI specification

### ReDoc
Visit `http://localhost:8000/redoc` for:
- Clean, readable API documentation
- Detailed schema information
- Request/response examples

### OpenAPI Schema
Access the raw OpenAPI schema at `http://localhost:8000/openapi.json`

---

## Examples

### Complete Upload Flow

```javascript
// 1. Upload PDF file
const uploadFile = async (file) => {
  const formData = new FormData()
  formData.append('file', file)
  
  const uploadResponse = await fetch('http://localhost:8000/api/v1/upload/', {
    method: 'POST',
    body: formData
  })
  
  const uploadResult = await uploadResponse.json()
  console.log('Upload ID:', uploadResult.id)
  
  return uploadResult.id
}

// 2. Check upload status
const checkStatus = async (uploadId) => {
  const response = await fetch(`http://localhost:8000/api/v1/upload/${uploadId}/status`)
  const status = await response.json()
  console.log('Status:', status.status)
  
  return status
}

// 3. Get audiobook details
const getAudiobook = async (audiobookId) => {
  const response = await fetch(`http://localhost:8000/api/v1/audiobooks/${audiobookId}`)
  const audiobook = await response.json()
  console.log('Audiobook:', audiobook)
  
  return audiobook
}

// Usage
const file = document.getElementById('fileInput').files[0]
const uploadId = await uploadFile(file)
const status = await checkStatus(uploadId)
const audiobook = await getAudiobook(uploadId)
```

### Python Client Example

```python
import requests

# Upload file
with open('document.pdf', 'rb') as f:
    files = {'file': f}
    response = requests.post('http://localhost:8000/api/v1/upload/', files=files)
    upload_result = response.json()
    print(f"Upload ID: {upload_result['id']}")

# Check status
upload_id = upload_result['id']
response = requests.get(f'http://localhost:8000/api/v1/upload/{upload_id}/status')
status = response.json()
print(f"Status: {status['status']}")

# Get audiobook
response = requests.get(f'http://localhost:8000/api/v1/audiobooks/{upload_id}')
audiobook = response.json()
print(f"Audiobook: {audiobook}")
```
