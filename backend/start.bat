@echo off
REM MedReport AI Backend Startup Script for Windows

echo 🏥 MedReport AI - Starting Backend Server
echo ========================================

REM Check if .env file exists
if not exist .env (
    echo ⚠️  Warning: .env file not found!
    echo 📝 Creating .env from .env.example...
    copy .env.example .env
    echo ✅ Please edit .env and add your GEMINI_API_KEY
    echo.
)

REM Check if virtual environment exists
if not exist venv (
    echo 📦 Creating virtual environment...
    python -m venv venv
    echo ✅ Virtual environment created
    echo.
)

REM Activate virtual environment
echo 🔧 Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo 📥 Installing dependencies...
pip install -r requirements.txt --quiet

echo.
echo ✅ Setup complete!
echo.
echo 🚀 Starting FastAPI server...
echo 📍 Server will be available at: http://localhost:8000
echo 📖 API docs at: http://localhost:8000/docs
echo.

REM Start the server
python main.py
