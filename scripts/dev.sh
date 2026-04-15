#!/bin/bash
set -e

# Install backend dependencies if needed
cd backend
pip install -e ".[dev]" 2>/dev/null || pip install -e .

# Start FastAPI in background
echo "Starting FastAPI on :8000..."
(uvicorn app.main:app --reload --port 8000) &
BACKEND_PID=$!

# Install frontend dependencies if needed
cd ../frontend
if [ ! -d "node_modules" ]; then
  echo "Installing frontend dependencies..."
  npm install
fi

# Start Vite dev server
echo "Starting Vite dev server on :5173..."
npm run dev

# Clean up backend process on exit
kill $BACKEND_PID 2>/dev/null
