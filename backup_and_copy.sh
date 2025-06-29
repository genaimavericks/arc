#!/bin/bash

# Function to display usage information
show_usage() {
    echo "Usage:"
    echo "  Backup & Copy Mode: $0 backup <source_path> <destination_path>"
    echo "  Restore Mode:       $0 restore <backup_dir> <destination_path>"
    echo ""
    echo "Examples:"
    echo "  $0 backup /path/to/source /path/to/destination"
    echo "  $0 restore /path/to/backup_20250623_220130 /path/to/destination"
    exit 1
}

# Check if the correct number of arguments are provided
if [ $# -ne 3 ]; then
    show_usage
fi

# Store operation mode and paths
OPERATION_MODE="$1"
SOURCE_PATH="$2"
DEST_PATH="$3"

# Validate operation mode
if [ "$OPERATION_MODE" != "backup" ] && [ "$OPERATION_MODE" != "restore" ]; then
    echo "Error: Operation mode must be 'backup' or 'restore'"
    show_usage
fi

# Validation based on mode
if [ "$OPERATION_MODE" = "backup" ]; then
    # In backup mode, SOURCE_PATH should be the source RSW installation
    if [ ! -d "$SOURCE_PATH" ]; then
        echo "Error: Source path '$SOURCE_PATH' does not exist or is not a directory"
        exit 1
    fi
elif [ "$OPERATION_MODE" = "restore" ]; then
    # In restore mode, SOURCE_PATH should be a backup directory
    if [ ! -d "$SOURCE_PATH" ]; then
        echo "Error: Backup directory '$SOURCE_PATH' does not exist"
        exit 1
    fi
    
    # Check if it looks like a valid backup directory
    BACKUP_DIRS_COUNT=0
    for dir in "api/data" "api/uploads" "api/kginsights/saved_schemas" "api/datapuur_ai/data" "runtime-data"; do
        if [ -d "$SOURCE_PATH/$dir" ]; then
            BACKUP_DIRS_COUNT=$((BACKUP_DIRS_COUNT + 1))
        fi
    done
    
    if [ $BACKUP_DIRS_COUNT -eq 0 ]; then
        echo "Error: '$SOURCE_PATH' doesn't appear to be a valid backup directory"
        echo "       It should contain at least one of the expected backup directories"
        exit 1
    fi
fi

# Check if destination path exists
if [ ! -d "$DEST_PATH" ]; then
    echo "Error: Destination path '$DEST_PATH' does not exist or is not a directory"
    exit 1
fi

# Variables and setup based on operation mode
if [ "$OPERATION_MODE" = "backup" ]; then
    # Generate timestamp for backups
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    BACKUP_DIR="${DEST_PATH}/rsw_backup_${TIMESTAMP}"
    
    echo "===== RSW Backup and Copy Script ====="
    echo "Mode: Backup"
    echo "Source: $SOURCE_PATH"
    echo "Destination: $DEST_PATH"
    echo "Backup Directory: $BACKUP_DIR"
    echo "Starting backup and copy process..."
    
    # Create backup directory
    mkdir -p "$BACKUP_DIR"
    if [ $? -ne 0 ]; then
        echo "Error: Failed to create backup directory"
        exit 1
    fi
elif [ "$OPERATION_MODE" = "restore" ]; then
    BACKUP_DIR="$SOURCE_PATH"
    
    echo "===== RSW Restore Script ====="
    echo "Mode: Restore"
    echo "Backup Source: $BACKUP_DIR"
    echo "Destination: $DEST_PATH"
    echo "Starting restore process..."
fi



# Function to backup a directory if it exists
backup_directory() {
    local src_dir="$1"
    local dir_name="$2"
    
    if [ -d "$DEST_PATH/$dir_name" ]; then
        echo "Backing up $dir_name to $BACKUP_DIR/$dir_name"
        mkdir -p "$BACKUP_DIR/$(dirname "$dir_name")"
        cp -R "$DEST_PATH/$dir_name" "$BACKUP_DIR/$dir_name"
        if [ $? -ne 0 ]; then
            echo "Warning: Failed to backup $dir_name"
        else
            echo "✓ Backup of $dir_name completed"
        fi
    else
        echo "Directory $dir_name does not exist in destination, no backup needed"
    fi
}

if [ "$OPERATION_MODE" = "backup" ]; then
    # Backup directories
    echo "Starting backup of directories..."
    backup_directory "$DEST_PATH/api/data" "api/data"
    backup_directory "$DEST_PATH/api/uploads" "api/uploads"
    backup_directory "$DEST_PATH/api/kginsights/saved_schemas" "api/kginsights/saved_schemas"
    backup_directory "$DEST_PATH/api/datapuur_ai/data" "api/datapuur_ai/data"
    backup_directory "$DEST_PATH/runtime-data" "runtime-data"
    echo "Backup process completed"
fi

# Function to copy directory with proper error handling
copy_directory() {
    local src_dir="$1"
    local dest_dir="$2"
    
    if [ -d "$src_dir" ]; then
        echo "Copying $src_dir to $dest_dir"
        mkdir -p "$(dirname "$dest_dir")"
        # Use rsync for better copy with progress indication
        rsync -a --info=progress2 "$src_dir" "$(dirname "$dest_dir")"
        if [ $? -ne 0 ]; then
            echo "Error: Failed to copy $src_dir to $dest_dir"
            return 1
        else
            echo "✓ Copy of $src_dir completed"
        fi
    else
        echo "Warning: Source directory $src_dir does not exist, skipping..."
    fi
    return 0
}

# Copy or restore directories based on operation mode
if [ "$OPERATION_MODE" = "backup" ]; then
    echo "Starting copy process..."
    copy_directory "$SOURCE_PATH/api/data" "$DEST_PATH/api/data"
    copy_directory "$SOURCE_PATH/api/uploads" "$DEST_PATH/api/uploads"
    copy_directory "$SOURCE_PATH/api/kginsights/saved_schemas" "$DEST_PATH/api/kginsights/saved_schemas"
    copy_directory "$SOURCE_PATH/api/datapuur_ai/data" "$DEST_PATH/api/datapuur_ai/data"
    copy_directory "$SOURCE_PATH/runtime-data" "$DEST_PATH/runtime-data"
elif [ "$OPERATION_MODE" = "restore" ]; then
    echo "Starting restore process..."
    # Restore from backup directory
    copy_directory "$BACKUP_DIR/api/data" "$DEST_PATH/api/data"
    copy_directory "$BACKUP_DIR/api/uploads" "$DEST_PATH/api/uploads"
    copy_directory "$BACKUP_DIR/api/kginsights/saved_schemas" "$DEST_PATH/api/kginsights/saved_schemas"
    copy_directory "$BACKUP_DIR/api/datapuur_ai/data" "$DEST_PATH/api/datapuur_ai/data"
    copy_directory "$BACKUP_DIR/runtime-data" "$DEST_PATH/runtime-data"
fi

# Function to validate copied directories
validate_directory() {
    local src_dir="$1"
    local dest_dir="$2"
    local dir_name="$3"
    
    if [ ! -d "$src_dir" ] && [ ! -d "$dest_dir" ]; then
        echo "Both source and destination $dir_name directories don't exist, validation skipped"
        return 0
    elif [ ! -d "$src_dir" ]; then
        echo "Source $dir_name directory doesn't exist, validation skipped"
        return 0
    elif [ ! -d "$dest_dir" ]; then
        echo "Error: Destination $dir_name directory wasn't created during copy"
        return 1
    else
        # Compare the directories using diff
        echo "Validating $dir_name..."
        diff -r "$src_dir" "$dest_dir" > /dev/null 2>&1
        if [ $? -eq 0 ]; then
            echo "✓ Validation successful: $dir_name copied correctly"
            return 0
        else
            echo "Error: Validation failed for $dir_name - differences found"
            
            # Calculate size difference for reporting
            SRC_SIZE=$(du -sh "$src_dir" | cut -f1)
            DEST_SIZE=$(du -sh "$dest_dir" | cut -f1)
            echo "  Source size: $SRC_SIZE"
            echo "  Destination size: $DEST_SIZE"
            
            # Count files for additional diagnostics
            SRC_FILES=$(find "$src_dir" -type f | wc -l)
            DEST_FILES=$(find "$dest_dir" -type f | wc -l)
            echo "  Source files: $SRC_FILES"
            echo "  Destination files: $DEST_FILES"
            
            return 1
        fi
    fi
}

# Validate copied or restored directories
echo "Starting validation process..."
VALIDATION_FAILED=0

if [ "$OPERATION_MODE" = "backup" ]; then
    # Validation for backup mode
    validate_directory "$SOURCE_PATH/api/data" "$DEST_PATH/api/data" "api/data"
    if [ $? -ne 0 ]; then VALIDATION_FAILED=1; fi

    validate_directory "$SOURCE_PATH/api/uploads" "$DEST_PATH/api/uploads" "api/uploads"
    if [ $? -ne 0 ]; then VALIDATION_FAILED=1; fi

    validate_directory "$SOURCE_PATH/api/kginsights/saved_schemas" "$DEST_PATH/api/kginsights/saved_schemas" "api/kginsights/saved_schemas"
    if [ $? -ne 0 ]; then VALIDATION_FAILED=1; fi

    validate_directory "$SOURCE_PATH/api/datapuur_ai/data" "$DEST_PATH/api/datapuur_ai/data" "api/datapuur_ai/data"
    if [ $? -ne 0 ]; then VALIDATION_FAILED=1; fi

    validate_directory "$SOURCE_PATH/runtime-data" "$DEST_PATH/runtime-data" "runtime-data"
    if [ $? -ne 0 ]; then VALIDATION_FAILED=1; fi
elif [ "$OPERATION_MODE" = "restore" ]; then
    # Validation for restore mode
    validate_directory "$BACKUP_DIR/api/data" "$DEST_PATH/api/data" "api/data"
    if [ $? -ne 0 ]; then VALIDATION_FAILED=1; fi

    validate_directory "$BACKUP_DIR/api/uploads" "$DEST_PATH/api/uploads" "api/uploads"
    if [ $? -ne 0 ]; then VALIDATION_FAILED=1; fi

    validate_directory "$BACKUP_DIR/api/kginsights/saved_schemas" "$DEST_PATH/api/kginsights/saved_schemas" "api/kginsights/saved_schemas"
    if [ $? -ne 0 ]; then VALIDATION_FAILED=1; fi

    validate_directory "$BACKUP_DIR/api/datapuur_ai/data" "$DEST_PATH/api/datapuur_ai/data" "api/datapuur_ai/data"
    if [ $? -ne 0 ]; then VALIDATION_FAILED=1; fi

    validate_directory "$BACKUP_DIR/runtime-data" "$DEST_PATH/runtime-data" "runtime-data"
    if [ $? -ne 0 ]; then VALIDATION_FAILED=1; fi
fi

# Summary
echo "===== Operation Summary ====="
if [ "$OPERATION_MODE" = "backup" ]; then
    echo "Mode: Backup"
    echo "Source: $SOURCE_PATH"
    echo "Destination: $DEST_PATH"
    echo "Backup Directory: $BACKUP_DIR"
elif [ "$OPERATION_MODE" = "restore" ]; then
    echo "Mode: Restore"
    echo "Backup Source: $BACKUP_DIR"
    echo "Destination: $DEST_PATH"
fi

if [ $VALIDATION_FAILED -eq 0 ]; then
    echo "✅ All operations completed successfully!"
    echo "✅ Validation passed: Copied content matches source"
else
    echo "⚠️ Operation completed with validation errors"
    echo "⚠️ Some directories may not have been copied correctly"
    echo "Please check the log above for details"
fi

echo ""
if [ "$OPERATION_MODE" = "backup" ]; then
    echo "In case of issues, your original data is backed up at: $BACKUP_DIR"
fi
echo "===== End of Script ====="
