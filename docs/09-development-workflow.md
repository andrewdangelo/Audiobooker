# Development Workflow

## Git Workflow

### Branching Strategy

```
master (main branch)
  ├── feature/upload-ui
  ├── feature/pdf-processing
  ├── feature/tts-integration
  └── bugfix/cors-issue
```

### Branch Naming Convention

- `feature/` - New features
- `bugfix/` - Bug fixes
- `hotfix/` - Urgent production fixes
- `refactor/` - Code refactoring
- `docs/` - Documentation updates

### Workflow Steps

1. **Create Feature Branch**
   ```bash
   git checkout master
   git pull origin master
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**
   ```bash
   # Make code changes
   git add .
   git commit -m "Add feature: description"
   ```

3. **Push to Remote**
   ```bash
   git push origin feature/your-feature-name
   ```

4. **Create Pull Request**
   - Go to GitHub repository
   - Click "Pull Request"
   - Select your branch
   - Add description and reviewers
   - Submit for review

5. **Merge to Master**
   ```bash
   # After approval
   git checkout master
   git pull origin master
   git merge feature/your-feature-name
   git push origin master
   ```

### Commit Message Convention

Follow conventional commits:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting, missing semicolons, etc.
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance tasks

**Examples**:
```bash
git commit -m "feat(upload): add drag-and-drop support"
git commit -m "fix(api): resolve CORS issue with frontend"
git commit -m "docs(readme): update installation instructions"
```

## Code Style

### Python (Backend)

Follow PEP 8 style guide.

**Formatting with Black**:
```bash
# Install Black
pip install black

# Format all files
black .

# Check without modifying
black --check .
```

**Linting with Flake8**:
```bash
# Install Flake8
pip install flake8

# Run linter
flake8 .

# Configuration in .flake8
[flake8]
max-line-length = 100
exclude = venv,__pycache__
```

**Type Checking with mypy**:
```bash
# Install mypy
pip install mypy

# Run type checker
mypy .
```

### TypeScript (Frontend)

Follow standard TypeScript conventions.

**Linting with ESLint**:
```bash
# Run linter
npm run lint

# Auto-fix issues
npm run lint -- --fix
```

**Configuration** (`.eslintrc.js`):
```javascript
module.exports = {
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:react/recommended',
    'plugin:react-hooks/recommended',
  ],
  rules: {
    'no-console': 'warn',
    '@typescript-eslint/no-unused-vars': 'error',
  },
}
```

## Testing

### Backend Tests

**Setup**:
```bash
pip install pytest pytest-asyncio pytest-cov httpx
```

**Run Tests**:
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_upload.py

# Run specific test
pytest tests/test_upload.py::test_upload_valid_pdf
```

**Example Test** (`tests/test_upload.py`):
```python
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_upload_pdf():
    files = {"file": ("test.pdf", b"fake content", "application/pdf")}
    response = client.post("/api/v1/upload/", files=files)
    assert response.status_code == 200
    assert "id" in response.json()
```

### Frontend Tests

**Setup**:
```bash
npm install -D vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event
```

**Run Tests**:
```bash
# Run all tests
npm run test

# Run in watch mode
npm run test:watch

# Run with coverage
npm run test:coverage
```

**Example Test** (`src/components/FileUpload.test.tsx`):
```typescript
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import FileUpload from './FileUpload'

describe('FileUpload', () => {
  it('renders upload area', () => {
    render(<FileUpload />)
    expect(screen.getByText(/drop your pdf/i)).toBeInTheDocument()
  })

  it('handles file selection', async () => {
    const { container } = render(<FileUpload />)
    const input = container.querySelector('input[type="file"]')
    
    const file = new File(['content'], 'test.pdf', { type: 'application/pdf' })
    fireEvent.change(input!, { target: { files: [file] } })
    
    expect(screen.getByText('test.pdf')).toBeInTheDocument()
  })
})
```

## Code Review Checklist

### Before Submitting PR

- [ ] Code follows style guidelines
- [ ] All tests pass
- [ ] New tests added for new features
- [ ] Documentation updated
- [ ] No commented-out code
- [ ] No console.log or print statements
- [ ] Environment variables properly handled
- [ ] Error handling in place
- [ ] Type safety maintained

### Reviewer Checklist

- [ ] Code logic is sound
- [ ] Tests are comprehensive
- [ ] No security vulnerabilities
- [ ] Performance considerations
- [ ] Documentation is clear
- [ ] Follows project conventions
- [ ] No breaking changes (or documented)

## Development Tools

### VS Code Extensions

