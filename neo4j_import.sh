#!/bin/bash
# Neo4j Admin Import Script for Ubuntu Linux and macOS
# This script automates the process of importing CSV data into Neo4j using neo4j-admin import tool

# Exit on error
set -e
NEO4J_HOME="C:\development\neo4j"
# --- Detect Operating System ---
PLATFORM="unknown"
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    PLATFORM="linux"
    echo "Detected Linux operating system"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    PLATFORM="mac"
    echo "Detected macOS operating system"
elif [[ "$OSTYPE" == "msys"* ]] || [[ "$OSTYPE" == "cygwin"* ]] || [[ "$OSTYPE" == "win32"* ]]; then
    PLATFORM="windows"
    echo "Detected Windows operating system"
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
elif [[ "$PLATFORM" == "windows" ]]; then
    # Windows defaults
    #NEO4J_HOME=${NEO4J_HOME:-"C:\Program Files\Neo4j"}
    NEO4J_HOME="C:\\development\\neo4j"
    #NEO4J_BIN=${NEO4J_BIN:-"$NEO4J_HOME\\bin"}
    NEO4J_BIN="C:\\development\\neo4j\\bin"
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
            # Convert Windows backslashes to forward slashes for bash if needed
            if [[ "$PLATFORM" == "windows" ]]; then
                IMPORT_DIR=$(echo "$IMPORT_DIR" | sed 's/\\/\//g')
            fi
            shift 2
            ;;
        -n|--neo4j-home)
            NEO4J_HOME="$2"
            # Convert Windows backslashes to forward slashes for bash if needed
            if [[ "$PLATFORM" == "windows" ]]; then
                NEO4J_HOME=$(echo "$NEO4J_HOME" | sed 's/\\/\//g')
            fi
            shift 2
            ;;
        -b|--neo4j-bin)
            NEO4J_BIN="$2"
            # Convert Windows backslashes to forward slashes for bash if needed
            if [[ "$PLATFORM" == "windows" ]]; then
                NEO4J_BIN=$(echo "$NEO4J_BIN" | sed 's/\\/\//g')
            fi
            shift 2
            ;;
        -f|--force)
            FORCE_IMPORT=true
            shift
            ;;
        -db|--database)
            DATABASE_NAME="$2"
            shift 2
            ;;
        --sudo)
            FORCE_SUDO=true
            shift
            ;;
        *)
            echo "Error: Unknown option $1"
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
        if systemctl is-active --quiet neo4j; then
            sudo systemctl stop neo4j
        else
            echo "Neo4j service is not running"
        fi
    elif [[ "$PLATFORM" == "mac" ]]; then
        if brew services list | grep neo4j | grep started > /dev/null; then
            brew services stop neo4j
        else
            echo "Neo4j service is not running"
        fi
    elif [[ "$PLATFORM" == "windows" ]]; then
        # Windows service control
        if sc query neo4j | grep RUNNING > /dev/null; then
            net stop neo4j
        else
            echo "Neo4j service is not running"
        fi
    fi
    
    # Wait for Neo4j to fully stop
    echo "Waiting for Neo4j to stop completely..."
    sleep 5
}

# Function to start Neo4j service based on platform
function start_neo4j {
    echo "Starting Neo4j service..."
    if [[ "$PLATFORM" == "linux" ]]; then
        sudo systemctl start neo4j
    elif [[ "$PLATFORM" == "mac" ]]; then
        brew services start neo4j
    elif [[ "$PLATFORM" == "windows" ]]; then
        net start neo4j
    fi
    
    # Wait for Neo4j to fully start
    echo "Waiting for Neo4j to start completely..."
    sleep 10
}

