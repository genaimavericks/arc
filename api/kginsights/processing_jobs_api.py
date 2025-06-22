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
from .neo4j_config import get_neo4j_connection_params
from ..db_config import SessionLocal


async def generate_prompts_async(schema_id: int, job_id: str = None):
    """
    Asynchronous function to generate prompt templates and sample queries.
    This runs in a background task to avoid blocking API calls.
    
    Args:
        schema_id: ID of the schema to generate prompts for
        job_id: ID of the job to update progress for
    """
    print(f"Starting async prompt generation for schema_id={schema_id}, job_id={job_id}")
    
    # Initialize progress tracker if job_id is provided
    progress_tracker = None
    if job_id:
        from api.utils.job_progress import JobProgressTracker
        
        # Get the schema record from the database
        from api.db_config import SessionLocal
        from api.models import Schema
        import traceback
        
        db = SessionLocal()
        
        # Create the progress tracker with the database session
        # The JobProgressTracker is already initialized with DATA_LOADING_STAGES from constants.py
        progress_tracker = JobProgressTracker(job_id, db)
        
        # Initialize the job with the existing stages
        await progress_tracker.initialize_job()
        
        # Mark data_loading stages as complete since we're only doing prompt generation
        await progress_tracker.update_stage("schema_loading", 100, "Schema loading complete")
        await progress_tracker.update_stage("data_validation", 100, "Data validation complete")
        await progress_tracker.update_stage("csv_generation", 100, "CSV generation complete")
        await progress_tracker.update_stage("neo4j_import", 100, "Neo4j import complete")
        await progress_tracker.update_stage("neo4j_startup", 100, "Neo4j startup complete")
        await progress_tracker.update_stage("stats_collection", 100, "Statistics collection complete")
        await progress_tracker.update_stage("prompt_generation_prep", 100, "Prompt generation preparation complete")
    
    # We already have a database session if progress_tracker is initialized
    # Otherwise, create a new one
    from api.db_config import SessionLocal
    from api.models import Schema
    import traceback
    
    # Use the existing db session if we have a progress tracker, otherwise create a new one
    db_session = db if progress_tracker else SessionLocal()
    
    try:
        schema_db = db_session.query(Schema).filter(Schema.id == schema_id).first()
        
        if schema_db and schema_db.schema and schema_db.db_id:
            # Update progress to prompt generation stage
            if progress_tracker:
                await progress_tracker.update_stage("prompt_generation", 10, "Starting Cypher prompt generation")
                
            from api.kgdatainsights.data_insights_api import get_schema_aware_assistant
            assistant = get_schema_aware_assistant(schema_db.db_id, schema_id, schema_db.schema)
            
            # Generate prompts with progress updates
            try:
                # Pass the progress tracker to _ensure_prompt
                assistant._ensure_prompt(progress_tracker)
                
                # Update progress after initiating prompt generation - start with just the first stage
                if progress_tracker:
                    # Only update the prompt_generation stage initially
                    await progress_tracker.update_stage("prompt_generation", 10, "Starting Cypher prompt generation")
                    
                    # Set other stages to 0% to show they're coming up next
                    await progress_tracker.update_stage("qa_generation", 0, "Waiting for Cypher prompt generation to complete")
                    await progress_tracker.update_stage("query_generation", 0, "Waiting for QA prompt generation to complete")
                    
                    # DO NOT mark the job as complete yet - the prompt generation will continue in the background
                    # and the job will be marked as complete when prompt generation finishes
                    # This ensures the frontend can continue to receive progress updates
                    print(f"Job {job_id} remains in running state while prompt generation continues in background")
                
                print(f"Prompt generation initiated for schema_id={schema_id}")
            except Exception as e:
                print(f"Error during prompt generation: {e}")
                print(f"Traceback: {traceback.format_exc()}")
                if progress_tracker:
                    await progress_tracker.fail_job(f"Error during prompt generation: {str(e)}")
        else:
            print(f"Could not generate prompts: Schema record not found or incomplete for schema_id={schema_id}")
            if progress_tracker:
                await progress_tracker.fail_job("Schema record not found or incomplete")
    except Exception as e:
        print(f"Error generating prompts: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        if progress_tracker:
            await progress_tracker.fail_job(f"Error: {str(e)}")
    finally:
        # Only close the session if we created a new one (no progress_tracker)
        if not progress_tracker and db_session:
            db_session.close()
        # Note: If we have a progress_tracker, its db session will be closed elsewhere
        print(f"Completed async prompt generation task for schema_id={schema_id}")

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
    # New fields for detailed progress tracking
    current_stage: Optional[str] = None
    stage_progress: Optional[int] = None
    stages: Optional[Dict[str, Any]] = None

class JobCreateRequest(BaseModel):
    schema_id: int
    job_type: str
    params: Dict[str, Any] = {}

class LoadDataRequest(BaseModel):
    schema_id: int
    graph_name: str = "default_graph"
    drop_existing: bool = False
    batch_size: int = 1000
    dataset_type: Optional[str] = None  # Optional parameter to specify the dataset type (source/transformed)

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
    print(f"Fetching jobs with filters - schema_id: {schema_id}, job_type: {job_type}")
    
    # Updated to use GraphIngestionJob
    query = db.query(GraphIngestionJob)
    
    if schema_id:
        # Direct filter on schema_id field
        query = query.filter(GraphIngestionJob.schema_id == schema_id)
        print(f"Filtering jobs by schema_id: {schema_id}")
        
    if job_type:
        # Direct filter on job_type field
        query = query.filter(GraphIngestionJob.job_type == job_type)
        print(f"Filtering jobs by job_type: {job_type}")
    
    jobs = query.order_by(GraphIngestionJob.created_at.desc()).all()
    print(f"Found {len(jobs)} jobs matching the criteria")
    
    # Print details for each job
    for job in jobs:
        print(f"Job ID: {job.id}, Type: {job.job_type}, Schema ID: {job.schema_id}, Status: {job.status}, Message: {job.message}, Progress: {job.progress}%, Created: {job.created_at}")
    
    return jobs

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
    Format job database record into API response format with enhanced logging
    """
    # Log the raw job data to help diagnose issues
    print(f"TRACE: Formatting job response for job_id={job.id}")
    print(f"TRACE: Raw job data - Status: {job.status}, Progress: {job.progress}%, Message: {job.message}, Current Stage: {job.current_stage}, Stage Progress: {job.stage_progress}")
    
    # Parse result JSON if available
    result = None
    if job.result:
        try:
            result = json.loads(job.result)
            print(f"TRACE: Successfully parsed job result JSON")
        except Exception as e:
            print(f"WARNING: Failed to parse job result JSON: {e}")
            result = {"raw": job.result}
    
    # Parse stages JSON if available
    stages = None
    if job.stages:
        try:
            stages = json.loads(job.stages)
            print(f"TRACE: Successfully parsed job stages JSON with {len(stages) if stages else 0} stages")
        except Exception as e:
            print(f"WARNING: Failed to parse job stages JSON: {e}")
            stages = None
    
    # Ensure progress is properly normalized to 0.0-1.0 range
    normalized_progress = 0.0
    if job.progress is not None:
        normalized_progress = float(job.progress) / 100
        print(f"TRACE: Normalized progress from {job.progress}% to {normalized_progress}")
    
    # Create the response object
    response = JobStatus(
        id=job.id,
        schema_id=job.schema_id,
        job_type=job.job_type,
        status=job.status,
        progress=normalized_progress,  # Convert from 0-100 to 0.0-1.0
        message=job.message or "",
        created_at=job.created_at,
        updated_at=job.updated_at,
        result=result,
        error=job.error,
        # Include new progress tracking fields
        current_stage=job.current_stage,
        stage_progress=job.stage_progress,
        stages=stages
    )
    
    print(f"TRACE: Formatted job response - Status: {response.status}, Progress: {response.progress}, Message: {response.message}, Current Stage: {response.current_stage}")
    
    return response

# Background task for processing Neo4j data loading
async def process_load_data_job(job_id: str, schema_id: int, graph_name: str, drop_existing: bool, dataset_type: str = None, db: Session = None):
    """
    Background task to load data into Neo4j
    """
    from api.utils.thread_pool import run_in_threadpool
    from api.utils.job_progress import JobProgressTracker
    
    # Create a new session specifically for this background task
    task_db = BackgroundSessionLocal()
    
    try:
        # Get the job using the new session - run in thread pool to avoid blocking
        job = await run_in_threadpool(lambda: task_db.query(GraphIngestionJob).filter(GraphIngestionJob.id == job_id).first())
        if not job:
            print(f"Error: Job with ID {job_id} not found")
            return
        
        # Initialize the job progress tracker
        print(f"TRACE: Initializing job progress tracker for job_id={job_id}")
        progress_tracker = JobProgressTracker(job_id, task_db)
        await progress_tracker.initialize_job()
        print(f"TRACE: Job progress tracker initialized successfully")
        
        try:
            # Update stage to data validation
            print(f"TRACE: Updating progress - data_validation 0%")
            await progress_tracker.update_stage("data_validation", 0, "Validating schema and data path")
            print(f"TRACE: Progress updated for data_validation stage")
            
            # Force commit to ensure progress updates are visible to frontend
            await run_in_threadpool(lambda: task_db.commit())
            print(f"TRACE: Database changes committed")
            
            # Call the existing load_data_from_schema function with our new session
            # if dataset_type is empty or null then it will load it from schema table using given schema id
            from api.utils.thread_pool import run_in_threadpool
            
            # The ProgressDataLoader will handle stage updates for CSV generation, Neo4j import, etc.
            # We just need to set the initial stage
            print(f"TRACE: Updating progress - data_validation 100%")
            await progress_tracker.update_stage("data_validation", 100, "Data validation completed")
            print(f"TRACE: Progress updated for data_validation completion")
            
            # Force commit to ensure progress updates are visible to frontend
            await run_in_threadpool(lambda: task_db.commit())
            print(f"TRACE: Database changes committed")
            
            if dataset_type is None or dataset_type == "":
                # Load data from schema - ProgressDataLoader will handle detailed progress updates
                result = await graphschema_load_data(
                    schema_id=schema_id,
                    graph_name=graph_name,
                    drop_existing=drop_existing,
                    db=task_db,
                    job_id=job_id  # Pass job_id to the data loader
                )
            else:
                # Load data from schema with dataset_type - ProgressDataLoader will handle detailed progress updates
                result = await graphschema_load_data(
                    schema_id=schema_id,
                    graph_name=graph_name,
                    drop_existing=drop_existing,
                    dataset_type=dataset_type,
                    db=task_db,
                    job_id=job_id  # Pass job_id to the data loader
                )
            
            print(f"Data loading result: {result}")
            # Get a fresh instance of the job from the database instead of refreshing
            # This prevents the 'not persistent within this Session' error
            from api.utils.thread_pool import run_in_threadpool
            
            job = await run_in_threadpool(lambda: db.query(GraphIngestionJob).filter(GraphIngestionJob.id == job_id).first())
            if not job:
                print(f"Error: Job with ID {job_id} not found after data loading")
                return
            
            # Only update the job if it's still in running status
            # This prevents overwriting updates made by the DataLoader
            if job.status == "running":
                print(f"Job {job_id} still in running status, updating to completed")
                
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
                
                # Update schema record with db_id if it's not already set
                schema = await run_in_threadpool(lambda: task_db.query(Schema).filter(Schema.id == schema_id).first())
                if schema and not schema.db_id:
                    schema.db_id = graph_name
                    print(f"Updated schema record {schema_id} with db_id={graph_name}")
                    await run_in_threadpool(lambda: task_db.commit())
                    
                # Also update db_loaded flag if not already set
                if schema and schema.db_loaded != 'yes':
                    schema.db_loaded = 'yes'
                    print(f"Updated schema record {schema_id} with db_loaded=yes")
                    await run_in_threadpool(lambda: task_db.commit())
                    
                # Complete the job with the progress tracker
                await progress_tracker.complete_job(result_data if result and isinstance(result, dict) else None)
            else:
                print(f"Job {job_id} already in {job.status} status, not updating")
                # Still commit any schema updates if needed
                from api.utils.thread_pool import run_in_threadpool
                schema_db = await run_in_threadpool(lambda: db.query(Schema).filter(Schema.id == schema_id).first())
                if schema_db and schema_db.db_loaded != "yes":
                    schema_db.db_loaded = "yes"
                    print(f"Updated schema record {schema_id} with db_loaded=yes")
                    await run_in_threadpool(lambda: db.commit())
            
            # Update stage to prompt generation preparation
            print(f"TRACE: Updating progress - prompt_generation_prep 0%")
            await progress_tracker.update_stage("prompt_generation_prep", 0, "Preparing for prompt generation")
            print(f"TRACE: Progress updated for prompt_generation_prep stage")
            
            # Force commit to ensure progress updates are visible to frontend
            await run_in_threadpool(lambda: task_db.commit())
            print(f"TRACE: Database changes committed")
            
            # Start prompt template generation as a background task with job_id for progress tracking
            print(f"TRACE: Starting prompt template generation as a background task")
            background_tasks = BackgroundTasks()
            background_tasks.add_task(
                generate_prompts_async,
                schema_id=schema_id,
                job_id=job_id
            )
            # Run the background task
            asyncio.create_task(background_tasks())
            print(f"TRACE: Started async prompt template generation for schema_id={schema_id} with job_id={job_id}")
            
            # Force commit to ensure all progress updates are visible to frontend
            await run_in_threadpool(lambda: task_db.commit())
            print(f"TRACE: Final database changes committed for this phase")
            
        
        except Exception as e:
            print(f"Error during data loading: {str(e)}")
            print(traceback.format_exc())
            
            # Update job with error using the progress tracker
            await progress_tracker.fail_job(f"Error during data loading: {str(e)}")
        
        finally:
            # Make sure to close the new session
            task_db.close()
        
    except Exception as e:
        print(f"Error in process_load_data_job: {str(e)}")
        print(traceback.format_exc())
        
        # Try to update job with error if progress_tracker wasn't initialized
        try:
            job = await run_in_threadpool(lambda: task_db.query(GraphIngestionJob).filter(GraphIngestionJob.id == job_id).first())
            if job:
                job.status = "failed"
                job.error = str(e)
                job.message = f"Error in process_load_data_job: {str(e)}"
                job.completed_at = datetime.now()
                await run_in_threadpool(lambda: task_db.commit())
        except Exception as inner_e:
            print(f"Error updating job status: {str(inner_e)}")
            print(traceback.format_exc())
    finally:
        # Always close the task-specific session
        task_db.close()

# Background task for cleaning Neo4j data
async def process_clean_data_job(job_id: str, schema_id: int, graph_name: str, db: Session):
    """
    Background task to clean data from Neo4j
    """
    from api.utils.thread_pool import run_in_threadpool
    
    # Create a new session specifically for this background task
    task_db = BackgroundSessionLocal()
    
    try:
        # Get the job using the new session - run in thread pool to avoid blocking
        job = await run_in_threadpool(lambda: task_db.query(GraphIngestionJob).filter(GraphIngestionJob.id == job_id).first())
        if not job:
            print(f"Error: Job with ID {job_id} not found")
            return
        
        # Update job status to running - run in thread pool to avoid blocking
        job.status = "running"
        job.started_at = datetime.now()
        job.message = f"Starting data cleaning for schema ID {schema_id} from graph {graph_name}"
        job.progress = 5
        await run_in_threadpool(lambda: task_db.commit())
        
        try:
            # Get schema record
            schema = task_db.query(Schema).filter(Schema.id == schema_id).first()
            if not schema:
                raise ValueError(f"Schema with ID {schema_id} not found")
            
            # Get Neo4j connection details from centralized configuration
            from neo4j import GraphDatabase
            
            # Get connection parameters directly from the centralized configuration
            connection_params = get_neo4j_connection_params("default_graph")
            
            # Connect to Neo4j using the connection parameters
            driver = GraphDatabase.driver(
                connection_params.get("uri", ""),
                auth=(connection_params.get("username", ""), connection_params.get("password", ""))
            )
            
            # Clean data
            with driver.session(database=connection_params.get("database", "neo4j")) as session:
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
                    "nodes_removed": total_deleted,  # Using the actual defined variable
                    "relationships_removed": 0  # We don't track relationships separately
                }
                job.result = json.dumps(result_data)
                
                task_db.commit()
                print(f"DEBUG: Job status updated to completed in task_db connection")
                
                # Update schema record to indicate data has been cleaned
                schema_db = db.query(Schema).filter(Schema.id == schema_id).first()
                if schema_db:
                    schema_db.db_loaded = "no"
                    print(f"Updated schema record {schema_id} with db_loaded=no")
            
            driver.close()
        finally:
            # Make sure to close the new session
            task_db.close()
        
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
    print(f"TRACE: get_jobs endpoint called with schema_id={schema_id}, job_type={job_type}")
    
    # Get all jobs matching the criteria
    jobs = get_all_jobs(db, schema_id, job_type)
    print(f"TRACE: Found {len(jobs)} jobs matching the criteria")
    
    # Format job responses with detailed logging
    formatted_jobs = []
    for job in jobs:
        formatted_job = format_job_response(job)
        print(f"TRACE: Formatted job - ID: {job.id}, Status: {formatted_job.status}, Progress: {formatted_job.progress}, Current Stage: {formatted_job.current_stage}")
        formatted_jobs.append(formatted_job)
    
    return formatted_jobs

@router.get("/{job_id}", response_model=JobStatus)
async def get_job(
    job_id: str,
    current_user: User = Depends(has_any_permission(["kginsights:read"])),
    db: Session = Depends(get_db)
):
    """
    Get status of a specific job
    """
    print(f"TRACE: get_job endpoint called for job_id={job_id}")
    
    # Updated to use GraphIngestionJob
    job = db.query(GraphIngestionJob).filter(GraphIngestionJob.id == job_id).first()
    if not job:
        print(f"ERROR: Job with ID {job_id} not found")
        raise HTTPException(status_code=404, detail=f"Job with ID {job_id} not found")
    
    print(f"TRACE: Found job - ID: {job.id}, Type: {job.job_type}, Status: {job.status}, Progress: {job.progress}%, Message: {job.message}, Current Stage: {job.current_stage}, Stage Progress: {job.stage_progress}")
    
    # Format the job response
    response = format_job_response(job)
    print(f"TRACE: Formatted job response - Status: {response.status}, Progress: {response.progress}, Message: {response.message}, Current Stage: {response.current_stage}")
    
    return response

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
        dataset_type=request.dataset_type,
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
