from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime
import json
import uuid
import time
import asyncio
import traceback

# Updated import to use GraphIngestionJob instead of IngestionJob
from ..models import get_db, GraphIngestionJob, Schema, User
from ..auth import has_any_permission
from .graphschemaapi import load_data_from_schema as graphschema_load_data
from ..db_config import engine
from sqlalchemy.orm import sessionmaker

# Create a session factory for background tasks
BackgroundSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Models
class JobStatus(BaseModel):
    id: str
    schema_id: int
    job_type: str  # "load_data" or "clean_data"
    status: str  # "pending", "running", "completed", "failed"
    progress: float  # 0.0 to 1.0
    message: str
    created_at: datetime
    updated_at: datetime
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class JobCreateRequest(BaseModel):
    schema_id: int
    job_type: str
    params: Dict[str, Any] = {}

class LoadDataRequest(BaseModel):
    schema_id: int
    graph_name: str = "default_graph"
    drop_existing: bool = False
    batch_size: int = 1000

class CleanDataRequest(BaseModel):
    schema_id: int
    graph_name: str = "default_graph"

# Router
router = APIRouter(prefix="/processing-jobs", tags=["processing_jobs"])

# Helper functions
def get_all_jobs(db: Session, schema_id: Optional[int] = None, job_type: Optional[str] = None):
    """
    Get all jobs, optionally filtered by schema ID or job type
    """
    # Updated to use GraphIngestionJob
    query = db.query(GraphIngestionJob)
    
    if schema_id:
        # Direct filter on schema_id field
        query = query.filter(GraphIngestionJob.schema_id == schema_id)
        
    if job_type:
        # Direct filter on job_type field
        query = query.filter(GraphIngestionJob.job_type == job_type)
        
    return query.order_by(GraphIngestionJob.created_at.desc()).all()

def create_job(db: Session, schema_id: int, job_type: str, params: Dict[str, Any] = {}):
    """
    Create a new job in the database
    """
    # First check if schema exists
    schema = db.query(Schema).filter(Schema.id == schema_id).first()
    if not schema:
        print(f"Schema with ID {schema_id} not found")
        raise HTTPException(status_code=404, detail=f"Schema with ID {schema_id} not found")
    
    # Create job record using GraphIngestionJob
    job_id = str(uuid.uuid4())
    new_job = GraphIngestionJob(
        id=job_id,
        schema_id=schema_id,  # Direct field
        job_type=job_type,    # No prefix needed
        status="pending",
        progress=0,
        message=f"Initializing {job_type} job for schema: {schema.name}",
        params=json.dumps(params) if params else None
    )
    
    db.add(new_job)
    db.commit()
    
    return job_id

def format_job_response(job: GraphIngestionJob) -> JobStatus:
    """
    Format job database record into API response format
    """
    # Simplified since we have direct fields now
    result = None
    if job.params:
        try:
            result = json.loads(job.params)
        except:
            result = {"raw": job.params}
    
    return JobStatus(
        id=job.id,
        schema_id=job.schema_id,
        job_type=job.job_type,
        status=job.status,
        progress=float(job.progress) / 100 if job.progress is not None else 0.0,  # Convert from 0-100 to 0.0-1.0
        message=job.message or "",
        created_at=job.created_at,
        updated_at=job.updated_at,
        result=result,
        error=job.error
    )

# Background task for processing Neo4j data loading
async def process_load_data_job(job_id: str, schema_id: int, graph_name: str, drop_existing: bool, db: Session):
    """
    Background task to load data into Neo4j
    """
    # Create a new session specifically for this background task
    task_db = BackgroundSessionLocal()
    
    try:
        # Get the job using the new session
        job = task_db.query(GraphIngestionJob).filter(GraphIngestionJob.id == job_id).first()
        if not job:
            print(f"Error: Job with ID {job_id} not found")
            return
        
        # Update job status to running
        job.status = "running"
        job.started_at = datetime.now()
        job.message = f"Starting data load for schema ID {schema_id} to graph {graph_name}"
        job.progress = 5
        task_db.commit()
        
        try:
            # Call the existing load_data_from_schema function with our new session
            result = await graphschema_load_data(
                schema_id=schema_id,
                graph_name=graph_name,
                drop_existing=drop_existing,
                db=task_db,  # Pass the new session
                current_user=None  # We're in a background task, no user context
            )
            
            # Update job with success
            job = task_db.query(GraphIngestionJob).filter(GraphIngestionJob.id == job_id).first()
            if job and job.status != "cancelled":  # Only update if job wasn't cancelled
                job.status = "completed"
                job.completed_at = datetime.now()
                job.progress = 100
                job.message = f"Successfully loaded data for schema ID {schema_id} to graph {graph_name}"
                
                # Store node and relationship counts from the result
                if "result" in result and result["result"]:
                    result_data = result["result"]
                    if "node_count" in result_data:
                        job.node_count = result_data["node_count"]
                    if "relationship_count" in result_data:
                        job.relationship_count = result_data["relationship_count"]
                        
                    # Store the full result as JSON
                    job.result = json.dumps(result_data)
                
                task_db.commit()
                print(f"Job {job_id} completed successfully")
            else:
                print(f"Job {job_id} was cancelled or not found, not updating to completed")
                
        except Exception as e:
            # Update job with failure
            job = task_db.query(GraphIngestionJob).filter(GraphIngestionJob.id == job_id).first()
            if job and job.status != "cancelled":  # Only update if job wasn't cancelled
                job.status = "failed"
                job.completed_at = datetime.now()
                job.progress = 0
                job.message = f"Failed to load data: {str(e)}"
                job.error = str(e)
                task_db.commit()
                print(f"Job {job_id} failed: {str(e)}")
                print(traceback.format_exc())
            else:
                print(f"Job {job_id} was cancelled or not found, not updating to failed")
    except Exception as e:
        print(f"Error in process_load_data_job: {str(e)}")
        print(traceback.format_exc())
    finally:
        # Always close the task-specific session
        task_db.close()

