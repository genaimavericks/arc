#!/bin/bash
# Script to build and run RSW Docker containers

# Set default values
DB_TYPE=${DB_TYPE:-sqlite}
ACTION=${1:-help}

# Display help
show_help() {
  echo "RSW Docker Build and Run Script"
  echo "-------------------------------"
  echo "Usage: ./build-and-run.sh [action]"
  echo ""
  echo "Actions:"
  echo "  build       - Build the RSW Docker image"
  echo "  run         - Run the RSW application with the configured database"
  echo "  run-sqlite  - Run the RSW application with SQLite database"
  echo "  run-pg      - Run the RSW application with PostgreSQL database"
  echo "  stop        - Stop all running containers"
  echo "  logs        - Show logs from the RSW application container"
  echo "  help        - Show this help message"
  echo ""
  echo "Environment variables:"
  echo "  DB_TYPE     - Database type (sqlite or postgresql)"
  echo ""
  echo "Examples:"
  echo "  ./build-and-run.sh build      # Build the Docker image"
  echo "  ./build-and-run.sh run-pg     # Run with PostgreSQL"
  echo "  ./build-and-run.sh logs       # Show application logs"
}

# Build the Docker image
build_image() {
  echo "Building RSW Docker image..."
  docker build -t rsw-app:latest -f Dockerfile ..
  echo "Build complete!"
}

# Run the application with the configured database
run_app() {
  echo "Starting RSW application with $DB_TYPE database..."
  if [ "$DB_TYPE" = "postgresql" ] || [ "$DB_TYPE" = "postgres" ]; then
    docker-compose up -d
  else
    docker-compose up -d rsw-app
  fi
  echo "Application started! Available at http://localhost:9090"
}

# Run the application with SQLite
run_sqlite() {
  export DB_TYPE=sqlite
  echo "Starting RSW application with SQLite database..."
  docker-compose up -d rsw-app
  echo "Application started! Available at http://localhost:9090"
}

# Run the application with PostgreSQL
run_pg() {
  export DB_TYPE=postgresql
  echo "Starting RSW application with PostgreSQL database..."
  docker-compose up -d
  echo "Application started! Available at http://localhost:9090"
}

# Stop all containers
stop_app() {
  echo "Stopping all RSW containers..."
  docker-compose down
  echo "All containers stopped!"
}

# Show logs
show_logs() {
  echo "Showing logs from RSW application container..."
  docker-compose logs -f rsw-app
}

# Main script logic
case "$ACTION" in
  build)
    build_image
    ;;
  run)
    run_app
    ;;
  run-sqlite)
    run_sqlite
    ;;
  run-pg)
    run_pg
    ;;
  stop)
    stop_app
    ;;
  logs)
    show_logs
    ;;
  *)
    show_help
    ;;
esac
