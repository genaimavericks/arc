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
    # Get the job
    job = db.query(GraphIngestionJob).filter(GraphIngestionJob.id == job_id).first()
    if not job:
        print(f"Error: Job with ID {job_id} not found")
        return
    
    try:
        # Update job status to running
        job.status = "running"
        job.started_at = datetime.now()
        job.message = f"Starting data load for schema ID {schema_id} to graph {graph_name}"
        job.progress = 5
        db.commit()
        
        # Create a new session for the background task
        # This is necessary because we can't reuse the Depends(get_db) session
        from sqlalchemy.orm import sessionmaker
        from ..db_config import engine
        
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        task_db = SessionLocal()
        
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
            job.status = "completed"
            job.completed_at = datetime.now()
            job.progress = 100
            job.message = f"Successfully loaded data for schema ID {schema_id} to graph {graph_name}"
            
            # Store node and relationship counts from the result
            if result and isinstance(result, dict):
                # Extract the actual result data - handle nested structure
                result_data = result.get("result", result)
                
                # Store counts
                job.node_count = result_data.get("nodes_created", 0)
                job.relationship_count = result_data.get("relationships_created", 0)
                
                # Store detailed counts as JSON in the result field
                job_result = {}
                if "node_counts" in result_data:
                    job_result["node_counts"] = result_data["node_counts"]
                if "relationship_counts" in result_data:
                    job_result["relationship_counts"] = result_data["relationship_counts"]
                    
                # Log the counts for debugging
                print(f"DEBUG: Storing job counts - nodes: {job.node_count}, relationships: {job.relationship_count}")
                
                if job_result:
                    job.result = json.dumps(job_result)
            db.commit()
            
            # TEMP: Generate prompt templates and sample queries after data load
            try:
                schema_db = db.query(Schema).filter(Schema.id == schema_id).first()
                if schema_db and schema_db.schema and schema_db.db_id:
                    from api.kgdatainsights.data_insights_api import get_schema_aware_assistant
                    assistant = get_schema_aware_assistant(schema_db.db_id, schema_id, schema_db.schema)
                    assistant._ensure_prompt()
                    print(f"Prompt templates and queries generated for schema_id={schema_id}")
                else:
                    print(f"Could not generate prompts: Schema record not found or incomplete for schema_id={schema_id}")
            except Exception as e:
                print(f"Error generating prompts after data load for schema_id={schema_id}: {e}")
        
        finally:
            # Make sure to close the new session
            task_db.close()
        
    except Exception as e:
        # Update job with error
        job.status = "failed"
        job.completed_at = datetime.now()
        job.error = str(e)
        job.message = f"Error loading data: {str(e)}"
        print(f"Error in process_load_data_job: {str(e)}")
        print(traceback.format_exc())
        db.commit()