# Background task for cleaning Neo4j data
async def process_clean_data_job(job_id: str, schema_id: int, graph_name: str, db: Session):
    """
    Background task to clean data from Neo4j
    """
    # Create a new session specifically for this background task
    task_db = BackgroundSessionLocal()
    
    try:
        # Get the job using the new session
        job = task_db.query(GraphIngestionJob).filter(GraphIngestionJob.id == job_id).first()
        if not job:
            print(f"Error: Job with ID {job_id} not found")
            return
        
        # Update job status to running
        job.status = "running"
        job.started_at = datetime.now()
        job.message = f"Starting data cleaning for schema ID {schema_id} from graph {graph_name}"
        job.progress = 5
        task_db.commit()
        
        try:
            # Get schema record
            schema = task_db.query(Schema).filter(Schema.id == schema_id).first()
            if not schema:
                raise ValueError(f"Schema with ID {schema_id} not found")
                
            # Get database connection info
            from .database_api import get_database_config, parse_connection_params
            db_config = get_database_config()
            uri, username, password = parse_connection_params(db_config)
            
            # Parse schema data
            schema_data = json.loads(schema.schema)
            
            # Connect to Neo4j
            from neo4j import GraphDatabase
            driver = GraphDatabase.driver(uri, auth=(username, password))
            
            # Update job progress
            job = task_db.query(GraphIngestionJob).filter(GraphIngestionJob.id == job_id).first()
            if job and job.status == "cancelled":
                driver.close()
                return
                
            job.progress = 10
            job.message = "Connected to Neo4j, preparing to clean data"
            task_db.commit()
            
            # Get node and relationship counts before cleaning
            with driver.session() as session:
                # Count total nodes
                result = session.run("MATCH (n) RETURN count(n) as count")
                total_nodes_before = result.single()["count"]
                
                # Count total relationships
                result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
                total_relationships_before = result.single()["count"]
            
            # Update job progress
            job = task_db.query(GraphIngestionJob).filter(GraphIngestionJob.id == job_id).first()
            if job and job.status == "cancelled":
                driver.close()
                return
                
            job.progress = 20
            job.message = f"Found {total_nodes_before} nodes and {total_relationships_before} relationships to clean"
            task_db.commit()
            
            # Clean data by deleting all nodes and relationships for this schema
            with driver.session() as session:
                # Delete all relationships first
                session.run("MATCH ()-[r]->() DELETE r")
                
                # Update job progress
                job = task_db.query(GraphIngestionJob).filter(GraphIngestionJob.id == job_id).first()
                if job and job.status == "cancelled":
                    driver.close()
                    return
                    
                job.progress = 60
                job.message = "Deleted all relationships, now deleting nodes"
                task_db.commit()
                
                # Delete all nodes
                session.run("MATCH (n) DELETE n")
            
            # Close Neo4j connection
            driver.close()
            
            # Update job with success
            job = task_db.query(GraphIngestionJob).filter(GraphIngestionJob.id == job_id).first()
            if job and job.status != "cancelled":  # Only update if job wasn't cancelled
                job.status = "completed"
                job.completed_at = datetime.now()
                job.progress = 100
                job.message = f"Successfully cleaned data for schema ID {schema_id} from graph {graph_name}"
                
                # Store the result
                result_data = {
                    "nodes_removed": total_nodes_before,
                    "relationships_removed": total_relationships_before
                }
                job.result = json.dumps(result_data)
                
                task_db.commit()
                print(f"Job {job_id} completed successfully")
            else:
                print(f"Job {job_id} was cancelled or not found, not updating to completed")
                
        except Exception as e:
            # Update job with failure
            job = task_db.query(GraphIngestionJob).filter(GraphIngestionJob.id == job_id).first()
            if job and job.status != "cancelled":  # Only update if job wasn't cancelled
                job.status = "failed"
                job.completed_at = datetime.now()
                job.progress = 0
                job.message = f"Failed to clean data: {str(e)}"
                job.error = str(e)
                task_db.commit()
                print(f"Job {job_id} failed: {str(e)}")
                print(traceback.format_exc())
            else:
                print(f"Job {job_id} was cancelled or not found, not updating to failed")
    except Exception as e:
        print(f"Error in process_clean_data_job: {str(e)}")
        print(traceback.format_exc())
    finally:
        # Always close the task-specific session
        task_db.close()

# API Routes
@router.get("", response_model=List[JobStatus])
async def get_jobs(
    schema_id: Optional[int] = None,
    job_type: Optional[str] = None,
    current_user: User = Depends(has_any_permission(["kginsights:read"])),
    db: Session = Depends(get_db)
):
    """
    Get all KGInsights processing jobs, optionally filtered by schema ID or job type
    """
    print(f"DEBUG: get_jobs endpoint called with schema_id={schema_id}, job_type={job_type}")
    jobs = get_all_jobs(db, schema_id, job_type)
    print(f"DEBUG: Found {len(jobs)} jobs")
    return [format_job_response(job) for job in jobs]

@router.get("/{job_id}", response_model=JobStatus)
async def get_job(
    job_id: str,
    current_user: User = Depends(has_any_permission(["kginsights:read"])),
    db: Session = Depends(get_db)
):
    """
    Get status of a specific job
    """
    # Updated to use GraphIngestionJob
    job = db.query(GraphIngestionJob).filter(GraphIngestionJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job with ID {job_id} not found")
        
    return format_job_response(job)

@router.post("", response_model=JobStatus)
async def create_new_job(
    job_request: JobCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(has_any_permission(["kginsights:write"])),
    db: Session = Depends(get_db)
):
    """
    Create a new processing job
    """
    job_id = create_job(db, job_request.schema_id, job_request.job_type, job_request.params)
    
    # Get the created job
    job = db.query(GraphIngestionJob).filter(GraphIngestionJob.id == job_id).first()
    
    # TODO: Add background task handling for the job
    # background_tasks.add_task(process_job, job_id, job_request.job_type, job_request.params)
    
    return format_job_response(job)

@router.post("/load-data", response_model=JobStatus)
async def load_data_to_neo4j(
    request: LoadDataRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(has_any_permission(["kginsights:write"])),
    db: Session = Depends(get_db)
):
    """
    Load data into Neo4j for a specific schema
    """
    # Create a new job for loading data
    job_id = create_job(
        db, 
        request.schema_id, 
        "load_data", 
        {
            "graph_name": request.graph_name,
            "drop_existing": request.drop_existing,
            "batch_size": request.batch_size
        }
    )
    
    # Get the created job
    job = db.query(GraphIngestionJob).filter(GraphIngestionJob.id == job_id).first()
    
    # Start the background task for loading data using FastAPI's background_tasks
    background_tasks.add_task(
        process_load_data_job,
        job_id=job_id,
        schema_id=request.schema_id,
        graph_name=request.graph_name,
        drop_existing=request.drop_existing,
        db=db
    )
    
    return format_job_response(job)

@router.post("/clean-data", response_model=JobStatus)
async def clean_data_from_neo4j(
    request: CleanDataRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(has_any_permission(["kginsights:write"])),
    db: Session = Depends(get_db)
):
    """
    Clean data from Neo4j for a specific schema
    """
    # Create a new job for cleaning data
    job_id = create_job(
        db, 
        request.schema_id, 
        "clean_data", 
        {
            "graph_name": request.graph_name
        }
    )
    
    # Get the created job
    job = db.query(GraphIngestionJob).filter(GraphIngestionJob.id == job_id).first()
    
    # Start the background task for cleaning data using FastAPI's background_tasks
    background_tasks.add_task(
        process_clean_data_job,
        job_id=job_id,
        schema_id=request.schema_id,
        graph_name=request.graph_name,
        db=db
    )
    
    return format_job_response(job)

@router.delete("/{job_id}", response_model=Dict[str, str])
async def cancel_job(
    job_id: str,
    current_user: User = Depends(has_any_permission(["kginsights:write"])),
    db: Session = Depends(get_db)
):
    """
    Cancel a running job
    """
    # Check if the job ID starts with "temp-" which indicates a temporary frontend job
    if job_id.startswith("temp-"):
        # For temporary jobs that don't exist in the database, return a success message
        # This helps the frontend clean up its state without showing an error
        return {"message": "Temporary job removed successfully", "status": "not_found"}
        
    job = db.query(GraphIngestionJob).filter(GraphIngestionJob.id == job_id).first()
    if not job:
        # Instead of raising a 404 error, return a message that can be used by the frontend
        # to clean up its state
        return {"message": f"Job with ID {job_id} not found", "status": "not_found"}
        
    if job.status not in ["pending", "running"]:
        return {"message": f"Job is already in {job.status} state and cannot be cancelled"}
    
    job.status = "cancelled"
    job.message = "Job cancelled by user"
    job.updated_at = datetime.now()
    db.commit()
    
    return {"message": "Job cancelled successfully", "status": "cancelled"}
