# Auth Service - API Test Examples

This document provides ready-to-use examples for testing the Auth Service API.

## Prerequisites

Service running on `http://localhost:8003`

## Test Cases

### 1. Health Check

**Request:**
```bash
curl -X GET http://localhost:8003/api/v1/auth/health/
```

**Expected Response (200 OK):**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "service": "Auth Service"
}
```

---

### 2. Signup - Create New User

**Request:**
```bash
curl -X POST http://localhost:8003/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john.doe@example.com",
    "password": "SecurePassword123",
    "first_name": "John",
    "last_name": "Doe",
    "username": "johndoe"
  }'
```

**Expected Response (201 Created):**
```json
{
  "user": {
    "id": 1,
    "email": "john.doe@example.com",
    "username": "johndoe",
    "first_name": "John",
    "last_name": "Doe",
    "profile_picture_url": null,
    "is_active": true,
    "is_verified": false,
    "auth_provider": "local",
    "created_at": "2024-01-12T20:30:00",
    "last_login": null
  },
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Validation:**
- ✓ User created with all fields
- ✓ Password securely hashed
- ✓ Both access and refresh tokens issued
- ✓ User marked as not verified
- ✓ Auth provider set to "local"

---

### 3. Signup Error - Email Already Exists

**Request:**
```bash
curl -X POST http://localhost:8003/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john.doe@example.com",
    "password": "AnotherPassword123",
    "first_name": "Jane",
    "last_name": "Smith"
  }'
```

**Expected Response (400 Bad Request):**
```json
{
  "detail": "Email already registered"
}
```

---

### 4. Login - Valid Credentials

**Request:**
```bash
curl -X POST http://localhost:8003/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john.doe@example.com",
    "password": "SecurePassword123"
  }'
```

**Expected Response (200 OK):**
```json
{
  "user": {
    "id": 1,
    "email": "john.doe@example.com",
    "username": "johndoe",
    "first_name": "John",
    "last_name": "Doe",
    "profile_picture_url": null,
    "is_active": true,
    "is_verified": false,
    "auth_provider": "local",
    "created_at": "2024-01-12T20:30:00",
    "last_login": "2024-01-12T20:35:00"
  },
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Validation:**
- ✓ User authenticated successfully
- ✓ Last login timestamp updated
- ✓ New tokens issued

---

### 5. Login Error - Invalid Password

**Request:**
```bash
curl -X POST http://localhost:8003/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john.doe@example.com",
    "password": "WrongPassword123"
  }'
```

**Expected Response (401 Unauthorized):**
```json
{
  "detail": "Invalid email or password"
}
```

---

### 6. Get User Profile

**Request:**
```bash
curl -X GET http://localhost:8003/api/v1/accounts/profile \
  -H "Authorization: Bearer <access_token_from_login>"
```

**Expected Response (200 OK):**
```json
{
  "id": 1,
  "email": "john.doe@example.com",
  "username": "johndoe",
  "first_name": "John",
  "last_name": "Doe",
  "profile_picture_url": null,
  "is_active": true,
  "is_verified": false,
  "auth_provider": "local",
  "created_at": "2024-01-12T20:30:00",
  "last_login": "2024-01-12T20:35:00"
}
```

---

### 7. Update User Profile

**Request:**
```bash
curl -X PUT http://localhost:8003/api/v1/accounts/profile \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "first_name": "Jonathan",
    "last_name": "Doe-Smith",
    "username": "jonathandoe"
  }'
```

**Expected Response (200 OK):**
```json
{
  "id": 1,
  "email": "john.doe@example.com",
  "username": "jonathandoe",
  "first_name": "Jonathan",
  "last_name": "Doe-Smith",
  "profile_picture_url": null,
  "is_active": true,
  "is_verified": false,
  "auth_provider": "local",
  "created_at": "2024-01-12T20:30:00",
  "last_login": "2024-01-12T20:35:00"
}
```

**Validation:**
- ✓ First name updated
- ✓ Last name updated
- ✓ Username updated

---

### 8. Change Password

**Request:**
```bash
curl -X POST http://localhost:8003/api/v1/accounts/change-password \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "old_password": "SecurePassword123",
    "new_password": "NewSecurePassword456"
  }'
```

**Expected Response (200 OK):**
```json
{
  "message": "Password changed successfully"
}
```

**Validation:**
- ✓ Old password verified before change
- ✓ New password securely hashed
- ✓ Can login with new password afterward

---

### 9. Refresh Access Token

**Request:**
```bash
curl -X POST http://localhost:8003/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "<refresh_token_from_login>"
  }'
