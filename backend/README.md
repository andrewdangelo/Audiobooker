# Audiobooker Backend

FastAPI-based backend for the Audiobooker PDF-to-Audiobook conversion system.

## 🚀 Tech Stack

- **FastAPI** - Modern, fast web framework
- **PostgreSQL** - Primary database
- **SQLAlchemy** - ORM for database operations
- **Pydantic** - Data validation
- **Cloudflare R2** - Object storage (S3-compatible)
- **Boto3** - AWS SDK for Python (R2 access)

## 📁 Project Structure

```
backend/
├── config/           # Configuration files
├── app/
│   ├── models/      # SQLAlchemy models
│   ├── schemas/     # Pydantic schemas
│   ├── routers/     # API route handlers
│   ├── services/    # Business logic
│   ├── database/    # Database configuration
│   ├── core/        # Core utilities
│   └── utils/       # Utility functions
└── tests/           # Test files
```

## 🛠️ Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- pip or poetry

### Installation

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # For development
   ```

3. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. Initialize the database:
   ```bash
   python scripts/init_db.py
   ```

5. Run the development server:
   ```bash
   python main.py
   ```
   Or with uvicorn directly:
   ```bash
   uvicorn main:app --reload
   ```

The API will be available at `http://localhost:8000`

## 📝 API Documentation

Once the server is running, you can access:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🧪 Testing

Run tests with pytest:

```bash
pytest
```

With coverage:

```bash
pytest --cov=app tests/
```

## 🗄️ Database Migrations

Create a new migration:

```bash
alembic revision --autogenerate -m "Description"
```

Apply migrations:

```bash
alembic upgrade head
```

Rollback migration:

```bash
alembic downgrade -1
```

## 🔧 Configuration

Environment variables are managed through `.env` file:

- `DATABASE_URL`: PostgreSQL connection string
- `R2_ACCOUNT_ID`: Cloudflare R2 account ID
- `R2_ACCESS_KEY_ID`: R2 access key
- `R2_SECRET_ACCESS_KEY`: R2 secret key
- `R2_BUCKET_NAME`: R2 bucket name

## 📚 Key Features

- **PDF Processing**: Extract text from PDF documents
- **Text-to-Speech**: Convert text to audio
- **Cloud Storage**: Store files in Cloudflare R2
- **Async Support**: Asynchronous request handling
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Validation**: Pydantic models for request/response validation

## 🏗️ Development

### Code Style

Format code with Black:
```bash
black .
```

Lint with Flake8:
```bash
flake8 .
```

Type checking with mypy:
```bash
mypy .
```

## 📖 Documentation

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
