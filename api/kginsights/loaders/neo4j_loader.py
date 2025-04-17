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
    Provides methods for database management including cleaning and data loading.
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
            print(f"Database configuration: {db_config}")  # Debug output
            if not db_config:
                print("Failed to get database configuration")
                return False
                
            # Parse connection parameters for the specified graph
            graph_config = db_config.get(self.graph_name, {})
            print(f"Graph configuration: {graph_config}")  # Debug output
            print(f"Graph name: {self.graph_name}")  # Debug output
            self.connection_params = parse_connection_params(graph_config)
            if not self.connection_params:
                print(f"Failed to parse connection parameters for graph: {self.graph_name}")
                return False
                
            # Create Neo4j driver
            uri = self.connection_params.get("uri")
            username = self.connection_params.get("username")
            password = self.connection_params.get("password")
            
            if not all([uri, username, password]):
                print("Missing Neo4j connection parameters")
                return False
                
            print(f"Connecting to Neo4j at {uri}")
            self.driver = GraphDatabase.driver(uri, auth=(username, password))
            
            # Verify connection
            with self.driver.session() as session:
                result = session.run("RETURN 1 as test")
                test_value = result.single()["test"]
                if test_value != 1:
                    print("Neo4j connection test failed")
                    return False
                    
            print("Successfully connected to Neo4j")
            return True
            
        except Exception as e:
            print(f"Error connecting to Neo4j: {str(e)}")
            print(traceback.format_exc())
            return False
            
    def close(self):
        """Close the Neo4j driver connection."""
        if self.driver:
            self.driver.close()
            print("Neo4j connection closed")
            
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
        print("Skipping creation of constraints and indexes as requested")
        
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
        
        print(f"Node ID properties: {node_id_properties}")
        
        # Track unique nodes to avoid duplicates
        unique_nodes = {}
        
        try:
            with self.driver.session() as session:
                # First pass: Create unique nodes for each node type
                for node_label, properties in node_properties.items():
                    # Skip if no ID properties found for this node type
                    if not node_id_properties.get(node_label, []):
                        print(f"No ID properties found for {node_label}, will create duplicate nodes")
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
                    
                    print(f"Found {len(unique_values)} unique {node_label} nodes")
                    
                    # Create unique nodes
                    for unique_value in unique_values:
                        # Find the first record with this ID value
                        for record in records:
                            if id_column in record and record[id_column] == unique_value:
                                # Build properties dict for this node
                                node_props = {}
                                for prop in properties:
                                    # Check if prop is a dictionary or a string
                                    if isinstance(prop, dict):
                                        csv_column = prop.get("csv_column")
                                        property_name = prop.get("property")
                                        
                                        if csv_column and property_name and csv_column in record:
                                            node_props[property_name] = record[csv_column]
                                    elif isinstance(prop, str):
                                        # If prop is a string, use it as both property name and column name
                                        if prop in record:
                                            node_props[prop] = record[prop]
                                
                                # Skip if no properties
                                if not node_props:
                                    continue
                                
                                # Create node with MERGE to avoid duplicates
                                try:
                                    # Escape ID property name if it contains spaces or special characters
                                    escaped_id_prop = f"`{id_property}`" if " " in id_property or "(" in id_property or ")" in id_property or "$" in id_property or "%" in id_property else id_property
                                    
                                    cypher = f"MERGE (n:{node_label} {{{escaped_id_prop}: $id_value}}) "
                                    
                                    # Add SET clause for other properties
                                    if len(node_props) > 1:  # More than just the ID
                                        # Escape property names with backticks if they contain spaces or special characters
                                        set_clauses = []
                                        for k in node_props.keys():
                                            if k != id_property:
                                                # Escape property name if needed
                                                escaped_prop = f"`{k}`" if " " in k or "(" in k or ")" in k or "$" in k or "%" in k else k
                                                
                                                # Create a safe parameter name by replacing spaces and special characters
                                                safe_param_name = k.replace(" ", "_").replace("(", "").replace(")", "").replace("$", "").replace("%", "")
                                                set_clauses.append(f"n.{escaped_prop} = ${safe_param_name}")
                                        
                                        cypher += "SET " + ", ".join(set_clauses)
                                    
                                    # Prepare parameters
                                    # Convert ID to string to ensure consistent type handling
                                    id_value = str(unique_value) if unique_value is not None else None
                                    params = {"id_value": id_value}
                                    
                                    print(f"ID value type: {type(id_value).__name__}, value: {id_value}")
                                    
                                    for k, v in node_props.items():
                                        if k != id_property:  # ID is already in params
                                            # Use the same safe parameter name as in the SET clause
                                            safe_param_name = k.replace(" ", "_").replace("(", "").replace(")", "").replace("$", "").replace("%", "")
                                            params[safe_param_name] = v
                                    
                                    # Print detailed Cypher information for debugging
                                    print(f"===== NODE CREATION =====")
                                    print(f"Node Label: {node_label}")
                                    print(f"ID Property: {id_property}={unique_value}")
                                    print(f"Cypher Statement: {cypher}")
                                    #print(f"Parameters: {json.dumps(params, indent=2)}")
                                    
                                    # Print the full executable Cypher for direct testing in Neo4j Browser
                                    param_cypher = cypher
                                    for param_name, param_value in params.items():
                                        if isinstance(param_value, str):
                                            param_cypher = param_cypher.replace(f"${param_name}", f"'{param_value}'")
                                        else:
                                            param_cypher = param_cypher.replace(f"${param_name}", str(param_value))
                                    print(f"Executable Cypher: {param_cypher}")
                                    
                                    result_set = session.run(cypher, params)
                                    summary = result_set.consume()
                                    
                                    # Check if node was created or matched
                                    if summary.counters.nodes_created > 0:
                                        print(f"Created new node {node_label} with ID {id_property}={unique_value}")
                                        result["nodes_created"] += 1
                                    else:
                                        print(f"Matched existing node {node_label} with ID {id_property}={unique_value}")
                                    
                                    # Store the node for relationship creation
                                    if node_label not in unique_nodes:
                                        unique_nodes[node_label] = {}
                                    unique_nodes[node_label][unique_value] = node_props
                                    
                                except Exception as e:
                                    error_msg = f"Error creating node {node_label}: {str(e)}"
                                    print(error_msg)
                                    result["errors"].append(error_msg)
                                
                                # Move to next unique value
                                break
                
                # For node types without ID properties, create them for each record
                for node_label, properties in node_properties.items():
                    if node_label in unique_nodes:
                        continue  # Already processed
                    
                    print(f"Creating non-unique nodes for {node_label}")
                    
                    # First, collect all unique values for this node type
                    unique_values = set()
                    for record in records:
                        # For each property in this node type
                        for prop in properties:
                            # Check if prop is a dictionary or a string
                            if isinstance(prop, dict):
                                csv_column = prop.get("csv_column")
                                if csv_column and csv_column in record:
                                    unique_values.add(record[csv_column])
                            elif isinstance(prop, str):
                                # If prop is a string, use it as both property name and column name
                                if prop in record:
                                    unique_values.add(record[prop])
                    
                    print(f"Found {len(unique_values)} unique values for {node_label}")
                    
                    # Create a node for each unique value
                    for value in unique_values:
                        if not value:  # Skip empty values
                            continue
                            
                        # Create a property dict with the value
                        node_props = {}
                        
                        # Use the property name from the schema
                        prop_name = None
                        for prop in properties:
                            if isinstance(prop, dict):
                                prop_name = prop.get("property")
                                if prop_name:
                                    break
                            elif isinstance(prop, str):
                                prop_name = prop
                                break
                        
                        if not prop_name:  # Skip if no property name found
                            continue
                            
                        node_props[prop_name] = value
                        
                        # Create the node
                        try:
                            # Escape property names with backticks if they contain spaces or special characters
                            escaped_prop_name = f"`{prop_name}`" if " " in prop_name or "(" in prop_name or ")" in prop_name or "$" in prop_name or "%" in prop_name else prop_name
                            
                            cypher = f"MERGE (n:{node_label} {{{escaped_prop_name}: $value}}) RETURN n"
                            params = {"value": value}
                            
                            print(f"Creating {node_label} node with {prop_name}={value}")
                            print(f"Cypher: {cypher}")
                            session.run(cypher, params)
                            result["nodes_created"] += 1
                            
                            # Store the node for relationship creation
                            if node_label not in unique_nodes:
                                unique_nodes[node_label] = {}
                            unique_nodes[node_label][value] = {prop_name: value}
                            
                        except Exception as e:
                            error_msg = f"Error creating node {node_label}: {str(e)}"
                            print(error_msg)
                            result["errors"].append(error_msg)
                    
                    # Skip the original per-record processing for this node type
                    continue
                    
                    # Process each record
                    for record in records:
                        # Build properties dict for this node
                        node_props = {}
                        for prop in properties:
                            # Check if prop is a dictionary or a string
                            if isinstance(prop, dict):
                                csv_column = prop.get("csv_column")
                                property_name = prop.get("property")
                                
                                if csv_column and property_name and csv_column in record:
                                    node_props[property_name] = record[csv_column]
                            elif isinstance(prop, str):
                                # If prop is a string, use it as both property name and column name
                                if prop in record:
                                    node_props[prop] = record[prop]
                                
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
                            print(error_msg)
                            result["errors"].append(error_msg)
                            
        except Exception as e:
            error_msg = f"Error loading nodes: {str(e)}"
            print(error_msg)
            print(traceback.format_exc())
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
        print(f"Relationship columns: {relationship_columns}")
        
        try:
            with self.driver.session() as session:
                # Process each relationship type
                for rel_def in relationships:
                    rel_type = rel_def.get("type")
                    source_label = rel_def.get("startNode") or rel_def.get("source")  # Support both naming conventions
                    target_label = rel_def.get("endNode") or rel_def.get("target")    # Support both naming conventions
                    
                    if not all([rel_type, source_label, target_label]):
                        print(f"Incomplete relationship definition: {rel_def}")
                        continue
                    
                    print(f"Processing relationship: {source_label}-[{rel_type}]->{target_label}")
                    
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
                    
                    print(f"Using columns: {source_col} -> {target_col} for relationship {rel_type}")
                    
                    # Skip if we can't find suitable columns
                    if not source_col or not target_col:
                        print(f"Could not find suitable columns for relationship {rel_type}")
                        continue
                    
                    # Process each record to create relationships
                    created_relationships = set()  # Track to avoid duplicates
                    
                    # Determine the property names to use for matching nodes
                    # First, try to find the most likely ID property for each node label
                    source_prop_name = None
                    target_prop_name = None
                    
                    # Get all properties for source and target node labels
                    source_props_query = f"MATCH (n:{source_label}) RETURN keys(n) as props LIMIT 1"
                    target_props_query = f"MATCH (n:{target_label}) RETURN keys(n) as props LIMIT 1"
                    
                    try:
                        source_props_result = session.run(source_props_query).single()
                        if source_props_result:
                            source_props = source_props_result["props"]
                            print(f"Available properties for {source_label}: {source_props}")
                            
                            # Try to find a suitable ID property
                            for prop in source_props:
                                if prop.lower() in ['id', 'key', 'identifier', 'uuid', source_col.lower()]:
                                    source_prop_name = prop
                                    break
                            
                            # If no ID-like property found, use the first property
                            if not source_prop_name and source_props:
                                source_prop_name = source_props[0]
                    except Exception as e:
                        print(f"Error getting properties for {source_label}: {str(e)}")
                    
                    try:
                        target_props_result = session.run(target_props_query).single()
                        if target_props_result:
                            target_props = target_props_result["props"]
                            print(f"Available properties for {target_label}: {target_props}")
                            
                            # Try to find a suitable ID property
                            for prop in target_props:
                                if prop.lower() in ['id', 'key', 'identifier', 'uuid', target_col.lower()]:
                                    target_prop_name = prop
                                    break
                            
                            # If no ID-like property found, use the first property
                            if not target_prop_name and target_props:
                                target_prop_name = target_props[0]
                    except Exception as e:
                        print(f"Error getting properties for {target_label}: {str(e)}")
                    
                    # If we couldn't determine property names from the database, use the column names
                    if not source_prop_name:
                        source_prop_name = source_col
                    if not target_prop_name:
                        target_prop_name = target_col
                    
                    print(f"Using property '{source_prop_name}' for {source_label} nodes")
                    print(f"Using property '{target_prop_name}' for {target_label} nodes")
                    
                    for record in records:
                        if source_col not in record or target_col not in record:
                            continue
                            
                        source_id_value = record[source_col]
                        target_id_value = record[target_col]
                        
                        # Skip if missing values
                        if not source_id_value or not target_id_value:
                            continue
                        
                        # Convert ID values to strings for consistent handling
                        source_id_str = str(source_id_value) if source_id_value is not None else None
                        target_id_str = str(target_id_value) if target_id_value is not None else None
                            
                        # Skip if already created this relationship
                        rel_signature = f"{source_id_str}_{rel_type}_{target_id_str}"
                        if rel_signature in created_relationships:
                            continue
                            
                        # Create relationship using MERGE to avoid duplicates
                        try:
                            # Log ID types and values for debugging
                            print(f"Source ID type: {type(source_id_str).__name__}, value: {source_id_str}")
                            print(f"Target ID type: {type(target_id_str).__name__}, value: {target_id_str}")
                            
                            # Escape property names with backticks if they contain spaces or special characters
                            escaped_source_prop = f"`{source_prop_name}`" if " " in source_prop_name or "(" in source_prop_name or ")" in source_prop_name or "$" in source_prop_name or "%" in source_prop_name else source_prop_name
                            escaped_target_prop = f"`{target_prop_name}`" if " " in target_prop_name or "(" in target_prop_name or ")" in target_prop_name or "$" in target_prop_name or "%" in target_prop_name else target_prop_name
                            
                            # Verify that both nodes exist
                            verify_source = f"MATCH (n:{source_label} {{{escaped_source_prop}: $id}}) RETURN count(n) as count"
                            verify_target = f"MATCH (n:{target_label} {{{escaped_target_prop}: $id}}) RETURN count(n) as count"
                            
                            # Print verification queries for debugging
                            print("===== NODE VERIFICATION =====")
                            # Use format method instead of f-strings with backslashes
                            source_query = verify_source.replace('$id', "'{}'".format(source_id_str))
                            target_query = verify_target.replace('$id', "'{}'".format(target_id_str))
                            print(f"Source verification: {source_query}") 
                            print(f"Target verification: {target_query}") 
                            
                            # Try to find all nodes of these types to help with debugging
                            all_source_nodes_query = f"MATCH (n:{source_label}) RETURN n.{escaped_source_prop} as id LIMIT 10"
                            all_target_nodes_query = f"MATCH (n:{target_label}) RETURN n.{escaped_target_prop} as id LIMIT 10"
                            
                            all_source_nodes = session.run(all_source_nodes_query).values()
                            all_target_nodes = session.run(all_target_nodes_query).values()
                            
                            print(f"Sample {source_label} node IDs: {all_source_nodes}")
                            print(f"Sample {target_label} node IDs: {all_target_nodes}")
                            
                            # Execute verification queries
                            source_exists = session.run(verify_source, {"id": source_id_str}).single()
                            target_exists = session.run(verify_target, {"id": target_id_str}).single()
                            
                            source_count = source_exists["count"] if source_exists else 0
                            target_count = target_exists["count"] if target_exists else 0
                            
                            print(f"Relationship {rel_type}: Source {source_label}({source_prop_name}={source_id_value}) exists: {source_count > 0}")
                            print(f"Relationship {rel_type}: Target {target_label}({target_prop_name}={target_id_value}) exists: {target_count > 0}")
                            
                            # Only proceed if both nodes exist
                            if source_count > 0 and target_count > 0:
                                # Escape property names with backticks if they contain spaces or special characters
                                escaped_source_prop = f"`{source_prop_name}`" if " " in source_prop_name or "(" in source_prop_name or ")" in source_prop_name or "$" in source_prop_name or "%" in source_prop_name else source_prop_name
                                escaped_target_prop = f"`{target_prop_name}`" if " " in target_prop_name or "(" in target_prop_name or ")" in target_prop_name or "$" in target_prop_name or "%" in target_prop_name else target_prop_name
                                
                                # Extract relationship properties from the record if defined in schema
                                rel_props = {}
                                if 'properties' in rel_def and rel_def['properties']:
                                    for prop in rel_def['properties']:
                                        # Check if property is defined as a dict with csv_column mapping
                                        if isinstance(prop, dict) and 'csv_column' in prop and 'property' in prop:
                                            csv_col = prop['csv_column']
                                            prop_name = prop['property']
                                            if csv_col in record and record[csv_col] is not None:
                                                rel_props[prop_name] = record[csv_col]
                                        # Or if it's a direct string property name that matches a column
                                        elif isinstance(prop, str) and prop in record and record[prop] is not None:
                                            rel_props[prop] = record[prop]
                                
                                # Build the Cypher query
                                cypher = (
                                    f"MATCH (source:{source_label} {{{escaped_source_prop}: $source_id}}), "
                                    f"(target:{target_label} {{{escaped_target_prop}: $target_id}}) "
                                    f"MERGE (source)-[r:{rel_type}]->(target) "
                                )
                                
                                # Add SET clause for relationship properties if any
                                if rel_props:
                                    set_clauses = []
                                    for k in rel_props.keys():
                                        # Escape property name if needed
                                        escaped_prop = f"`{k}`" if " " in k or "(" in k or ")" in k or "$" in k or "%" in k else k
                                        # Create a safe parameter name
                                        safe_param_name = f"rel_{k.replace(' ', '_').replace('(', '').replace(')', '').replace('$', '').replace('%', '')}"
                                        set_clauses.append(f"r.{escaped_prop} = ${safe_param_name}")
                                    
                                    cypher += "SET " + ", ".join(set_clauses) + " "
                                
                                cypher += "RETURN r"
                                
                                # Prepare parameters
                                params = {
                                    "source_id": source_id_str,
                                    "target_id": target_id_str
                                }
                                
                                # Add relationship property parameters with safe names
                                for k, v in rel_props.items():
                                    safe_param_name = f"rel_{k.replace(' ', '_').replace('(', '').replace(')', '').replace('$', '').replace('%', '')}"
                                    params[safe_param_name] = v
                                
                                # Print detailed Cypher information for debugging
                                print(f"===== RELATIONSHIP CREATION =====")
                                print(f"Relationship Type: {rel_type}")
                                print(f"Source: {source_label}({source_prop_name}={source_id_str})")
                                print(f"Target: {target_label}({target_prop_name}={target_id_str})")
                                print(f"Cypher Statement: {cypher}")
                                print(f"Parameters: {json.dumps(params, indent=2)}")
                                
                                # Print the full executable Cypher for direct testing in Neo4j Browser
                                param_cypher = cypher
                                for param_name, param_value in params.items():
                                    if isinstance(param_value, str):
                                        param_cypher = param_cypher.replace(f"${param_name}", f"'{param_value}'")
                                    else:
                                        param_cypher = param_cypher.replace(f"${param_name}", str(param_value))
                                print(f"Executable Cypher: {param_cypher}")
                                
                                # Try a different approach with explicit node matching
                                try:
                                    # First, try to create the relationship with the original query
                                    result_set = session.run(cypher, params)
                                    summary = result_set.consume()
                                    
                                    # Check if relationship was created
                                    if summary.counters.relationships_created > 0:
                                        print(f"Successfully created relationship {rel_type} from {source_id_str} to {target_id_str}")
                                        result["relationships_created"] += 1
                                        created_relationships.add(rel_signature)
                                    elif summary.counters.relationships_created == 0 and summary.counters.contains_updates:
                                        # Relationship might have been matched but not created (already exists)
                                        print(f"Relationship {rel_type} from {source_id_str} to {target_id_str} already exists")
                                        created_relationships.add(rel_signature)
                                    else:
                                        # Try a more direct approach with explicit node creation and relationship
                                        print(f"Initial relationship creation failed. Trying alternative approach...")
                                        
                                        # Create a simpler Cypher query that first ensures both nodes exist
                                        # Escape property names with backticks if they contain spaces or special characters
                                        escaped_source_prop = f"`{source_prop_name}`" if " " in source_prop_name or "(" in source_prop_name or ")" in source_prop_name or "$" in source_prop_name or "%" in source_prop_name else source_prop_name
                                        escaped_target_prop = f"`{target_prop_name}`" if " " in target_prop_name or "(" in target_prop_name or ")" in target_prop_name or "$" in target_prop_name or "%" in target_prop_name else target_prop_name
                                        
                                        # Properly escape the string values in the Cypher query
                                        source_id_str_escaped = source_id_str.replace("'", "\\'") if isinstance(source_id_str, str) else source_id_str
                                        target_id_str_escaped = target_id_str.replace("'", "\\'") if isinstance(target_id_str, str) else target_id_str
                                        
                                        # Build the alternative Cypher query
                                        alt_cypher = (
                                            f"MERGE (source:{source_label} {{{escaped_source_prop}: '{source_id_str_escaped}'}}) "
                                            f"MERGE (target:{target_label} {{{escaped_target_prop}: '{target_id_str_escaped}'}}) "
                                            f"MERGE (source)-[r:{rel_type}]->(target) "
                                        )
                                        
                                        # Add relationship properties if any
                                        if rel_props:
                                            prop_sets = []
                                            for k, v in rel_props.items():
                                                # Escape property name if needed
                                                escaped_prop = f"`{k}`" if " " in k or "(" in k or ")" in k or "$" in k or "%" in k else k
                                                
                                                # Format the value based on its type
                                                if isinstance(v, str):
                                                    # Escape any single quotes in string values
                                                    v_escaped = v.replace("'", "\\'") 
                                                    prop_sets.append(f"r.{escaped_prop} = '{v_escaped}'")
                                                elif v is None:
                                                    prop_sets.append(f"r.{escaped_prop} = NULL")
                                                else:
                                                    prop_sets.append(f"r.{escaped_prop} = {v}")
                                            
                                            if prop_sets:
                                                alt_cypher += "SET " + ", ".join(prop_sets) + " "
                                        
                                        alt_cypher += "RETURN r"
                                        
                                        print(f"Alternative Cypher: {alt_cypher}")
                                        alt_result = session.run(alt_cypher)
                                        alt_summary = alt_result.consume()
                                        
                                        if alt_summary.counters.relationships_created > 0:
                                            print(f"Successfully created relationship with alternative approach")
                                            result["relationships_created"] += 1
                                            created_relationships.add(rel_signature)
                                        else:
                                            print(f"Alternative approach also failed. No relationship created.")
                                except Exception as e:
                                    print(f"Error in alternative relationship creation approach: {str(e)}")
                            else:
                                print(f"Cannot create relationship - nodes don't exist: {source_label}({source_id_str}) to {target_label}({target_id_str})")
                            
                        except Exception as e:
                            error_msg = f"Error creating relationship {rel_type}: {str(e)}"
                            print(error_msg)
                            result["errors"].append(error_msg)
        
        except Exception as e:
            error_msg = f"Error in relationship loading: {str(e)}"
            print(error_msg)
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
        
    async def inspect_database(self, schema: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Inspect the database to check for nodes and relationships.
        
        Args:
            schema: Optional schema to check specific node labels and relationship types
            
        Returns:
            Dict with inspection results
        """
        if not self.driver:
            raise ValueError("Neo4j driver not initialized. Call connect() first.")
            
        result = {
            "node_counts": {},
            "relationship_counts": {},
            "sample_nodes": {},
            "sample_relationships": []
        }
        
        try:
            with self.driver.session() as session:
                # Get node counts by label
                print("===== DATABASE INSPECTION =====")
                print("Checking node counts by label...")
                
                # If schema provided, check specific node labels
                node_labels = []
                if schema and "nodes" in schema:
                    for node in schema.get("nodes", []):
                        if "label" in node:
                            node_labels.append(node["label"])
                
                # If no schema or empty node labels, get all labels
                if not node_labels:
                    labels_result = session.run("CALL db.labels() YIELD label RETURN label")
                    node_labels = [record["label"] for record in labels_result]
                
                # Get count for each label
                for label in node_labels:
                    count_result = session.run(f"MATCH (n:{label}) RETURN count(n) as count").single()
                    count = count_result["count"] if count_result else 0
                    result["node_counts"][label] = count
                    print(f"Node label '{label}': {count} nodes")
                    
                    # Get sample nodes
                    if count > 0:
                        sample_result = session.run(f"MATCH (n:{label}) RETURN n LIMIT 3")
                        samples = [dict(record["n"]) for record in sample_result]
                        result["sample_nodes"][label] = samples
                        print(f"Sample {label} nodes: {json.dumps(samples, indent=2)}")
                
                # Get relationship counts by type
                print("Checking relationship counts by type...")
                
                # If schema provided, check specific relationship types
                rel_types = []
                if schema and "relationships" in schema:
                    for rel in schema.get("relationships", []):
                        if "type" in rel:
                            rel_types.append(rel["type"])
                
                # If no schema or empty rel types, get all types
                if not rel_types:
                    types_result = session.run("CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType")
                    rel_types = [record["relationshipType"] for record in types_result]
                
                # Get count for each type
                for rel_type in rel_types:
                    count_result = session.run(f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as count").single()
                    count = count_result["count"] if count_result else 0
                    result["relationship_counts"][rel_type] = count
                    print(f"Relationship type '{rel_type}': {count} relationships")
                    
                    # Get sample relationships
                    if count > 0:
                        sample_result = session.run(
                            f"MATCH (a)-[r:{rel_type}]->(b) "
                            f"RETURN type(r) as type, a.id as source_id, labels(a)[0] as source_label, "
                            f"b.id as target_id, labels(b)[0] as target_label LIMIT 3"
                        )
                        for record in sample_result:
                            rel_info = {
                                "type": record["type"],
                                "source_label": record["source_label"],
                                "source_id": record["source_id"],
                                "target_label": record["target_label"],
                                "target_id": record["target_id"]
                            }
                            result["sample_relationships"].append(rel_info)
                            print(f"Sample relationship: {json.dumps(rel_info, indent=2)}")
                
                # Check for data inconsistencies
                print("Checking for data inconsistencies...")
                if schema and "relationships" in schema:
                    for rel in schema.get("relationships", []):
                        rel_type = rel.get("type")
                        source = rel.get("source") or rel.get("startNode")
                        target = rel.get("target") or rel.get("endNode")
                        
                        if all([rel_type, source, target]):
                            # Check if there are nodes without relationships
                            orphan_query = f"""
                            MATCH (a:{source})
                            WHERE NOT (a)-[:{rel_type}]->() 
                            RETURN a.id as id LIMIT 5
                            """
                            orphans = session.run(orphan_query).values()
                            if orphans:
                                print(f"Found {source} nodes without {rel_type} relationships: {orphans}")
                            
                            # Check if there are relationships with missing nodes
                            invalid_query = f"""
                            MATCH (a:{source})-[r:{rel_type}]->(b:{target})
                            WHERE a.id IS NULL OR b.id IS NULL
                            RETURN count(r) as count
                            """
                            invalid_count = session.run(invalid_query).single()["count"]
                            if invalid_count > 0:
                                print(f"Found {invalid_count} {rel_type} relationships with missing node IDs")
        
        except Exception as e:
            print(f"Error during database inspection: {str(e)}")
            self.logger.exception(e)
        
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
                    print("Attempting to clean database using APOC")
                    session.run("CALL apoc.schema.assert({}, {})")
                    result["constraints_dropped"] += 1
                    result["indexes_dropped"] += 1
                    print("Successfully dropped all constraints and indexes using APOC")
                except Exception as e:
                    print(f"APOC not available or error using it: {str(e)}")
                    
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
                        print(error_msg)
                        result["errors"].append(error_msg)
                        
                # Delete all nodes and relationships
                try:
                    delete_result = session.run("MATCH (n) DETACH DELETE n RETURN count(n) as deleted")
                    result["nodes_deleted"] = delete_result.single()["deleted"]
                    print(f"Deleted {result['nodes_deleted']} nodes and their relationships")
                except Exception as e:
                    error_msg = f"Error deleting nodes and relationships: {str(e)}"
                    print(error_msg)
                    result["errors"].append(error_msg)
                    
                result["success"] = True
                
        except Exception as e:
            error_msg = f"Error cleaning database: {str(e)}"
            print(error_msg)
            print(traceback.format_exc())
            result["errors"].append(error_msg)
            
        return result
