#!/bin/bash
# Script to run the RSW Docker containers

echo "=========================================="
echo "RSW Docker Container Run Script"
echo "=========================================="

# Check if running from the docker directory
if [ ! -f "docker-compose.yml" ]; then
  echo "Error: This script must be run from the docker directory."
  echo "Please run: cd /path/to/rsw/docker && ./run.sh"
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

# Default values
DB_TYPE=${DB_TYPE:-sqlite}
ACTION=${1:-run}

# Display help function
show_help() {
  echo "Usage: ./run.sh [action] [options]"
  echo ""
  echo "Actions:"
  echo "  run         - Run the RSW application (default)"
  echo "  sqlite      - Run with SQLite database"
  echo "  postgresql  - Run with PostgreSQL database"
  echo "  stop        - Stop all running containers"
  echo "  logs        - Show logs from the RSW application container"
  echo "  help        - Show this help message"
  echo ""
  echo "Environment variables:"
  echo "  DB_TYPE     - Database type (sqlite or postgresql)"
  echo ""
  echo "Examples:"
  echo "  ./run.sh                  - Run with default database (SQLite)"
  echo "  ./run.sh sqlite           - Run with SQLite database"
  echo "  ./run.sh postgresql       - Run with PostgreSQL database"
  echo "  DB_TYPE=postgresql ./run.sh - Run with PostgreSQL database"
}

# Run the application with the configured database
run_app() {
  echo "Starting RSW application with $DB_TYPE database..."
  
  # Check if the image exists
  if ! docker images | grep -q rsw-app; then
    echo "RSW Docker image not found. Please build it first with: ./build.sh"
    exit 1
  fi
  
  if [ "$DB_TYPE" = "postgresql" ] || [ "$DB_TYPE" = "postgres" ]; then
    echo "Using PostgreSQL database..."
    docker-compose --profile postgresql up -d
  else
    echo "Using SQLite database..."
    docker-compose --profile sqlite up -d
  fi
  
  # Wait a moment for containers to start
  sleep 3
  
  # Check if containers are running
  if docker ps | grep -q rsw-app; then
    echo "=========================================="
    echo "RSW application started successfully!"
    echo "Available at: http://localhost:9090"
    echo "=========================================="
    echo "To view logs: ./run.sh logs"
    echo "To stop: ./run.sh stop"
  else
    echo "=========================================="
    echo "Error: RSW application failed to start. Check logs with: docker-compose logs"
    echo "=========================================="
    exit 1
  fi
}

# Stop all containers
stop_app() {
  echo "Stopping RSW application containers..."
  docker-compose down
  echo "Containers stopped."
}

# Show logs
show_logs() {
  echo "Showing logs from RSW application container..."
  docker-compose logs -f rsw-app
}

# Main script logic
case "$ACTION" in
  run)
    run_app
    ;;
  sqlite)
    DB_TYPE=sqlite
    run_app
    ;;
  postgresql|postgres)
    DB_TYPE=postgresql
    run_app
    ;;
  stop)
    stop_app
    ;;
  logs)
    show_logs
    ;;
  help)
    show_help
    ;;
  *)
    echo "Unknown action: $ACTION"
    show_help
    exit 1
    ;;
esac
