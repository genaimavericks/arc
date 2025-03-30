# RSW Application Deployment Guide

This document provides instructions for deploying the packaged RSW (Smart Data Intelligence) application.

## Package Contents

This package contains a pre-built version of the RSW application with the following components:

- **Frontend**: Pre-built Next.js application
- **Backend**: FastAPI-based API server
- **Configuration**: Environment templates
- **Scripts**: Deployment and startup utilities

## Deployment Steps

### 1. Prerequisites

- Linux server (Ubuntu 20.04+ recommended)
- Python 3.10+
- Node.js 18+
- Nginx or Caddy for reverse proxy (optional but recommended)

### 2. Extract the Package

```bash
# Create deployment directory
mkdir -p /opt/rsw
cd /opt/rsw

# Extract the package
tar -xzf /path/to/rsw-deployment.tar.gz
cd package
```

### 3. Configure the Application

```bash
# Copy and edit configuration
cp config/.env.template config/.env
nano config/.env
```

Required configuration settings:

```
# Basic settings
PORT=9090
DEBUG=false

# Database settings
DB_HOST=localhost
DB_PORT=5432
DB_NAME=rsw
DB_USER=rsw_user
DB_PASSWORD=your_secure_password

# Security settings
SECRET_KEY=your_secure_secret_key
JWT_SECRET=your_secure_jwt_secret
```

### 3.1. Production Environment Configuration

If you're deploying to a production environment, you should also set up the production environment file:

```bash
# Copy and edit production configuration
cp config/.env.production.sample config/.env.production
nano config/.env.production
```

Required production settings:

```
# API URL for frontend to connect to the backend
NEXT_PUBLIC_API_URL=http://<your_server_ip>:9090

# OpenAI API Key for Knowledge Graph features
OPENAI_API_KEY=<your_openai_api_key>

# Neo4j Database Configuration
NEO4J_USERNAME=neo4j
NEO4J_DB=neo4j
NEO4J_URI=bolt://<neo4j_host>:<neo4j_port>
NEO4J_PASSWORD=<neo4j_password>
```

Replace placeholder values with your actual configuration.

### 4. Deploy the Application

```bash
# Run deployment script
./deploy.sh
```

The deployment script will:
- Set up Python virtual environment
- Install required dependencies
- Prepare the application for startup

### 5. Start the Application

```bash
# Start the application
./start.sh
```

The application will be available at http://localhost:9090 (or the configured PORT).

## Production Setup

For production environments, we recommend setting up the application as a system service.

### Setting Up as a System Service

1. **Edit the service template**

```bash
# Copy and edit the service template
cp rsw.service.template /tmp/rsw.service
nano /tmp/rsw.service
```

Replace the placeholders:
- `REPLACE_WITH_YOUR_USER` with your system username
- `REPLACE_WITH_FULL_PATH_TO_PACKAGE` with the absolute path to the package directory

2. **Install the service**

```bash
# Move the service file to systemd
sudo mv /tmp/rsw.service /etc/systemd/system/rsw.service

# Reload systemd
sudo systemctl daemon-reload

# Enable and start the service
sudo systemctl enable rsw
sudo systemctl start rsw
```

3. **Check service status**

```bash
sudo systemctl status rsw
```

### Setting Up with Caddy (Recommended)

1. **Install Caddy**

```bash
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install caddy
```

2. **Configure Caddy**

```bash
sudo nano /etc/caddy/Caddyfile
```

For domain-based setup:
```
yourdomain.com {
    # Automatic HTTPS will be enabled by default
    reverse_proxy localhost:9090
}
```

For IP-based setup with external certificates:
```
{
  # Global options
  auto_https off  # Disable automatic HTTPS since we're using IP
}

:443 {
  # Use external certificates
  tls /path/to/certificate.crt /path/to/private_key.key
  
  # Reverse proxy to the application
  reverse_proxy localhost:9090
}

# Redirect HTTP to HTTPS
:80 {
  redir https://{host}{uri} permanent
}
```

3. **Start Caddy**

```bash
sudo systemctl reload caddy
sudo systemctl status caddy
```

## Troubleshooting

### Common Issues

1. **Application won't start**
   - Check logs: `sudo journalctl -u rsw -f`
   - Verify configuration in `config/.env`
   - Ensure Python dependencies are installed

2. **Database connection errors**
   - Verify database credentials in `config/.env`
   - Check if database service is running
   - Ensure database user has proper permissions

3. **Permission issues**
   - Check ownership: `sudo chown -R your_user:your_user /opt/rsw`
   - Set proper permissions: `chmod -R 755 /opt/rsw`

4. **Proxy errors**
   - Verify the application is running: `curl http://localhost:9090`
   - Check Caddy/Nginx configuration
   - Ensure firewall allows traffic on configured ports

## Updating the Application

1. Stop the service: `sudo systemctl stop rsw`
2. Back up your configuration: `cp /opt/rsw/package/config/.env /tmp/rsw-env-backup`
3. Extract the new package over the existing one
4. Restore your configuration: `cp /tmp/rsw-env-backup /opt/rsw/package/config/.env`
5. Run the deployment script: `cd /opt/rsw/package && ./deploy.sh`
6. Start the service: `sudo systemctl start rsw`

## Support

For support, please contact the RSW Team or open an issue in the GitHub repository.
