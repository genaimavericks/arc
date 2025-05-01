#!/bin/bash

# Default values
HOST=${HOST:-127.0.0.1}
PORT=${PORT:-9090}
BUILD_FRONTEND=${BUILD_FRONTEND:-yes}
REDIS_HOST=${REDIS_HOST:-localhost}
REDIS_PORT=${REDIS_PORT:-6379}

# Parse command line arguments
while [[ "$#" -gt 0 ]]; do
  case $1 in
    --host=*) HOST="${1#*=}"; shift ;;
    --port=*) PORT="${1#*=}"; shift ;;
    --build-frontend=*) BUILD_FRONTEND="${1#*=}"; shift ;;
    --redis-host=*) REDIS_HOST="${1#*=}"; shift ;;
    --redis-port=*) REDIS_PORT="${1#*=}"; shift ;;
    *) echo "Unknown parameter: $1"; exit 1 ;;
  esac
done

# Check if Redis is available
echo "Checking Redis availability at ${REDIS_HOST}:${REDIS_PORT}..."
if command -v redis-cli > /dev/null; then
  if redis-cli -h ${REDIS_HOST} -p ${REDIS_PORT} ping > /dev/null 2>&1; then
    echo "Redis is available and responding!"
  else
    echo "WARNING: Redis server is not responding. Dramatiq workers may not function correctly."
    echo "Please ensure Redis is running at ${REDIS_HOST}:${REDIS_PORT}"
    exit 1
  fi
else
  echo "WARNING: redis-cli not found. Cannot verify Redis availability."
  echo "Please ensure Redis is running at ${REDIS_HOST}:${REDIS_PORT}"
  exit 1
fi

# Build frontend if requested (default is yes)
if [ "$BUILD_FRONTEND" = "yes" ]; then
  rm -rf api/static

  # Check if the static directory exists
  if [ ! -d "api/static" ] || [ ! -f "api/static/index.html" ]; then
    echo "Static files not found. Building frontend..."
    bash build-frontend.sh
  fi
else
  echo "Skipping frontend build as requested"
  
  # Ensure static directory exists even if we're not building
  if [ ! -d "api/static" ]; then
    mkdir -p api/static
  fi
fi

# Start Dramatiq workers in the background
echo "Starting Dramatiq workers..."
python -m api.datapuur_dramatiq &
DRAMATIQ_PID=$!
echo "Dramatiq workers started with PID: $DRAMATIQ_PID"

# Give workers a moment to initialize
sleep 2

# Start the FastAPI server
echo "Starting combined server on ${HOST}:${PORT}..."
HOST=${HOST} PORT=${PORT} python -m api.run

# When the main application exits, also kill the Dramatiq workers
kill $DRAMATIQ_PID 2>/dev/null
