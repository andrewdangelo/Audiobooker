# Auth Proxy Quick Reference

## Endpoints

### Frontend → Proxy → Auth Service

| Frontend Request | Proxy Route | Auth Service Endpoint |
|-----------------|-------------|----------------------|
| `POST /auth/signup` | `/auth/signup` | `/api/v1/auth/signup` |
| `POST /auth/login` | `/auth/login` | `/api/v1/auth/login` |
| `GET /auth/me` | `/auth/me` | `/api/v1/auth/me` |
| `POST /auth/refresh` | `/auth/refresh` | `/api/v1/auth/refresh` |
| `POST /auth/logout` | `/auth/logout` | `/api/v1/auth/logout` |
| `GET /auth/google/auth-url` | `/auth/google/auth-url` | `/api/v1/auth/google/auth-url` |
| `POST /auth/google/callback` | `/auth/google/callback` | `/api/v1/auth/google/callback` |
| `GET /auth/../accounts/profile` | `/auth/../accounts/profile` | `/api/v1/auth/../accounts/profile` |
| `PUT /auth/../accounts/profile` | `/auth/../accounts/profile` | `/api/v1/auth/../accounts/profile` |
| `GET /auth/../accounts/settings` | `/auth/../accounts/settings` | `/api/v1/auth/../accounts/settings` |
| `PUT /auth/../accounts/settings` | `/auth/../accounts/settings` | `/api/v1/auth/../accounts/settings` |
| `POST /auth/../accounts/change-password` | `/auth/../accounts/change-password` | `/api/v1/auth/../accounts/change-password` |
| `DELETE /auth/../accounts/account` | `/auth/../accounts/account` | `/api/v1/auth/../accounts/account` |

## Configuration

```env
# api_proxy/.env
AUTH_SERVICE_URL=http://localhost:8003/api/v1/auth
MAX_CONCURRENT_AUTH=10
RATE_LIMIT_PER_HOUR=1000
```

## Quick Commands

### Start Services
```bash
# Terminal 1: Auth Service
cd microservices/auth-service
python main.py

# Terminal 2: API Proxy
cd api_proxy
python main.py
```

### Test Connection
```bash
# Health check
curl http://localhost:8000/health | jq '.services.auth'

# Metrics
curl http://localhost:8000/metrics | jq '.auth_service'

# Test signup
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"TestPass123","first_name":"Test"}'
```

### Run Test Suite
```bash
cd api_proxy
python test_auth_proxy.py
```

## Frontend Code Snippets

### Login
```javascript
const login = async (email, password) => {
  const response = await fetch('http://localhost:8000/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });
  return await response.json();
};
```

### Get Current User
```javascript
const getCurrentUser = async (token) => {
  const response = await fetch('http://localhost:8000/auth/me', {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return await response.json();
};
```

### Update Profile
```javascript
const updateProfile = async (token, updates) => {
  const response = await fetch('http://localhost:8000/auth/../accounts/profile', {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify(updates)
  });
  return await response.json();
};
```

## Status Codes

| Code | Meaning | Action |
|------|---------|--------|
| 200 | Success | Process response |
| 202 | Queued | Check queue status at `/queue/{id}` |
| 400 | Bad Request | Fix request data |
| 401 | Unauthorized | Refresh token or re-login |
| 429 | Rate Limited | Wait and retry |
| 503 | Service Unavailable | Auth service is down |
| 504 | Gateway Timeout | Request took too long |

## Files Modified

1. `api_proxy/app/core/config_settings.py` - Config
2. `api_proxy/app/services/request_service.py` - Service mapping
3. `api_proxy/app/routers/proxy_router.py` - Routes
4. `api_proxy/.env` - Environment variables

## Documentation

- `AUTH_PROXY_INTEGRATION.md` - Full integration guide
- `INTEGRATION_SUMMARY.md` - Changes summary
- `test_auth_proxy.py` - Test script
- `AUTH_PROXY_QUICK_REF.md` - This file

## Support

If auth proxy isn't working:

1. Check auth service is running: `curl http://localhost:8003/api/v1/auth/health/`
2. Check proxy is running: `curl http://localhost:8000/health`
3. Verify .env has correct AUTH_SERVICE_URL
4. Check logs in both services
5. Run test script: `python test_auth_proxy.py`
