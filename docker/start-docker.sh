#!/bin/bash
# Start script for RSW application in Docker
set -e  # Exit on error

echo "Starting RSW application..."

# Create log directory if it doesn't exist
mkdir -p /app/logs

# Debug information
echo "=== Environment Variables ==="
echo "DB_TYPE: $DB_TYPE"
echo "HOST: $HOST"
echo "PORT: $PORT"
echo "PYTHONPATH: $PYTHONPATH"
echo "==========================="

# Check if static directory exists and has files
echo "=== Static Files Check ==="
if [ -d "/app/api/static" ]; then
  echo "Static directory exists"
  ls -la /app/api/static
  if [ -f "/app/api/static/index.html" ]; then
    echo "index.html found in static directory"
  else
    echo "WARNING: index.html not found in static directory"
    # Create a simple index.html for testing
    echo "<html><body><h1>RSW Application</h1><p>This is a temporary index page.</p></body></html>" > /app/api/static/index.html
    echo "Created temporary index.html for testing"
  fi
else
  echo "WARNING: Static directory does not exist"
  mkdir -p /app/api/static
  echo "<html><body><h1>RSW Application</h1><p>This is a temporary index page.</p></body></html>" > /app/api/static/index.html
  echo "Created static directory and temporary index.html for testing"
fi
echo "==========================="

# Check if we're using PostgreSQL and need to wait for it
if [ "$DB_TYPE" = "postgresql" ] || [ "$DB_TYPE" = "postgres" ]; then
  echo "Using PostgreSQL database at $DB_HOST:$DB_PORT"
  
  # Wait for PostgreSQL to be ready
  echo "Waiting for PostgreSQL to be ready..."
  until PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c '\q'; do
    echo "PostgreSQL is unavailable - sleeping"
    sleep 1
  done
  
  echo "PostgreSQL is up - starting application"
else
  echo "Using SQLite database"
fi

# Check if Python modules are installed correctly
echo "=== Python Module Check ==="
python -m pip list | grep uvicorn
python -m pip list | grep fastapi
echo "==========================="

# Check if main.py exists
echo "=== File Check ==="
if [ -f "/app/api/main.py" ]; then
  echo "main.py exists"
else
  echo "ERROR: main.py not found!"
  exit 1
fi
echo "==========================="

# Start the FastAPI application
cd /app
echo "Starting FastAPI application with uvicorn..."
echo "Command: python -m uvicorn api.main:app --host $HOST --port $PORT --log-level debug"

# Run with detailed error reporting
python -m uvicorn api.main:app --host $HOST --port $PORT --log-level debug
