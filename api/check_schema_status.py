"""
Check schema status script to verify the consistency between db_loaded flag and actual Neo4j data.
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

def check_schema_status(schema_id: int, db: Session):
    """
    Check the schema status by comparing db_loaded flag with actual Neo4j data.
    """
    print("-" * 80)
    print(f"Checking schema status for schema ID: {schema_id}")
    print("-" * 80)
    
    # Get schema from database
    schema_record = db.query(Schema).filter(Schema.id == schema_id).first()
    if not schema_record:
        print(f"Schema with ID {schema_id} not found")
        return False
    
    print(f"Found schema: {schema_record.name} (ID: {schema_id})")
    print(f"Current db_loaded value: {schema_record.db_loaded}")
    print(f"Has data according to database: {schema_record.db_loaded.lower() == 'yes'}")
    
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
        
        print(f"\nTotal nodes found in Neo4j: {total_nodes}")
        print(f"Has data according to Neo4j: {total_nodes > 0}")
        
        # Check if db_loaded flag is consistent with Neo4j data
        is_consistent = (schema_record.db_loaded.lower() == 'yes' and total_nodes > 0) or \
                        (schema_record.db_loaded.lower() == 'no' and total_nodes == 0)
        
        print(f"\nIs db_loaded flag consistent with Neo4j data? {'Yes' if is_consistent else 'No'}")
        
        if not is_consistent:
            print(f"INCONSISTENCY DETECTED: db_loaded is '{schema_record.db_loaded}' but Neo4j has {total_nodes} nodes")
        else:
            print(f"Status is consistent: db_loaded is '{schema_record.db_loaded}' and Neo4j has {total_nodes} nodes")
        
        return True
    except Exception as e:
        print(f"Error checking Neo4j data: {str(e)}")
        return False
    finally:
        if 'driver' in locals():
            driver.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_schema_status.py <schema_id>")
        sys.exit(1)
    
    try:
        schema_id = int(sys.argv[1])
    except ValueError:
        print("Schema ID must be an integer")
        sys.exit(1)
    
    # Get database session
    db = next(get_db())
    
    try:
        success = check_schema_status(schema_id, db)
        if success:
            print("\nSchema status check completed successfully")
        else:
            print("\nFailed to check schema status")
    finally:
        db.close()
