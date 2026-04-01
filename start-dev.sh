#!/bin/bash

echo "========================================"
echo "  MedReport AI - Development Setup"
echo "========================================"
echo ""

echo "[1/2] Starting Backend..."
cd backend
python3 main.py &
BACKEND_PID=$!
cd ..

sleep 3

echo "[2/2] Starting Frontend..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "========================================"
echo "  Both servers are running!"
echo "  Backend: http://localhost:8000"
echo "  Frontend: http://localhost:3000"
echo "========================================"
echo ""
echo "Press Ctrl+C to stop both servers"

# Wait for Ctrl+C
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait
