#!/bin/bash
# Neo4j Admin Import Script for Ubuntu Linux and macOS
# This script automates the process of importing CSV data into Neo4j using neo4j-admin import tool

# Exit on error
set -e

# --- Detect Operating System ---
PLATFORM="unknown"
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    PLATFORM="linux"
    echo "Detected Linux operating system"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    PLATFORM="mac"
    echo "Detected macOS operating system"
else
    echo "Unsupported operating system: $OSTYPE"
    exit 1
fi

# --- Set Default Values Based on Platform ---
if [[ "$PLATFORM" == "linux" ]]; then
    # Ubuntu defaults
    NEO4J_HOME=${NEO4J_HOME:-/var/lib/neo4j}
    NEO4J_BIN=${NEO4J_BIN:-/usr/bin}
    DEFAULT_USER="neo4j"
    FORCE_SUDO=true
elif [[ "$PLATFORM" == "mac" ]]; then
    # macOS Homebrew defaults
    NEO4J_HOME=${NEO4J_HOME:-/opt/homebrew/var/neo4j}
    NEO4J_BIN=${NEO4J_BIN:-/opt/homebrew/bin}
    DEFAULT_USER=$(whoami)
    FORCE_SUDO=false
fi

# Directory containing CSV files to import
IMPORT_DIR=${IMPORT_DIR:-""}

# Database name (Community Edition only supports neo4j as the default database)
DATABASE_NAME=${DATABASE_NAME:-"anifactory"}

# Flag to force import (overwrite existing database)
FORCE_IMPORT=false

# Print usage information
function print_usage {
    echo "Usage: $0 [OPTIONS]"
    echo "Options:"
    echo "  -h, --help                 Show this help message"
    echo "  -d, --import-dir DIR       Directory containing CSV files (REQUIRED)"
    echo "  -n, --neo4j-home DIR       Neo4j home directory (default: $NEO4J_HOME)"
    echo "  -b, --neo4j-bin DIR        Neo4j bin directory (default: $NEO4J_BIN)"
    echo "  -f, --force                Force import (will delete existing database)"
    echo "  -db, --database NAME       Database name (default: anifactory)"
    echo "  --sudo                     Force using sudo for all commands (for Linux systems)"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        -h|--help)
            print_usage
            exit 0
            ;;
        -d|--import-dir)
            IMPORT_DIR="$2"
            shift 2
            ;;
        -n|--neo4j-home)
            NEO4J_HOME="$2"
            shift 2
            ;;
        -b|--neo4j-bin)
            NEO4J_BIN="$2"
            shift 2
            ;;
        -f|--force)
            FORCE_IMPORT=true
            shift
            ;;
        -db|--database)
            DATABASE_NAME="$2"
            shift
            shift
            ;;
        --sudo)
            FORCE_SUDO=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            print_usage
            exit 1
            ;;
    esac
done

# Validate required parameters
if [ -z "$IMPORT_DIR" ]; then
    echo "Error: Import directory not specified"
    print_usage
    exit 1
fi

# Validate required directories
if [ ! -d "$IMPORT_DIR" ]; then
    echo "Error: Import directory '$IMPORT_DIR' does not exist"
    exit 1
fi

if [ ! -d "$NEO4J_HOME" ]; then
    echo "Error: Neo4j home directory '$NEO4J_HOME' does not exist"
    exit 1
fi

# Check if Neo4j bin directory exists
if [ ! -d "$NEO4J_BIN" ]; then
    echo "Warning: Neo4j bin directory '$NEO4J_BIN' does not exist"
    echo "Attempting to find neo4j-admin in PATH"
    if ! command -v neo4j-admin &> /dev/null; then
        echo "Error: neo4j-admin command not found in PATH"
        exit 1
    else
        NEO4J_ADMIN="neo4j-admin"
    fi
else
    NEO4J_ADMIN="$NEO4J_BIN/neo4j-admin"
fi

# Check if we need sudo access (Linux typically requires it)
if [[ "$PLATFORM" == "linux" && "$FORCE_SUDO" == true && "$(id -u)" != "0" ]]; then
    echo "This script might need root access on Linux"
    echo "If you encounter permission errors, please run with sudo"
fi

