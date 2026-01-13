# Auth Service Proxy Integration

## Overview

The API Proxy now supports the Auth microservice, handling authentication requests between the frontend and the auth service with rate limiting and queueing capabilities.

## Configuration

### Environment Variables

```env
# Auth Service
AUTH_SERVICE_URL=http://localhost:8003/api/v1/auth
MAX_CONCURRENT_AUTH=10
```

The auth service supports higher concurrency (10 vs 5 for PDF/TTS) since auth operations are typically lighter weight.

## Proxy Endpoints

All auth service endpoints are accessible through the proxy at:

```
http://localhost:8000/auth/{path}
```

### Supported HTTP Methods

- **GET** - For retrieving profile, settings, current user info
- **POST** - For signup, login, logout, token refresh, Google OAuth callback
- **PUT** - For updating profile and settings
- **DELETE** - For account deletion

## Example Usage

### Frontend to Auth Service via Proxy

#### 1. User Signup
```javascript
const response = await fetch('http://localhost:8000/auth/signup', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'SecurePass123',
    first_name: 'John',
    last_name: 'Doe'
  })
});
```

**Proxied to:** `http://localhost:8003/api/v1/auth/signup`

#### 2. User Login
```javascript
const response = await fetch('http://localhost:8000/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'SecurePass123'
  })
});

const { access_token, refresh_token } = await response.json();
```

**Proxied to:** `http://localhost:8003/api/v1/auth/login`

#### 3. Get Current User
```javascript
const response = await fetch('http://localhost:8000/auth/me', {
  method: 'GET',
  headers: { 
    'Authorization': `Bearer ${access_token}`
  }
});
```

**Proxied to:** `http://localhost:8003/api/v1/auth/me`

#### 4. Get User Profile
```javascript
const response = await fetch('http://localhost:8000/auth/../accounts/profile', {
  method: 'GET',
  headers: { 
    'Authorization': `Bearer ${access_token}`
  }
});
```

**Proxied to:** `http://localhost:8003/api/v1/auth/../accounts/profile`

#### 5. Update Profile
```javascript
const response = await fetch('http://localhost:8000/auth/../accounts/profile', {
  method: 'PUT',
  headers: { 
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${access_token}`
  },
  body: JSON.stringify({
    first_name: 'Jane',
    username: 'jane_doe'
  })
});
```

**Proxied to:** `http://localhost:8003/api/v1/auth/../accounts/profile`

#### 6. Google OAuth Flow
```javascript
// Step 1: Get Google authorization URL
const authUrlResponse = await fetch('http://localhost:8000/auth/google/auth-url');
const { authorization_url } = await authUrlResponse.json();

// Step 2: Redirect user to Google
window.location.href = authorization_url;

// Step 3: Handle callback (after Google redirects back)
const code = new URLSearchParams(window.location.search).get('code');
const response = await fetch('http://localhost:8000/auth/google/callback', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ code, state: 'optional_state' })
});
```

**Proxied to:** `http://localhost:8003/api/v1/auth/google/auth-url` and `/google/callback`

#### 7. Token Refresh
```javascript
const response = await fetch('http://localhost:8000/auth/refresh', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    refresh_token: refresh_token
  })
});

const { access_token: new_token } = await response.json();
```

**Proxied to:** `http://localhost:8003/api/v1/auth/refresh`

#### 8. Logout
```javascript
const response = await fetch('http://localhost:8000/auth/logout', {
  method: 'POST',
  headers: { 
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${access_token}`
  },
  body: JSON.stringify({
    refresh_token: refresh_token
  })
});
```

**Proxied to:** `http://localhost:8003/api/v1/auth/logout`

## Rate Limiting

All auth endpoints are rate limited to:
- **1000 requests per hour** (default `RATE_LIMIT_PER_HOUR`)

## Queueing

If the auth service reaches maximum concurrent requests (10), additional requests are queued:

```json
{
  "status": "queued",
  "queue_id": "uuid-here",
  "message": "Request queued - service at capacity",
  "queue_position": 3,
  "check_status_url": "/queue/uuid-here"
}
```

Check queue status:
```javascript
const response = await fetch('http://localhost:8000/queue/uuid-here');
```

## Health Check

Check if auth service is available:

```bash
curl http://localhost:8000/health
```

Response includes auth service status:
```json
{
  "status": "healthy",
  "services": {
    "redis": "ok",
    "pdf": "ok",
    "tts": "ok",
    "auth": "ok"
  },
  "queues": {
    "auth": {
      "queued": 0,
      "active": 2,
      "max": 10
    }
  }
}
```

## Metrics

Get detailed auth service metrics:

```bash
curl http://localhost:8000/metrics
```

Response:
```json
{
  "auth_service": {
    "queued_requests": 0,
    "active_requests": 2,
    "max_concurrent": 10,
    "available_slots": 8
  }
}
```

## Error Handling

### Service Unavailable
If auth service is down:
```json
{
  "detail": "Service unavailable"
}
```
Status: 503

