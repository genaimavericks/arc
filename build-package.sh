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
  
  # Check if main.py exists in the api directory
  if [ ! -f api/main.py ]; then
    echo "WARNING: main.py not found in api directory. Creating a basic one."
    cat > package/api/main.py << 'EOF'
from fastapi import FastAPI
import os
import sys

# Add the parent directory to the path so we can import from api
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = FastAPI(title="RSW API", description="Smart Data Intelligence Platform API")

# Import and include routers
try:
    from api.datapuur import router as datapuur_router
    app.include_router(datapuur_router, prefix="/api/datapuur", tags=["datapuur"])
except ImportError as e:
    print(f"Warning: Could not import datapuur router: {e}")

@app.get("/")
async def root():
    return {"message": "Welcome to RSW API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "9090")))
EOF
  fi
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
python3.11 -m venv .venv
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

# Start the application
echo "Starting RSW application..."
source .venv/bin/activate

# Check if we're in the right directory structure
if [ -d "api" ]; then
  python -m uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-9090}
else
  # If we're already in the package directory
  cd ..
  python -m uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-9090}
fi
EOF

chmod +x package/start.sh

# Create systemd service template
# cat > package/rsw.service.template << 'EOF'
# [Unit]
# Description=RSW Application
# After=network.target

# [Service]
# User=REPLACE_WITH_YOUR_USER
# WorkingDirectory=REPLACE_WITH_FULL_PATH_TO_PACKAGE
# ExecStart=REPLACE_WITH_FULL_PATH_TO_PACKAGE/start.sh
# Restart=always
# RestartSec=5
# StandardOutput=syslog
# StandardError=syslog
# SyslogIdentifier=rsw

# [Install]
# WantedBy=multi-user.target
# EOF

# Copy package README
cp PACKAGE_README.md package/README.md

# Create archive
echo "Creating deployment archive..."
tar -czf rsw-deployment.tar.gz package/

echo "=== Package created successfully ==="
echo "Deployment archive: rsw-deployment.tar.gz"
echo "See PACKAGE_README.md for deployment instructions"
