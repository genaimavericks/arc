"""
Comprehensive script to fix data loading issues.
This script will:
1. Check schema details
2. Allow updating the CSV file path
3. Test data loading
4. Update schema status
"""
import sys
import os
import json
import asyncio
from datetime import datetime
from sqlalchemy.orm import Session

# Add the parent directory to the path so we can import from api
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.models import Schema, GraphIngestionJob, get_db
from api.kginsights.loaders.data_loader import DataLoader

def check_schema_details(schema_id: int, db: Session):
    """
    Check detailed information about a schema.
    """
    print("-" * 80)
    print(f"Schema Details for ID: {schema_id}")
    print("-" * 80)
    
    # Get schema from database
    schema_record = db.query(Schema).filter(Schema.id == schema_id).first()
    if not schema_record:
        print(f"Schema with ID {schema_id} not found")
        return None
    
    print(f"Name: {schema_record.name}")
    print(f"Source ID: {schema_record.source_id}")
    print(f"Created at: {schema_record.created_at}")
    print(f"Updated at: {schema_record.updated_at}")
    print(f"db_loaded: {schema_record.db_loaded}")
    print(f"schema_generated: {schema_record.schema_generated}")
    print(f"db_id: {schema_record.db_id}")
    print(f"CSV file path: {schema_record.csv_file_path}")
    
    # Check if CSV file exists
    if schema_record.csv_file_path:
        if os.path.exists(schema_record.csv_file_path):
            print(f"CSV file exists: Yes")
            file_size = os.path.getsize(schema_record.csv_file_path)
            print(f"CSV file size: {file_size} bytes ({file_size / (1024*1024):.2f} MB)")
        else:
            print(f"CSV file exists: No")
            print(f"WARNING: CSV file does not exist at the specified path")
    else:
        print(f"CSV file path: Not specified")
    
    # Parse schema data
    try:
        schema_data = json.loads(schema_record.schema)
        
        # Print node types
        nodes = schema_data.get("nodes", [])
        print(f"\nSchema contains {len(nodes)} node types:")
        for idx, node in enumerate(nodes):
            node_label = node.get("label")
            node_props = node.get("properties", {})
            print(f"  - Node {idx+1}: {node_label} with {len(node_props)} properties")
        
        # Print relationship types
        relationships = schema_data.get("relationships", [])
        print(f"\nSchema contains {len(relationships)} relationship types:")
        for idx, rel in enumerate(relationships):
            rel_type = rel.get("type")
            source = rel.get("source") or rel.get("startNode") or rel.get("from_node")
            target = rel.get("target") or rel.get("endNode") or rel.get("to_node")
            print(f"  - Relationship {idx+1}: {source}-[{rel_type}]->{target}")
        
        return schema_record
    except json.JSONDecodeError:
        print(f"Error parsing schema JSON for schema ID {schema_id}")
        return None

def update_csv_path(schema_id: int, new_path: str, db: Session):
    """
    Update the CSV file path for a schema.
    """
    print("-" * 80)
    print(f"Updating CSV file path for schema ID: {schema_id}")
    print("-" * 80)
    
    # Get schema from database
    schema_record = db.query(Schema).filter(Schema.id == schema_id).first()
    if not schema_record:
        print(f"Schema with ID {schema_id} not found")
        return False
    
    # Update the CSV file path
    old_path = schema_record.csv_file_path
    schema_record.csv_file_path = new_path
    
    # Check if the new path exists
    if not os.path.exists(new_path):
        print(f"WARNING: The new CSV file path does not exist: {new_path}")
        print("Do you want to continue? (y/n)")
        response = input().strip().lower()
        if response != 'y':
            print("CSV path update cancelled")
            return False
    
    # Commit the changes
    try:
        db.commit()
        print(f"CSV file path updated successfully")
        print(f"Old path: {old_path}")
        print(f"New path: {new_path}")
        return True
    except Exception as e:
        db.rollback()
        print(f"Error updating CSV file path: {str(e)}")
        return False