**Python**:
- Python (Microsoft)
- Pylance
- Python Docstring Generator

**TypeScript/React**:
- ESLint
- Prettier
- ES7+ React/Redux/React-Native snippets

**General**:
- GitLens
- Docker
- Thunder Client (API testing)

### VS Code Settings

```json
{
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": true
  },
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "[typescript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter"
  }
}
```

## Debugging

### Backend Debugging

**VS Code Launch Configuration** (`.vscode/launch.json`):
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "main:app",
        "--reload",
        "--host",
        "0.0.0.0",
        "--port",
        "8000"
      ],
      "jinja": true,
      "justMyCode": false,
      "env": {
        "PYTHONPATH": "${workspaceFolder}/backend"
      }
    }
  ]
}
```

**Debug with print statements**:
```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@router.post("/upload")
async def upload_file(file: UploadFile):
    logger.debug(f"Received file: {file.filename}")
    logger.debug(f"File size: {file.size}")
    # Your code
```

### Frontend Debugging

**Browser DevTools**:
- Use React DevTools extension
- Use Network tab for API calls
- Use Console for errors
- Use Sources tab for breakpoints

**VS Code Debugging**:
```json
{
  "name": "Chrome: Frontend",
  "type": "chrome",
  "request": "launch",
  "url": "http://localhost:5173",
  "webRoot": "${workspaceFolder}/frontend/src"
}
```

## Performance Profiling

### Backend

```python
import cProfile
import pstats

def profile_function():
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Your code here
    
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumtime')
    stats.print_stats(10)
```

### Frontend

```typescript
// React DevTools Profiler
import { Profiler } from 'react'

function onRenderCallback(
  id, phase, actualDuration, baseDuration, startTime, commitTime
) {
  console.log(`${id} took ${actualDuration}ms`)
}

<Profiler id="FileUpload" onRender={onRenderCallback}>
  <FileUpload />
</Profiler>
```

## Documentation

### Code Comments

**Python**:
```python
def upload_file(file_content: bytes, file_name: str) -> str:
    """
    Upload a file to storage.
    
    Args:
        file_content: The binary content of the file
        file_name: The name to save the file as
        
    Returns:
        The path where the file was saved
        
    Raises:
        StorageException: If upload fails
    """
    pass
```

**TypeScript**:
```typescript
/**
 * Upload a PDF file to the server
 * @param file - The PDF file to upload
 * @param onProgress - Progress callback (0-100)
 * @returns Promise resolving to upload response
 * @throws {AxiosError} If upload fails
 */
async function uploadPDF(
  file: File,
  onProgress?: (progress: number) => void
): Promise<UploadResponse> {
  // Implementation
}
```

### API Documentation

Update OpenAPI schemas in FastAPI:

```python
@router.post(
    "/upload/",
    response_model=UploadResponse,
    summary="Upload PDF file",
    description="Upload a PDF file for conversion to audiobook",
    responses={
        200: {"description": "File uploaded successfully"},
        400: {"description": "Invalid file or size too large"},
        500: {"description": "Server error during upload"}
    }
)
async def upload_pdf(file: UploadFile = File(...)):
    pass
```

## Continuous Integration (Future)

### GitHub Actions Workflow

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [ master ]
  pull_request:
    branches: [ master ]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
      - name: Run tests
        run: |
          cd backend
          pytest

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      - name: Install dependencies
        run: |
          cd frontend
          npm ci
      - name: Run tests
        run: |
          cd frontend
          npm run test
      - name: Build
        run: |
          cd frontend
          npm run build
```

## Release Process

1. **Version Bump**
   ```bash
   # Update version in package.json and __init__.py
   git add .
   git commit -m "chore: bump version to 1.1.0"
   ```

2. **Create Tag**
   ```bash
   git tag -a v1.1.0 -m "Release version 1.1.0"
   git push origin v1.1.0
   ```

3. **Generate Changelog**
   ```bash
   git log v1.0.0..v1.1.0 --oneline > CHANGELOG.md
   ```

4. **Deploy**
   ```bash
   # Deploy to production
   docker-compose up -d --build
   ```

## Daily Workflow

```bash
# Start your day
git checkout master
git pull origin master
git checkout -b feature/my-feature

# Start services
docker-compose up -d postgres
cd backend && source venv/Scripts/activate && uvicorn main:app --reload
cd frontend && npm run dev

# Make changes, test, commit

# End of day
git add .
git commit -m "feat: work in progress on my feature"
git push origin feature/my-feature

# Stop services
docker-compose down
```
