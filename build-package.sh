#!/bin/bash

# RSW Application Packager
# This script creates a deployable package of the RSW application

# Exit on any error
set -e

echo "=== RSW Application Packager ==="
echo "Building deployable package..."

# Create package directory structure
echo "Creating package directory structure..."
rm -rf package
mkdir -p package/config
mkdir -p package/dist

# Copy configuration templates
echo "Copying configuration templates..."
if [ -f api/env.example ]; then
  cp api/env.example package/config/.env.template
else
  echo "WARNING: env.example not found in api folder. Creating empty template."
  touch package/config/.env.template
fi

# Copy .env.production.sample if it exists
if [ -f .env.production.sample ]; then
  cp .env.production.sample package/config/.env.production.sample
fi

# Copy scripts if they exist
if [ -d scripts ]; then
  cp -r scripts package/scripts
fi

# Build frontend
echo "Building frontend assets..."
npm run build

# Copy frontend assets
echo "Copying frontend assets..."
if [ -d .next ]; then
  cp -r .next package/dist/
else
  echo "ERROR: Frontend build failed or .next directory not found."
  exit 1
fi

if [ -d public ]; then
  cp -r public package/dist/
fi

# Copy backend code
echo "Copying backend code..."
if [ -d api ]; then
  # Create the package with the correct structure
  cp -r api package/
  
 
else
  echo "ERROR: API directory not found."
  exit 1
fi

# Copy requirements
if [ -f api/requirements.txt ]; then
  cp api/requirements.txt package/
else
  echo "WARNING: requirements.txt not found in api folder. Creating empty file."
  touch package/requirements.txt
fi

# Create deployment script
echo "Creating deployment scripts..."
cat > package/deploy.sh << 'EOF'
#!/bin/bash

# Configuration
APP_DIR=$(pwd)
CONFIG_FILE="$APP_DIR/config/.env"

# Check if configuration exists
if [ ! -f "$CONFIG_FILE" ]; then
  echo "Creating configuration file from template..."
  cp "$APP_DIR/config/.env.template" "$CONFIG_FILE"
  echo "Please edit $CONFIG_FILE with your settings"
  echo "Then run this script again"
  exit 1
fi

# Set up Python environment
echo "Setting up Python environment..."
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p uploads
mkdir -p data

# Set proper permissions
echo "Setting proper permissions..."
chmod +x start.sh

echo "RSW application is ready to start!"
echo "Run ./start.sh to launch the application"
EOF

chmod +x package/deploy.sh

# Create start script
cat > package/start.sh << 'EOF'
#!/bin/bash

# Load environment variables (skip comments and empty lines)
set -a
grep -v '^#' config/.env | grep -v '^$' | while IFS='=' read -r key value; do
  export "$key"="$value"
done
set +a

# Set default environment variables if not in .env
export HOST=${HOST:-0.0.0.0}
export PORT=${PORT:-9090}
export NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL:-"http://${HOST}:${PORT}"}

# Start the application
echo "Starting RSW application..."
source .venv/bin/activate

# Check if we're in the right directory structure
if [ -d "api" ]; then
  python -m uvicorn api.main:app --host "$HOST" --port "$PORT"
else
  # If we're already in the package directory
  cd ..
  python -m uvicorn api.main:app --host "$HOST" --port "$PORT"
fi
EOF

chmod +x package/start.sh

# Create systemd service template


# Copy package README
cp PACKAGE_README.md package/README.md

# Create archive
echo "Creating deployment archive..."
tar -czf rsw-deployment.tar.gz package/

echo "=== Package created successfully ==="
echo "Deployment archive: rsw-deployment.tar.gz"
echo "See PACKAGE_README.md for deployment instructions"
