#!/bin/bash
# Market-Sync AI — Start both backend and frontend

echo "Starting Market-Sync AI..."

# Start backend
echo "Starting backend on :8000..."
cd "$(dirname "$0")"
python -m uvicorn backend.api.main:app --reload --port 8000 &
BACKEND_PID=$!

# Start frontend
echo "Starting frontend on :3000..."
cd frontend
npm run dev &
FRONTEND_PID=$!

echo ""
echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop both servers."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait
