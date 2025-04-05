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
            self.connection_params = parse_connection_params(db_config, self.graph_name)
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
        Create constraints and indexes based on schema.
        
        Args:
            schema: The schema definition
            
        Returns:
            Dict with results of constraint and index creation
        """
        if not self.driver:
            raise ValueError("Neo4j driver not initialized. Call connect() first.")
            
        result = {
            "constraints_created": 0,
            "indexes_created": 0,
            "errors": []
        }
        
        try:
            with self.driver.session() as session:
                # Create constraints for nodes
                for node in schema.get("nodes", []):
                    node_label = node.get("label")
                    if not node_label:
                        continue
                        
                    properties = node.get("properties", {})
                    
                    # Handle properties as dictionary
                    if isinstance(properties, dict):
                        # Look for ID properties to create constraints on
                        id_properties = [p for p in ['id', 'ID', 'Id', 'CustomerID', 'customer_id'] 
                                        if p in properties]
                        
                        if id_properties:
                            id_property = id_properties[0]
                            try:
                                # Create constraint if it doesn't exist
                                cypher = (
                                    f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{node_label}) "
                                    f"REQUIRE n.{id_property} IS UNIQUE"
                                )
                                session.run(cypher)
                                result["constraints_created"] += 1
                                self.logger.info(f"Created constraint on {node_label}.{id_property}")
                            except Exception as e:
                                error_msg = f"Error creating constraint on {node_label}.{id_property}: {str(e)}"
                                self.logger.error(error_msg)
                                result["errors"].append(error_msg)
                                
                        # Create index on the node label if it doesn't exist
                        try:
                            cypher = f"CREATE INDEX IF NOT EXISTS FOR (n:{node_label}) ON (n.id)"
                            session.run(cypher)
                            result["indexes_created"] += 1
                            self.logger.info(f"Created index on {node_label}.id")
                        except Exception as e:
                            error_msg = f"Error creating index on {node_label}.id: {str(e)}"
                            self.logger.error(error_msg)
                            result["errors"].append(error_msg)
                    
                    # Handle properties as list
                    elif isinstance(properties, list):
                        # Look for ID properties to create constraints on
                        id_property = next((p.get('name') for p in properties 
                                        if p.get('name') in ['id', 'ID', 'Id', 'CustomerID', 'customer_id']), None)
                        
                        if id_property:
                            try:
                                # Create constraint if it doesn't exist
                                cypher = (
                                    f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{node_label}) "
                                    f"REQUIRE n.{id_property} IS UNIQUE"
                                )
                                session.run(cypher)
                                result["constraints_created"] += 1
                                self.logger.info(f"Created constraint on {node_label}.{id_property}")
                            except Exception as e:
                                error_msg = f"Error creating constraint on {node_label}.{id_property}: {str(e)}"
                                self.logger.error(error_msg)
                                result["errors"].append(error_msg)
                                
                        # Create index on the node label if it doesn't exist
                        try:
                            cypher = f"CREATE INDEX IF NOT EXISTS FOR (n:{node_label}) ON (n.id)"
                            session.run(cypher)
                            result["indexes_created"] += 1
                            self.logger.info(f"Created index on {node_label}.id")
                        except Exception as e:
                            error_msg = f"Error creating index on {node_label}.id: {str(e)}"
                            self.logger.error(error_msg)
                            result["errors"].append(error_msg)
                            
        except Exception as e:
            error_msg = f"Error creating constraints and indexes: {str(e)}"
            self.logger.error(error_msg)
            self.logger.error(traceback.format_exc())
            result["errors"].append(error_msg)
            
        return result
        
    async def load_nodes(
        self, 
        records: List[Dict[str, Any]], 
        schema: Dict[str, Any],
        column_mapping: Dict[str, Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Load nodes into Neo4j from CSV records.
        
        Args:
            records: List of records from CSV
            schema: The schema definition
            column_mapping: Mapping of CSV columns to node properties
            
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
        for column, mapping in column_mapping.items():
            node_label = mapping.get("node_label")
            if not node_label:
                continue
                
            if node_label not in node_properties:
                node_properties[node_label] = []
                
            node_properties[node_label].append({
                "csv_column": column,
                "property": mapping.get("property", column)
            })
            
        try:
            with self.driver.session() as session:
                # Process each record
                for record in records:
                    # Create nodes for each node label
                    for node_label, properties in node_properties.items():
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
                            
                        # Create node
                        try:
                            cypher, params = self._create_node_cypher(node_label, node_props)
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
        schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Load relationships into Neo4j from CSV records.
        
        Args:
            records: List of records from CSV
            schema: The schema definition
            
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
            
        try:
            with self.driver.session() as session:
                # Process each record
                for record in records:
                    # Create relationships for each relationship definition
                    for rel in relationships:
                        rel_type = rel.get("type")
                        source_label = rel.get("source")
                        target_label = rel.get("target")
                        
                        if not all([rel_type, source_label, target_label]):
                            continue
                            
                        # Find ID properties for source and target nodes
                        source_id_prop = "id"
                        target_id_prop = "id"
                        
                        # Find source and target ID values in the record
                        source_id_value = None
                        target_id_value = None
                        
                        # Look for columns that might contain the IDs
                        for column, value in record.items():
                            if column.lower() == f"{source_label.lower()}_id":
                                source_id_value = value
                            elif column.lower() == f"{target_label.lower()}_id":
                                target_id_value = value
                                
                        # Skip if we can't find both IDs
                        if not source_id_value or not target_id_value:
                            continue
                            
                        # Create relationship
                        try:
                            cypher, params = self._create_relationship_cypher(
                                source_label=source_label,
                                source_id_prop=source_id_prop,
                                source_id_value=source_id_value,
                                target_label=target_label,
                                target_id_prop=target_id_prop,
                                target_id_value=target_id_value,
                                rel_type=rel_type
                            )
                            session.run(cypher, params)
                            result["relationships_created"] += 1
                        except Exception as e:
                            error_msg = (f"Error creating relationship {source_label}-[{rel_type}]->{target_label}: "
                                        f"{str(e)}")
                            self.logger.error(error_msg)
                            result["errors"].append(error_msg)
                            
        except Exception as e:
            error_msg = f"Error loading relationships: {str(e)}"
            self.logger.error(error_msg)
            self.logger.error(traceback.format_exc())
            result["errors"].append(error_msg)
            
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
