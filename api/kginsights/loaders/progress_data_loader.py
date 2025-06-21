"""
Enhanced DataLoader with progress tracking capabilities
"""
import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session as SessionLocal

from api.utils.thread_pool import run_in_threadpool
from api.utils.job_progress import JobProgressTracker
from api.models import Schema
from .data_loader import DataLoader

class ProgressDataLoader(DataLoader):
    """
    Enhanced DataLoader with progress tracking capabilities.
    Extends the base DataLoader to provide detailed progress updates during CSV generation and Neo4j import.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize with the same parameters as DataLoader"""
        super().__init__(*args, **kwargs)
        self.progress_tracker = None
        
    async def initialize_progress_tracker(self, db: SessionLocal):
        """
        Initialize the progress tracker if job_id is provided
        
        Args:
            db: Database session
        """
        if self.job_id:
            self.progress_tracker = JobProgressTracker(self.job_id, db)
            
    async def load_data(self, db: SessionLocal) -> Dict[str, Any]:
        """
        Load data with progress tracking
        
        Args:
            db: Database session
            
        Returns:
            Dict with loading results
        """
        # Initialize progress tracker
        await self.initialize_progress_tracker(db)
        
        # Start the normal data loading process
        self.status["start_time"] = datetime.now().isoformat()
        self.status["status"] = "running"
        
        try:
            # Load schema - run in thread pool to avoid blocking
            if self.progress_tracker:
                await self.progress_tracker.update_stage("schema_loading", 0, "Loading schema configuration")
                
            # Don't use asyncio.run inside a thread pool - it creates a new event loop which can cause deadlocks
            schema_loaded = await self._load_schema(db)
            
            if not schema_loaded:
                self.status["status"] = "failed"
                self.status["end_time"] = datetime.now().isoformat()
                if self.progress_tracker:
                    await self.progress_tracker.fail_job(f"Failed to load schema: {self.status['errors'][-1] if self.status['errors'] else 'Unknown error'}")
                return self.status
            
            if self.progress_tracker:
                await self.progress_tracker.update_stage("schema_loading", 100, "Schema configuration loaded")
                
            # Validate data path
            if self.progress_tracker:
                await self.progress_tracker.update_stage("data_validation", 0, "Validating data files")
                
            # Call the method directly without nesting asyncio.run
            data_path_valid = await self._validate_data_path()
            
            if not data_path_valid:
                self.status["status"] = "failed"
                self.status["end_time"] = datetime.now().isoformat()
                if self.progress_tracker:
                    await self.progress_tracker.fail_job(f"Failed to validate data path: {self.status['errors'][-1] if self.status['errors'] else 'Unknown error'}")
                return self.status
            
            if self.progress_tracker:
                await self.progress_tracker.update_stage("data_validation", 100, "Data files validated")
                
            # Initialize Neo4j configuration
            config_initialized = await self._initialize_neo4j_config()
            
            if not config_initialized:
                self.status["status"] = "failed"
                self.status["end_time"] = datetime.now().isoformat()
                if self.progress_tracker:
                    await self.progress_tracker.fail_job(f"Failed to initialize Neo4j configuration: {self.status['errors'][-1] if self.status['errors'] else 'Unknown error'}")
                return self.status
            
            # Generate Neo4j import files - run in thread pool to avoid blocking
            if self.progress_tracker:
                await self.progress_tracker.update_stage("csv_generation", 0, "Starting CSV file generation")
                
            print(f"Starting data loading from {self.data_path}")
            
            # Override _generate_neo4j_files to track progress
            original_generate_files = self._generate_neo4j_files
            
            async def generate_files_with_progress():
                # Track progress during CSV generation
                if self.progress_tracker:
                    await self.progress_tracker.update_stage("csv_generation", 20, "Processing node data")
                
                result = await original_generate_files()
                
                if result and self.progress_tracker:
                    await self.progress_tracker.update_stage("csv_generation", 100, "CSV files generated")
                
                return result
            
            # Replace the method temporarily
            self._generate_neo4j_files = generate_files_with_progress
            
            files_generated = await run_in_threadpool(lambda: asyncio.run(self._generate_neo4j_files()))
            
            # Restore the original method
            self._generate_neo4j_files = original_generate_files
            
            if not files_generated:
                self.status["status"] = "failed"
                self.status["end_time"] = datetime.now().isoformat()
                if self.progress_tracker:
                    await self.progress_tracker.fail_job(f"Failed to generate Neo4j files: {self.status['errors'][-1] if self.status['errors'] else 'Unknown error'}")
                return self.status
            
            # Run Neo4j import - run in thread pool to avoid blocking
            if self.progress_tracker:
                await self.progress_tracker.update_stage("neo4j_import", 0, "Starting Neo4j data import")
            
            # Override _run_neo4j_import to track progress
            original_run_import = self._run_neo4j_import
            
            async def run_import_with_progress():
                # Track progress during Neo4j import
                if self.progress_tracker:
                    await self.progress_tracker.update_stage("neo4j_import", 20, "Importing node data")
                    # We'll simulate progress updates since we can't get real-time progress from neo4j-admin
                    await asyncio.sleep(1)  # Small delay to avoid too many DB updates
                    await self.progress_tracker.update_stage("neo4j_import", 50, "Importing relationship data")
                
                result = await original_run_import()
                
                if result and self.progress_tracker:
                    await self.progress_tracker.update_stage("neo4j_import", 100, "Neo4j import completed")
                
                return result
            
            # Replace the method temporarily
            self._run_neo4j_import = run_import_with_progress
            
            import_successful = await run_in_threadpool(lambda: asyncio.run(self._run_neo4j_import()))
            
            # Restore the original method
            self._run_neo4j_import = original_run_import
            
            if not import_successful:
                self.status["status"] = "failed"
                self.status["end_time"] = datetime.now().isoformat()
                if self.progress_tracker:
                    await self.progress_tracker.fail_job(f"Failed to import data into Neo4j: {self.status['errors'][-1] if self.status['errors'] else 'Unknown error'}")
                return self.status
            
            # Start Neo4j to ensure the database is available - run in thread pool to avoid blocking
            if self.progress_tracker:
                await self.progress_tracker.update_stage("neo4j_startup", 0, "Starting Neo4j database")
                
            print("Starting Neo4j service to make the imported database available...")
            neo4j_started = await run_in_threadpool(lambda: asyncio.run(self._start_neo4j()))
            
            if not neo4j_started:
                print("WARNING: Neo4j may not have started properly. You might need to start it manually.")
                self.status["warnings"].append("Neo4j may not have started properly. Consider restarting it manually.")
            
            if self.progress_tracker:
                await self.progress_tracker.update_stage("neo4j_startup", 100, "Neo4j database started")
                
            # Get database statistics - run in thread pool to avoid blocking
            if self.progress_tracker:
                await self.progress_tracker.update_stage("stats_collection", 0, "Collecting database statistics")
                
            print("Inspecting database after data loading...")
            stats = await run_in_threadpool(lambda: asyncio.run(self._get_database_stats()))
            
            if self.progress_tracker:
                await self.progress_tracker.update_stage("stats_collection", 100, "Database statistics collected")
                
            # Update status with database statistics
            self.status["nodes_created"] = stats.get("node_count", 0)
            self.status["relationships_created"] = stats.get("relationship_count", 0)
            self.status["node_counts"] = stats.get("node_counts", {})
            self.status["relationship_counts"] = stats.get("relationship_counts", {})
            
            # The rest of the method remains the same as in the original DataLoader
            # but we'll update the job status using our progress tracker instead
            
            # Mark the job as completed using the progress tracker
            if stats.get("has_data", False) and self.schema_id and self.progress_tracker:
                result_data = {
                    "nodes_created": self.status["nodes_created"],
                    "relationships_created": self.status["relationships_created"],
                    "node_counts": self.status.get("node_counts", {}),
                    "relationship_counts": self.status.get("relationship_counts", {})
                }
                
                # Call complete_job with the result data dictionary
                await self.progress_tracker.complete_job(result_data)
                
                # Update the schema record to mark data as loaded
                schema_record = db.query(Schema).filter(Schema.id == self.schema_id).first()
                if schema_record:
                    schema_record.db_loaded = 'yes'
                    await run_in_threadpool(lambda: db.commit())
                    print(f"Updated schema record {self.schema_id}: db_loaded set to 'yes'")
            
            # Update final status
            self.status["status"] = "completed"
            self.status["end_time"] = datetime.now().isoformat()
            
            # Clean up temporary files
            await run_in_threadpool(lambda: self._cleanup_temp_files())
            
            return self.status
            
        except Exception as e:
            import traceback
            print(f"Error in load_data: {str(e)}")
            print(traceback.format_exc())
            
            self.status["status"] = "failed"
            self.status["errors"].append(str(e))
            self.status["end_time"] = datetime.now().isoformat()
            
            if self.progress_tracker:
                await self.progress_tracker.fail_job(f"Error during data loading: {str(e)}")
                
            return self.status
