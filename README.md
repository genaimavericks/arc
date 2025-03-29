# Smart Data Intelligence (SDI)

A comprehensive GenAI-based data intelligence platform that combines data processing with knowledge graph capabilities.

## Overview

Smart Data Intelligence (SDI) is a powerful application that integrates data ingestion, transformation, knowledge graph management, and AI-powered analytics capabilities to deliver intelligent data insights through various interfaces. The system architecture consists of two primary component groups:

1. **DataPuur** - Focused on intelligent data acquisition, transformation, profiling, and analytics
2. **KGInsight** - Specialized in knowledge graph generation, management, and exploration

Built with Next.js for the frontend and Python FastAPI for the backend, this application provides a powerful foundation for advanced data intelligence operations.

## Key Features

- **Comprehensive Data Pipeline**: End-to-end data processing, from ingestion to visualization
- **Knowledge Graph Management**: Create, visualize, and query complex knowledge graphs
- **GenAI Integration**: LLMs, RAG, and specialized agents for various tasks:
  - Intelligent data transformation and profiling
  - Automated knowledge graph schema generation
  - AI-powered analytics dashboard creation
- **Interactive Chatbots**: Natural language interfaces for both data and knowledge graph queries
- **Role-based Access**: Tailored interfaces for administrators, data engineers/scientists, executives, HR personnel, and finance teams
- **Modern React Development**: Component-based UI with comprehensive component library
- **Responsive Design**: Fully responsive interfaces using Tailwind CSS

## Technology Stack

### Frontend
- React.js with component-based responsive design
- Next.js for server-side rendering and routing
- Tailwind CSS for styling
- Radix UI and custom components for UI elements
- Interactive data visualization tools

### Backend
- FastAPI with async capabilities
- Caddy as API gateway/reverse proxy
- RESTful API design

### Data Processing
- Pandas for data manipulation and analysis
- Architecture designed for future extensibility to distributed processing

### Databases
- Redis for vector database operations and semantic search
- MongoDB for raw data storage
- MySQL for processed data and metadata
- Neo4j for knowledge graph management

## User Interfaces

The application provides several key interfaces:

### Landing Screen
Entry point to the application offering navigation to DataPuur and KGInsights components

### DataPuur Interfaces
- **Dashboard**: Overview of all datasets in the system
- **Ingestion**: Data import from various sources
- **Profiling**: Data quality analysis and insights
- **Transformation**: AI-assisted data transformation
- **Export**: Data export capabilities
- **Insights**: AI-powered analytics and visualization

### KGInsights Interfaces
- **Dashboard**: Overview of all knowledge graphs
- **Generate Schema**: AI-powered schema recommendation
- **Manage Schema**: Visual schema editor
- **Explore**: Interactive knowledge graph visualization
- **Query**: Natural language interface for graph queries

## Getting Started

### Prerequisites

- Node.js (v18+)
- Python (v3.10+)
- Git

### Local Development Setup

#### Windows Setup

1. **Clone the Repository**
   ```bash
   git clone https://github.com/RSWdjinni/rsw.git
   cd rsw
   ```

2. **Set Up Environment**
   ```bash
   # Python setup
   python -m venv .venv
   .\.venv\Scripts\activate
   pip install -r requirements.txt

   # Node.js setup
   npm install
   ```

3. **Start Development Server**
   ```bash
   # Start the combined server
   ./start.sh
   ```
   Access the application at http://localhost:9090

#### Mac Setup

1. **Clone the Repository**
   ```bash
   git clone https://github.com/RSWdjinni/rsw.git
   cd rsw
   ```

2. **Set Up Environment**
   ```bash
   # Python setup
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt

   # Node.js setup
   npm install
   ```

3. **Start Development Server**
   ```bash
   # Start the combined server
   ./start.sh
   ```
   Access the application at http://localhost:9090

## Deployment

### Ubuntu Server Deployment

1. **Install Dependencies**
   ```bash
   sudo apt update && sudo apt upgrade -y
   sudo apt install -y python3-pip python3-venv nodejs npm nginx
   sudo npm install -g pm2
   ```

