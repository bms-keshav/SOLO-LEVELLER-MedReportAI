@echo off
echo ========================================
echo   MedReport AI - Development Setup
echo ========================================
echo.

echo [1/2] Starting Backend...
cd backend
start cmd /k "python main.py"
cd ..

timeout /t 3 /nobreak > nul

echo [2/2] Starting Frontend...
cd frontend
start cmd /k "npm run dev"
cd ..

echo.
echo ========================================
echo   Both servers are starting!
echo   Backend: http://localhost:8000
echo   Frontend: http://localhost:3000
echo ========================================
echo.
pause
