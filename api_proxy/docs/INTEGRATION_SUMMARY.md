# API Proxy - Auth Service Integration Summary

## Changes Made

### 1. Configuration Updates

**File:** `api_proxy/app/core/config_settings.py`
- Added `AUTH_SERVICE_URL` configuration pointing to `http://localhost:8003/api/v1/auth`
- Added `MAX_CONCURRENT_AUTH = 10` for auth service concurrency control

### 2. Service URL Mapping

**File:** `api_proxy/app/services/request_service.py`
- Added `"auth": settings.AUTH_SERVICE_URL` to the service URL mapping
- Auth service now recognized as a valid proxy target

### 3. Proxy Routes

**File:** `api_proxy/app/routers/proxy_router.py`

Added 4 new proxy endpoints for auth service:
- `GET /auth/{path:path}` - Profile, settings, current user
- `POST /auth/{path:path}` - Signup, login, logout, refresh, OAuth callback
- `PUT /auth/{path:path}` - Update profile and settings
- `DELETE /auth/{path:path}` - Account deletion

All routes include:
- Rate limiting (1000 req/hour)
- Automatic queueing when service overloaded
- Request forwarding with proper headers

### 4. Health Monitoring

**File:** `api_proxy/app/routers/proxy_router.py`

Updated `/health` endpoint:
- Added auth service health check (`/api/v1/auth/health/`)
- Monitors auth service availability
- Reports auth service status in response
- Includes auth queue metrics (queued, active, max concurrent)

### 5. Metrics Tracking

**File:** `api_proxy/app/routers/proxy_router.py`

Updated `/metrics` endpoint:
- Added auth service metrics
- Tracks queued requests, active requests, available slots
- Provides real-time auth service load information

### 6. Environment Configuration

**File:** `api_proxy/.env`
- Updated microservice URLs to match actual service endpoints
- Added auth service configuration:
  ```env
  AUTH_SERVICE_URL=http://localhost:8003/api/v1/auth
  MAX_CONCURRENT_AUTH=10
  ```

## How It Works

### Request Flow

```
Frontend → API Proxy (port 8000) → Auth Service (port 8003)
   ↓
Check rate limit
   ↓
Check service load
   ↓
[If capacity available]
   → Forward immediately → Return response
   
[If service overloaded]
   → Queue request → Return queue ID
   → Process when slot available
```

### Example Requests

#### Signup
```javascript
// Frontend calls proxy
POST http://localhost:8000/auth/signup

// Proxy forwards to
POST http://localhost:8003/api/v1/auth/signup
```

#### Login
```javascript
// Frontend calls proxy
POST http://localhost:8000/auth/login

// Proxy forwards to
POST http://localhost:8003/api/v1/auth/login
```

#### Get Profile
```javascript
// Frontend calls proxy
GET http://localhost:8000/auth/../accounts/profile
Authorization: Bearer <token>

// Proxy forwards to
GET http://localhost:8003/api/v1/auth/../accounts/profile
Authorization: Bearer <token>
```

## Frontend Integration

### Before (Direct to Auth Service)
```javascript
const response = await fetch('http://localhost:8003/api/v1/auth/login', { ... });
```

### After (Via Proxy)
```javascript
const response = await fetch('http://localhost:8000/auth/login', { ... });
```

### Benefits

1. **Single Entry Point** - Frontend only needs to know about proxy (port 8000)
2. **Rate Limiting** - Automatic protection against abuse
3. **Load Management** - Queueing prevents service overload
4. **Monitoring** - Centralized health checks and metrics
5. **Consistent Pattern** - Same proxy interface for all services (PDF, TTS, Auth)

## Configuration

### Auth Service Must Be Running
```bash
cd microservices/auth-service
python main.py
# Runs on http://localhost:8003
```

