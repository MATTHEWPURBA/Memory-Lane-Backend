#!/bin/bash
# Memory Lane Backend Startup Script

echo "🚀 Starting Memory Lane Backend..."

# Activate virtual environment
source venv/bin/activate

# Set environment variables
export DATABASE_URL="postgresql://postgres:Robherto82@localhost:5432/memory_lane_db"
export FLASK_ENV=development
export FLASK_APP=run.py
export PORT=5001

# Start the application
echo "✅ Database: memory_lane_db"
echo "✅ Environment: development"
echo "✅ Starting server on http://localhost:5001"
echo ""

python3 run.py 