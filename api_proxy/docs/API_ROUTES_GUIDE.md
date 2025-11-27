# API Routes Quick Reference

## Adding a New Route - Checklist

- [ ] Create router file in `app/routers/`
- [ ] Create schemas in `app/schemas/` (if needed)
- [ ] Register router in `main.py`
- [ ] Update `config/settings.py` with any new service URLs
- [ ] Update `.env` with new environment variables
- [ ] Test endpoints using `/docs`
- [ ] Update this documentation

## Route Template

### Step 1: Create Router (`app/routers/your_feature.py`)

```python
"""
Your Feature Router
"""

from fastapi import APIRouter, HTTPException, status
import httpx
import logging

from config.settings import settings
from app.services.http_client import http_client

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/")
async def list_items():
    """List all items"""
    try:
        response = await http_client.get(
            f"{settings.YOUR_SERVICE_URL}/api/v1/items"
        )
        return response.json()
    except httpx.RequestError as e:
        logger.error(f"Service error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable"
        )


@router.get("/{item_id}")
async def get_item(item_id: str):
    """Get item by ID"""
    try:
        response = await http_client.get(
            f"{settings.YOUR_SERVICE_URL}/api/v1/items/{item_id}"
        )
        
        if response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found"
            )
            
        return response.json()
    except HTTPException:
        raise
    except httpx.RequestError as e:
        logger.error(f"Service error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable"
        )


@router.post("/")
async def create_item(data: dict):
    """Create new item"""
    try:
        response = await http_client.post(
            f"{settings.YOUR_SERVICE_URL}/api/v1/items",
            json=data
        )
        return response.json()
    except httpx.RequestError as e:
        logger.error(f"Service error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable"
        )
```

### Step 2: Create Schemas (`app/schemas/your_feature.py`)

```python
"""
Your Feature Schemas
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class CreateItemRequest(BaseModel):
    """Request model for creating an item"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Example Item",
                "description": "This is an example"
            }
        }


class ItemResponse(BaseModel):
    """Response model for item data"""
    id: str
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "item_123",
                "name": "Example Item",
                "description": "This is an example",
                "created_at": "2025-11-26T10:00:00Z"
            }
        }
```

### Step 3: Register in `main.py`

```python
# Import your router
from app.routers import health, pdf, your_feature

# Register with prefix and tags
app.include_router(
    your_feature.router,
    prefix=f"{settings.API_V1_PREFIX}/your-feature",
    tags=["Your Feature"]
)
```

### Step 4: Update `config/settings.py`

```python
class Settings(BaseSettings):
    # ... existing settings ...
    
    # Add your service URL
    YOUR_SERVICE_URL: str = "http://localhost:8005"
```

### Step 5: Update `.env`

```bash
# Add to .env
YOUR_SERVICE_URL=http://localhost:8005
```

## Common Patterns

### File Upload Proxy

```python
from fastapi import UploadFile, File

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload file to microservice"""
    try:
        contents = await file.read()
        response = await http_client.post_file(
            f"{settings.SERVICE_URL}/upload",
            file=contents,
            filename=file.filename
        )
        return response.json()
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail="Upload failed")
```

### Pagination

```python
from typing import List

@router.get("/", response_model=List[ItemResponse])
async def list_items(
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None
):
    """List items with pagination"""
    params = {
        "page": page,
        "page_size": page_size,
    }
    if search:
        params["search"] = search
        
    response = await http_client.get(
        f"{settings.SERVICE_URL}/items",
        params=params
    )
    return response.json()
```

### Authentication Required

```python
from fastapi import Depends, Header

async def verify_token(authorization: str = Header(...)):
    """Verify JWT token"""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token")
    
    token = authorization.split(" ")[1]
    # Validate token logic here
    return token

@router.get("/protected")
async def protected_route(token: str = Depends(verify_token)):
    """Route that requires authentication"""
    response = await http_client.get(
        f"{settings.SERVICE_URL}/protected",
        headers={"Authorization": f"Bearer {token}"}
    )
    return response.json()
```

### Background Processing

