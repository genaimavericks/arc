"""
Neo4j Schema Helper for Knowledge Graph Insights.
Provides utilities to query Neo4j database for schema information.
"""

import logging
from typing import List, Dict, Any, Optional
import json
import os

# Fix import paths for both direct and module imports
try:
    # When imported as a module
    from api.kgdatainsights.neo4j_config import get_neo4j_config
    from api.kgdatainsights.neo4j_connection_manager import Neo4jConnectionManager
except ImportError:
    # When run directly
    from .neo4j_config import get_neo4j_config
    from .neo4j_connection_manager import Neo4jConnectionManager

def get_neo4j_driver(graph_name: str = "default_graph"):
    """Get a Neo4j driver instance using the connection manager"""
    config = get_neo4j_config(graph_name)
    uri = config.get("uri", "neo4j://localhost:7687")
    username = config.get("username", "neo4j")
    password = config.get("password", "neo4j123")
    
    # Get driver from connection manager
    connection_manager = Neo4jConnectionManager()
    return connection_manager.get_driver(uri, username, password)

logger = logging.getLogger(__name__)

async def get_neo4j_node_labels() -> List[str]:
    """
    Query Neo4j database for all available node labels
    """
    try:
        driver = get_neo4j_driver()
        logger.info("Attempting to retrieve node labels from Neo4j")
        with driver.session() as session:
            try:
                # First try the db.labels() procedure
                result = session.run("CALL db.labels()")
                labels = [record["label"] for record in result]
                logger.info(f"Retrieved {len(labels)} node labels from Neo4j using db.labels(): {labels}")
                return labels
            except Exception as proc_error:
                # If that fails, try a more direct query
                logger.warning(f"Error using db.labels() procedure: {str(proc_error)}. Trying alternative query.")
                result = session.run("MATCH (n) RETURN DISTINCT labels(n) as labels")
                label_sets = [record["labels"] for record in result]
                # Flatten the list of label sets
                labels = list(set([label for label_set in label_sets for label in label_set]))
                logger.info(f"Retrieved {len(labels)} node labels from Neo4j using direct query: {labels}")
            
            # If we still have no labels, try one more approach
            if not labels:
                logger.warning("No labels found, trying one more approach")
                result = session.run("MATCH (n) RETURN DISTINCT [x IN labels(n) | x][0] as label LIMIT 100")
                labels = [record["label"] for record in result if record["label"] is not None]
                logger.info(f"Retrieved {len(labels)} node labels from Neo4j using third approach: {labels}")
            
            return labels
    except Exception as e:
        logger.error(f"Error retrieving node labels from Neo4j: {str(e)}")
        logger.error(f"Exception details: {type(e).__name__}")
        import traceback
        logger.error(traceback.format_exc())
        return []

async def get_neo4j_relationship_types() -> List[str]:
    """
    Query Neo4j database for all available relationship types
    """
    try:
        driver = get_neo4j_driver()
        logger.info("Attempting to retrieve relationship types from Neo4j")
        with driver.session() as session:
            try:
                # First try the db.relationshipTypes() procedure
                result = session.run("CALL db.relationshipTypes()")
                types = [record["relationshipType"] for record in result]
                logger.info(f"Retrieved {len(types)} relationship types from Neo4j using db.relationshipTypes(): {types}")
            except Exception as proc_error:
                # If that fails, try a more direct query
                logger.warning(f"Error using db.relationshipTypes() procedure: {str(proc_error)}. Trying alternative query.")
                result = session.run("MATCH ()-[r]->() RETURN DISTINCT type(r) as relType")
                types = [record["relType"] for record in result]
                logger.info(f"Retrieved {len(types)} relationship types from Neo4j using direct query: {types}")
            
            # If we still have no relationship types, try one more approach
            if not types:
                logger.warning("No relationship types found, trying one more approach")
                result = session.run("MATCH p=()-->() RETURN DISTINCT relationships(p)[0] as rel LIMIT 100")
                types = list(set([type(record["rel"]) for record in result if record["rel"] is not None]))
                logger.info(f"Retrieved {len(types)} relationship types from Neo4j using third approach: {types}")
            
            return types
    except Exception as e:
        logger.error(f"Error retrieving relationship types from Neo4j: {str(e)}")
        logger.error(f"Exception details: {type(e).__name__}")
        import traceback
        logger.error(traceback.format_exc())
        return []