2. **Set Up Application**
   ```bash
   # Clone repository
   git clone https://github.com/RSWdjinni/rsw.git
   cd rsw

   # Python setup
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt

   # Node.js setup
   npm install
   npm run build
   ```

   ### Cloning a Private Repository

   If the repository is private, you'll need to set up authentication:

   #### Option 1: Using SSH Keys (Recommended)

   1. Generate an SSH key on your server:
      ```bash
      ssh-keygen -t ed25519 -C "your_email@example.com"
      ```

   2. Add the public key to your GitHub account:
      ```bash
      # Display the public key to copy
      cat ~/.ssh/id_ed25519.pub
      ```
      Then add this key to your GitHub account under Settings > SSH and GPG keys

   3. Clone using SSH URL:
      ```bash
      git clone git@github.com:RSWdjinni/rsw.git
      cd rsw
      ```

   #### Option 2: Using Personal Access Token

   1. Create a Personal Access Token in GitHub (Settings > Developer settings > Personal access tokens)

   2. Clone using HTTPS with token:
      ```bash
      git clone https://USERNAME:TOKEN@github.com/RSWdjinni/rsw.git
      cd rsw
      ```
      Replace USERNAME with your GitHub username and TOKEN with your personal access token

   #### Option 3: Using GitHub CLI

   1. Install GitHub CLI:
      ```bash
      sudo apt install gh
      ```

   2. Authenticate with GitHub:
      ```bash
      gh auth login
      ```
      Follow the prompts to authenticate

   3. Clone the repository:
      ```bash
      gh repo clone RSWdjinni/rsw
      cd rsw
      ```

### Deployment with Caddy (Ubuntu)

Caddy is a modern web server with automatic HTTPS certificate provisioning.

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

   For IP address with external certificates:
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

   ### Creating Self-Signed Certificates for IP Address

   If you don't have certificates, you can create self-signed ones:

   ```bash
   # Install OpenSSL if not already installed
   sudo apt install -y openssl

   # Create directory for certificates
   sudo mkdir -p /etc/ssl/rsw

   # Generate private key
   sudo openssl genrsa -out /etc/ssl/rsw/server.key 2048

   # Create self-signed certificate (include your IP in the SAN)
   sudo openssl req -new -x509 -key /etc/ssl/rsw/server.key -out /etc/ssl/rsw/server.crt -days 3650 -subj "/CN=RSW Application" -addext "subjectAltName = IP:YOUR_SERVER_IP"

   # Set proper permissions
   sudo chmod 400 /etc/ssl/rsw/server.key
   sudo chmod 444 /etc/ssl/rsw/server.crt
   ```

   Then update your Caddyfile to use these certificates:
   ```
   {
     auto_https off
   }

   :443 {
     tls /etc/ssl/rsw/server.crt /etc/ssl/rsw/server.key
     reverse_proxy localhost:9090
   }

   :80 {
     redir https://{host}{uri} permanent
   }
   ```

   For certificate chains or different formats:
   ```
   yourdomain.com {
       # Certificate with full chain (PEM format)
       tls /path/to/fullchain.pem /path/to/private_key.key
       
       # Optional: Configure TLS settings
       tls {
           # Minimum TLS version
           min_version 1.2
           
           # Specify cipher suites (if needed)
           # cipher_suites TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384 TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384
       }
       
       # Reverse proxy to the application
       reverse_proxy localhost:9090
   }
   ```

3. **Start Caddy Service**
   ```bash
   sudo systemctl reload caddy
   sudo systemctl status caddy
   ```

4. **Start Application with PM2**
   ```bash
   # Start the application
   pm2 start "./start.sh" --name rsw
   pm2 save
   pm2 startup
   ```

5. **Verify Setup**
   - Visit https://yourdomain.com
   - Caddy automatically provisions and renews HTTPS certificates

## Creating a Deployable Package

The RSW project includes a build script that creates a configurable and deployable package for easier distribution and deployment.

### Building the Package