### API Proxy Configuration
```bash
cd api_proxy
# Ensure .env has:
# AUTH_SERVICE_URL=http://localhost:8003/api/v1/auth
# MAX_CONCURRENT_AUTH=10

python main.py
# Runs on http://localhost:8000
```

### Frontend Configuration
```javascript
// config.js
export const API_BASE = 'http://localhost:8000';
export const AUTH_API = `${API_BASE}/auth`;
```

## Testing

### 1. Start Both Services
```bash
# Terminal 1: Auth Service
cd microservices/auth-service
python main.py

# Terminal 2: API Proxy
cd api_proxy
python main.py
```

### 2. Test Health
```bash
curl http://localhost:8000/health
```

Expected response includes:
```json
{
  "services": {
    "auth": "ok"
  },
  "queues": {
    "auth": {
      "queued": 0,
      "active": 0,
      "max": 10
    }
  }
}
```

### 3. Test Signup via Proxy
```bash
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPass123",
    "first_name": "Test"
  }'
```

### 4. Test Login via Proxy
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPass123"
  }'
```

## Files Modified

1. `api_proxy/app/core/config_settings.py` - Added AUTH_SERVICE_URL and MAX_CONCURRENT_AUTH
2. `api_proxy/app/services/request_service.py` - Added auth to service URL mapping
3. `api_proxy/app/routers/proxy_router.py` - Added auth routes, health checks, metrics
4. `api_proxy/.env` - Updated microservice URLs and added auth configuration

## Files Created

1. `api_proxy/AUTH_PROXY_INTEGRATION.md` - Comprehensive integration guide
2. `api_proxy/INTEGRATION_SUMMARY.md` - This file

## Next Steps

1. **Update Frontend** - Point all auth API calls to proxy endpoint
2. **Test Integration** - Verify signup/login flows work through proxy
3. **Monitor Metrics** - Check `/metrics` endpoint for auth service load
4. **Adjust Concurrency** - Tune `MAX_CONCURRENT_AUTH` based on actual usage
5. **Production Config** - Update URLs for production environment

## Troubleshooting

### Auth Service Health Check Fails
```bash
# Check if auth service is running
curl http://localhost:8003/api/v1/auth/health/
```

### Proxy Can't Connect to Auth Service
- Verify AUTH_SERVICE_URL in `.env` is correct
- Ensure auth service is running on port 8003
- Check firewall/network settings

### Rate Limit Issues
- Check `RATE_LIMIT_PER_HOUR` setting
- View current limits in proxy logs
- Adjust rate limits in `config_settings.py` if needed

## Architecture

```
┌─────────────┐
│  Frontend   │
│ (React/Vue) │
└──────┬──────┘
       │
       │ HTTP Requests
       │ (port 8000)
       ↓
┌─────────────────────────────────────┐
│        API Proxy                    │
│  ┌──────────────────────────────┐  │
│  │  Rate Limiter                │  │
│  └─────────────┬────────────────┘  │
│                ↓                    │
│  ┌──────────────────────────────┐  │
│  │  Queue Service               │  │
│  │  (Redis-backed)              │  │
│  └─────────────┬────────────────┘  │
│                ↓                    │
│  ┌──────────────────────────────┐  │
│  │  Request Service             │  │
│  │  (Forwards to microservices) │  │
│  └──────┬───────┬────────┬───────┘ │
└─────────┼───────┼────────┼─────────┘
          │       │        │
          ↓       ↓        ↓
     ┌────────┐ ┌────┐ ┌──────┐
     │  PDF   │ │TTS │ │ Auth │
     │Service │ │Svc │ │ Svc  │
     │  8029  │ │8002│ │ 8003 │
     └────────┘ └────┘ └──────┘
```

## Status

✅ Configuration updated  
✅ Routes added  
✅ Health monitoring enabled  
✅ Metrics tracking enabled  
✅ Documentation created  
✅ Ready for frontend integration  

The API proxy now fully supports the auth microservice with the same robust features as PDF and TTS services!
