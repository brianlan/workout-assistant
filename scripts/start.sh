#!/bin/bash
set -e

echo "=== Building Workout Assistant ==="

# Install frontend dependencies and build
echo "Installing frontend dependencies..."
cd frontend
npm install
echo "Building frontend..."
npm run build

# Copy build output to backend static directory
echo "Copying frontend build to backend/static/..."
rm -rf ../backend/static
cp -r dist/ ../backend/static/

# Install backend dependencies
cd ../backend
echo "Installing backend dependencies..."
pip install -e ".[dev]" 2>/dev/null || pip install -e .

# Start production server
echo "Starting Workout Assistant on port ${PORT:-8000}..."
uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
