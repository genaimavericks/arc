# RSW Application Dockerfile
# Multi-stage build for optimized production image

# Stage 1: Build the Next.js frontend
FROM node:20-alpine AS frontend-builder

WORKDIR /app

# Copy package files and install dependencies
COPY package.json package-lock.json* ./
RUN npm install --legacy-peer-deps

# Copy the rest of the frontend code
COPY . .

# Build the Next.js application
RUN npm run build

# Verify the static files were built correctly
RUN ls -la /app/api/static || echo "Static directory not found after build"

# Stage 2: Build the Python backend
FROM python:3.11-slim AS backend-builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy Python requirements and install dependencies
COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 3: Final production image
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from backend-builder
COPY --from=backend-builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=backend-builder /usr/local/bin /usr/local/bin

# Create static directory if it doesn't exist
RUN mkdir -p /app/api/static

# Copy built frontend from frontend-builder
COPY --from=frontend-builder /app/api/static /app/api/static
RUN ls -la /app/api/static || echo "Static directory is empty in final image"

# Copy the backend code
COPY api /app/api
COPY docker/start-docker.sh /app/

# Update the start script to include more debugging
RUN sed -i 's/exec python -m api.main/echo "Starting FastAPI application..." \&\& python -m api.main/g' /app/start-docker.sh

# Make the start script executable
RUN chmod +x /app/start-docker.sh

# Create a non-root user to run the application
RUN useradd -m appuser
RUN chown -R appuser:appuser /app
USER appuser

# Set environment variables
ENV PYTHONPATH=/app
ENV PORT=9090
ENV HOST=0.0.0.0
ENV PYTHONUNBUFFERED=1

# Expose the application port
EXPOSE 9090

# Start the application
CMD ["/app/start-docker.sh"]
