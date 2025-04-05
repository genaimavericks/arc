"""
Neo4j Loader for loading data from CSV files into Neo4j.
"""
import os
import json
import logging
import traceback
from typing import Dict, List, Any, Optional, Tuple
from neo4j import GraphDatabase, Driver, Session, Transaction
from ..database_api import get_database_config, parse_connection_params

class Neo4jLoader:
    """
    Handles loading data into Neo4j from processed CSV records.
    Manages Neo4j connections, transactions, and Cypher execution.
    """
    
    def __init__(self, graph_name: str = "default"):
        """
        Initialize the Neo4j loader.
        
        Args:
            graph_name: Name of the Neo4j graph to connect to
        """
        self.graph_name = graph_name
        self.logger = logging.getLogger(__name__)
        self.driver = None
        self.connection_params = None
        
    async def connect(self) -> bool:
        """
        Connect to the Neo4j database.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Get database configuration
            db_config = get_database_config()
            if not db_config:
                self.logger.error("Failed to get database configuration")
                return False
                
            # Parse connection parameters for the specified graph
            graph_config = db_config.get(self.graph_name, {})
            self.connection_params = parse_connection_params(graph_config)
            if not self.connection_params:
                self.logger.error(f"Failed to parse connection parameters for graph: {self.graph_name}")
                return False
                
            # Create Neo4j driver
            uri = self.connection_params.get("uri")
            username = self.connection_params.get("username")
            password = self.connection_params.get("password")
            
            if not all([uri, username, password]):
                self.logger.error("Missing Neo4j connection parameters")
                return False
                
            self.logger.info(f"Connecting to Neo4j at {uri}")
            self.driver = GraphDatabase.driver(uri, auth=(username, password))
            
            # Verify connection
            with self.driver.session() as session:
                result = session.run("RETURN 1 as test")
                test_value = result.single()["test"]
                if test_value != 1:
                    self.logger.error("Neo4j connection test failed")
                    return False
                    
            self.logger.info("Successfully connected to Neo4j")
            return True
            
        except Exception as e:
            self.logger.error(f"Error connecting to Neo4j: {str(e)}")
            self.logger.error(traceback.format_exc())
            return False
            
    def close(self):
        """Close the Neo4j driver connection."""
        if self.driver:
            self.driver.close()
            self.logger.info("Neo4j connection closed")
            
    def _create_node_cypher(self, label: str, properties: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """
        Create a Cypher statement for creating a node.
        
        Args:
            label: Node label
            properties: Node properties
            
        Returns:
            Tuple of (cypher_statement, parameters)
        """
        # Create parameter dict with properly formatted keys
        params = {f"prop_{k}": v for k, v in properties.items()}
        
        # Build property string for Cypher
        prop_string = ", ".join([f"{k}: ${f'prop_{k}'}" for k in properties.keys()])
        
        # Create Cypher statement
        cypher = f"CREATE (n:{label} {{{prop_string}}})"
        
        return cypher, params
        
    def _create_relationship_cypher(
        self, 
        source_label: str, 
        source_id_prop: str,
        source_id_value: Any,
        target_label: str,
        target_id_prop: str,
        target_id_value: Any,
        rel_type: str,
        rel_properties: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Create a Cypher statement for creating a relationship.
        
        Args:
            source_label: Label of source node
            source_id_prop: ID property name of source node
            source_id_value: ID value of source node
            target_label: Label of target node
            target_id_prop: ID property name of target node
            target_id_value: ID value of target node
            rel_type: Type of relationship
            rel_properties: Optional properties for the relationship
            
        Returns:
            Tuple of (cypher_statement, parameters)
        """
        params = {
            "source_id": source_id_value,
            "target_id": target_id_value
        }
        
        # Add relationship properties to params if provided
        rel_prop_string = ""
        if rel_properties:
            rel_prop_string = " {"
            for i, (k, v) in enumerate(rel_properties.items()):
                if i > 0:
                    rel_prop_string += ", "
                rel_prop_string += f"{k}: $rel_prop_{k}"
                params[f"rel_prop_{k}"] = v
            rel_prop_string += "}"
            
        # Create Cypher statement
        cypher = (
            f"MATCH (source:{source_label} {{{source_id_prop}: $source_id}}), "
            f"(target:{target_label} {{{target_id_prop}: $target_id}}) "
            f"CREATE (source)-[r:{rel_type}{rel_prop_string}]->(target)"
        )
        
        return cypher, params
        
    async def create_constraints_and_indexes(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Skip creating constraints and indexes based on schema.
        
        Args:
            schema: The schema definition
            
        Returns:
            Dict with results of constraint and index creation (always empty)
        """
        if not self.driver:
            raise ValueError("Neo4j driver not initialized. Call connect() first.")
            
        result = {
            "constraints_created": 0,
            "indexes_created": 0,
            "errors": []
        }
        
        # Skip creating constraints and indexes as requested
        self.logger.info("Skipping creation of constraints and indexes as requested")
        
        return result
        
    async def load_nodes(
        self, 
        records: List[Dict[str, Any]], 
        schema: Dict[str, Any],
        column_mapping: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Load nodes into Neo4j from CSV records.
        
        Args:
            records: List of records from CSV
            schema: The schema definition
            column_mapping: Mapping of CSV columns to node properties with metadata
            
        Returns:
            Dict with results of node loading
        """
        if not self.driver:
            raise ValueError("Neo4j driver not initialized. Call connect() first.")
            
        result = {
            "nodes_created": 0,
            "errors": []
        }
        
        # Group columns by node label
        node_properties = {}
        node_id_properties = {}
        
        # Identify which properties are likely IDs for each node label
        for column, mapping in column_mapping.items():
            node_label = mapping.get("node_label")
            if not node_label:
                continue
                
            if node_label not in node_properties:
                node_properties[node_label] = []
                node_id_properties[node_label] = []
                
            # Add to general properties
            node_properties[node_label].append({
                "csv_column": column,
                "property": mapping.get("property", column),
                "is_likely_id": mapping.get("is_likely_id", False),
                "is_likely_reference": mapping.get("is_likely_reference", False),
                "unique_count": mapping.get("unique_count", 0)
            })
            
            # If this is likely an ID property, add to ID properties
            if mapping.get("is_likely_id", False) or "id" in column.lower():
                node_id_properties[node_label].append({
                    "csv_column": column,
                    "property": mapping.get("property", column)
                })
        
        self.logger.info(f"Node ID properties: {node_id_properties}")
        
        # Track unique nodes to avoid duplicates
        unique_nodes = {}
        
        try:
            with self.driver.session() as session:
                # First pass: Create unique nodes for each node type
                for node_label, properties in node_properties.items():
                    # Skip if no ID properties found for this node type
                    if not node_id_properties.get(node_label, []):
                        self.logger.warning(f"No ID properties found for {node_label}, will create duplicate nodes")
                        continue
                    
                    # Get the primary ID property for this node type
                    id_property = node_id_properties[node_label][0]["property"]
                    id_column = node_id_properties[node_label][0]["csv_column"]
                    
                    # Track unique values for this node type
                    unique_values = set()
                    
                    # First pass to collect unique values
                    for record in records:
                        if id_column in record and record[id_column]:
                            unique_values.add(record[id_column])
                    
                    self.logger.info(f"Found {len(unique_values)} unique {node_label} nodes")
                    
                    # Create unique nodes
                    for unique_value in unique_values:
                        # Find the first record with this ID value
                        for record in records:
                            if id_column in record and record[id_column] == unique_value:
                                # Build properties dict for this node
                                node_props = {}
                                for prop in properties:
                                    csv_column = prop.get("csv_column")
                                    property_name = prop.get("property")
                                    
                                    if csv_column in record:
                                        node_props[property_name] = record[csv_column]
                                
                                # Skip if no properties
                                if not node_props:
                                    continue
                                
                                # Create node with MERGE to avoid duplicates
                                try:
                                    cypher = f"MERGE (n:{node_label} {{{id_property}: $id_value}}) "
                                    
                                    # Add SET clause for other properties
                                    if len(node_props) > 1:  # More than just the ID
                                        cypher += "SET " + ", ".join([f"n.{k} = ${k}" for k in node_props.keys() if k != id_property])
                                    
                                    # Prepare parameters
                                    params = {"id_value": unique_value}
                                    for k, v in node_props.items():
                                        if k != id_property:  # ID is already in params
                                            params[k] = v
                                    
                                    session.run(cypher, params)
                                    result["nodes_created"] += 1
                                    
                                    # Store the node for relationship creation
                                    if node_label not in unique_nodes:
                                        unique_nodes[node_label] = {}
                                    unique_nodes[node_label][unique_value] = node_props
                                    
                                except Exception as e:
                                    error_msg = f"Error creating node {node_label}: {str(e)}"
                                    self.logger.error(error_msg)
                                    result["errors"].append(error_msg)
                                
                                # Move to next unique value
                                break
                
                # For node types without ID properties, create them for each record
                for node_label, properties in node_properties.items():
                    if node_label in unique_nodes:
                        continue  # Already processed
                    
                    self.logger.warning(f"Creating non-unique nodes for {node_label}")
                    
                    # Process each record
                    for record in records:
                        # Build properties dict for this node
                        node_props = {}
                        for prop in properties:
                            csv_column = prop.get("csv_column")
                            property_name = prop.get("property")
                            
                            if csv_column in record:
                                node_props[property_name] = record[csv_column]
                                
                        # Skip if no properties
                        if not node_props:
                            continue
                            
                        # Create node using MERGE to avoid duplicates
                        try:
                            # Generate a unique property if possible
                            id_prop = None
                            id_value = None
                            
                            # Try to find a property that could serve as an identifier
                            for prop_name, prop_value in node_props.items():
                                if prop_name.lower() in ['id', 'key', 'identifier', 'uuid']:
                                    id_prop = prop_name
                                    id_value = prop_value
                                    break
                            
                            # If no ID property found, use all properties for uniqueness
                            if id_prop and id_value:
                                cypher = f"MERGE (n:{node_label} {{{id_prop}: $id_value}}) "
                                
                                # Add SET clause for other properties
                                if len(node_props) > 1:  # More than just the ID
                                    cypher += "SET " + ", ".join([f"n.{k} = ${k}" for k in node_props.keys() if k != id_prop])
                                
                                # Prepare parameters
                                params = {"id_value": id_value}
                                for k, v in node_props.items():
                                    if k != id_prop:  # ID is already in params
                                        params[k] = v
                            else:
                                # Create a property string for the MERGE clause
                                prop_string = ", ".join([f"{k}: ${k}" for k in node_props.keys()])
                                cypher = f"MERGE (n:{node_label} {{{prop_string}}}) RETURN n"
                                
                                # Prepare parameters
                                params = {}
                                for k, v in node_props.items():
                                    params[k] = v
                            
                            session.run(cypher, params)
                            result["nodes_created"] += 1
                        except Exception as e:
                            error_msg = f"Error creating node {node_label}: {str(e)}"
                            self.logger.error(error_msg)
                            result["errors"].append(error_msg)
                            
        except Exception as e:
            error_msg = f"Error loading nodes: {str(e)}"
            self.logger.error(error_msg)
            self.logger.error(traceback.format_exc())
            result["errors"].append(error_msg)
            
        return result
        
    async def load_relationships(
        self, 
        records: List[Dict[str, Any]], 
        schema: Dict[str, Any],
        column_mapping: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Load relationships into Neo4j from CSV records.
        
        Args:
            records: List of records from CSV
            schema: The schema definition
            column_mapping: Optional mapping of CSV columns to node properties
            
        Returns:
            Dict with results of relationship loading
        """
        if not self.driver:
            raise ValueError("Neo4j driver not initialized. Call connect() first.")
            
        result = {
            "relationships_created": 0,
            "errors": []
        }
        
        # Extract relationships from schema
        relationships = schema.get("relationships", [])
        if not relationships:
            return result
            
        # Analyze the records to find potential relationship columns
        relationship_columns = self._analyze_relationship_columns(records, relationships)
        self.logger.info(f"Relationship columns: {relationship_columns}")
        
        try:
            with self.driver.session() as session:
                # Process each relationship type
                for rel in relationships:
                    rel_type = rel.get("type")
                    source_label = rel.get("startNode") or rel.get("source")  # Support both naming conventions
                    target_label = rel.get("endNode") or rel.get("target")    # Support both naming conventions
                    
                    if not all([rel_type, source_label, target_label]):
                        self.logger.warning(f"Incomplete relationship definition: {rel}")
                        continue
                    
                    self.logger.info(f"Processing relationship: {source_label}-[{rel_type}]->{target_label}")
                    
                    # Find columns that might represent this relationship
                    rel_key = f"{source_label}_{rel_type}_{target_label}"
                    source_col = None
                    target_col = None
                    
                    # Check if we have identified columns for this relationship
                    if rel_key in relationship_columns:
                        source_col = relationship_columns[rel_key].get("source_column")
                        target_col = relationship_columns[rel_key].get("target_column")
                    
                    # If not found, try to find columns by name patterns
                    if not source_col or not target_col:
                        # Try common naming patterns
                        for column in records[0].keys() if records else []:
                            col_lower = column.lower()
                            if source_label.lower() in col_lower and "id" in col_lower:
                                source_col = column
                            elif target_label.lower() in col_lower and "id" in col_lower:
                                target_col = column
                    
                    # If still not found, use any column that has the label name
                    if not source_col:
                        for column in records[0].keys() if records else []:
                            if source_label.lower() in column.lower():
                                source_col = column
                                break
                    
                    if not target_col:
                        for column in records[0].keys() if records else []:
                            if target_label.lower() in column.lower():
                                target_col = column
                                break
                    
                    self.logger.info(f"Using columns: {source_col} -> {target_col} for relationship {rel_type}")
                    
                    # Skip if we can't find suitable columns
                    if not source_col or not target_col:
                        self.logger.warning(f"Could not find suitable columns for relationship {rel_type}")
                        continue
                    
                    # Process each record to create relationships
                    created_relationships = set()  # Track to avoid duplicates
                    for record in records:
                        if source_col not in record or target_col not in record:
                            continue
                            
                        source_id_value = record[source_col]
                        target_id_value = record[target_col]
                        
                        # Skip if missing values
                        if not source_id_value or not target_id_value:
                            continue
                            
                        # Skip if already created this relationship
                        rel_signature = f"{source_id_value}_{rel_type}_{target_id_value}"
                        if rel_signature in created_relationships:
                            continue
                            
                        # Create relationship using MERGE to avoid duplicates
                        try:
                            cypher = (
                                f"MATCH (source:{source_label} {{id: $source_id}}), "
                                f"(target:{target_label} {{id: $target_id}}) "
                                f"MERGE (source)-[r:{rel_type}]->(target) "
                                f"RETURN r"
                            )
                            
                            params = {
                                "source_id": source_id_value,
                                "target_id": target_id_value
                            }
                            
                            session.run(cypher, params)
                            result["relationships_created"] += 1
                            created_relationships.add(rel_signature)
                            
                        except Exception as e:
                            error_msg = f"Error creating relationship {rel_type}: {str(e)}"
                            self.logger.error(error_msg)
                            result["errors"].append(error_msg)
        
        except Exception as e:
            error_msg = f"Error in relationship loading: {str(e)}"
            self.logger.error(error_msg)
            self.logger.exception(e)
            result["errors"].append(error_msg)
            
        return result
        
    def _analyze_relationship_columns(self, records: List[Dict[str, Any]], relationships: List[Dict[str, Any]]) -> Dict[str, Dict[str, str]]:
        """
        Analyze records to find columns that might represent relationships.
        
        Args:
            records: List of records from CSV
            relationships: List of relationship definitions from schema
            
        Returns:
            Dict mapping relationship keys to source and target columns
        """
        if not records:
            return {}
            
        result = {}
        
        # Get all column names
        columns = list(records[0].keys())
        
        # For each relationship, try to find matching columns
        for rel in relationships:
            rel_type = rel.get("type")
            source_label = rel.get("startNode") or rel.get("source")
            target_label = rel.get("endNode") or rel.get("target")
            
            if not all([rel_type, source_label, target_label]):
                continue
                
            rel_key = f"{source_label}_{rel_type}_{target_label}"
            result[rel_key] = {
                "source_column": None,
                "target_column": None
            }
            
            # Look for columns that might contain IDs for these node types
            for column in columns:
                col_lower = column.lower()
                
                # Check for exact matches first
                if col_lower == f"{source_label.lower()}_id":
                    result[rel_key]["source_column"] = column
                elif col_lower == f"{target_label.lower()}_id":
                    result[rel_key]["target_column"] = column
                    
            # If not found, look for partial matches
            if not result[rel_key]["source_column"]:
                for column in columns:
                    if source_label.lower() in column.lower() and ("id" in column.lower() or "key" in column.lower()):
                        result[rel_key]["source_column"] = column
                        break
                        
            if not result[rel_key]["target_column"]:
                for column in columns:
                    if target_label.lower() in column.lower() and ("id" in column.lower() or "key" in column.lower()):
                        result[rel_key]["target_column"] = column
                        break
                        
        return result
        
    async def clean_database(self) -> Dict[str, Any]:
        """
        Clean the database by removing all nodes and relationships.
        
        Returns:
            Dict with results of database cleaning
        """
        if not self.driver:
            raise ValueError("Neo4j driver not initialized. Call connect() first.")
            
        result = {
            "constraints_dropped": 0,
            "indexes_dropped": 0,
            "nodes_deleted": 0,
            "success": False,
            "errors": []
        }
        
        try:
            with self.driver.session() as session:
                # Try to use APOC if available for a clean wipe
                try:
                    self.logger.info("Attempting to clean database using APOC")
                    session.run("CALL apoc.schema.assert({}, {})")
                    result["constraints_dropped"] += 1
                    result["indexes_dropped"] += 1
                    self.logger.info("Successfully dropped all constraints and indexes using APOC")
                except Exception as e:
                    self.logger.warning(f"APOC not available or error using it: {str(e)}")
                    
                    # Fallback to manual constraint and index dropping
                    try:
                        # Get all constraints
                        constraints = session.run("SHOW CONSTRAINTS").data()
                        for constraint in constraints:
                            name = constraint.get("name")
                            if name:
                                session.run(f"DROP CONSTRAINT {name}")
                                result["constraints_dropped"] += 1
                                
                        # Get all indexes
                        indexes = session.run("SHOW INDEXES").data()
                        for index in indexes:
                            name = index.get("name")
                            if name:
                                session.run(f"DROP INDEX {name}")
                                result["indexes_dropped"] += 1
                    except Exception as e2:
                        error_msg = f"Error dropping constraints and indexes: {str(e2)}"
                        self.logger.error(error_msg)
                        result["errors"].append(error_msg)
                        
                # Delete all nodes and relationships
                try:
                    delete_result = session.run("MATCH (n) DETACH DELETE n RETURN count(n) as deleted")
                    result["nodes_deleted"] = delete_result.single()["deleted"]
                    self.logger.info(f"Deleted {result['nodes_deleted']} nodes and their relationships")
                except Exception as e:
                    error_msg = f"Error deleting nodes and relationships: {str(e)}"
                    self.logger.error(error_msg)
                    result["errors"].append(error_msg)
                    
                result["success"] = True
                
        except Exception as e:
            error_msg = f"Error cleaning database: {str(e)}"
            self.logger.error(error_msg)
            self.logger.error(traceback.format_exc())
            result["errors"].append(error_msg)
            
        return result