# Background task for cleaning Neo4j data
async def process_clean_data_job(job_id: str, schema_id: int, graph_name: str, db: Session):
    """
    Background task to clean data from Neo4j
    """
    # Get the job
    job = db.query(GraphIngestionJob).filter(GraphIngestionJob.id == job_id).first()
    if not job:
        print(f"Error: Job with ID {job_id} not found")
        return
    
    try:
        # Update job status to running
        job.status = "running"
        job.started_at = datetime.now()
        job.message = f"Starting data cleaning for schema ID {schema_id} from graph {graph_name}"
        job.progress = 5
        db.commit()
        
        # Create a new session for the background task
        from sqlalchemy.orm import sessionmaker
        from ..db_config import engine
        
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        task_db = SessionLocal()
        
        try:
            # Get the schema
            schema = task_db.query(Schema).filter(Schema.id == schema_id).first()
            if not schema:
                raise ValueError(f"Schema with ID {schema_id} not found")
            
            # Get Neo4j connection details from configuration
            from .database_api import get_database_config, parse_connection_params
            db_config = get_database_config()
            
            # Get the default graph configuration
            default_graph = db_config.get("default_graph", {})
            
            # Connect to Neo4j using the default graph configuration
            from neo4j import GraphDatabase
            driver = GraphDatabase.driver(
                default_graph.get("uri", ""),
                auth=(default_graph.get("username", ""), default_graph.get("password", ""))
            )
            
            # Clean data
            with driver.session(database=default_graph.get("database", None)) as session:
                # Parse schema to get node labels
                schema_json = json.loads(schema.schema)
                node_labels = [node["label"] for node in schema_json.get("nodes", [])]
                
                # Update job progress
                job.progress = 20
                job.message = f"Identified {len(node_labels)} node types to clean"
                task_db.commit()
                print(f"DEBUG: Starting clean job for {len(node_labels)} node types")
                
                total_deleted = 0
                for i, label in enumerate(node_labels):
                    # Update progress for each node type
                    progress_percent = 20 + int((i / max(1, len(node_labels))) * 70)
                    job.progress = progress_percent
                    job.message = f"Cleaning nodes with label '{label}'"
                    task_db.commit()
                    print(f"DEBUG: Cleaning nodes with label '{label}', progress: {progress_percent}%")
                    
                    try:
                        # Execute the deletion query
                        result = session.run(f"MATCH (n:{label}) DETACH DELETE n")
                        summary = result.consume()
                        nodes_deleted = summary.counters.nodes_deleted
                        total_deleted += nodes_deleted
                        print(f"DEBUG: Deleted {nodes_deleted} nodes with label '{label}'")
                    except Exception as e:
                        print(f"ERROR deleting nodes with label '{label}': {str(e)}")
                        # Continue with other labels even if one fails
                
                # Update job status to completed
                print(f"DEBUG: Clean job completed, total deleted: {total_deleted} nodes")
                
                # Get a fresh reference to the job from the main db connection
                main_job = db.query(GraphIngestionJob).filter(GraphIngestionJob.id == job_id).first()
                if main_job:
                    main_job.status = "completed"
                    main_job.completed_at = datetime.now()
                    main_job.progress = 100
                    main_job.message = f"Successfully cleaned {total_deleted} nodes from the graph"
                    
                    # Reset node and relationship counts to 0
                    main_job.node_count = 0
                    main_job.relationship_count = 0
                    
                    # Update the result with empty counts
                    main_job.result = json.dumps({
                        "nodes_deleted": total_deleted,
                        "node_types_cleaned": len(node_labels),
                        "node_counts": {},
                        "relationship_counts": {}
                    })
                    db.commit()
                    print(f"DEBUG: Main job status updated to completed in main DB connection")
                    print(f"DEBUG: Reset node_count and relationship_count to 0")
                
                # Also update in the task_db connection
                job.status = "completed"
                job.completed_at = datetime.now()
                job.progress = 100
                job.message = f"Successfully cleaned {total_deleted} nodes from the graph"
                
                # Reset node and relationship counts to 0
                job.node_count = 0
                job.relationship_count = 0
                
                # Update the result with empty counts
                job.result = json.dumps({
                    "nodes_deleted": total_deleted,
                    "node_types_cleaned": len(node_labels),
                    "node_counts": {},
                    "relationship_counts": {}
                })
                task_db.commit()
                print(f"DEBUG: Job status updated to completed in task_db connection")
            
            driver.close()
        finally:
            # Make sure to close the new session
            task_db.close()
        
    except Exception as e:
        # Update job with error
        print(f"Error in process_clean_data_job: {str(e)}")
        print(traceback.format_exc())
        
        try:
            # Make sure job is marked as failed
            job = db.query(GraphIngestionJob).filter(GraphIngestionJob.id == job_id).first()
            if job:
                job.status = "failed"
                job.error = str(e)
                job.message = f"Failed to clean data: {str(e)[:100]}"
                db.commit()
                print(f"DEBUG: Job marked as failed due to error")
        except Exception as inner_e:
            print(f"Error updating job status: {str(inner_e)}")
        
        db.commit()

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
    
    # Start the background task for loading data
    # Use asyncio.create_task instead of background_tasks.add_task for async functions
    asyncio.create_task(
        process_load_data_job(
            job_id=job_id,
            schema_id=request.schema_id,
            graph_name=request.graph_name,
            drop_existing=request.drop_existing,
            db=db
        )
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
    
    # Start the background task for cleaning data
    # Use asyncio.create_task instead of background_tasks.add_task for async functions
    asyncio.create_task(
        process_clean_data_job(
            job_id=job_id,
            schema_id=request.schema_id,
            graph_name=request.graph_name,
            db=db
        )
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
    # Updated to use GraphIngestionJob
    job = db.query(GraphIngestionJob).filter(GraphIngestionJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job with ID {job_id} not found")
        
    if job.status in ["completed", "failed"]:
        return {"message": f"Job is already in {job.status} state and cannot be cancelled"}
        
    job.status = "cancelled"
    job.message = "Job cancelled by user"
    job.updated_at = datetime.now()
    
    db.commit()
    
    return {"message": "Job cancelled successfully"}
