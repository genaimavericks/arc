#!/bin/bash

# Default values
HOST=${HOST:-127.0.0.1}
PORT=${PORT:-9090}
BUILD_FRONTEND=${BUILD_FRONTEND:-yes}

# Parse command line arguments
while [[ "$#" -gt 0 ]]; do
  case $1 in
    --host=*) HOST="${1#*=}"; shift ;;
    --port=*) PORT="${1#*=}"; shift ;;
    --build-frontend=*) BUILD_FRONTEND="${1#*=}"; shift ;;
    *) echo "Unknown parameter: $1"; exit 1 ;;
  esac
done



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

# Start the FastAPI server
echo "Starting combined server on ${HOST}:${PORT}..."
HOST=${HOST} PORT=${PORT} python -m api.run
