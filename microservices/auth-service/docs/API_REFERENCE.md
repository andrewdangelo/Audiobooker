# Auth Service - API Reference

## Base URL
```
http://localhost:8003
```

## Authentication
Most endpoints require an `Authorization` header with a Bearer token:
```
Authorization: Bearer <access_token>
```

---

## Health Check Endpoints

### Get Health Status
**Endpoint:** `GET /api/v1/auth/health/`

**Description:** Check if the service is running and healthy

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "service": "Auth Service"
}
```

**Status Code:** 200

---

### Liveness Check
**Endpoint:** `GET /api/v1/auth/health/live`

**Description:** Kubernetes liveness probe endpoint

**Response:**
```json
{
  "status": "alive"
}
```

**Status Code:** 200

---

### Readiness Check
**Endpoint:** `GET /api/v1/auth/health/ready`

**Description:** Kubernetes readiness probe endpoint

**Response:**
```json
{
  "status": "ready"
}
```

**Status Code:** 200

---

## Authentication Endpoints

### User Signup
**Endpoint:** `POST /api/v1/auth/signup`

**Description:** Register a new user account

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123",
  "first_name": "John",
  "last_name": "Doe",
  "username": "johndoe"
}
```

**Required Fields:**
- `email`: Valid email address
- `password`: Min 8 chars, 1 uppercase, 1 digit
- `first_name`: User's first name

**Optional Fields:**
- `last_name`
- `username`: Unique username

**Response (201 Created):**
```json
{
  "user": {
    "id": 1,
    "email": "user@example.com",
    "username": "johndoe",
    "first_name": "John",
    "last_name": "Doe",
    "profile_picture_url": null,
    "is_active": true,
    "is_verified": false,
    "auth_provider": "local",
    "created_at": "2024-01-12T10:30:00Z",
    "last_login": null
  },
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

**Error Responses:**
- `400 Bad Request`: Email already registered, invalid input
- `422 Unprocessable Entity`: Validation error (password strength, etc.)

---

### User Login
**Endpoint:** `POST /api/v1/auth/login`

**Description:** Authenticate user with email and password

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123"
}
```

**Response (200 OK):**
```json
{
  "user": {
    "id": 1,
    "email": "user@example.com",
    "username": "johndoe",
    "first_name": "John",
    "last_name": "Doe",
    "profile_picture_url": null,
    "is_active": true,
    "is_verified": false,
    "auth_provider": "local",
    "created_at": "2024-01-12T10:30:00Z",
    "last_login": "2024-01-12T15:45:00Z"
  },
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

**Error Responses:**
- `401 Unauthorized`: Invalid credentials
- `400 Bad Request`: User disabled

---

### Get Google Authorization URL
**Endpoint:** `GET /api/v1/auth/google/auth-url`

**Description:** Get Google OAuth authorization URL

**Query Parameters:** None

**Response (200 OK):**
```json
{
  "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?client_id=...",
  "state": "random-csrf-token"
}
```

---

### Google OAuth Callback
**Endpoint:** `POST /api/v1/auth/google/callback`

**Description:** Handle Google OAuth authorization code exchange

**Request Body:**
```json
{
  "code": "authorization-code-from-google",
  "state": "csrf-token"
}
```

**Response (200 OK):**
```json
{
  "user": {
    "id": 2,
    "email": "user@gmail.com",
    "username": null,
    "first_name": "John",
    "last_name": "Doe",
    "profile_picture_url": "https://...",
    "is_active": true,
    "is_verified": true,
    "auth_provider": "google",
    "created_at": "2024-01-12T10:30:00Z",
    "last_login": "2024-01-12T15:45:00Z"
  },
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

**Error Responses:**
- `401 Unauthorized`: Invalid code or state mismatch
- `400 Bad Request`: Failed to get user info

---

### Refresh Access Token
**Endpoint:** `POST /api/v1/auth/refresh`

**Description:** Get a new access token using refresh token

**Request Body:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**Error Responses:**
- `401 Unauthorized`: Invalid or expired refresh token

---

### Logout
**Endpoint:** `POST /api/v1/auth/logout`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Response (200 OK):**
```json
{
  "message": "Logged out successfully"
}
```

---

### Get Current User
**Endpoint:** `GET /api/v1/auth/me`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200 OK):**
```json
{
  "id": 1,
  "email": "user@example.com",
  "username": "johndoe",
  "first_name": "John",
  "last_name": "Doe",
  "profile_picture_url": null,
  "is_active": true,
  "is_verified": false,
  "auth_provider": "local",
  "created_at": "2024-01-12T10:30:00Z",
  "last_login": "2024-01-12T15:45:00Z"
}
```

**Error Responses:**
- `401 Unauthorized`: Missing or invalid token
- `404 Not Found`: User not found

