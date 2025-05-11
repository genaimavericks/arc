"""
Simple script to update the db_loaded flag for a schema.
This directly updates the database without requiring Neo4j connectivity.
"""
import sys
import os

# Add the parent directory to the path so we can import from api
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.models import Schema, get_db

def update_schema_loaded_flag(schema_id, db_loaded_value='no'):
    """
    Update the db_loaded flag for a schema.
    
    Args:
        schema_id: ID of the schema to update
        db_loaded_value: Value to set for db_loaded ('yes' or 'no')
    """
    # Get database session
    db = next(get_db())
    
    try:
        # Get schema from database
        schema_record = db.query(Schema).filter(Schema.id == schema_id).first()
        if not schema_record:
            print(f"Schema with ID {schema_id} not found")
            return False
        
        print(f"Found schema: {schema_record.name} (ID: {schema_id})")
        print(f"Current db_loaded value: {schema_record.db_loaded}")
        
        # Update the schema record
        old_value = schema_record.db_loaded
        schema_record.db_loaded = db_loaded_value
        db.commit()
        
        print(f"Schema status updated:")
        print(f"db_loaded changed from '{old_value}' to '{schema_record.db_loaded}'")
        
        return True
    except Exception as e:
        print(f"Error updating schema: {str(e)}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python update_schema_loaded_flag.py <schema_id> [db_loaded_value]")
        sys.exit(1)
    
    try:
        schema_id = int(sys.argv[1])
    except ValueError:
        print("Schema ID must be an integer")
        sys.exit(1)
    
    db_loaded_value = 'no'
    if len(sys.argv) > 2:
        db_loaded_value = sys.argv[2]
        if db_loaded_value not in ['yes', 'no']:
            print("db_loaded_value must be 'yes' or 'no'")
            sys.exit(1)
    
    success = update_schema_loaded_flag(schema_id, db_loaded_value)
    if success:
        print("Schema status updated successfully")
    else:
        print("Failed to update schema status")
