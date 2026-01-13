# Auth Service - Frontend Integration Guide

## Overview

The Auth Service provides a complete authentication and account management system for the Audiobooker frontend. It supports both local authentication (email/password) and Google OAuth.

## Service Details

- **Base URL**: `http://localhost:8003` (development)
- **API Prefix**: `/api/v1`
- **Auth Endpoints**: `/api/v1/auth`
- **Account Endpoints**: `/api/v1/accounts`

## Authentication Flows

### 1. Email/Password Signup

```javascript
// Frontend Code
const signup = async (email, password, firstName, lastName) => {
  const response = await fetch('http://localhost:8003/api/v1/auth/signup', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      email,
      password,
      first_name: firstName,
      last_name: lastName,
    })
  });

  if (!response.ok) {
    throw new Error(await response.text());
  }

  return await response.json();
};

// Usage
try {
  const { access_token, refresh_token, user } = await signup(
    'user@example.com',
    'SecurePass123',
    'John',
    'Doe'
  );
  
  // Store tokens
  localStorage.setItem('access_token', access_token);
  localStorage.setItem('refresh_token', refresh_token);
  
  // Redirect to dashboard
  window.location.href = '/dashboard';
} catch (error) {
  console.error('Signup failed:', error);
}
```

### 2. Email/Password Login

```javascript
const login = async (email, password) => {
  const response = await fetch('http://localhost:8003/api/v1/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email, password })
  });

  if (!response.ok) {
    throw new Error(await response.text());
  }

  return await response.json();
};
```

### 3. Google OAuth Login

#### Step 1: Get Authorization URL

```javascript
const initGoogleLogin = async () => {
  const response = await fetch('http://localhost:8003/api/v1/auth/google/auth-url');
  const { auth_url, state } = await response.json();
  
  // Store state for verification
  sessionStorage.setItem('oauth_state', state);
  
  // Redirect to Google
  window.location.href = auth_url;
};
```

#### Step 2: Handle Redirect Callback

Setup a callback route in your frontend (e.g., `/auth/google/callback`):

```javascript
// pages/auth/GoogleCallback.tsx or similar
import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

export const GoogleCallback = () => {
  const navigate = useNavigate();

  useEffect(() => {
    const handleCallback = async () => {
      // Get authorization code from URL
      const urlParams = new URLSearchParams(window.location.search);
      const code = urlParams.get('code');
      const state = urlParams.get('state');

      // Verify state
      const storedState = sessionStorage.getItem('oauth_state');
      if (state !== storedState) {
        console.error('State mismatch - possible CSRF attack');
        navigate('/login');
        return;
      }

      try {
        // Exchange code for tokens
        const response = await fetch('http://localhost:8003/api/v1/auth/google/callback', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ code, state })
        });

        if (!response.ok) {
          throw new Error('Authentication failed');
        }

        const { access_token, refresh_token, user } = await response.json();

        // Store tokens
        localStorage.setItem('access_token', access_token);
        localStorage.setItem('refresh_token', refresh_token);

        // Redirect to dashboard
        navigate('/dashboard');
      } catch (error) {
        console.error('Google login failed:', error);
        navigate('/login?error=google_login_failed');
      }
    };

    handleCallback();
  }, [navigate]);

  return <div>Loading...</div>;
};
```

## Token Management

### Access Token

- **Expiration**: 30 minutes
- **Storage**: Recommend secure HTTP-only cookie or local storage
- **Usage**: Include in `Authorization` header as `Bearer <token>`

### Refresh Token

- **Expiration**: 7 days
- **Storage**: Secure HTTP-only cookie (preferred) or local storage
- **Usage**: Used to obtain new access token when it expires

### Refresh Access Token

```javascript
const refreshAccessToken = async () => {
  const refreshToken = localStorage.getItem('refresh_token');
  
  const response = await fetch('http://localhost:8003/api/v1/auth/refresh', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ refresh_token })
  });

  if (!response.ok) {
    // Refresh token expired, redirect to login
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    window.location.href = '/login';
    return null;
  }

  const { access_token, refresh_token: newRefreshToken } = await response.json();
  
  // Update tokens
  localStorage.setItem('access_token', access_token);
  localStorage.setItem('refresh_token', newRefreshToken);
  
  return access_token;
};
```

## API Requests

### Include Token in Headers

```javascript
// Helper function
const apiRequest = async (url, options = {}) => {
  const token = localStorage.getItem('access_token');
  
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  // If 401, try to refresh token
  if (response.status === 401) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      headers['Authorization'] = `Bearer ${newToken}`;
      return fetch(url, { ...options, headers });
    }
  }

  return response;
};

// Usage
const response = await apiRequest('http://localhost:8003/api/v1/accounts/profile');
const userProfile = await response.json();
```