1. **Using the Automated Build Script**
   ```bash
   # Make the build script executable
   chmod +x build-package.sh
   
   # Run the build script
   ./build-package.sh
   ```

   This script will:
   - Create a structured package directory
   - Build optimized frontend assets
   - Copy backend code and configuration templates
   - Create deployment and startup scripts
   - Package everything into a single archive (`rsw-deployment.tar.gz`)

2. **Package Contents**
   The generated package includes:
   - Frontend assets (built with Next.js)
   - Backend API code
   - Configuration templates
   - Deployment scripts
   - Startup scripts

### Deploying the Package

1. **Transfer the Package**
   ```bash
   # Using SCP
   scp rsw-deployment.tar.gz user@server:/path/to/deployment/
   
   # Or using SFTP
   sftp user@server
   put rsw-deployment.tar.gz /path/to/deployment/
   ```

2. **Extract and Configure**
   ```bash
   # On the server
   mkdir -p /opt/rsw
   cd /opt/rsw
   tar -xzf /path/to/rsw-deployment.tar.gz
   cd package
   
   # Run the deployment script
   ./deploy.sh
   
   # Edit configuration when prompted
   nano config/.env
   
   # Run deploy script again after configuration
   ./deploy.sh
   ```

3. **Start the Application**
   ```bash
   # Start the application
   ./start.sh
   ```

4. **Set Up as a Service (Optional)**
   ```bash
   # Create systemd service file
   sudo nano /etc/systemd/system/rsw.service
   ```
   
   Add the following content:
   ```
   [Unit]
   Description=RSW Application
   After=network.target
   
   [Service]
   User=your_user
   WorkingDirectory=/opt/rsw/package
   ExecStart=/opt/rsw/package/start.sh
   Restart=always
   RestartSec=5
   StandardOutput=journal
   StandardError=journal
   SyslogIdentifier=rsw
   
   [Install]
   WantedBy=multi-user.target
   ```
   
   Enable and start the service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable rsw
   sudo systemctl start rsw
   ```

5. **Monitor the Application**
   ```bash
   # Check service status
   sudo systemctl status rsw
   
   # View logs
   sudo journalctl -u rsw -f
   ```

### Setting Up with Caddy (Recommended)

For production environments, we recommend using Caddy as a reverse proxy with HTTPS.

1. **Install Caddy**
   ```bash
   sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
   curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
   curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
   sudo apt update
   sudo apt install caddy
   ```

2. **Configure Caddy for IP-based Access with External Certificates**
   ```bash
   sudo nano /etc/caddy/Caddyfile
   ```
   
   Add the following configuration:
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

### Troubleshooting Common Deployment Issues

1. **Application Won't Start**
   - Check logs: `sudo journalctl -u rsw -f`
   - Verify configuration in `config/.env`
   - Ensure Python dependencies are installed

2. **Module Import Errors**
   - Ensure the package structure is intact
   - Check if all required Python packages are installed
   - Verify Python version (Python 3.10+ recommended)

3. **Permission Issues**
   - Check ownership: `sudo chown -R your_user:your_user /opt/rsw`
   - Set proper permissions: `chmod -R 755 /opt/rsw`
   - Ensure start.sh is executable: `chmod +x start.sh`

For more detailed deployment instructions, refer to the `PACKAGE_README.md` file included in the deployment package.

## Security Considerations

- User authentication with role-based access control
- API Gateway for centralized security management
- Secure data processing and storage

## Troubleshooting

### Common Issues and Solutions

1. **Database Connection Errors**
   - Verify database credentials in `.env` file
   - Check if database service is running

2. **API Authentication Failures**
   - Ensure JWT secret is properly configured
   - Check token expiration settings

3. **Frontend Build Errors**
   - Clear npm cache: `npm cache clean --force`
   - Delete node_modules and reinstall: `rm -rf node_modules && npm install`

4. **Permission Issues on Ubuntu**
   - Ensure proper ownership: `sudo chown -R $USER:$USER /path/to/app`
   - Set correct permissions: `chmod -R 755 /path/to/app`

## License

[Your license information here]

## Contributors

RSW Team
