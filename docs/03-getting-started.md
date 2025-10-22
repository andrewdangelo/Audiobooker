# Getting Started

This guide will help you set up the Audiobooker project on your local development environment.

## Prerequisites

### Required Software

- **Node.js**: Version 18.x or higher
- **npm**: Version 9.x or higher (comes with Node.js)
- **Python**: Version 3.9 or higher
- **Docker**: Docker Desktop or Docker Engine
- **Docker Compose**: Version 2.x or higher
- **Git**: For version control

### Verify Installations

```bash
# Check Node.js version
node --version  # Should be v18.x or higher

# Check npm version
npm --version   # Should be 9.x or higher

# Check Python version
python --version  # Should be 3.9 or higher

# Check Docker version
docker --version

# Check Docker Compose version
docker-compose --version
```

## Initial Setup

### 1. Clone the Repository

```bash
git clone https://github.com/andrewdangelo/Audiobooker.git
cd Audiobooker
```

### 2. Backend Setup

#### Create Python Virtual Environment

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows (Git Bash):
source venv/Scripts/activate

# On macOS/Linux:
source venv/bin/activate
```

#### Install Backend Dependencies

```bash
# Ensure virtual environment is activated
pip install -r requirements.txt
```

#### Configure Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit .env file with your preferred editor
# Update the following variables:
# - DATABASE_URL (already configured for Docker PostgreSQL)
# - SECRET_KEY (change in production)
# - R2 credentials (optional for development)
```

**Default `.env` configuration:**
```properties
DATABASE_URL=postgresql://audiobooker:password@localhost:5433/audiobooker_db
ENVIRONMENT=development
DEBUG=true
SECRET_KEY=your-secret-key-change-in-production
```

### 3. Frontend Setup

```bash
# Navigate to frontend directory
cd ../frontend

# Install dependencies
npm install
```

#### Configure Frontend Environment

```bash
# Copy example environment file
cp .env.example .env

# The default configuration should work for local development
```

**Default frontend `.env`:**
```properties
VITE_API_URL=http://localhost:8000
VITE_APP_NAME=Audiobooker
VITE_MAX_FILE_SIZE=52428800
```

### 4. Database Setup

#### Start PostgreSQL with Docker Compose

```bash
# Navigate to project root
cd ..

# Start PostgreSQL container
docker-compose up -d postgres

# Verify PostgreSQL is running
docker-compose ps

# Expected output:
# NAME                   STATUS              PORTS
# audiobooker-postgres   Up (healthy)        0.0.0.0:5433->5432/tcp
```

#### Initialize Database Tables

```bash
cd backend

# Activate virtual environment (if not already active)
source venv/Scripts/activate

# Create database tables
python -c "from config.database import Base, engine; Base.metadata.create_all(bind=engine); print('✅ Database tables created')"
```

## Running the Application

### Start the Backend Server

```bash
# In backend directory with virtual environment activated
cd backend
source venv/Scripts/activate

# Start development server
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Expected output:
# INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
# INFO:     Started reloader process
# 🚀 Audiobooker API starting up...
```

The backend API will be available at:
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Start the Frontend Server

```bash
# In a new terminal, navigate to frontend directory
cd frontend

# Start development server
npm run dev

# Expected output:
# VITE v5.4.21  ready in XXX ms
# ➜  Local:   http://localhost:5173/
# ➜  Network: use --host to expose
```

The frontend will be available at: http://localhost:5173

## Verify Installation

### 1. Check Backend Health

Open your browser or use curl:

```bash
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy"}
```

### 2. Check API Documentation

Visit http://localhost:8000/docs to view the interactive API documentation.

### 3. Test Frontend

1. Open http://localhost:5173 in your browser
2. Navigate to the Upload page
3. Try uploading a PDF file (create a simple test PDF if needed)
4. Verify you see upload progress and success message

## Common Development Commands

### Backend

```bash
# Activate virtual environment
source venv/Scripts/activate  # Windows Git Bash
source venv/bin/activate      # macOS/Linux

# Run development server
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Run tests
pytest

# Create database migration (future)
alembic revision --autogenerate -m "Description"

# Apply migrations (future)
alembic upgrade head
```

### Frontend

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Run linter
npm run lint
```

### Docker

```bash
# Start all services
docker-compose up -d

# Start specific service
docker-compose up -d postgres

# Stop all services
docker-compose down

# View logs
docker-compose logs -f postgres

# Remove volumes (caution: deletes data)
docker-compose down -v

# Rebuild containers
docker-compose up -d --build
```

## Development Workflow

### Typical Development Session

1. **Start Docker services**
   ```bash
   docker-compose up -d postgres
   ```

2. **Start backend** (Terminal 1)
   ```bash
   cd backend
   source venv/Scripts/activate
   python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

3. **Start frontend** (Terminal 2)
   ```bash
   cd frontend
   npm run dev
   ```

4. **Make changes** - both servers will auto-reload
   - Backend: Uvicorn watches for Python file changes
   - Frontend: Vite HMR updates instantly

5. **Stop servers**
   - Press `Ctrl+C` in both terminals
   - Stop Docker: `docker-compose down`

## Next Steps

- Read the [Frontend Guide](./04-frontend.md) for frontend development details
- Read the [Backend Guide](./05-backend.md) for backend development details
- Review the [API Reference](./07-api-reference.md) for available endpoints
- Check the [Troubleshooting Guide](./10-troubleshooting.md) if you encounter issues

## Quick Reference

| Service | URL | Purpose |
|---------|-----|---------|
| Frontend | http://localhost:5173 | React development server |
| Backend API | http://localhost:8000 | FastAPI application |
| API Docs | http://localhost:8000/docs | Swagger UI documentation |
| ReDoc | http://localhost:8000/redoc | Alternative API documentation |
| PostgreSQL | localhost:5433 | Database server |
| PgAdmin (optional) | http://localhost:5050 | Database management UI |

## Environment Variables Reference

### Backend (.env)

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://audiobooker:password@localhost:5433/audiobooker_db` |
| `ENVIRONMENT` | Environment name | `development` |
| `DEBUG` | Enable debug mode | `true` |
| `SECRET_KEY` | Secret key for signing | Random string |
| `API_V1_PREFIX` | API version prefix | `/api/v1` |
| `CORS_ORIGINS` | Allowed CORS origins | `http://localhost:5173,http://localhost:3000` |
| `MAX_UPLOAD_SIZE` | Max file upload size (bytes) | `52428800` (50MB) |
| `R2_ACCOUNT_ID` | Cloudflare R2 account ID | Optional |
| `R2_ACCESS_KEY_ID` | Cloudflare R2 access key | Optional |
| `R2_SECRET_ACCESS_KEY` | Cloudflare R2 secret key | Optional |

### Frontend (.env)

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_URL` | Backend API URL | `http://localhost:8000` |
| `VITE_APP_NAME` | Application name | `Audiobooker` |
| `VITE_MAX_FILE_SIZE` | Max upload size (bytes) | `52428800` |