```

**Expected Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...(new_token)...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...(new_token)...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**Validation:**
- ✓ New access token issued
- ✓ New refresh token issued
- ✓ Tokens stored for revocation tracking

---

### 10. Get Account Settings

**Request:**
```bash
curl -X GET http://localhost:8003/api/v1/accounts/settings \
  -H "Authorization: Bearer <access_token>"
```

**Expected Response (200 OK):**
```json
{
  "user_id": 1,
  "two_factor_enabled": false,
  "email_notifications": true,
  "marketing_emails": false,
  "created_at": "2024-01-12T20:30:00",
  "updated_at": "2024-01-12T20:30:00"
}
```

---

### 11. Update Account Settings

**Request:**
```bash
curl -X PUT http://localhost:8003/api/v1/accounts/settings \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "two_factor_enabled": true,
    "email_notifications": false,
    "marketing_emails": true
  }'
```

**Expected Response (200 OK):**
```json
{
  "user_id": 1,
  "two_factor_enabled": true,
  "email_notifications": false,
  "marketing_emails": true,
  "created_at": "2024-01-12T20:30:00",
  "updated_at": "2024-01-12T20:40:00"
}
```

---

### 12. Google OAuth - Get Authorization URL

**Request:**
```bash
curl -X GET http://localhost:8003/api/v1/auth/google/auth-url
```

**Expected Response (200 OK):**
```json
{
  "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?client_id=test-google-client-id&redirect_uri=http%3A%2F%2Flocalhost%3A3000%2Fauth%2Fgoogle%2Fcallback&response_type=code&scope=openid%20email%20profile&state=...",
  "state": "secure-random-state-value"
}
```

---

### 13. Logout

**Request:**
```bash
curl -X POST http://localhost:8003/api/v1/auth/logout \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "refresh_token": "<refresh_token>"
  }'
```

**Expected Response (200 OK):**
```json
{
  "message": "Logged out successfully"
}
```

**Validation:**
- ✓ Refresh token marked as revoked
- ✓ User cannot use revoked token for refresh

---

### 14. Delete Account

**Request:**
```bash
curl -X DELETE http://localhost:8003/api/v1/accounts/account \
  -H "Authorization: Bearer <access_token>"
```

**Expected Response (200 OK):**
```json
{
  "message": "Account deleted successfully"
}
```

**Validation:**
- ✓ User marked as inactive (soft delete)
- ✓ Account data preserved for compliance
- ✓ Cannot login after deletion

---

## Error Test Cases

### Invalid Token

**Request:**
```bash
curl -X GET http://localhost:8003/api/v1/accounts/profile \
  -H "Authorization: Bearer invalid.token.here"
```

**Expected Response (401 Unauthorized):**
```json
{
  "detail": "Invalid token"
}
```

---

### Missing Authorization Header

**Request:**
```bash
curl -X GET http://localhost:8003/api/v1/accounts/profile
```

**Expected Response (401 Unauthorized):**
```json
{
  "detail": "Not authenticated"
}
```

---

### Password Too Weak

**Request:**
```bash
curl -X POST http://localhost:8003/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "weak",
    "first_name": "Test"
  }'
```

**Expected Response (400 Bad Request):**
```json
{
  "detail": [
    {
      "loc": ["body", "password"],
      "msg": "Password must contain at least one uppercase letter",
      "type": "value_error"
    }
  ]
}
```

---

## Postman Collection

Import this JSON into Postman for complete test suite:

```json
{
  "info": {
    "name": "Auth Service API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Health Check",
      "request": {
        "method": "GET",
        "url": "http://localhost:8003/api/v1/auth/health/"
      }
    },
    {
      "name": "Signup",
      "request": {
        "method": "POST",
        "url": "http://localhost:8003/api/v1/auth/signup",
        "body": {
          "mode": "raw",
          "raw": "{\"email\": \"test@example.com\", \"password\": \"TestPass123\", \"first_name\": \"Test\"}"
        }
      }
    }
  ]
}
```

## Testing Checklist

- [ ] Health check returns healthy status
- [ ] Signup creates user successfully
- [ ] Signup rejects duplicate email
- [ ] Login works with valid credentials
- [ ] Login rejects invalid credentials
- [ ] Access token works for authenticated endpoints
- [ ] Refresh token issues new access token
- [ ] Invalid token rejected
- [ ] Password change works
- [ ] Account settings CRUD works
- [ ] Account deletion marks user inactive
- [ ] Google OAuth URL generation works

## Notes

- Replace `<access_token>` and `<refresh_token>` with actual tokens from login
- Tokens expire after configured time (default 30 min access, 7 days refresh)
- All responses use standard HTTP status codes
- All errors include descriptive `detail` messages
- Database uses SQLite for development (auto-created)

## Debugging

Enable debug logging:
```bash
# In .env
LOG_LEVEL=DEBUG
```

View logs:
```bash
tail -f logs/auth_service.log
```
