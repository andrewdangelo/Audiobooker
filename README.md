# Audiobooker - PDF to Audiobook Conversion System

A modern web application that converts PDF documents into high-quality audiobooks using AI-powered text-to-speech technology.

## 🚀 Features

- **PDF Upload & Processing**: Extract text from PDF documents
- **Text-to-Speech Conversion**: Convert extracted text to natural-sounding audio
- **Cloud Storage**: Store audiobooks securely on Cloudflare R2
- **User Library**: Manage and organize your audiobook collection
- **Audio Player**: Built-in player with playback controls
- **Progress Tracking**: Monitor conversion progress in real-time

## 🏗️ Tech Stack

### Frontend
- **React** with TypeScript
- **Vite** for fast development and building
- **Tailwind CSS** for styling
- **shadcn/ui** for UI components
- **React Router** for navigation

### Backend
- **Python FastAPI** for high-performance API
- **PostgreSQL** for data persistence
- **Cloudflare R2** for object storage
- **SQLAlchemy** for ORM
- **Pydantic** for data validation

## 📁 Project Structure

```
audiobooker/
├── frontend/          # React frontend application
├── backend/           # FastAPI backend application
├── scripts/           # Utility scripts
└── docker-compose.yml # Docker setup for local development
```

## 🛠️ Getting Started

### Prerequisites

- Node.js 18+ and npm/yarn
- Python 3.11+
- Docker and Docker Compose
- PostgreSQL (or use Docker)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd audiobooker
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start the database**
   ```bash
   docker-compose up -d postgres
   ```

4. **Set up the backend**
   ```bash
   cd backend
   cp .env.example .env
   # Edit backend/.env with your configuration
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   python main.py
   ```

5. **Set up the frontend**
   ```bash
   cd frontend
   cp .env.example .env
   # Edit frontend/.env with your configuration
   npm install
   npm run dev
   ```

6. **Access the application**
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

## 🧪 Testing

### Backend Tests
```bash
cd backend
pytest
```

### Frontend Tests
```bash
cd frontend
npm run test
```

## 📝 Documentation

- [Frontend Documentation](./frontend/README.md)
- [Backend Documentation](./backend/README.md)
- [API Documentation](http://localhost:8000/docs) (when running)

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines before submitting PRs.

## 📄 License

This project is licensed under the MIT License.

## 🔗 Links

- [Project Repository](#)
- [Issue Tracker](#)
- [Documentation](#)