def update_db_loaded_flag(schema_id: int, db_loaded_value: str, db: Session):
    """
    Update the db_loaded flag for a schema.
    """
    print("-" * 80)
    print(f"Updating db_loaded flag for schema ID: {schema_id}")
    print("-" * 80)
    
    # Get schema from database
    schema_record = db.query(Schema).filter(Schema.id == schema_id).first()
    if not schema_record:
        print(f"Schema with ID {schema_id} not found")
        return False
    
    # Update the db_loaded flag
    old_value = schema_record.db_loaded
    schema_record.db_loaded = db_loaded_value
    
    # Commit the changes
    try:
        db.commit()
        print(f"db_loaded flag updated successfully")
        print(f"Old value: {old_value}")
        print(f"New value: {db_loaded_value}")
        return True
    except Exception as e:
        db.rollback()
        print(f"Error updating db_loaded flag: {str(e)}")
        return False

async def test_data_loading(schema_id: int, db: Session):
    """
    Test data loading for a schema.
    """
    print("-" * 80)
    print(f"Testing data loading for schema ID: {schema_id}")
    print("-" * 80)
    
    # Get schema from database
    schema_record = db.query(Schema).filter(Schema.id == schema_id).first()
    if not schema_record:
        print(f"Schema with ID {schema_id} not found")
        return False
    
    # Check if CSV file path exists
    if not schema_record.csv_file_path:
        print(f"Schema does not have a CSV file path defined")
        print(f"Please update the CSV file path first")
        return False
    
    if not os.path.exists(schema_record.csv_file_path):
        print(f"CSV file does not exist at the specified path: {schema_record.csv_file_path}")
        print(f"Please update the CSV file path to a valid file")
        return False
    
    # Create a data loader instance
    loader = DataLoader(
        schema_id=schema_id,
        data_path=schema_record.csv_file_path,
        graph_name="default_graph",  # Use the default graph
        batch_size=1000,
        drop_existing=True  # Set to True to drop existing data before loading
    )
    
    # Load data
    print(f"Starting data loading process...")
    result = await loader.load_data(db)
    
    # Check result
    if result["status"] == "completed":
        print(f"Data loading completed successfully")
        print(f"Nodes created: {result['nodes_created']}")
        print(f"Relationships created: {result['relationships_created']}")
        
        # Verify the schema record was updated
        schema_record = db.query(Schema).filter(Schema.id == schema_id).first()
        print(f"Schema db_loaded value after loading: {schema_record.db_loaded}")
        
        if schema_record.db_loaded.lower() == 'yes':
            print("SUCCESS: Schema record was properly updated")
        else:
            print("ERROR: Schema record was not updated correctly")
            
        return True
    else:
        print(f"Data loading failed with status: {result['status']}")
        if result.get("errors"):
            print("Errors:")
            for error in result["errors"]:
                print(f"  - {error}")
        return False

async def main():
    if len(sys.argv) < 2:
        print("Usage: python fix_data_loading.py <schema_id> [command]")
        print("  - schema_id: ID of the schema to fix")
        print("  - command: Optional command to run")
        print("    - check: Check schema details (default)")
        print("    - update-path <new_path>: Update CSV file path")
        print("    - update-flag <yes|no>: Update db_loaded flag")
        print("    - load: Test data loading")
        sys.exit(1)
    
    try:
        schema_id = int(sys.argv[1])
    except ValueError:
        print("Schema ID must be an integer")
        sys.exit(1)
    
    # Get command
    command = "check"
    if len(sys.argv) > 2:
        command = sys.argv[2].lower()
    
    # Get database session
    db = next(get_db())
    
    try:
        if command == "check":
            check_schema_details(schema_id, db)
        elif command == "update-path" and len(sys.argv) > 3:
            new_path = sys.argv[3]
            update_csv_path(schema_id, new_path, db)
        elif command == "update-flag" and len(sys.argv) > 3:
            db_loaded_value = sys.argv[3].lower()
            if db_loaded_value not in ['yes', 'no']:
                print("db_loaded_value must be 'yes' or 'no'")
                sys.exit(1)
            update_db_loaded_flag(schema_id, db_loaded_value, db)
        elif command == "load":
            await test_data_loading(schema_id, db)
        else:
            print(f"Unknown command: {command}")
            print("Use 'check', 'update-path <new_path>', 'update-flag <yes|no>', or 'load'")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