# Function to stop Neo4j service based on platform
function stop_neo4j {
    echo "Stopping Neo4j service..."
    if [[ "$PLATFORM" == "linux" ]]; then
        # Use direct neo4j command instead of systemctl
        sudo neo4j stop
        
        # Verify Neo4j has stopped
        if pgrep -f "neo4j" > /dev/null; then
            echo "Neo4j is still running. Waiting a bit longer..."
            sleep 5
            if pgrep -f "neo4j" > /dev/null; then
                echo "Warning: Neo4j may still be running"
            fi
        else
            echo "Neo4j has been stopped successfully"
        fi
    elif [[ "$PLATFORM" == "mac" ]]; then
        if brew services list | grep neo4j | grep started > /dev/null; then
            brew services stop neo4j
        else
            echo "Neo4j service is not running"
        fi
    fi
    
    # Wait for Neo4j to fully stop
    echo "Waiting for Neo4j to stop completely..."
    sleep 10
}

# Function to start Neo4j service based on platform
function start_neo4j {
    echo "Starting Neo4j service..."
    if [[ "$PLATFORM" == "linux" ]]; then
        # Use direct neo4j command instead of systemctl
        sudo neo4j start
        
        # Verify Neo4j has started
        sleep 5
        if ! pgrep -f "neo4j" > /dev/null; then
            echo "Warning: Neo4j may not have started properly"
        else
            echo "Neo4j has been started successfully"
        fi
    elif [[ "$PLATFORM" == "mac" ]]; then
        brew services start neo4j
    fi
    
    # Wait for Neo4j to fully start
    echo "Waiting for Neo4j to start completely..."
    sleep 15
}

# Function to restart Neo4j service based on platform
function restart_neo4j {
    echo "Restarting Neo4j service to ensure all changes are applied..."
    if [[ "$PLATFORM" == "linux" ]]; then
        # Use direct neo4j command instead of systemctl
        sudo neo4j restart
        
        # Verify Neo4j has restarted
        sleep 5
        if ! pgrep -f "neo4j" > /dev/null; then
            echo "Warning: Neo4j may not have restarted properly"
            echo "Attempting to start Neo4j explicitly..."
            sudo neo4j start
            sleep 5
        else
            echo "Neo4j has been restarted successfully"
        fi
    elif [[ "$PLATFORM" == "mac" ]]; then
        brew services restart neo4j
    fi
    
    # Wait for Neo4j to fully restart
    echo "Waiting for Neo4j to restart completely..."
    sleep 20
}

# Function to check if database directory exists
function check_database {
    DB_DIR="$NEO4J_HOME/data/databases/$DATABASE_NAME"
    if [ -d "$DB_DIR" ]; then
        if [ "$FORCE_IMPORT" = true ]; then
            echo "Database directory exists. Force flag is set. Will remove existing database."
            return 0
        else
            echo "Error: Database directory already exists at $DB_DIR"
            echo "Use --force to overwrite the existing database"
            return 1
        fi
    fi
    return 0
}

# Function to clean existing database
function clean_database {
    if [ "$FORCE_IMPORT" = true ]; then
        DB_DIR="$NEO4J_HOME/data/databases/$DATABASE_NAME"
        if [ -d "$DB_DIR" ]; then
            echo "Removing existing database at $DB_DIR"
            
            # Use sudo on Linux if needed
            if [[ "$PLATFORM" == "linux" && "$FORCE_SUDO" == true ]]; then
                sudo rm -rf "$DB_DIR"
            else
                rm -rf "$DB_DIR"
            fi
        fi
        
        # Also remove transaction logs
        TX_DIR="$NEO4J_HOME/data/transactions/$DATABASE_NAME"
        if [ -d "$TX_DIR" ]; then
            echo "Removing transaction logs at $TX_DIR"
            
            # Use sudo on Linux if needed
            if [[ "$PLATFORM" == "linux" && "$FORCE_SUDO" == true ]]; then
                sudo rm -rf "$TX_DIR"
            else
                rm -rf "$TX_DIR"
            fi
        fi
    fi
}

