"""
Fix schema status script to correct the discrepancy between db_loaded flag and actual Neo4j data.
This script will check if there's actual data in Neo4j and update the schema record accordingly.
"""
import sys
import os
import json
from sqlalchemy.orm import Session
from neo4j import GraphDatabase

# Add the parent directory to the path so we can import from api
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.models import Schema, get_db
from api.kginsights.neo4j_config import get_neo4j_connection_params

def fix_schema_status(schema_id: int, db: Session):
    """
    Fix the schema status by checking if there's actual data in Neo4j
    and updating the schema record accordingly.
    """
    print("-" * 80)
    print(f"Fixing schema status for schema ID: {schema_id}")
    print("-" * 80)
    
    # Get schema from database
    schema_record = db.query(Schema).filter(Schema.id == schema_id).first()
    if not schema_record:
        print(f"Schema with ID {schema_id} not found")
        return False
    
    print(f"Found schema: {schema_record.name} (ID: {schema_id})")
    print(f"Current db_loaded value: {schema_record.db_loaded}")
    
    # Parse schema data
    try:
        schema_data = json.loads(schema_record.schema)
    except json.JSONDecodeError:
        print(f"Error parsing schema JSON for schema ID {schema_id}")
        return False
    
    # Get the graph name from the schema if available
    graph_name = schema_data.get("graph_name", "default_graph")
    print(f"Using graph name: {graph_name}")
    
    # Get connection parameters for the specific graph
    connection_params = get_neo4j_connection_params(graph_name)
    if not connection_params:
        print(f"Could not get Neo4j connection parameters for graph: {graph_name}")
        return False
        
    uri = connection_params.get("uri")
    username = connection_params.get("username")
    password = connection_params.get("password")
    
    if not all([uri, username, password]):
        print(f"Missing required Neo4j connection parameters")
        return False
    
    print(f"Connecting to Neo4j at: {uri}")
    
    # Connect to Neo4j and check if there's data
    try:
        driver = GraphDatabase.driver(uri, auth=(username, password))
        
        # Check if there's any data for the node types defined in the schema
        has_data = False
        node_counts = {}
        total_nodes = 0
        
        with driver.session() as session:
            # Test connection
            try:
                session.run("RETURN 1 as test").single()
                print("Neo4j connection successful")
            except Exception as e:
                print(f"Neo4j connection failed: {str(e)}")
                return False
                
            # Count nodes for each node type
            print("\nCounting nodes for each node type:")
            print("-" * 40)
            for node_type in schema_data.get("nodes", []):
                label = node_type.get("label", "")
                if not label:
                    continue
                
                query = f"MATCH (n:{label}) RETURN count(n) as count"
                try:
                    result = session.run(query)
                    count = result.single()["count"]
                    node_counts[label] = count
                    total_nodes += count
                    print(f"Node count for {label}: {count}")
                except Exception as e:
                    print(f"Error querying node count for {label}: {str(e)}")
                    node_counts[label] = 0
            
            has_data = total_nodes > 0
        
        print(f"\nTotal nodes found: {total_nodes}")
        print(f"Has data: {has_data}")
        
        # Update the schema record
        old_value = schema_record.db_loaded
        schema_record.db_loaded = 'yes' if has_data else 'no'
        db.commit()
        
        print(f"\nSchema status updated:")
        print(f"db_loaded changed from '{old_value}' to '{schema_record.db_loaded}'")
        
        return True
    except Exception as e:
        print(f"Error checking Neo4j data: {str(e)}")
        return False
    finally:
        if 'driver' in locals():
            driver.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fix_schema_status.py <schema_id>")
        sys.exit(1)
    
    try:
        schema_id = int(sys.argv[1])
    except ValueError:
        print("Schema ID must be an integer")
        sys.exit(1)
    
    # Get database session
    db = next(get_db())
    
    try:
        success = fix_schema_status(schema_id, db)
        if success:
            print("\nSchema status fixed successfully")
        else:
            print("\nFailed to fix schema status")
    finally:
        db.close()
