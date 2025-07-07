#!/bin/bash

# Memory Lane Backend Startup Script
echo "Starting Memory Lane Backend..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3 and try again."
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Set environment variables for CORS
export CORS_ORIGINS="http://localhost:3000,http://localhost:8081,http://localhost:19006"
export FLASK_ENV=development
export FLASK_DEBUG=1
export PORT=5001

# Start the backend
echo "Starting backend server on http://localhost:5001..."
echo "CORS Origins: $CORS_ORIGINS"
echo "Press Ctrl+C to stop the server"
echo ""

python3 run.py 