```python
from fastapi import BackgroundTasks

def process_in_background(item_id: str):
    """Long-running background task"""
    logger.info(f"Processing {item_id}")
    # Do work here

@router.post("/process/{item_id}")
async def start_processing(
    item_id: str,
    background_tasks: BackgroundTasks
):
    """Start background processing"""
    background_tasks.add_task(process_in_background, item_id)
    return {"message": "Processing started", "item_id": item_id}
```

### Query Parameters

```python
from typing import Optional, List
from enum import Enum

class SortOrder(str, Enum):
    asc = "asc"
    desc = "desc"

@router.get("/items")
async def list_items(
    status: Optional[str] = None,
    category: Optional[List[str]] = None,
    sort_by: str = "created_at",
    sort_order: SortOrder = SortOrder.desc,
    limit: int = 20
):
    """Advanced filtering and sorting"""
    params = {
        "sort_by": sort_by,
        "sort_order": sort_order,
        "limit": limit
    }
    if status:
        params["status"] = status
    if category:
        params["category"] = ",".join(category)
        
    response = await http_client.get(
        f"{settings.SERVICE_URL}/items",
        params=params
    )
    return response.json()
```

### Error Handling

```python
import httpx
from fastapi import HTTPException, status

@router.get("/{item_id}")
async def get_item(item_id: str):
    """Comprehensive error handling"""
    try:
        response = await http_client.get(
            f"{settings.SERVICE_URL}/items/{item_id}"
        )
        
        # Handle different status codes
        if response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item {item_id} not found"
            )
        elif response.status_code == 403:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        elif response.status_code >= 500:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Service error"
            )
            
        return response.json()
        
    except HTTPException:
        raise
    except httpx.TimeoutException:
        logger.error(f"Timeout fetching item {item_id}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Service timeout"
        )
    except httpx.RequestError as e:
        logger.error(f"Request error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service unavailable"
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
```

## Testing Your Routes

### 1. Interactive Testing (Swagger UI)

Visit `http://localhost:8000/docs` and use the interactive interface to test your endpoints.

### 2. cURL Commands

```bash
# GET request
curl http://localhost:8000/api/v1/your-feature

# GET with parameters
curl "http://localhost:8000/api/v1/your-feature?page=1&limit=10"

# POST with JSON
curl -X POST http://localhost:8000/api/v1/your-feature \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Item", "description": "Test"}'

# File upload
curl -X POST http://localhost:8000/api/v1/your-feature/upload \
  -F "file=@/path/to/file.pdf"

# With authentication
curl http://localhost:8000/api/v1/your-feature/protected \
  -H "Authorization: Bearer your_token_here"
```

### 3. Python Requests

```python
import requests

# GET
response = requests.get("http://localhost:8000/api/v1/your-feature")
print(response.json())

# POST
response = requests.post(
    "http://localhost:8000/api/v1/your-feature",
    json={"name": "Test Item"}
)
print(response.json())

# File upload
files = {"file": open("document.pdf", "rb")}
response = requests.post(
    "http://localhost:8000/api/v1/your-feature/upload",
    files=files
)
print(response.json())
```

## Best Practices

1. **Always log errors** - Use `logger.error()` for debugging
2. **Use proper HTTP status codes** - 404 for not found, 503 for service unavailable
3. **Validate inputs** - Use Pydantic models
4. **Document endpoints** - Use docstrings and examples
5. **Handle timeouts** - Set appropriate timeouts for different operations
6. **Return consistent responses** - Use response models
7. **Test all paths** - Including error cases

## Common HTTP Status Codes

| Code | Status | When to Use |
|------|--------|-------------|
| 200 | OK | Successful GET, PUT, DELETE |
| 201 | Created | Successful POST creating resource |
| 400 | Bad Request | Invalid request data |
| 401 | Unauthorized | Missing/invalid authentication |
| 403 | Forbidden | Authenticated but not authorized |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Resource already exists |
| 422 | Unprocessable Entity | Validation error |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Unexpected server error |
| 502 | Bad Gateway | Upstream service error |
| 503 | Service Unavailable | Service down/unreachable |
| 504 | Gateway Timeout | Upstream service timeout |

## Next Steps

1. Review existing routes in `app/routers/`
2. Check the [Development Guide](DEVELOPMENT_GUIDE.md) for detailed examples
3. Test your routes using `/docs`
4. Update documentation when adding new features
