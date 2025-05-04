"""
Data Loader for loading data from CSV files into Neo4j using neo4j-admin import.
"""
import os
import json
import logging
import asyncio
import traceback
import tempfile
import shutil
import platform
import subprocess
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path

from ..database_api import get_database_config, parse_connection_params
from ...db_config import SessionLocal
from ...models import Schema
from neo4j import GraphDatabase
import time

class DataLoader:
    """
    Main class for loading data from CSV files into Neo4j.
    Orchestrates the loading process using neo4j-admin import utility.
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
            batch_size: Number of records to process in each batch (not used with neo4j-admin)
            drop_existing: Whether to drop existing data before loading
        """
        self.schema_id = schema_id
        self.schema_data = schema_data
        self.data_path = data_path
        self.graph_name = graph_name
        self.batch_size = batch_size
        self.drop_existing = drop_existing
        self.logger = logging.getLogger(__name__)
        
        # Neo4j configuration (will be set during initialization)
        self.neo4j_home = None
        self.neo4j_bin = None
        self.neo4j_import_dir = None
        self.database_name = None
        self.connection_params = None
        
        # Temporary directory for generated CSV files
        self.temp_dir = None
        
        # Will be initialized during loading
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
        
    async def _initialize_neo4j_config(self) -> bool:
        """
        Initialize Neo4j configuration and connection parameters.
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Get database configuration
            db_config = get_database_config()
            if not db_config:
                print("Failed to get database configuration")
                self.status["errors"].append("Failed to get database configuration")
                return False
                
            # Parse connection parameters for the specified graph
            graph_config = db_config.get(self.graph_name, {})
            self.connection_params = parse_connection_params(graph_config)
            if not self.connection_params:
                print(f"Failed to parse connection parameters for graph: {self.graph_name}")
                self.status["errors"].append(f"Failed to parse connection parameters for graph: {self.graph_name}")
                return False
            
            # Set Neo4j paths based on OS
            system = platform.system()
            if system == "Windows":
                # Default paths for Windows
                self.neo4j_home = self.connection_params.get("neo4j_home", "C:\\development\\neo4j")
                self.neo4j_bin = os.path.join(self.neo4j_home, "bin")
            elif system == "Linux":
                # Default paths for Linux
                self.neo4j_home = self.connection_params.get("neo4j_home", "/var/lib/neo4j")
                self.neo4j_bin = self.connection_params.get("neo4j_bin", "/usr/bin")
            elif system == "Darwin":  # macOS
                # Default paths for macOS
                self.neo4j_home = self.connection_params.get("neo4j_home", "/opt/homebrew/var/neo4j")
                self.neo4j_bin = self.connection_params.get("neo4j_bin", "/opt/homebrew/bin")
            
            # Set database name and import directory
            self.database_name = self.connection_params.get("database", "neo4j")
            self.neo4j_import_dir = os.path.join(self.neo4j_home, "import")
            
            # Create temporary directory for generated CSV files
            self.temp_dir = tempfile.mkdtemp(prefix="neo4j_import_")
            
            print(f"Neo4j configuration initialized: home={self.neo4j_home}, bin={self.neo4j_bin}, import_dir={self.neo4j_import_dir}")
            return True
        except Exception as e:
            print(f"Error initializing Neo4j configuration: {str(e)}")
            print(traceback.format_exc())
            self.status["errors"].append(f"Error initializing Neo4j configuration: {str(e)}")
            return False
            
    async def _generate_neo4j_files(self) -> bool:
        """
        Generate CSV files for Neo4j import using generate_neo4j_files.py.
        
        Returns:
            True if files generated successfully, False otherwise
        """
        try:
            # Import the generate_neo4j_files module
            import sys
            sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            from api.kgdata_loader.generate_neo4j_files import create_neo4j_import_files
            
            # Create output directory for CSV files
            os.makedirs(self.temp_dir, exist_ok=True)
            
            # Save schema to temporary file if it's provided as data
            schema_path = os.path.join(self.temp_dir, "schema.json")
            with open(schema_path, 'w') as f:
                json.dump(self.schema, f)
            
            print(f"Generating Neo4j import files from {self.data_path} using schema {schema_path}")
            # Generate CSV files
            start = time.time()
            create_neo4j_import_files(schema_path, self.data_path, self.temp_dir)
            end = time.time()
            print(f"Generated CSV files in {end - start:.2f} seconds")
            
            # Verify files were created
            node_files = [f for f in os.listdir(self.temp_dir) if f.endswith('_nodes.csv')]
            rel_file = os.path.join(self.temp_dir, "relationships.csv")
            
            if not node_files:
                print("No node CSV files were generated")
                self.status["errors"].append("No node CSV files were generated")
                return False
                
            if not os.path.exists(rel_file):
                print("Warning: No relationship CSV file was generated")
                self.status["warnings"].append("No relationship CSV file was generated")
            
            print(f"Generated {len(node_files)} node CSV files and relationship file")
            return True
        except Exception as e:
            print(f"Error generating Neo4j import files: {str(e)}")
            print(traceback.format_exc())
            self.status["errors"].append(f"Error generating Neo4j import files: {str(e)}")
            return False
            
    async def _run_neo4j_import(self) -> bool:
        """
        Run neo4j-admin import to load data into Neo4j.
        
        Returns:
            True if import successful, False otherwise
        """
        try:
            # Ensure Neo4j import directory exists
            if not os.path.exists(self.neo4j_import_dir):
                try:
                    os.makedirs(self.neo4j_import_dir, exist_ok=True)
                    print(f"Created Neo4j import directory: {self.neo4j_import_dir}")
                except PermissionError:
                    # If we can't create the directory (e.g., on Windows with Program Files), use a temporary directory
                    temp_import_dir = tempfile.mkdtemp(prefix="neo4j_import_dir_")
                    print(f"Permission denied to create {self.neo4j_import_dir}, using temporary directory: {temp_import_dir}")
                    self.neo4j_import_dir = temp_import_dir
            
            # Copy CSV files to Neo4j import directory
            for file in os.listdir(self.temp_dir):
                if file.endswith('.csv'):
                    src = os.path.join(self.temp_dir, file)
                    dst = os.path.join(self.neo4j_import_dir, file)
                    try:
                        shutil.copy2(src, dst)
                        print(f"Copied {file} to Neo4j import directory")
                    except Exception as copy_error:
                        print(f"Error copying file {file}: {str(copy_error)}")
                        self.status["errors"].append(f"Error copying file {file}: {str(copy_error)}")
                        return False
            
            # Use the neo4j_import.sh script for all platforms
            import_script = os.path.join(os.getcwd(), "neo4j_import.sh")
            print(f"CWD: {os.getcwd()}")
            print(f"Import script: {import_script}")
            # Make script executable (this is needed for Linux/macOS)
            if platform.system() != "Windows":
                os.chmod(import_script, 0o755)
            
            # Build command for all platforms
            cmd = [
                import_script,
                "--import-dir", self.neo4j_import_dir,
                "--neo4j-home", self.neo4j_home,
                "--neo4j-bin", self.neo4j_bin,
                "--database", self.database_name
            ]
            
            cmd.append("--force")
                
            # For Windows, we need to use bash to run the shell script
            if platform.system() == "Windows":
                # Check if Git Bash is available
                git_bash_path = "C:\\development\\sdks\\git\\bin\\bash.exe"
                if os.path.exists(git_bash_path):
                    cmd = [git_bash_path, import_script, 
                           "--import-dir", self.neo4j_import_dir,
                           "--neo4j-home", self.neo4j_home,
                           "--neo4j-bin", self.neo4j_bin,
                           "--database", self.database_name]
                   
                    cmd.append("--force")
                else:
                    # If Git Bash is not available, try with WSL bash
                    wsl_bash_path = "wsl"
                    try:
                        # Check if WSL is available
                        subprocess.run([wsl_bash_path, "--version"], 
                                      stdout=subprocess.PIPE, 
                                      stderr=subprocess.PIPE, 
                                      check=True)
                        # Convert Windows paths to WSL paths
                        wsl_import_dir = subprocess.check_output(
                            [wsl_bash_path, "wslpath", self.neo4j_import_dir], 
                            text=True).strip()
                        wsl_neo4j_home = subprocess.check_output(
                            [wsl_bash_path, "wslpath", self.neo4j_home], 
                            text=True).strip()
                        wsl_neo4j_bin = subprocess.check_output(
                            [wsl_bash_path, "wslpath", self.neo4j_bin], 
                            text=True).strip()
                        wsl_import_script = subprocess.check_output(
                            [wsl_bash_path, "wslpath", import_script], 
                            text=True).strip()
                        
                        cmd = [wsl_bash_path, wsl_import_script, 
                               "--import-dir", wsl_import_dir,
                               "--neo4j-home", wsl_neo4j_home,
                               "--neo4j-bin", wsl_neo4j_bin,
                               "--database", self.database_name]
                        if self.drop_existing:
                            cmd.append("--force")
                    except (subprocess.SubprocessError, FileNotFoundError):
                        # If neither Git Bash nor WSL is available, fall back to direct neo4j-admin command
                        print("Neither Git Bash nor WSL is available. Falling back to direct neo4j-admin command.")
                        neo4j_admin_path = os.path.join(self.neo4j_bin, "neo4j-admin.bat")
                        if not os.path.exists(neo4j_admin_path):
                            # Try without .bat extension
                            neo4j_admin_path = os.path.join(self.neo4j_bin, "neo4j-admin")
                            if not os.path.exists(neo4j_admin_path):
                                print(f"Neo4j admin utility not found at {neo4j_admin_path}")
                                self.status["errors"].append(f"Neo4j admin utility not found at {neo4j_admin_path}")
                                return False
                        
                        # Build command for Windows fallback
                        cmd = [
                            neo4j_admin_path,
                            "database",
                            "import",
                            "--database", self.database_name,
                            "--delimiter", ",",
                            "--array-delimiter", ";",
                            "--quote", "\"",
                            "--multiline-fields", "true"
                        ]
                        
                        # Add node files
                        for file in os.listdir(self.neo4j_import_dir):
                            if file.endswith('_nodes.csv'):
                                node_label = file.replace('_nodes.csv', '')
                                cmd.extend(["--nodes", f"{node_label}={os.path.join(self.neo4j_import_dir, file)}"])
                        
                        # Add relationship file if it exists
                        rel_file = os.path.join(self.neo4j_import_dir, "relationships.csv")
                        if os.path.exists(rel_file):
                            cmd.extend(["--relationships", rel_file])
                        
                        if self.drop_existing:
                            cmd.append("--force")
            
            # Run the command
            print(f"Running import command: {' '.join(cmd)}")
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate()
            
            # Process output
            for line in stdout.splitlines():
                print(f"Import: {line}")
            
            if process.returncode != 0:
                print(f"Import failed with code {process.returncode}")
                for line in stderr.splitlines():
                    print(f"Import error: {line}")
                    self.status["errors"].append(f"Import error: {line}")
                return False
            
            print("Import completed successfully")
            return True
        except Exception as e:
            print(f"Error running Neo4j import: {str(e)}")
            print(traceback.format_exc())
            self.status["errors"].append(f"Error running Neo4j import: {str(e)}")
            return False
            
    async def _get_database_stats(self) -> Dict[str, Any]:
        """
        Get statistics about nodes and relationships in the database.
        
        Returns:
            Dict with database statistics
        """
        try:
            # Connect to Neo4j
            uri = self.connection_params.get("uri")
            username = self.connection_params.get("username")
            password = self.connection_params.get("password")
            
            driver = GraphDatabase.driver(uri, auth=(username, password))
            
            node_counts = {}
            relationship_counts = {}
            total_nodes = 0
            total_relationships = 0
            
            with driver.session() as session:
                # Get node counts
                for node in self.schema.get("nodes", []):
                    label = node.get("label")
                    if label:
                        result = session.run(f"MATCH (n:{label}) RETURN count(n) as count")
                        count = result.single()["count"]
                        node_counts[label] = count
                        total_nodes += count
                
                # Get relationship counts
                for rel in self.schema.get("relationships", []):
                    rel_type = rel.get("type")
                    source = rel.get("source") or rel.get("startNode") or rel.get("from_node")
                    target = rel.get("target") or rel.get("endNode") or rel.get("to_node")
                    
                    if all([rel_type, source, target]):
                        result = session.run(
                            f"MATCH (a:{source})-[r:{rel_type}]->(b:{target}) RETURN count(r) as count"
                        )
                        count = result.single()["count"]
                        relationship_counts[f"{source}-{rel_type}->{target}"] = count
                        total_relationships += count
            
            driver.close()
            
            return {
                "has_data": total_nodes > 0,
                "node_count": total_nodes,
                "relationship_count": total_relationships,
                "node_counts": node_counts,
                "relationship_counts": relationship_counts
            }
        except Exception as e:
            print(f"Error getting database stats: {str(e)}")
            print(traceback.format_exc())
            return {
                "has_data": False,
                "node_count": 0,
                "relationship_count": 0,
                "error": str(e)
            }
            
    def _cleanup_temp_files(self):
        """
        Clean up temporary files created during import.
        """
        try:
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                print(f"Cleaned up temporary directory: {self.temp_dir}")
        except Exception as e:
            print(f"Error cleaning up temporary files: {str(e)}")
            self.status["warnings"].append(f"Error cleaning up temporary files: {str(e)}")

        
    # The _initialize_loaders method has been removed as it's no longer needed with the neo4j-admin approach
            
    async def load_data(self, db: SessionLocal) -> Dict[str, Any]:
        """
        Load data from CSV file into Neo4j based on schema using neo4j-admin import.
        
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
            
            # Initialize Neo4j configuration
            config_initialized = await self._initialize_neo4j_config()
            if not config_initialized:
                self.status["status"] = "failed"
                self.status["end_time"] = datetime.now().isoformat()
                return self.status
            
            # Debug schema structure
            print("===== SCHEMA STRUCTURE =====")
            print(f"Schema ID: {self.schema_id}")
            
            # Log nodes defined in schema
            nodes = self.schema.get("nodes", [])
            print(f"Schema contains {len(nodes)} node types:")
            for idx, node in enumerate(nodes):
                node_label = node.get("label")
                node_props = node.get("properties", {})
                print(f"Node {idx+1}: {node_label} with {len(node_props)} properties")
            
            # Log relationships defined in schema
            relationships = self.schema.get("relationships", [])
            print(f"Schema contains {len(relationships)} relationship types:")
            for idx, rel in enumerate(relationships):
                rel_type = rel.get("type")
                source = rel.get("source") or rel.get("startNode") or rel.get("from_node")
                target = rel.get("target") or rel.get("endNode") or rel.get("to_node")
                print(f"Relationship {idx+1}: {source}-[{rel_type}]->{target}")
            
            # Generate Neo4j import files
            print(f"Starting data loading from {self.data_path}")
            files_generated = await self._generate_neo4j_files()
            if not files_generated:
                self.status["status"] = "failed"
                self.status["end_time"] = datetime.now().isoformat()
                return self.status
            
            # Run Neo4j import
            import_successful = await self._run_neo4j_import()
            if not import_successful:
                self.status["status"] = "failed"
                self.status["end_time"] = datetime.now().isoformat()
                return self.status
            
            # Get database statistics
            print("Inspecting database after data loading...")
            stats = await self._get_database_stats()
            
            # Update status with database statistics
            self.status["nodes_created"] = stats.get("node_count", 0)
            self.status["relationships_created"] = stats.get("relationship_count", 0)
            self.status["node_counts"] = stats.get("node_counts", {})
            self.status["relationship_counts"] = stats.get("relationship_counts", {})
            
            # Clean up temporary files
            self._cleanup_temp_files()
            
            # Set status to completed
            self.status["status"] = "completed"
            self.status["end_time"] = datetime.now().isoformat()
            self.status["success"] = True
            
            print(f"Data loading completed successfully")
            print(f"Created {self.status['nodes_created']} nodes and {self.status['relationships_created']} relationships")
            
            return self.status
            
        except Exception as e:
            print(f"Unhandled error in load_data: {str(e)}")
            print(traceback.format_exc())
            self.status["errors"].append(f"Unhandled error in load_data: {str(e)}")
            self.status["status"] = "failed"
            self.status["end_time"] = datetime.now().isoformat()
            
            # Clean up temporary files
            self._cleanup_temp_files()
            
            return self.status