### Rate Limit Exceeded
If rate limit is exceeded:
```json
{
  "error": "Rate limit exceeded"
}
```
Status: 429

### Timeout
If request times out:
```json
{
  "detail": "Service timeout"
}
```
Status: 504

## Frontend Integration Pattern

### Create an Auth Service Wrapper

```javascript
// authService.js
class AuthService {
  constructor() {
    this.baseUrl = 'http://localhost:8000/auth';
    this.accessToken = localStorage.getItem('access_token');
    this.refreshToken = localStorage.getItem('refresh_token');
  }

  async signup(email, password, firstName, lastName) {
    const response = await fetch(`${this.baseUrl}/signup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, first_name: firstName, last_name: lastName })
    });
    
    if (response.ok) {
      const data = await response.json();
      this.setTokens(data.access_token, data.refresh_token);
      return data;
    }
    throw new Error('Signup failed');
  }

  async login(email, password) {
    const response = await fetch(`${this.baseUrl}/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    
    if (response.ok) {
      const data = await response.json();
      this.setTokens(data.access_token, data.refresh_token);
      return data;
    }
    throw new Error('Login failed');
  }

  async getCurrentUser() {
    return this.authenticatedRequest('/me', 'GET');
  }

  async getProfile() {
    return this.authenticatedRequest('/../accounts/profile', 'GET');
  }

  async updateProfile(updates) {
    return this.authenticatedRequest('/../accounts/profile', 'PUT', updates);
  }

  async logout() {
    await this.authenticatedRequest('/logout', 'POST', { 
      refresh_token: this.refreshToken 
    });
    this.clearTokens();
  }

  async authenticatedRequest(endpoint, method = 'GET', body = null) {
    let response = await this.makeRequest(endpoint, method, body, this.accessToken);
    
    // If token expired, try to refresh
    if (response.status === 401) {
      const refreshed = await this.refreshAccessToken();
      if (refreshed) {
        response = await this.makeRequest(endpoint, method, body, this.accessToken);
      }
    }
    
    if (response.ok) {
      return await response.json();
    }
    throw new Error(`Request failed: ${response.status}`);
  }

  async makeRequest(endpoint, method, body, token) {
    const options = {
      method,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      }
    };
    
    if (body && method !== 'GET') {
      options.body = JSON.stringify(body);
    }
    
    return await fetch(`${this.baseUrl}${endpoint}`, options);
  }

  async refreshAccessToken() {
    try {
      const response = await fetch(`${this.baseUrl}/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: this.refreshToken })
      });
      
      if (response.ok) {
        const data = await response.json();
        this.setTokens(data.access_token, data.refresh_token);
        return true;
      }
    } catch (error) {
      this.clearTokens();
    }
    return false;
  }

  setTokens(accessToken, refreshToken) {
    this.accessToken = accessToken;
    this.refreshToken = refreshToken;
    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('refresh_token', refreshToken);
  }

  clearTokens() {
    this.accessToken = null;
    this.refreshToken = null;
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  }

  isAuthenticated() {
    return !!this.accessToken;
  }
}

export default new AuthService();
```

### Usage in Components

```javascript
// Login.jsx
import authService from './authService';

async function handleLogin(email, password) {
  try {
    const user = await authService.login(email, password);
    console.log('Logged in:', user);
    // Navigate to dashboard
  } catch (error) {
    console.error('Login failed:', error);
  }
}
```

## Configuration Requirements

### 1. Start Auth Service
```bash
cd microservices/auth-service
python main.py
```
Service runs on port 8003

### 2. Update API Proxy .env
```env
AUTH_SERVICE_URL=http://localhost:8003/api/v1/auth
MAX_CONCURRENT_AUTH=10
```

### 3. Start API Proxy
```bash
cd api_proxy
python main.py
```
Proxy runs on port 8000

### 4. Update Frontend Configuration
Point frontend to proxy:
```javascript
const API_BASE = 'http://localhost:8000';
const AUTH_API = `${API_BASE}/auth`;
```

## Testing

### Test Signup via Proxy
```bash
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPass123",
    "first_name": "Test"
  }'
```

### Test Login via Proxy
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPass123"
  }'
```

### Test Health Check
```bash
curl http://localhost:8000/health | jq '.services.auth'
```

## Benefits

1. **Centralized Entry Point** - Single endpoint for all services
2. **Rate Limiting** - Automatic rate limiting on all auth endpoints
3. **Queueing** - Handles high load gracefully
4. **Monitoring** - Health checks and metrics for auth service
5. **Consistent Interface** - Same proxy pattern for PDF, TTS, and Auth
6. **Load Management** - Prevents overwhelming the auth service

## Next Steps

1. Configure frontend to use proxy endpoint (`http://localhost:8000/auth/*`)
2. Update environment variables in production
3. Monitor metrics to adjust `MAX_CONCURRENT_AUTH` if needed
4. Consider adding caching for frequently accessed auth data
5. Implement token validation middleware in proxy for additional security
