"""
Job orchestration and pipeline management for DataPuur (Dramatiq variant).
This file is for orchestration, chaining, and advanced job logic.
"""
from .datapuur_dramatiq import (
    dramatiq_file_ingestion, 
    dramatiq_db_ingestion,
    dramatiq_file_upload
)
import uuid
from datetime import datetime
from .datapuur import save_ingestion_job, get_ingestion_job
import logging

logger = logging.getLogger(__name__)

def start_file_ingestion_pipeline(job_id, file_id, chunk_size):
    """Orchestrate file ingestion pipeline using Dramatiq."""
    dramatiq_file_ingestion.send(job_id, file_id, chunk_size)

def start_db_ingestion_pipeline(job_id, db_type, db_config, chunk_size):
    """Orchestrate database ingestion pipeline using Dramatiq."""
    dramatiq_db_ingestion.send(job_id, db_type, db_config, chunk_size)

def start_file_upload_pipeline(file_id, file_path, filename, file_type, uploaded_by):
    """Orchestrate file upload processing using Dramatiq."""
    dramatiq_file_upload.send(file_id, file_path, filename, file_type, uploaded_by)

def start_ingestion_and_profile_pipeline(ingestion_type, db, current_user, **kwargs):
    """
    Orchestrate a complete pipeline that runs ingestion followed by profiling.
    Returns the job_id for the initial ingestion job.
    """
    # Create ingestion job first
    job_id = str(uuid.uuid4())
    
    if ingestion_type == "file":
        # Extract file ingestion params
        file_id = kwargs.get("file_id")
        file_name = kwargs.get("file_name")
        chunk_size = kwargs.get("chunk_size", 1000)
        
        # Create job in database
        job_data = {
            "id": job_id,
            "name": file_name,
            "type": "file",
            "status": "queued",
            "progress": 0,
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "details": f"File: {file_name} (with auto-profiling)",
            "error": None,
            "duration": None,
            "config": {
                "file_id": file_id,
                "chunk_size": chunk_size,
                "auto_profile": True
            }
        }
        save_ingestion_job(db, job_id, job_data)
        
        # Start the ingestion
        dramatiq_file_ingestion.send(job_id, file_id, chunk_size)
        
        # Create a profile job ID to be used later
        profile_job_id = str(uuid.uuid4())
        
        # Set up a post-ingestion profiling job (but don't start it yet)
        # This will be started by a completion callback or monitoring system
        profile_job_data = {
            "id": profile_job_id,
            "name": f"Profile of {file_name}",
            "type": "profile",
            "status": "pending",  # Will be started after ingestion
            "progress": 0,
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "details": f"Pending profiling for ingestion: {job_id}",
            "error": None,
            "duration": None,
            "config": {
                "ingestion_job_id": job_id,
                "parent_job": job_id
            }
        }
        save_ingestion_job(db, profile_job_id, profile_job_data)
        
        # Set up a completion monitor for the ingestion job
        # In a real implementation, you'd use Dramatiq middleware or a scheduler
        # For this implementation, we'll rely on client polling and callback
        
        logger.info(f"Created chained ingestion+profiling jobs: {job_id} -> {profile_job_id}")
        
    elif ingestion_type == "database":
        # Extract DB ingestion params
        db_type = kwargs.get("db_type")
        db_config = kwargs.get("db_config")
        chunk_size = kwargs.get("chunk_size", 1000)
        connection_name = kwargs.get("connection_name")
        
        # Create job in database
        job_data = {
            "id": job_id,
            "name": connection_name,
            "type": "database",
            "status": "queued",
            "progress": 0,
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "details": f"DB: {db_config.get('database', '')}.{db_config.get('table', '')} (with auto-profiling)",
            "error": None,
            "duration": None,
            "config": {
                "type": db_type,
                "database": db_config.get("database", ""),
                "table": db_config.get("table", ""),
                "auto_profile": True
            }
        }
        save_ingestion_job(db, job_id, job_data)
        
        # Start the ingestion
        dramatiq_db_ingestion.send(job_id, db_type, db_config, chunk_size)
        
        # Create a profile job ID to be used later
        profile_job_id = str(uuid.uuid4())
        
        # Set up a post-ingestion profiling job (but don't start it yet)
        profile_job_data = {
            "id": profile_job_id,
            "name": f"Profile of {connection_name}",
            "type": "profile",
            "status": "pending",
            "progress": 0,
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "details": f"Pending profiling for ingestion: {job_id}",
            "error": None,
            "duration": None,
            "config": {
                "ingestion_job_id": job_id,
                "parent_job": job_id
            }
        }
        save_ingestion_job(db, profile_job_id, profile_job_data)
        
        logger.info(f"Created chained ingestion+profiling jobs: {job_id} -> {profile_job_id}")
    
    else:
        logger.error(f"Unknown ingestion type: {ingestion_type}")
        raise ValueError(f"Unknown ingestion type: {ingestion_type}")
    
    return job_id

def check_and_start_profiling(job_id, db):
    """
    Check if an ingestion job is complete and start profiling if needed.
    This would be called by a client-side polling mechanism or a server-side monitor.
    """
    # Check the ingestion job status
    job = get_ingestion_job(db, job_id)
    if not job:
        logger.error(f"Job not found: {job_id}")
        return False
    
    # If the job is not completed, don't proceed
    if job.status != "completed":
        logger.debug(f"Job {job_id} not completed (status: {job.status}). Profiling not started.")
        return False
    
    # Check if auto-profiling is enabled
    config = {}
    if job.config:
        import json
        try:
            config = json.loads(job.config)
        except:
            logger.error(f"Could not parse job config for {job_id}")
    
    if not config.get("auto_profile", False):
        logger.debug(f"Auto-profiling not enabled for job {job_id}")
        return False
    
    # Find the pending profile job
    from sqlalchemy import and_
    from .models import IngestionJob
    
    profile_job = db.query(IngestionJob).filter(
        and_(
            IngestionJob.type == "profile",
            IngestionJob.status == "pending"
        )
    ).first()
    
    if not profile_job:
        logger.warning(f"No pending profile job found for ingestion {job_id}")
        
        # Create a new profile job
        profile_job_id = str(uuid.uuid4())
        profile_job_data = {
            "id": profile_job_id,
            "name": f"Profile of {job.name}",
            "type": "profile",
            "status": "queued",
            "progress": 0,
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "details": f"Profiling data from ingestion: {job_id}",
            "error": None,
            "duration": None,
            "config": {
                "ingestion_job_id": job_id
            }
        }
        save_ingestion_job(db, profile_job_id, profile_job_data)
        
        # Start the profiling
        #dramatiq_profile_ingestion.send(profile_job_id, job_id)
        logger.info(f"Started profiling for ingestion {job_id} with profile job {profile_job_id}")
        return True
    
    # Start the profiling job
    profile_job.status = "queued"
    profile_job.details = f"Profiling data from ingestion: {job_id}"
    db.commit()
    
    #dramatiq_profile_ingestion.send(profile_job.id, job_id)
    logger.info(f"Started profiling for ingestion {job_id} with profile job {profile_job.id}")
    return True
