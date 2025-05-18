"""
Script to check schema details and CSV file path.
This provides a cleaner output of the schema information.
"""
import sys
import os
import json
from sqlalchemy.orm import Session

# Add the parent directory to the path so we can import from api
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.models import Schema, get_db

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
        return False
    
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
        
        return True
    except json.JSONDecodeError:
        print(f"Error parsing schema JSON for schema ID {schema_id}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_schema_details.py <schema_id>")
        sys.exit(1)
    
    try:
        schema_id = int(sys.argv[1])
    except ValueError:
        print("Schema ID must be an integer")
        sys.exit(1)
    
    # Get database session
    db = next(get_db())
    
    try:
        success = check_schema_details(schema_id, db)
        if not success:
            print("\nFailed to check schema details")
    finally:
        db.close()
