#!/bin/bash
# Quick Start Guide for Auth Service

echo "================================"
echo "Auth Service - Quick Start"
echo "================================"
echo ""

# Check if in the right directory
if [ ! -f "main.py" ]; then
    echo "Error: main.py not found. Please run from microservices/auth-service directory"
    exit 1
fi

echo "Step 1: Creating virtual environment..."
if [ ! -d "venv" ]; then
    # Prefer Windows 'py' launcher when available to create a venv with the correct Python
    if command -v py >/dev/null 2>&1; then
        py -3 -m venv venv
    else
        python -m venv venv
    fi
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

echo ""
echo "Step 2: Activating virtual environment..."
# Try both Windows and Unix activation scripts
if [ -f "venv/Scripts/activate" ]; then
    # Git Bash / MSYS style
    source venv/Scripts/activate
elif [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "Warning: virtualenv activation script not found, proceeding without activation"
fi
echo "✓ Virtual environment activated (if available)"

echo ""
echo "Step 3: Installing dependencies..."
# Use py -m pip on Windows if available to avoid ambiguous pip executable
if command -v py >/dev/null 2>&1; then
    py -3 -m pip install -q -r requirements.txt
else
    pip install -q -r requirements.txt
fi
echo "✓ Dependencies installed"

echo ""
echo "Step 4: Initializing database..."
if command -v py >/dev/null 2>&1; then
    py -3 -c "from app.database.database import init_db; init_db(); print('✓ Database initialized')"
else
    python -c "from app.database.database import init_db; init_db(); print('✓ Database initialized')"
fi

echo ""
echo "Step 5: Starting Auth Service..."
echo "Service will run on http://localhost:8003"
echo "API Docs: http://localhost:8003/docs"
echo ""

# Silence watchfiles spam
export WATCHFILES_LOG_LEVEL=warning

if command -v py >/dev/null 2>&1; then
    py -3 main.py
else
    python main.py
fi