# Function to check if database directory exists
function check_database {
    if [[ "$PLATFORM" == "windows" ]]; then
        # Windows path handling
        DB_DIR="$NEO4J_HOME\\data\\databases\\$DATABASE_NAME"
        DB_DIR_UNIX=$(echo "$DB_DIR" | sed 's/\\/\//g')
    else
        DB_DIR="$NEO4J_HOME/data/databases/$DATABASE_NAME"
        DB_DIR_UNIX="$DB_DIR"
    fi
    
    if [ -d "$DB_DIR_UNIX" ]; then
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
        if [[ "$PLATFORM" == "windows" ]]; then
            # Windows path handling
            DB_DIR="$NEO4J_HOME\\data\\databases\\$DATABASE_NAME"
            DB_DIR_UNIX=$(echo "$DB_DIR" | sed 's/\\/\//g')
        else
            DB_DIR="$NEO4J_HOME/data/databases/$DATABASE_NAME"
            DB_DIR_UNIX="$DB_DIR"
        fi
        
        if [ -d "$DB_DIR_UNIX" ]; then
            echo "Removing existing database at $DB_DIR"
            
            # Use sudo on Linux if needed
            if [[ "$PLATFORM" == "linux" && "$FORCE_SUDO" == true ]]; then
                sudo rm -rf "$DB_DIR_UNIX"
            elif [[ "$PLATFORM" == "windows" ]]; then
                # Windows needs special handling for paths with spaces
                rm -rf "$DB_DIR_UNIX"
            else
                rm -rf "$DB_DIR_UNIX"
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
    echo "Finding node CSV files in $IMPORT_DIR"
    NODE_FILES=()
    
    # Find all files matching *_nodes.csv
    if [[ "$PLATFORM" == "windows" ]]; then
        # Windows path handling
        for file in "$IMPORT_DIR"/*_nodes.csv; do
            # Convert to Unix-style path for bash on Windows
            file_unix=$(echo "$file" | sed 's/\\/\//g')
            if [ -f "$file_unix" ]; then
                NODE_FILES+=("$file")
            fi
        done
    else
        for file in "$IMPORT_DIR"/*_nodes.csv; do
            if [ -f "$file" ]; then
                NODE_FILES+=("$file")
            fi
        done
    fi
    
    if [ ${#NODE_FILES[@]} -eq 0 ]; then
        echo "Error: No node CSV files found in $IMPORT_DIR"
        echo "Node files should be named like: Label_nodes.csv"
        exit 1
    fi
    
    echo "Found ${#NODE_FILES[@]} node files:"
    for file in "${NODE_FILES[@]}"; do
        echo "  - $(basename "$file")"
    done
}

# Find relationship CSV file in the import directory
function find_relationship_file {
    echo "Finding relationship CSV file in $IMPORT_DIR"
    REL_FILE=""
    
    # Check for relationships.csv
    if [[ "$PLATFORM" == "windows" ]]; then
        # Windows path handling
        rel_path="$IMPORT_DIR/relationships.csv"
        rel_path_unix=$(echo "$rel_path" | sed 's/\\/\//g')
        if [ -f "$rel_path_unix" ]; then
            REL_FILE="$IMPORT_DIR\\relationships.csv"
            echo "Found relationship file: relationships.csv"
        else
            echo "Warning: No relationship CSV file found in $IMPORT_DIR"
            echo "Relationship file should be named: relationships.csv"
        fi
    else
        if [ -f "$IMPORT_DIR/relationships.csv" ]; then
            REL_FILE="$IMPORT_DIR/relationships.csv"
            echo "Found relationship file: $(basename "$REL_FILE")"
        else
            echo "Warning: No relationship CSV file found in $IMPORT_DIR"
            echo "Relationship file should be named: relationships.csv"
        fi
    fi
}

# Import the database using neo4j-admin import
function import_database {
    echo "Importing database using neo4j-admin import..."
    
    # Build the command
    if [[ "$PLATFORM" == "windows" ]]; then
        # Windows path handling
        IMPORT_CMD="\"$NEO4J_BIN\\neo4j-admin.bat\" database import"
        if [ ! -f "$(echo "$NEO4J_BIN\\neo4j-admin.bat" | sed 's/\\/\//g')" ]; then
            # Try without .bat extension
            IMPORT_CMD="\"$NEO4J_BIN\\neo4j-admin\" database import"
        fi
    else
        IMPORT_CMD="$NEO4J_BIN/neo4j-admin database import"
    fi
    
    IMPORT_CMD="$IMPORT_CMD --database=$DATABASE_NAME"
    IMPORT_CMD="$IMPORT_CMD --delimiter=,"
    IMPORT_CMD="$IMPORT_CMD --array-delimiter=;"
    IMPORT_CMD="$IMPORT_CMD --quote=\""
    IMPORT_CMD="$IMPORT_CMD --multiline-fields=true"
    
    # Add node files
    for NODE_FILE in "${NODE_FILES[@]}"; do
        NODE_LABEL=$(basename "$NODE_FILE" | sed 's/_nodes\.csv$//')
        if [[ "$PLATFORM" == "windows" ]]; then
            # Windows needs special handling for paths with spaces
            IMPORT_CMD="$IMPORT_CMD --nodes=$NODE_LABEL=\"$NODE_FILE\""
        else
            IMPORT_CMD="$IMPORT_CMD --nodes=$NODE_LABEL=$NODE_FILE"
        fi
    done
    
    # Add relationship file if it exists
    if [ -n "$REL_FILE" ]; then
        if [[ "$PLATFORM" == "windows" ]]; then
            # Windows needs special handling for paths with spaces
            IMPORT_CMD="$IMPORT_CMD --relationships=\"$REL_FILE\""
        else
            IMPORT_CMD="$IMPORT_CMD --relationships=$REL_FILE"
        fi
    fi
    
    # Add force flag if needed
    if [ "$FORCE_IMPORT" = true ]; then
        IMPORT_CMD="$IMPORT_CMD --force"
    fi
    
    # Execute the command
    echo "Executing: $IMPORT_CMD"
    if [[ "$PLATFORM" == "linux" && "$FORCE_SUDO" == true ]]; then
        sudo $IMPORT_CMD
    elif [[ "$PLATFORM" == "windows" ]]; then
        # For Windows, use eval to handle the quotes properly
        eval $IMPORT_CMD
    else
        $IMPORT_CMD
    fi
    
    # Check if import was successful
    if [ $? -ne 0 ]; then
        echo "Error: Import failed"
        exit 1
    fi
    
    echo "Import completed successfully"
}

# Fix ownership and permissions
function fix_permissions {
    if [[ "$PLATFORM" == "linux" && "$FORCE_SUDO" == true ]]; then
        echo "Fixing ownership and permissions..."
        sudo chown -R $DEFAULT_USER:$DEFAULT_USER "$NEO4J_HOME/data/databases/$DATABASE_NAME"
        sudo chmod -R 755 "$NEO4J_HOME/data/databases/$DATABASE_NAME"
    elif [[ "$PLATFORM" == "mac" ]]; then
        echo "Fixing permissions..."
        chmod -R 755 "$NEO4J_HOME/data/databases/$DATABASE_NAME"
    elif [[ "$PLATFORM" == "windows" ]]; then
        echo "Windows permissions are handled by the system, no changes needed"
        # Windows permissions are handled differently, no need to change them manually
    fi
}

# Set the default database (for Neo4j 4.x+)
function set_default_database {
    # Only needed for Neo4j 4.x+
    if [[ "$PLATFORM" == "windows" ]]; then
        # Windows path handling
        NEO4J_CONF="$NEO4J_HOME\\conf\\neo4j.conf"
        NEO4J_CONF_UNIX=$(echo "$NEO4J_CONF" | sed 's/\\/\//g')
    else
        NEO4J_CONF="$NEO4J_HOME/conf/neo4j.conf"
        NEO4J_CONF_UNIX="$NEO4J_CONF"
    fi
    
    if [ ! -f "$NEO4J_CONF_UNIX" ]; then
        echo "Warning: Neo4j configuration file not found at $NEO4J_CONF"
        echo "You may need to manually set the default database"
        return
    fi
    
    echo "Setting $DATABASE_NAME as the default database..."
    
    # Check if the setting already exists
    if grep -q "^dbms.default_database" "$NEO4J_CONF_UNIX"; then
        # Update existing setting
        if [[ "$PLATFORM" == "linux" && "$FORCE_SUDO" == true ]]; then
            sudo sed -i "s/^dbms.default_database=.*/dbms.default_database=$DATABASE_NAME/" "$NEO4J_CONF_UNIX"
        elif [[ "$PLATFORM" == "windows" ]]; then
            # Windows sed is different
            sed -i "s/^dbms.default_database=.*/dbms.default_database=$DATABASE_NAME/" "$NEO4J_CONF_UNIX"
        else
            sed -i "s/^dbms.default_database=.*/dbms.default_database=$DATABASE_NAME/" "$NEO4J_CONF_UNIX"
        fi
    else
        # Add new setting
        if [[ "$PLATFORM" == "linux" && "$FORCE_SUDO" == true ]]; then
            echo "dbms.default_database=$DATABASE_NAME" | sudo tee -a "$NEO4J_CONF_UNIX" > /dev/null
        elif [[ "$PLATFORM" == "windows" ]]; then
            echo "dbms.default_database=$DATABASE_NAME" >> "$NEO4J_CONF_UNIX"
        else
            echo "dbms.default_database=$DATABASE_NAME" >> "$NEO4J_CONF_UNIX"
        fi
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

echo "=== Import completed successfully ==="
echo "You can now access your data at http://localhost:7474/"
echo "Use username: neo4j, and the password you set during installation"
echo "Remember to create appropriate indexes for better performance."
