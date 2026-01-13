# Auth Service - Quick Start Guide

## 5-Minute Setup

### 1. Install Dependencies
```bash
cd microservices/auth-service
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env and set these critical values:
# - SECRET_KEY=your-secret-key
# - DATABASE_URL=postgresql://audiobooker:password@localhost:5432/audiobooker_db
# - GOOGLE_CLIENT_ID=your-google-client-id
# - GOOGLE_CLIENT_SECRET=your-google-client-secret
```

### 3. Initialize Database
```bash
python init_db.py create
```

### 4. Run Service
```bash
python main.py
```

Service will start at `http://localhost:8003`

## Quick Test

### Test Signup
```bash
curl -X POST "http://localhost:8003/api/v1/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPass123",
    "first_name": "Test"
  }'
```

### Test Login
```bash
curl -X POST "http://localhost:8003/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPass123"
  }'
```

### Check Health
```bash
curl http://localhost:8003/api/v1/auth/health/
```

## API Documentation

Visit `http://localhost:8003/docs` for interactive Swagger UI

## Key Features

✅ Email/Password Authentication
✅ Google OAuth Integration
✅ Account Management
✅ JWT Token System
✅ Database User Storage
✅ Password Hashing
✅ Account Settings
✅ Profile Management

## Database Schema

**Users**: Email, username, password, profile info, OAuth data
**Account Settings**: Notification preferences, 2FA settings
**Refresh Tokens**: Token management and revocation

## Frontend Integration

See `FRONTEND_INTEGRATION.md` for complete frontend setup and examples

## Environment Variables

### Required
- `SECRET_KEY` - JWT secret key
- `DATABASE_URL` - PostgreSQL connection string
- `GOOGLE_CLIENT_ID` - Google OAuth credentials
- `GOOGLE_CLIENT_SECRET` - Google OAuth credentials

### Optional
- `ENVIRONMENT` - development/staging/production
- `PORT` - Server port (default: 8003)
- `LOG_LEVEL` - Logging level
- `CORS_ORIGINS` - Allowed domains

## Docker

```bash
# Build
docker build -t auth-service .

# Run
docker run -p 8003:8003 --env-file .env auth-service
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Database connection error | Ensure PostgreSQL running, check DATABASE_URL |
| Google OAuth failure | Verify credentials in .env, check redirect URI |
| Port already in use | Change PORT in .env or kill process on port 8003 |
| Module not found | Run `pip install -r requirements.txt` |

## Next Steps

1. ✅ Setup and run auth service
2. ✅ Test with Swagger UI at `/docs`
3. ✅ Integrate with frontend using `FRONTEND_INTEGRATION.md`
4. ✅ Configure Google OAuth for production
5. ✅ Deploy to your environment

## Support Files

- `README.md` - Full documentation
- `FRONTEND_INTEGRATION.md` - Frontend integration guide
- `.env.example` - Environment template
- `dockerfile` - Docker configuration
- `requirements.txt` - Python dependencies

## Service Structure

```
Core
├── main.py              # Entry point
├── requirements.txt     # Dependencies
└── dockerfile          # Docker build

Configuration
├── app/core/config_settings.py    # Settings
├── app/core/logging_config.py     # Logging
└── .env.example                   # Environment template

Database
├── app/database/database.py       # Connection & ORM
└── app/models/user.py             # Data models

API Endpoints
├── app/routers/health.py          # Health checks
├── app/routers/auth.py            # Authentication
└── app/routers/accounts.py        # Account management

Business Logic
├── app/services/auth_service.py   # Auth logic
└── app/services/account_service.py # Account logic

Utilities
├── app/utils/security.py          # JWT & passwords
└── app/utils/google_oauth.py      # Google OAuth
```

## Password Requirements

- Minimum 8 characters
- At least one uppercase letter
- At least one digit

Example valid password: `SecurePass123`

## Authentication Flow

```
User Registration/Login
        ↓
Service validates input & database
        ↓
On success: return tokens + user info
        ↓
Frontend stores tokens
        ↓
Include token in Authorization header for API requests
        ↓
Service verifies token & grants access
```

## Token Flow

```
Access Token (30 min)
├── Short-lived
├── Used for API requests
└── Stored securely

Refresh Token (7 days)
├── Longer-lived
├── Used to get new access token
└── Can be revoked
```

## API Response Format

Success (200/201):
```json
{
  "user": { "id": 1, "email": "user@example.com", ... },
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

Error (400/401/500):
```json
{
  "detail": "Error message describing what went wrong"
}
```

## Monitoring

Logs are written to:
- Console (live output)
- `logs/auth_service.log` (persistent)

Check service health:
- `/api/v1/auth/health/` - Full health check
- `/api/v1/auth/health/live` - Liveness probe
- `/api/v1/auth/health/ready` - Readiness probe

## Rate Limiting

Currently not implemented. For production, consider:
- Limiting login attempts
- Throttling token refresh
- Rate limiting OAuth callbacks

## Security Checklist

- [ ] Change `SECRET_KEY` in production
- [ ] Use HTTPS in production
- [ ] Set secure CORS_ORIGINS
- [ ] Enable HTTPS for database connection
- [ ] Regularly rotate secrets
- [ ] Monitor logs for unauthorized access
- [ ] Implement rate limiting
- [ ] Enable 2FA for admin accounts

Ready to go! 🚀