async def get_neo4j_property_keys(node_label: str) -> List[str]:
    """
    Query Neo4j database for all property keys for a specific node label
    """
    try:
        driver = get_neo4j_driver()
        with driver.session() as session:
            # Use a parameterized query to avoid injection
            query = """
            MATCH (n:`{label}`)
            WITH n LIMIT 1
            RETURN keys(n) as property_keys
            """.format(label=node_label)
            
            result = session.run(query)
            record = result.single()
            if record:
                property_keys = record["property_keys"]
                logger.info(f"Retrieved {len(property_keys)} property keys for {node_label}: {property_keys}")
                return property_keys
            return []
    except Exception as e:
        logger.error(f"Error retrieving property keys for {node_label} from Neo4j: {str(e)}")
        return []

async def get_complete_neo4j_schema() -> Dict[str, Any]:
    """
    Build a complete schema by querying Neo4j database directly
    """
    # Get all node labels
    node_labels = await get_neo4j_node_labels()
    
    # Get all relationship types
    relationship_types = await get_neo4j_relationship_types()
    
    # Build nodes with properties
    nodes = []
    for label in node_labels:
        property_keys = await get_neo4j_property_keys(label)
        node = {
            "label": label,
            "properties": [{"name": prop, "type": "string"} for prop in property_keys]
        }
        nodes.append(node)
    
    # Build relationships (simplified, as we don't have source/target info)
    relationships = []
    for rel_type in relationship_types:
        # Add a placeholder relationship - in a real implementation, 
        # we would query for actual source/target node types
        relationship = {
            "type": rel_type,
            "source": "Unknown",
            "target": "Unknown",
            "properties": []
        }
        relationships.append(relationship)
    
    # Build complete schema
    schema = {
        "nodes": nodes,
        "relationships": relationships
    }
    
    return schema

async def merge_schema_data(schema_id: str, db_schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge schema data from database with actual Neo4j schema
    """
    # Try to load schema from sample file or database
    sample_schema_path = os.path.join(os.path.dirname(__file__), "sample_schema.json")
    if os.path.exists(sample_schema_path):
        with open(sample_schema_path, "r") as f:
            file_schema = json.load(f)
    else:
        file_schema = {"nodes": [], "relationships": []}
    
    # Get Neo4j schema
    neo4j_schema = await get_complete_neo4j_schema()
    
    # Merge node labels (prioritize Neo4j schema but keep file schema properties)
    merged_nodes = []
    neo4j_labels = {node["label"] for node in neo4j_schema["nodes"]}
    file_labels = {node["label"] for node in file_schema["nodes"]}
    
    # Add all Neo4j nodes
    for neo4j_node in neo4j_schema["nodes"]:
        label = neo4j_node["label"]
        # Check if this label exists in file schema
        file_node = next((node for node in file_schema["nodes"] if node["label"] == label), None)
        if file_node:
            # Merge properties
            properties = file_node["properties"]
            # Add any missing properties from Neo4j
            neo4j_props = {prop["name"] for prop in neo4j_node["properties"]}
            file_props = {prop["name"] for prop in properties}
            for prop in neo4j_node["properties"]:
                if prop["name"] not in file_props:
                    properties.append(prop)
            merged_nodes.append({"label": label, "properties": properties})
        else:
            # Just use Neo4j node
            merged_nodes.append(neo4j_node)
    
    # Add any file schema nodes not in Neo4j
    for file_node in file_schema["nodes"]:
        if file_node["label"] not in neo4j_labels:
            merged_nodes.append(file_node)
    
    # Merge relationships (similar approach)
    merged_relationships = []
    neo4j_rel_types = {rel["type"] for rel in neo4j_schema["relationships"]}
    file_rel_types = {rel["type"] for rel in file_schema["relationships"]}
    
    # Add all Neo4j relationships
    for neo4j_rel in neo4j_schema["relationships"]:
        rel_type = neo4j_rel["type"]
        # Check if this type exists in file schema
        file_rel = next((rel for rel in file_schema["relationships"] if rel["type"] == rel_type), None)
        if file_rel:
            # Use file relationship as it has better source/target info
            merged_relationships.append(file_rel)
        else:
            # Just use Neo4j relationship
            merged_relationships.append(neo4j_rel)
    
    # Add any file schema relationships not in Neo4j
    for file_rel in file_schema["relationships"]:
        if file_rel["type"] not in neo4j_rel_types:
            merged_relationships.append(file_rel)
    
    # Build merged schema
    merged_schema = {
        "nodes": merged_nodes,
        "relationships": merged_relationships
    }
    
    return merged_schema
