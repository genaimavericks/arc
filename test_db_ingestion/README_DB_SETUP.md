# PostgreSQL Setup for RSW DataPuur Testing

This guide provides instructions for setting up a PostgreSQL database to test the SQL database ingestion feature in the RSW DataPuur module. The setup includes creating a test database, populating it with sample e-commerce data, and configuring the connection.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Setup Instructions](#setup-instructions)
  - [macOS Setup](#macos-setup)
  - [Windows Setup](#windows-setup)
- [Verify Installation](#verify-installation)
- [Configure PostgreSQL for Network Connections](#configure-postgresql-for-network-connections)
- [Using the DataPuur Interface](#using-the-datapuur-interface)
- [Troubleshooting](#troubleshooting)
- [Sample Data Overview](#sample-data-overview)

## Prerequisites

- PostgreSQL 12 or later
- Basic familiarity with PostgreSQL commands
- RSW platform installed and running

## Setup Instructions

### macOS Setup

1. **Install PostgreSQL** (if not already installed):
   ```bash
   # Using Homebrew
   brew install postgresql
   
   # Start PostgreSQL service
   brew services start postgresql
   ```

2. **Create a test database**:
   ```bash
   # Connect to PostgreSQL as your system user
   psql postgres
   
   # Create the test database
   CREATE DATABASE rsw_test;
   
   # Exit the PostgreSQL prompt
   \q
   ```

3. **Run the sample data script**:
   ```bash
   # Run the SQL script to create tables and populate data
   psql -d rsw_test -f /Users/dhani/GitHub/dpk/rsw/populate_sample_data.sql
   ```

### Windows Setup

1. **Install PostgreSQL**:
   - Download the installer from [PostgreSQL Downloads](https://www.postgresql.org/download/windows/)
   - Run the installer and follow the installation wizard
   - Remember the password you set for the postgres user
   - Keep the default port (5432)
   - Complete the installation

2. **Create a test database**:
   ```bash
   # Open Windows Command Prompt or PowerShell
   
   # Connect to PostgreSQL (replace 'postgres' with your username if different)
   psql -U postgres
   
   # Enter your password when prompted
   
   # Create the test database
   CREATE DATABASE rsw_test;
   
   # Exit the PostgreSQL prompt
   \q
   ```

3. **Run the sample data script**:
   ```bash
   # Navigate to the script directory
   cd C:\path\to\rsw\directory
   
   # Run the SQL script (replace 'postgres' with your username if different)
   psql -U postgres -d rsw_test -f populate_sample_data.sql
   ```

   Alternatively, you can use pgAdmin:
   - Open pgAdmin
   - Connect to your PostgreSQL server
   - Right-click on the "rsw_test" database and select "Query Tool"
   - Open the SQL file and execute it

## Verify Installation

To verify that the data was loaded correctly:

```bash
# Connect to the test database
# macOS:
psql rsw_test

# Windows:
psql -U postgres -d rsw_test

# List all tables
\dt

# Check sample data in customers table
SELECT * FROM customers LIMIT 5;

# Check sample data in products table
SELECT * FROM products LIMIT 5;

# Check sample data in orders table 
SELECT * FROM orders LIMIT 5;

# Check sample data in order_items table
SELECT * FROM order_items LIMIT 5;

# Exit the PostgreSQL prompt
\q
```

## Configure PostgreSQL for Network Connections

### macOS Configuration

1. **Edit postgresql.conf** (typically in `/usr/local/var/postgres/postgresql.conf` for Homebrew installations):
   ```
   listen_addresses = '*'  # or 'localhost' for local-only connections
   ```

2. **Edit pg_hba.conf** (same directory):
   ```
   # Allow local connections with trust authentication
   host    all             all             127.0.0.1/32            trust
   host    all             all             ::1/128                 trust
   ```

3. **Restart PostgreSQL**:
   ```bash
   brew services restart postgresql
   ```

### Windows Configuration

1. **Edit postgresql.conf** (typically in `C:\Program Files\PostgreSQL\[version]\data\postgresql.conf`):
   ```
   listen_addresses = '*'  # or 'localhost' for local-only connections
   ```

2. **Edit pg_hba.conf** (same directory):
   ```
   # Allow local connections with password authentication
   host    all             all             127.0.0.1/32            md5
   host    all             all             ::1/128                 md5
   ```

3. **Restart PostgreSQL Service**:
   - Open Services from the Windows Control Panel
   - Find the PostgreSQL service
   - Right-click and select "Restart"
   
   Or use Command Prompt (as Administrator):
   ```cmd
   net stop postgresql
   net start postgresql
   ```

## Using the DataPuur Interface

1. **Open the RSW DataPuur Ingestion interface**
2. **Select "Database Connection"**
3. **Configure the connection**:
   - Connection Type: `postgresql`
   - Host: `localhost` (or `127.0.0.1`)
   - Port: `5432`
   - Database Name: `rsw_test`
   - Username: 
     - macOS: Your system username
     - Windows: `postgres` (or the username you created)
   - Password: 
     - macOS: Leave empty if using trust authentication
     - Windows: Your PostgreSQL password
   - Table: `customers` (or `products`, `orders`, `order_items`)
4. **Click "Test Connection"** to verify
5. **Click "Fetch Schema"** to preview the table structure
6. **Click "Start Ingestion"** to import the data

## Troubleshooting

- **Connection Failed**:
  - Ensure PostgreSQL is running
    - macOS: `brew services list`
    - Windows: Check Services application
  - Verify hostname, port, username, and password
  - Check that pg_hba.conf allows connections

- **Permission Denied**:
  - Check pg_hba.conf settings
  - Verify user permissions: `SELECT * FROM pg_roles;`
  - Try connecting with the postgres superuser

- **Table Not Found**:
  - Verify the table exists: `\dt` in psql
  - Check if you're connected to the correct database

- **Port Conflicts**:
  - Check if port 5432 is already in use
    - macOS: `lsof -i :5432`
    - Windows: `netstat -ano | findstr 5432`

- **"Trust Authentication Failed"** (macOS):
  - Edit pg_hba.conf to use `trust` for local connections

- **"Password Authentication Failed"** (Windows):
  - Double-check your password
  - Reset the PostgreSQL user password if needed

## Sample Data Overview

The sample data represents a simple e-commerce system with the following tables:

- **customers**: User accounts with contact information
- **products**: Product catalog with prices and stock levels
- **orders**: Customer orders with status and shipping information
- **order_items**: Line items for each order with quantities and prices

This structure allows for testing various database operations and relationships in the DataPuur module.