## Account Management

### Get User Profile

```javascript
const getUserProfile = async () => {
  const response = await apiRequest('http://localhost:8003/api/v1/accounts/profile');
  return await response.json();
};
```

### Update User Profile

```javascript
const updateProfile = async (firstName, lastName, username) => {
  const response = await apiRequest('http://localhost:8003/api/v1/accounts/profile', {
    method: 'PUT',
    body: JSON.stringify({
      first_name: firstName,
      last_name: lastName,
      username,
    })
  });
  
  return await response.json();
};
```

### Change Password

```javascript
const changePassword = async (oldPassword, newPassword) => {
  const response = await apiRequest('http://localhost:8003/api/v1/accounts/change-password', {
    method: 'POST',
    body: JSON.stringify({
      old_password: oldPassword,
      new_password: newPassword,
    })
  });
  
  return await response.json();
};
```

### Get Account Settings

```javascript
const getAccountSettings = async () => {
  const response = await apiRequest('http://localhost:8003/api/v1/accounts/settings');
  return await response.json();
};
```

### Update Account Settings

```javascript
const updateSettings = async (settings) => {
  const response = await apiRequest('http://localhost:8003/api/v1/accounts/settings', {
    method: 'PUT',
    body: JSON.stringify(settings) // { email_notifications, marketing_emails, two_factor_enabled }
  });
  
  return await response.json();
};
```

### Logout

```javascript
const logout = async () => {
  const refreshToken = localStorage.getItem('refresh_token');
  
  await fetch('http://localhost:8003/api/v1/auth/logout', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${localStorage.getItem('access_token')}`
    },
    body: JSON.stringify({ refresh_token: refreshToken })
  });

  // Clear tokens
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  
  // Redirect to login
  window.location.href = '/login';
};
```

## Error Handling

The Auth Service returns standard HTTP status codes:

- **200**: Success
- **201**: Created
- **400**: Bad request (invalid input)
- **401**: Unauthorized (invalid credentials or token)
- **404**: Not found
- **500**: Server error

Response format for errors:
```json
{
  "detail": "Error message"
}
```

## Example: Protected Component

```typescript
// components/ProtectedRoute.tsx
import { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

export const ProtectedRoute = ({ children }: ProtectedRouteProps) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem('access_token');
      
      if (!token) {
        setIsAuthenticated(false);
        setIsLoading(false);
        return;
      }

      try {
        const response = await fetch('http://localhost:8003/api/v1/accounts/profile', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });

        if (response.ok) {
          setIsAuthenticated(true);
        } else {
          // Token invalid, try to refresh
          const newToken = await refreshAccessToken();
          setIsAuthenticated(!!newToken);
        }
      } catch (error) {
        setIsAuthenticated(false);
      } finally {
        setIsLoading(false);
      }
    };

    checkAuth();
  }, []);

  if (isLoading) {
    return <div>Loading...</div>;
  }

  return isAuthenticated ? <>{children}</> : <Navigate to="/login" />;
};
```

## CORS Configuration

The service allows requests from:
- `http://localhost:3000` (development frontend)
- `http://localhost:8000` (alternative frontend)

To add more origins, update the environment variable:
```env
CORS_ORIGINS=["http://localhost:3000","http://localhost:8000","https://yourdomain.com"]
```

## Environment Configuration

For development, update your frontend `.env`:
```env
REACT_APP_AUTH_API_URL=http://localhost:8003
REACT_APP_GOOGLE_CLIENT_ID=your-google-client-id
```

For production:
```env
REACT_APP_AUTH_API_URL=https://auth.yourdomain.com
REACT_APP_GOOGLE_CLIENT_ID=your-google-client-id
```

## Testing

Use the provided Swagger UI for testing:
- Navigate to `http://localhost:8003/docs`
- Test endpoints directly from the UI
- View request/response examples

## Troubleshooting

### "CORS Error"
- Ensure your frontend URL is in `CORS_ORIGINS`
- Check requests include proper `Content-Type` header

### "Invalid Token"
- Token may have expired, refresh it
- Check token is properly stored and retrieved
- Verify Authorization header format: `Bearer <token>`

### "Google Login Failed"
- Verify redirect URI matches Google Cloud Console
- Check Google Client ID and Secret in service .env
- Ensure frontend callback URL is correct

## Support

For issues or questions:
1. Check service logs: `logs/auth_service.log`
2. Verify environment variables are set correctly
3. Test endpoints with provided Swagger UI
4. Check error messages returned by API
