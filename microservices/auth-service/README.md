# Auth Microservice

Authentication and Account Management Microservice for Audiobooker

## Features

- **Local Authentication**: Email and password based signup/login
- **Google OAuth**: Seamless Google login integration
- **Account Management**: User profile updates and settings management
- **Security**: JWT tokens, password hashing, refresh tokens
- **Database**: PostgreSQL with SQLAlchemy ORM
- **API Documentation**: Auto-generated Swagger UI and ReDoc

## Architecture

```
auth-service/
├── app/
│   ├── core/              # Core configuration and utilities
│   │   ├── config_settings.py    # Environment configuration
│   │   └── logging_config.py     # Logging setup
│   ├── database/          # Database configuration
│   │   └── database.py           # SQLAlchemy setup
│   ├── models/            # Data models and schemas
│   │   ├── user.py               # SQLAlchemy models
│   │   └── schemas.py            # Pydantic schemas
│   ├── routers/           # API endpoints
│   │   ├── health.py             # Health check endpoints
│   │   ├── auth.py               # Authentication endpoints
│   │   └── accounts.py           # Account management endpoints
│   ├── services/          # Business logic
│   │   ├── auth_service.py       # Authentication logic
│   │   └── account_service.py    # Account management logic
│   └── utils/             # Utility functions
│       ├── security.py           # JWT and password utilities
│       └── google_oauth.py       # Google OAuth integration
├── main.py               # Application entry point
├── requirements.txt      # Python dependencies
├── dockerfile            # Docker configuration
├── .env.example          # Environment variables template
└── README.md             # This file
```

## Setup

### Prerequisites

- Python 3.11+
- PostgreSQL
- Redis (optional, for session management)

### Installation

1. Clone the repository:
```bash
cd microservices/auth-service
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Initialize database:
```bash
python -c "from app.database.database import init_db; init_db()"
```

### Running Locally

```bash
python main.py
```

The service will be available at `http://localhost:8003`

API Documentation:
- Swagger UI: `http://localhost:8003/docs`
- ReDoc: `http://localhost:8003/redoc`

## Docker

Build the image:
```bash
docker build -t audiobooker-auth-service .
```

Run the container:
```bash
docker run -p 8003:8003 --env-file .env audiobooker-auth-service
```

## Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable the "Google+ API"
4. Create OAuth 2.0 credentials (Web application)
5. Add authorized redirect URI: `http://localhost:3000/auth/google/callback`
6. Copy Client ID and Client Secret to `.env`:

```env
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:3000/auth/google/callback
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/signup` - Register new user
- `POST /api/v1/auth/login` - Login with email and password
- `POST /api/v1/auth/google/callback` - Google OAuth callback
- `GET /api/v1/auth/google/auth-url` - Get Google authorization URL
- `POST /api/v1/auth/refresh` - Refresh access token
- `POST /api/v1/auth/logout` - Logout user
- `GET /api/v1/auth/me` - Get current user

### Account Management
- `GET /api/v1/accounts/profile` - Get user profile
- `PUT /api/v1/accounts/profile` - Update user profile
- `POST /api/v1/accounts/change-password` - Change password
- `GET /api/v1/accounts/settings` - Get account settings
- `PUT /api/v1/accounts/settings` - Update account settings
- `DELETE /api/v1/accounts/account` - Delete account

### Health
- `GET /api/v1/auth/health/` - Health check
- `GET /api/v1/auth/health/live` - Liveness check
- `GET /api/v1/auth/health/ready` - Readiness check

## Example Requests

### Signup
```bash
curl -X POST "http://localhost:8003/api/v1/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123",
    "first_name": "John",
    "last_name": "Doe"
  }'
```

### Login
```bash
curl -X POST "http://localhost:8003/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123"
  }'
```

### Get Profile
```bash
curl -X GET "http://localhost:8003/api/v1/accounts/profile" \
  -H "Authorization: Bearer <access_token>"
```

## Database Schema

### Users Table
- `id`: Primary key
- `email`: Unique email address
- `username`: Optional unique username
- `first_name`: User's first name
- `last_name`: User's last name
- `hashed_password`: Bcrypt hashed password (NULL for OAuth users)
- `profile_picture_url`: URL to profile picture
- `is_active`: Account active status
- `is_verified`: Email verification status
- `auth_provider`: LOCAL or GOOGLE
- `google_id`: Google account ID (for OAuth)
- `created_at`: Account creation timestamp
- `updated_at`: Last update timestamp
- `last_login`: Last login timestamp

### Account Settings Table
- `id`: Primary key
- `user_id`: Foreign key to users
- `two_factor_enabled`: 2FA status
- `email_notifications`: Email notification preference
- `marketing_emails`: Marketing email preference
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp

### Refresh Tokens Table
- `id`: Primary key
- `user_id`: Foreign key to users
- `token`: JWT refresh token
- `is_revoked`: Revocation status
- `created_at`: Creation timestamp
- `expires_at`: Expiration timestamp

## Security Features

- **Password Hashing**: Bcrypt with automatic salt generation
- **JWT Tokens**: Secure access and refresh tokens
- **Token Expiration**: Configurable access (30 min) and refresh (7 days) tokens
- **Password Requirements**: Minimum 8 characters, uppercase letter, digit
- **CORS Protection**: Configurable allowed origins
- **OAuth Integration**: Secure Google OAuth 2.0 flow

## Environment Variables

See `.env.example` for all configuration options:
- `SECRET_KEY`: JWT secret key
- `DATABASE_URL`: PostgreSQL connection string
- `GOOGLE_CLIENT_ID`: Google OAuth client ID
- `GOOGLE_CLIENT_SECRET`: Google OAuth client secret
- `CORS_ORIGINS`: Allowed origins for CORS

## Logging

Logs are written to:
- Console output (real-time)
- `logs/auth_service.log` (rotating file, 10MB max)

Log level is configurable via `LOG_LEVEL` environment variable.

## Development

### Running Tests
```bash
pytest
```

### Code Formatting
```bash
black .
isort .
```

### Linting
```bash
flake8 .
pylint app/
```

## Troubleshooting

### Database Connection Error
- Ensure PostgreSQL is running
- Verify `DATABASE_URL` in `.env`
- Check database credentials and permissions

### Google OAuth Issues
- Verify `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`
- Check redirect URI matches Google Cloud Console settings
- Ensure `GOOGLE_REDIRECT_URI` is correct in `.env`

### CORS Errors
- Add frontend URL to `CORS_ORIGINS` in `.env`
- Ensure credentials are included in requests

## Integration with Frontend

### Login Flow
1. User clicks "Login with Email" or "Login with Google"
2. Frontend sends credentials or authorization code to auth service
3. Service returns access token, refresh token, and user info
4. Frontend stores tokens (preferably in secure cookies)
5. Frontend includes access token in `Authorization` header for API requests

### Token Refresh
1. When access token expires (30 min)
2. Frontend uses refresh token to get new access token
3. Frontend updates stored tokens

### Example Frontend Integration
```javascript
// Signup
const response = await fetch('http://localhost:8003/api/v1/auth/signup', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'SecurePass123',
    first_name: 'John'
  })
});

const { access_token, refresh_token } = await response.json();

// Store tokens
localStorage.setItem('access_token', access_token);
localStorage.setItem('refresh_token', refresh_token);

// Use token for requests
const headers = {
  'Authorization': `Bearer ${access_token}`
};
```

## Contributing

Follow the existing code structure and naming conventions. Ensure all tests pass before submitting pull requests.

## License

Proprietary - Audiobooker