---

## Account Management Endpoints

### Get User Profile
**Endpoint:** `GET /api/v1/accounts/profile`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200 OK):**
```json
{
  "id": 1,
  "email": "user@example.com",
  "username": "johndoe",
  "first_name": "John",
  "last_name": "Doe",
  "profile_picture_url": null,
  "is_active": true,
  "is_verified": false,
  "auth_provider": "local",
  "created_at": "2024-01-12T10:30:00Z",
  "last_login": "2024-01-12T15:45:00Z"
}
```

---

### Update User Profile
**Endpoint:** `PUT /api/v1/accounts/profile`

**Headers:**
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "first_name": "Jonathan",
  "last_name": "Smith",
  "username": "jonsmith"
}
```

**All fields optional**

**Response (200 OK):**
```json
{
  "id": 1,
  "email": "user@example.com",
  "username": "jonsmith",
  "first_name": "Jonathan",
  "last_name": "Smith",
  "profile_picture_url": null,
  "is_active": true,
  "is_verified": false,
  "auth_provider": "local",
  "created_at": "2024-01-12T10:30:00Z",
  "last_login": "2024-01-12T15:45:00Z"
}
```

**Error Responses:**
- `400 Bad Request`: Username already taken
- `401 Unauthorized`: Invalid token

---

### Change Password
**Endpoint:** `POST /api/v1/accounts/change-password`

**Headers:**
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "old_password": "CurrentPass123",
  "new_password": "NewSecurePass456"
}
```

**Response (200 OK):**
```json
{
  "message": "Password changed successfully"
}
```

**Error Responses:**
- `400 Bad Request`: Invalid current password, weak new password
- `401 Unauthorized`: Invalid token

---

### Get Account Settings
**Endpoint:** `GET /api/v1/accounts/settings`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200 OK):**
```json
{
  "user_id": 1,
  "two_factor_enabled": false,
  "email_notifications": true,
  "marketing_emails": false,
  "created_at": "2024-01-12T10:30:00Z",
  "updated_at": "2024-01-12T10:30:00Z"
}
```

---

### Update Account Settings
**Endpoint:** `PUT /api/v1/accounts/settings`

**Headers:**
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "two_factor_enabled": true,
  "email_notifications": false,
  "marketing_emails": true
}
```

**All fields optional**

**Response (200 OK):**
```json
{
  "user_id": 1,
  "two_factor_enabled": true,
  "email_notifications": false,
  "marketing_emails": true,
  "created_at": "2024-01-12T10:30:00Z",
  "updated_at": "2024-01-12T16:00:00Z"
}
```

---

### Delete Account
**Endpoint:** `DELETE /api/v1/accounts/account`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200 OK):**
```json
{
  "message": "Account deleted successfully"
}
```

**Note:** This sets `is_active` to false (soft delete)

**Error Responses:**
- `401 Unauthorized`: Invalid token
- `404 Not Found`: User not found

---

## Error Response Codes

| Code | Meaning |
|------|---------|
| 200 | OK - Request successful |
| 201 | Created - Resource created successfully |
| 400 | Bad Request - Invalid input or validation error |
| 401 | Unauthorized - Authentication required or invalid token |
| 404 | Not Found - Resource doesn't exist |
| 422 | Unprocessable Entity - Validation error |
| 500 | Internal Server Error - Server-side error |

---

## Token Format

JWT tokens are composed of three parts separated by dots:
```
header.payload.signature
```

**Payload contains:**
- `sub`: User ID
- `exp`: Expiration timestamp
- `iat`: Issued at timestamp
- `type`: Token type (access or refresh)

**Example decoded payload:**
```json
{
  "sub": "1",
  "exp": 1705070400,
  "iat": 1705068600,
  "type": "access"
}
```

---

## Rate Limiting

Currently not implemented. Monitor your API usage to plan future implementation.

---

## Testing Endpoints

All endpoints can be tested via the interactive API documentation:
```
http://localhost:8003/docs
```

Use the "Try it out" button to test each endpoint directly from your browser.

---

## Common Patterns

### Full Authentication Flow
1. User signs up: `POST /api/v1/auth/signup`
2. Service returns tokens
3. Store tokens securely
4. Use access token for API requests
5. When expired, refresh with refresh token: `POST /api/v1/auth/refresh`
6. On logout: `POST /api/v1/auth/logout`

### Profile Management
1. Get profile: `GET /api/v1/accounts/profile`
2. Update profile: `PUT /api/v1/accounts/profile`
3. Manage settings: `GET/PUT /api/v1/accounts/settings`
4. Change password: `POST /api/v1/accounts/change-password`

### Error Handling
1. Check HTTP status code
2. Read `detail` field in response
3. Handle token expiration (401) by refreshing
4. Redirect to login on auth failure
