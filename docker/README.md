# RSW Docker Deployment Guide

This guide provides instructions for deploying the RSW (Smart Data Intelligence) platform using Docker. The deployment includes both the Next.js frontend and Python FastAPI backend in a single container, with optional PostgreSQL database support.

## Prerequisites

- Docker installed on your server (version 20.10.0 or later recommended)
- Docker Compose installed (version 2.0.0 or later recommended)
- At least 2GB of RAM available for the containers
- Git access to the RSW repository

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/RSWdjinni/rsw.git
cd rsw
```

### 2. Configure Environment Variables (Optional)

Create a `.env` file in the project root to configure your deployment:

```bash
# Database Configuration
DB_TYPE=sqlite  # Use 'postgresql' for PostgreSQL
# PostgreSQL settings (only used if DB_TYPE=postgresql)
DB_HOST=postgres
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_secure_password
DB_NAME=rsw

# OpenAI API Key (if needed)
OPENAI_API_KEY=your_openai_api_key
```

### 3. Build and Run the Application

We've provided convenient scripts to build and run the Docker containers:

#### Building the Docker Image

```bash
cd docker
./build.sh
```

This script will:
- Check if the Docker daemon is running
- Build the RSW Docker image with all necessary dependencies
- Show the build status and final image details

#### Running the Application

```bash
cd docker
./run.sh  # Default: SQLite database
```

Or specify a database type:

```bash
# For SQLite (default)
./run.sh sqlite

# For PostgreSQL
./run.sh postgresql
```

The application will be available at http://localhost:9090

#### Other Commands

```bash
# View application logs
./run.sh logs

# Stop all containers
./run.sh stop

# Show help
./run.sh help
```

## Database Options

The RSW application supports two database options:

### 1. SQLite (Default)

- Simpler setup, no additional configuration needed
- Data stored in a file within the container volume
- Good for development and smaller deployments

### 2. PostgreSQL

- Better performance for production use
- Supports larger datasets and concurrent users
- Requires additional configuration

To use PostgreSQL:

```bash
# Run with PostgreSQL
./run.sh postgresql

# Or set the environment variable
DB_TYPE=postgresql ./run.sh
```

## Deployment Details

### Container Structure

The Docker setup uses a multi-stage build to create an optimized image:
1. **Stage 1**: Builds the Next.js frontend
2. **Stage 2**: Installs Python dependencies
3. **Stage 3**: Creates the final production image

### Docker Compose Profiles

The docker-compose.yml file uses profiles to manage service dependencies:
- `sqlite` profile: Starts only the RSW application container
- `postgresql` profile: Starts both the RSW application and PostgreSQL containers

## PostgreSQL Setup with External Data Volume

For production deployments, it's recommended to store PostgreSQL data outside the container for better data management, backup capabilities, and persistence.

### 1. Create External Data Directory

Create a directory on your host machine to store the PostgreSQL data:

```bash
# Create a directory for PostgreSQL data
mkdir -p /path/to/postgres-data

# Set appropriate permissions
chmod 700 /path/to/postgres-data
```

### 2. Update docker-compose.yml

Modify the volumes section in your docker-compose.yml to use the external directory:

```yaml
services:
  postgres:
    image: postgres:15-alpine
    container_name: rsw-postgres
    restart: unless-stopped
    environment:
      - POSTGRES_USER=${DB_USER:-postgres}
      - POSTGRES_PASSWORD=${DB_PASSWORD:-postgres}
      - POSTGRES_DB=${DB_NAME:-rsw}
    volumes:
      - /path/to/postgres-data:/var/lib/postgresql/data
    ports:
      - "5432:5432"  # Optional: expose PostgreSQL port
```

### 3. Database Backup and Restore

With the external volume, you can easily backup and restore your database:

#### Backup
```bash
pg_dump -h localhost -U postgres -d rsw > rsw_backup_$(date +%Y%m%d).sql
```

#### Restore
```bash
psql -h localhost -U postgres -d rsw < rsw_backup_20250330.sql
```

## Troubleshooting

### Common Issues

#### Docker Daemon Not Running

If you see an error about the Docker daemon not running, start Docker Desktop (on macOS/Windows) or the Docker service (on Linux):

```bash
# On macOS
open -a Docker

# On Linux
sudo systemctl start docker
```

#### Dependency Conflicts

If you encounter dependency conflicts during the build process:

1. Update your local virtual environment: `source .venv/bin/activate && pip freeze > api/requirements.txt`
2. Rebuild the Docker image: `./build.sh`

#### PostgreSQL Connection Issues

If the application can't connect to PostgreSQL:

1. Check that the PostgreSQL container is running: `docker ps | grep postgres`
2. Verify the environment variables match your PostgreSQL configuration
3. Check the application logs: `./run.sh logs`

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [PostgreSQL Docker Image](https://hub.docker.com/_/postgres)
