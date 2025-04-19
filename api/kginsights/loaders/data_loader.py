"""
Data Loader for loading data from CSV files into Neo4j.
"""
import os
import json
import logging
import asyncio
import traceback
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from .csv_connector import CSVConnector
from .neo4j_loader import Neo4jLoader
from ..database_api import get_database_config, parse_connection_params
from ...db_config import SessionLocal
from ...models import Schema

class DataLoader:
    """
    Main class for loading data from CSV files into Neo4j.
    Orchestrates the loading process using CSVConnector and Neo4jLoader.
    """
    
    def __init__(
        self,
        schema_id: int = None,
        schema_data: Dict[str, Any] = None,
        data_path: str = None,
        graph_name: str = "default",
        batch_size: int = 1000,
        drop_existing: bool = False
    ):
        """
        Initialize the data loader.
        
        Args:
            schema_id: ID of the schema to use
            schema_data: Schema data (alternative to schema_id)
            data_path: Path to the CSV file
            graph_name: Name of the Neo4j graph to load data into
            batch_size: Number of records to process in each batch
            drop_existing: Whether to drop existing data before loading
        """
        self.schema_id = schema_id
        self.schema_data = schema_data
        self.data_path = data_path
        self.graph_name = graph_name
        self.batch_size = batch_size
        self.drop_existing = drop_existing
        self.logger = logging.getLogger(__name__)
        
        # Will be initialized during loading
        self.csv_connector = None
        self.neo4j_loader = None
        self.schema = None
        
        # Status tracking
        self.status = {
            "status": "initialized",
            "start_time": None,
            "end_time": None,
            "nodes_created": 0,
            "relationships_created": 0,
            "constraints_created": 0,
            "indexes_created": 0,
            "records_processed": 0,
            "errors": [],
            "warnings": []
        }
        
    async def _load_schema(self, db: SessionLocal) -> bool:
        """
        Load the schema from the database or use provided schema data.
        
        Args:
            db: Database session
            
        Returns:
            True if schema loaded successfully, False otherwise
        """
        try:
            # If schema data is provided directly, use it
            if self.schema_data:
                if isinstance(self.schema_data, str):
                    self.schema = json.loads(self.schema_data)
                else:
                    self.schema = self.schema_data
                    
                print("Using provided schema data")
                return True
                
            # Otherwise, load schema from database
            if not self.schema_id:
                print("No schema_id or schema_data provided")
                self.status["errors"].append("No schema_id or schema_data provided")
                return False
                
            schema_record = db.query(Schema).filter(Schema.id == self.schema_id).first()
            if not schema_record:
                print(f"Schema with ID {self.schema_id} not found")
                self.status["errors"].append(f"Schema with ID {self.schema_id} not found")
                return False
                
            # Parse schema JSON
            try:
                self.schema = json.loads(schema_record.schema)
                print(f"Loaded schema: {schema_record.name}")
                
                # If data_path is not provided, use the one from the schema
                if not self.data_path and schema_record.csv_file_path:
                    self.data_path = schema_record.csv_file_path
                    print(f"Using CSV file path from schema: {self.data_path}")
                    
                return True
            except json.JSONDecodeError as e:
                print(f"Error parsing schema JSON: {str(e)}")
                self.status["errors"].append(f"Error parsing schema JSON: {str(e)}")
                return False
                
        except Exception as e:
            print(f"Error loading schema: {str(e)}")
            print(traceback.format_exc())
            self.status["errors"].append(f"Error loading schema: {str(e)}")
            return False
            
    async def _validate_data_path(self) -> bool:
        """
        Validate that the data path exists and is readable.
        
        Returns:
            True if data path is valid, False otherwise
        """
        if not self.data_path:
            print("No data_path provided and none found in schema")
            self.status["errors"].append("No data_path provided and none found in schema")
            return False
            
        # Normalize path
        self.data_path = self.data_path.replace('\\', '/')
        
        # Check if file exists
        if not os.path.exists(self.data_path):
            print(f"Data file does not exist: {self.data_path}")
            self.status["errors"].append(f"Data file does not exist: {self.data_path}")
            return False
            
        # Check if file is readable
        if not os.access(self.data_path, os.R_OK):
            print(f"Data file is not readable: {self.data_path}")
            self.status["errors"].append(f"Data file is not readable: {self.data_path}")
            return False
            
        return True
        
    async def _initialize_loaders(self) -> bool:
        """
        Initialize the CSV connector and Neo4j loader.
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Initialize CSV connector
            self.csv_connector = CSVConnector(self.data_path, self.batch_size)
            
            # Validate CSV file
            validation = self.csv_connector.validate_file()
            if not validation["valid"]:
                for error in validation["errors"]:
                    print(f"CSV validation error: {error}")
                    self.status["errors"].append(f"CSV validation error: {error}")
                return False
                
            for warning in validation["warnings"]:
                print(f"CSV validation warning: {warning}")
                self.status["warnings"].append(f"CSV validation warning: {warning}")
                
            # Initialize Neo4j loader
            self.neo4j_loader = Neo4jLoader(self.graph_name)
            
            # Connect to Neo4j
            connected = await self.neo4j_loader.connect()
            if not connected:
                print("Failed to connect to Neo4j")
                self.status["errors"].append("Failed to connect to Neo4j")
                return False
                
            return True
            
        except Exception as e:
            print(f"Error initializing loaders: {str(e)}")
            print(traceback.format_exc())
            self.status["errors"].append(f"Error initializing loaders: {str(e)}")
            return False
            
    async def load_data(self, db: SessionLocal) -> Dict[str, Any]:
        """
        Load data from CSV file into Neo4j based on schema.
        
        Args:
            db: Database session
            
        Returns:
            Dict with loading results
        """
        self.status["start_time"] = datetime.now().isoformat()
        self.status["status"] = "running"
        
        try:
            # Load schema
            schema_loaded = await self._load_schema(db)
            if not schema_loaded:
                self.status["status"] = "failed"
                self.status["end_time"] = datetime.now().isoformat()
                return self.status
                
            # Validate data path
            data_path_valid = await self._validate_data_path()
            if not data_path_valid:
                self.status["status"] = "failed"
                self.status["end_time"] = datetime.now().isoformat()
                return self.status
                
            # Initialize loaders
            loaders_initialized = await self._initialize_loaders()
            if not loaders_initialized:
                self.status["status"] = "failed"
                self.status["end_time"] = datetime.now().isoformat()
                return self.status
                
            # Clean database if requested
            if self.drop_existing:
                print("Cleaning database before loading data")
                clean_result = await self.neo4j_loader.clean_database()
                if not clean_result["success"]:
                    for error in clean_result["errors"]:
                        print(f"Database cleaning error: {error}")
                        self.status["errors"].append(f"Database cleaning error: {error}")
                    self.status["status"] = "failed"
                    self.status["end_time"] = datetime.now().isoformat()
                    return self.status
                    
                print(f"Database cleaned: {clean_result['nodes_deleted']} nodes deleted")
                
            # Skip creating constraints and indexes
            print("Skipping constraints and indexes creation as requested")
            self.status["constraints_created"] = 0
            self.status["indexes_created"] = 0
                
            # Debug schema structure
            print("===== SCHEMA STRUCTURE =====")
            print(f"Schema ID: {self.schema_id}")
            
            # Log nodes defined in schema
            nodes = self.schema.get("nodes", [])
            print(f"Schema contains {len(nodes)} node types:")
            for idx, node in enumerate(nodes):
                node_label = node.get("label")
                node_props = node.get("properties", [])
                print(f"Node {idx+1}: {node_label} with {len(node_props)} properties")
                for prop in node_props:
                    # Check if prop is a dictionary or a string
                    if isinstance(prop, dict):
                        prop_name = prop.get("property")
                        csv_col = prop.get("csv_column")
                        print(f"  - Property: {prop_name}, CSV Column: {csv_col}")
                    else:
                        # Handle case where prop is a string
                        print(f"  - Property: {prop} (string format)")
            
            # Log relationships defined in schema
            relationships = self.schema.get("relationships", [])
            print(f"Schema contains {len(relationships)} relationship types:")
            for idx, rel in enumerate(relationships):
                rel_type = rel.get("type")
                source = rel.get("source") or rel.get("startNode")
                target = rel.get("target") or rel.get("endNode")
                print(f"Relationship {idx+1}: {source}-[{rel_type}]->{target}")
            
            # Get column mapping
            column_mapping = self.csv_connector.get_column_mapping(self.schema)
            if not column_mapping:
                print("No column mapping found between CSV and schema")
                self.status["warnings"].append("No column mapping found between CSV and schema")
            else:
                print("===== COLUMN MAPPING =====")
                for node_label, props in column_mapping.items():
                    print(f"Node {node_label} mappings:")
                    for prop in props:
                        if isinstance(prop, dict):
                            print(f"  - {prop.get('property')} <- {prop.get('csv_column')}")
                        elif isinstance(prop, str):
                            print(f"  - {prop} (direct mapping)")
                
            # Process data in batches
            print(f"Starting data loading from {self.data_path}")
            try:
                batch_count = 0
                for batch in self.csv_connector.read_batches():
                    batch_count += 1
                    print(f"Processing batch {batch_count} with {len(batch)} records")
                    
                    # Load nodes
                    node_result = await self.neo4j_loader.load_nodes(batch, self.schema, column_mapping)
                    self.status["nodes_created"] += node_result["nodes_created"]
                    
                    for error in node_result["errors"]:
                        print(f"Node loading error: {error}")
                        self.status["warnings"].append(f"Node loading error: {error}")
                        
                    # Debug schema relationships before loading
                    relationships = self.schema.get("relationships", [])
                    print(f"Found {len(relationships)} relationship definitions in schema")
                    for idx, rel in enumerate(relationships):
                        rel_type = rel.get("type")
                        source = rel.get("source") or rel.get("startNode")
                        target = rel.get("target") or rel.get("endNode")
                        print(f"Relationship {idx+1}: {source}-[{rel_type}]->{target}")
                    
                    # Debug first few records to see what data we're working with
                    if batch_count == 1:
                        sample_record = batch[0] if batch else {}
                        print(f"Sample record: {json.dumps(sample_record, indent=2)}")
                        
                        # Check for potential ID columns
                        for col, val in sample_record.items():
                            if "id" in col.lower() or "key" in col.lower():
                                print(f"Potential ID column: {col} = {val}")
                    
                    # Load relationships
                    rel_result = await self.neo4j_loader.load_relationships(batch, self.schema, column_mapping)
                    self.status["relationships_created"] += rel_result["relationships_created"]
                    
                    for error in rel_result["errors"]:
                        print(f"Relationship loading error: {error}")
                        self.status["warnings"].append(f"Relationship loading error: {error}")
                        
                    self.status["records_processed"] += len(batch)
                    
            except Exception as e:
                print(f"Error processing data: {str(e)}")
                print(traceback.format_exc())
                self.status["errors"].append(f"Error processing data: {str(e)}")
                self.status["status"] = "failed"
                self.status["end_time"] = datetime.now().isoformat()
                return self.status
                
            # Close Neo4j connection
            if self.neo4j_loader:
                self.neo4j_loader.close()
                
                # Inspect database to see what was actually created
                print("Inspecting database after data loading...")
                inspection_result = await self.neo4j_loader.inspect_database(self.schema)
                
                # Add inspection results to status
                self.status["node_counts"] = inspection_result["node_counts"]
                self.status["relationship_counts"] = inspection_result["relationship_counts"]
                
                # Check if relationships were actually created
                total_relationships = sum(inspection_result["relationship_counts"].values())
                total_nodes = sum(inspection_result["node_counts"].values())
                
                # Update the status with actual database counts
                if total_nodes > 0:
                    self.status["nodes_created"] = total_nodes
                
                if total_relationships > 0:
                    self.status["relationships_created"] = total_relationships
                
                # Add warning if there's a discrepancy
                if total_relationships == 0 and self.status["relationships_created"] > 0:
                    print("Relationship creation reported success but no relationships found in database!")
                    self.status["warnings"].append("Relationship creation reported success but no relationships found in database")
                
                self.status["status"] = "completed"
                self.status["end_time"] = datetime.now().isoformat()
                self.status["success"] = True
                
                print(f"Data loading completed: {self.status['records_processed']} records processed")
                print(f"Created {self.status['nodes_created']} nodes and {self.status['relationships_created']} relationships")
                print(f"Actual database state: {sum(inspection_result['node_counts'].values())} nodes and {total_relationships} relationships")
                
            return self.status
            
        except Exception as e:
            print(f"Unhandled error in load_data: {str(e)}")
            print(traceback.format_exc())
            self.status["errors"].append(f"Unhandled error in load_data: {str(e)}")
            self.status["status"] = "failed"
            self.status["end_time"] = datetime.now().isoformat()
            
            # Close Neo4j connection
            if self.neo4j_loader:
                self.neo4j_loader.close()
                
            return self.status
