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
mkdir -p package/api

# Copy configuration templates
echo "Copying configuration templates..."
if [ -f .env.example ]; then
  cp .env.example package/config/.env.template
else
  echo "WARNING: .env.example not found. Creating empty template."
  touch package/config/.env.template
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
  cp -r api package/api/
else
  echo "ERROR: API directory not found."
  exit 1
fi

# Copy requirements
if [ -f requirements.txt ]; then
  cp requirements.txt package/
else
  echo "WARNING: requirements.txt not found. Creating empty file."
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
  exit 1
fi

# Set up Python environment
echo "Setting up Python environment..."
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

echo "RSW application is ready to start!"
echo "Run ./start.sh to launch the application"
EOF

chmod +x package/deploy.sh

# Create start script
cat > package/start.sh << 'EOF'
#!/bin/bash

# Load environment variables
export $(grep -v '^#' config/.env | xargs)

# Start the application
echo "Starting RSW application..."
source .venv/bin/activate
python -m uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-9090}
EOF

chmod +x package/start.sh

# Create systemd service template
cat > package/rsw.service.template << 'EOF'
[Unit]
Description=RSW Application
After=network.target

[Service]
User=REPLACE_WITH_YOUR_USER
WorkingDirectory=REPLACE_WITH_FULL_PATH_TO_PACKAGE
ExecStart=REPLACE_WITH_FULL_PATH_TO_PACKAGE/start.sh
Restart=always
RestartSec=5
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=rsw

[Install]
WantedBy=multi-user.target
EOF

# Copy package README
cp PACKAGE_README.md package/README.md

# Create archive
echo "Creating deployment archive..."
tar -czf rsw-deployment.tar.gz package/

echo "=== Package created successfully ==="
echo "Deployment archive: rsw-deployment.tar.gz"
echo "See PACKAGE_README.md for deployment instructions"