# Find all node CSV files in the import directory
function find_node_files {
    echo "Finding node CSV files..."
    NODE_FILES=()
    NODE_FILES_BASENAME=()
    for file in "$IMPORT_DIR"/*_nodes.csv; do
        if [ -f "$file" ]; then
            NODE_FILES+=("$file")
            NODE_FILES_BASENAME+=($(basename "$file"))
            echo "  Found node file: $(basename "$file")"
        fi
    done
    
    if [ ${#NODE_FILES[@]} -eq 0 ]; then
        echo "Error: No node files found in $IMPORT_DIR"
        echo "Node files should be named <label>_nodes.csv"
        exit 1
    fi
}

# Find relationship CSV file in the import directory
function find_relationship_file {
    echo "Finding relationship CSV file..."
    REL_FILE="$IMPORT_DIR/relationships.csv"
    REL_FILE_BASENAME="relationships.csv"
    if [ ! -f "$REL_FILE" ]; then
        echo "Error: Relationship file not found at $REL_FILE"
        exit 1
    fi
    echo "  Found relationship file: $REL_FILE_BASENAME"
}

# Import the database using neo4j-admin import
function import_database {
    echo "Importing database using neo4j-admin import..."
    
    # Build command with full paths to files (don't change directory)
    IMPORT_CMD="$NEO4J_ADMIN database import full"
    
    # Add node files with full paths
    for file in "${NODE_FILES[@]}"; do
        IMPORT_CMD="$IMPORT_CMD --nodes=$file"
    done
    
    # Add relationship file with full path
    IMPORT_CMD="$IMPORT_CMD --relationships=$REL_FILE"
    
    # Add delimiter options
    IMPORT_CMD="$IMPORT_CMD --multiline-fields=true --delimiter=\",\" --array-delimiter=\";\""
    
    # Add verbose flag for detailed error output
    IMPORT_CMD="$IMPORT_CMD --verbose"
    
    # Add database name as positional argument
    IMPORT_CMD="$IMPORT_CMD $DATABASE_NAME"
    
    # Execute the import command
    echo "Executing: $IMPORT_CMD"
    if [[ "$PLATFORM" == "linux" && "$FORCE_SUDO" == true ]]; then
        sudo bash -c "$IMPORT_CMD"
    else
        eval "$IMPORT_CMD"
    fi
    
    # Store the exit code
    IMPORT_EXIT_CODE=$?
    
    # Check if import was successful
    if [ $IMPORT_EXIT_CODE -ne 0 ]; then
        echo "Error: Import failed with exit code $IMPORT_EXIT_CODE"
        exit $IMPORT_EXIT_CODE
    fi
}

# Fix ownership and permissions
function fix_permissions {
    echo "Fixing ownership and permissions..."
    if [[ "$PLATFORM" == "linux" && "$FORCE_SUDO" == true ]]; then
        sudo chown -R $DEFAULT_USER:$DEFAULT_USER "$NEO4J_HOME/data"
        sudo chmod -R 755 "$NEO4J_HOME/data"
    elif [[ "$PLATFORM" == "mac" ]]; then
        # On macOS, adjust permissions if needed
        chmod -R 755 "$NEO4J_HOME/data"
    fi
}

# Set the default database (for Neo4j 4.x+)
function set_default_database {
    echo "Setting $DATABASE_NAME as the default database..."
    # Find neo4j.conf
    NEO4J_CONF=""
    if [[ "$PLATFORM" == "linux" ]]; then
        NEO4J_CONF="/etc/neo4j/neo4j.conf"
    elif [[ "$PLATFORM" == "mac" ]]; then
        NEO4J_CONF="/opt/homebrew/Cellar/neo4j/2025.04.0/libexec/conf/neo4j.conf"
    fi

    if [ -f "$NEO4J_CONF" ]; then
        echo "Found Neo4j configuration at $NEO4J_CONF"
        
        # Use sudo on Linux if needed
        if [[ "$PLATFORM" == "linux" && "$FORCE_SUDO" == true ]]; then
            sudo sed -i 's/#*initial.dbms.default_database=.*/initial.dbms.default_database='$DATABASE_NAME'/' "$NEO4J_CONF"
        elif [[ "$PLATFORM" == "mac" ]]; then
            # macOS requires a different sed syntax
            sed -i '' 's/#*initial.dbms.default_database=.*/initial.dbms.default_database='$DATABASE_NAME'/' "$NEO4J_CONF"
        fi
    else
        echo "Warning: Could not find Neo4j configuration file"
        echo "You may need to manually set $DATABASE_NAME as the default database"
    fi
}

# Main execution flow
echo "=== Neo4j Admin Import Script ==="
echo "Platform: $PLATFORM"
echo "Import directory: $IMPORT_DIR"
echo "Neo4j home: $NEO4J_HOME"
echo "Neo4j bin: $NEO4J_BIN"
echo "Database name: $DATABASE_NAME"

# Check if database already exists
check_database || exit 1

# Stop Neo4j service
stop_neo4j

# Clean existing database if force flag is set
clean_database

# Find CSV files
find_node_files
find_relationship_file

# Import database
import_database

# Fix permissions
fix_permissions

# Set default database
set_default_database

# Start Neo4j service
start_neo4j

# Restart Neo4j service to ensure all changes are applied
restart_neo4j

echo "=== Import completed successfully ==="
echo "You can now access your data at http://localhost:7474/"
echo "Use username: neo4j, and the password you set during installation"
echo "Remember to create appropriate indexes for better performance."
