#!/bin/bash

# MedReport AI Backend Startup Script

echo "🏥 MedReport AI - Starting Backend Server"
echo "========================================"

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found!"
    echo "📝 Creating .env from .env.example..."
    cp .env.example .env
    echo "✅ Please edit .env and add your GEMINI_API_KEY"
    echo ""
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python -m venv venv
    echo "✅ Virtual environment created"
    echo ""
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate || source venv/Scripts/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt --quiet

echo ""
echo "✅ Setup complete!"
echo ""
echo "🚀 Starting FastAPI server..."
echo "📍 Server will be available at: http://localhost:8000"
echo "📖 API docs at: http://localhost:8000/docs"
echo ""

# Start the server
python main.py
