#!/bin/bash
# Script to build the RSW Docker image

echo "=========================================="
echo "RSW Docker Image Build Script"
echo "=========================================="

# Check if running from the docker directory
if [ ! -f "Dockerfile" ]; then
  echo "Error: This script must be run from the docker directory."
  echo "Please run: cd /path/to/rsw/docker && ./build.sh"
  exit 1
fi

# Check if Docker daemon is running
if ! docker info > /dev/null 2>&1; then
  echo "Error: Docker daemon is not running."
  echo ""
  echo "Please start Docker Desktop or the Docker service before continuing."
  echo ""
  echo "On macOS:"
  echo "  - Start Docker Desktop application from Applications folder"
  echo "  - Or run: open -a Docker"
  echo ""
  echo "On Linux:"
  echo "  - Run: sudo systemctl start docker"
  echo ""
  echo "Once Docker is running, try this script again."
  echo "=========================================="
  exit 1
fi

echo "Building RSW Docker image..."
echo "This may take a few minutes..."

# Build the Docker image
docker build -t rsw-app:latest -f Dockerfile ..

# Check if build was successful
if [ $? -eq 0 ]; then
  echo "=========================================="
  echo "Build successful! RSW image is ready."
  echo "Image details:"
  docker images | grep rsw-app
  echo "=========================================="
  echo "To run the application, use: ./run.sh"
else
  echo "=========================================="
  echo "Build failed! Please check the error messages above."
  echo "=========================================="
  exit 1
fi
