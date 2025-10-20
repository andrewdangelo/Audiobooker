#!/bin/bash
# Setup script for Audiobooker project

echo "🚀 Setting up Audiobooker..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Start PostgreSQL with Docker Compose
echo "📦 Starting PostgreSQL..."
docker-compose up -d postgres

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
sleep 5

# Setup backend
echo "🐍 Setting up backend..."
cd backend || exit

# Create virtual environment
if [ ! -d "venv" ]; then
    python -m venv venv
fi

# Activate virtual environment
source venv/bin/activate  # Use venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Copy env file
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "📝 Created .env file. Please update with your configuration."
fi

# Initialize database
python ../scripts/init_db.py

cd ..

# Setup frontend
echo "⚛️  Setting up frontend..."
cd frontend || exit

# Install dependencies
npm install

# Copy env file
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "📝 Created frontend .env file."
fi

cd ..

echo "✅ Setup complete!"
echo ""
echo "To start the application:"
echo "  Backend:  cd backend && source venv/bin/activate && python main.py"
echo "  Frontend: cd frontend && npm run dev"
echo ""
echo "API Documentation: http://localhost:8000/docs"
echo "Frontend: http://localhost:5173"
