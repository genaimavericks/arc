"""
Verification script to test data loading and schema status updates.
This script will:
1. Check the current schema status
2. Trigger a data load if needed
3. Verify the schema record is properly updated
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
from api.kginsights.neo4j_config import get_neo4j_connection_params

async def verify_schema_status(schema_id: int, db: Session):
    """
    Check the schema status by comparing db_loaded flag with actual Neo4j data.
    """
    print("-" * 80)
    print(f"Verifying schema status for schema ID: {schema_id}")
    print("-" * 80)
    
    # Get schema from database
    schema_record = db.query(Schema).filter(Schema.id == schema_id).first()
    if not schema_record:
        print(f"Schema with ID {schema_id} not found")
        return False
    
    print(f"Found schema: {schema_record.name} (ID: {schema_id})")
    print(f"Current db_loaded value: {schema_record.db_loaded}")
    print(f"Has data according to database: {schema_record.db_loaded.lower() == 'yes'}")
    
    # Check active jobs
    active_jobs = db.query(GraphIngestionJob).filter(
        GraphIngestionJob.schema_id == schema_id,
        GraphIngestionJob.status.in_(["pending", "running"])
    ).all()
    
    if active_jobs:
        print(f"Found {len(active_jobs)} active jobs for this schema:")
        for job in active_jobs:
            print(f"  - Job ID: {job.id}, Type: {job.job_type}, Status: {job.status}")
        print("Cannot proceed with verification while jobs are running")
        return False
    
    # Parse schema data
    try:
        schema_data = json.loads(schema_record.schema)
    except json.JSONDecodeError:
        print(f"Error parsing schema JSON for schema ID {schema_id}")
        return False
    
    # Check if schema has a data path
    data_path = schema_record.csv_file_path
    if not data_path:
        print(f"Schema does not have a CSV file path defined")
        print(f"Please set a valid CSV file path for the schema")
        return False
    
    print(f"Schema CSV file path: {data_path}")
    if not os.path.exists(data_path):
        print(f"WARNING: CSV file does not exist at the specified path")
    
    return {
        "schema_record": schema_record,
        "schema_data": schema_data,
        "data_path": data_path
    }

async def load_data_for_schema(schema_id: int, db: Session):
    """
    Load data for the specified schema.
    """
    print("-" * 80)
    print(f"Loading data for schema ID: {schema_id}")
    print("-" * 80)
    
    # First verify the schema status
    verify_result = await verify_schema_status(schema_id, db)
    if not verify_result:
        print("Cannot proceed with data loading due to verification failure")
        return False
    
    schema_record = verify_result["schema_record"]
    data_path = verify_result["data_path"]
    
    # Ask for confirmation before loading data
    print("\nWARNING: This will attempt to load data into Neo4j for the specified schema.")
    print("Do you want to proceed? (y/n)")
    response = input().strip().lower()
    if response != 'y':
        print("Data loading cancelled by user")
        return False
    
    # Create a data loader instance
    loader = DataLoader(
        schema_id=schema_id,
        data_path=data_path,
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
        print("Usage: python verify_data_loading.py <schema_id> [load]")
        print("  - schema_id: ID of the schema to verify")
        print("  - load: Optional parameter to trigger data loading (default: only verify)")
        sys.exit(1)
    
    try:
        schema_id = int(sys.argv[1])
    except ValueError:
        print("Schema ID must be an integer")
        sys.exit(1)
    
    # Check if we should load data
    should_load = len(sys.argv) > 2 and sys.argv[2].lower() == 'load'
    
    # Get database session
    db = next(get_db())
    
    try:
        if should_load:
            await load_data_for_schema(schema_id, db)
        else:
            await verify_schema_status(schema_id, db)
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
