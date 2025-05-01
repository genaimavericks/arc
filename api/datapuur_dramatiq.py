"""
Dramatiq actors for DataPuur background job processing.
These actors replicate the existing ingestion functionality but run in Dramatiq workers.
"""
import dramatiq
from dramatiq.brokers.redis import RedisBroker
from sqlalchemy.orm import Session
from .datapuur import (
    process_file_ingestion_with_db,
    process_db_ingestion_with_db,
    # Add other relevant functions as needed
)
from .models import SessionLocal
import logging
import os
import sys
import redis
from datetime import datetime

logger = logging.getLogger(__name__)

# Configure Redis broker
redis_host = os.environ.get("REDIS_HOST", "localhost")
redis_port = int(os.environ.get("REDIS_PORT", 6379))

# Initialize broker with Redis connection
redis_broker = RedisBroker(host=redis_host, port=redis_port)
dramatiq.set_broker(redis_broker)

# Dramatiq actor for file ingestion
@dramatiq.actor
def dramatiq_file_ingestion(job_id: str, file_id: str, chunk_size: int):
    """
    Dramatiq actor to process file ingestion using existing logic.
    """
    db: Session = SessionLocal()
    try:
        logger.info(f"[Dramatiq] Starting file ingestion: job_id={job_id}, file_id={file_id}")
        process_file_ingestion_with_db(job_id, file_id, chunk_size, db)
        logger.info(f"[Dramatiq] File ingestion completed: job_id={job_id}")
    except Exception as e:
        logger.error(f"[Dramatiq] File ingestion failed: job_id={job_id}, error={e}")
        # Optionally update job status in DB here
    finally:
        db.close()

# Dramatiq actor for DB ingestion
@dramatiq.actor
def dramatiq_db_ingestion(job_id: str, db_type: str, db_config: dict, chunk_size: int):
    """
    Dramatiq actor to process DB ingestion using existing logic.
    """
    db: Session = SessionLocal()
    try:
        logger.info(f"[Dramatiq] Starting DB ingestion: job_id={job_id}, db_type={db_type}")
        process_db_ingestion_with_db(job_id, db_type, db_config, chunk_size, db)
        logger.info(f"[Dramatiq] DB ingestion completed: job_id={job_id}")
    except Exception as e:
        logger.error(f"[Dramatiq] DB ingestion failed: job_id={job_id}, error={e}")
        # Optionally update job status in DB here
    finally:
        db.close()

# Direct file upload handling
@dramatiq.actor
def dramatiq_file_upload(file_id: str, file_path: str, filename: str, file_type: str, uploaded_by: str):
    """
    Dramatiq actor to handle post-upload processing.
    This actor would be called after a file is uploaded to perform any needed processing.
    """
    db: Session = SessionLocal()
    try:
        logger.info(f"[Dramatiq] Processing uploaded file: file_id={file_id}, filename={filename}")
        
        # Perform any necessary post-upload processing
        # This could include:
        # - Validation
        # - Virus scanning
        # - Moving to permanent storage
        # - Generating thumbnails or previews
        # - Updating file metadata
        
        # Here we just log and update the file status if needed
        from .datapuur import get_uploaded_file, save_uploaded_file
        file_info = get_uploaded_file(db, file_id)
        if file_info:
            # Update with any processing results
            file_data = {
                "status": "ready",
                "processed_at": datetime.now().isoformat()
            }
            save_uploaded_file(db, file_id, file_data)
            
        logger.info(f"[Dramatiq] File upload processing completed: file_id={file_id}")
    except Exception as e:
        logger.error(f"[Dramatiq] File upload processing failed: file_id={file_id}, error={e}")
    finally:
        db.close()

# Orchestration functions (can be expanded for chaining jobs)
def start_ingestion_pipeline(job_type: str, **kwargs):
    """
    Example orchestration function to enqueue Dramatiq jobs based on type.
    """
    if job_type == "file":
        dramatiq_file_ingestion.send(kwargs["job_id"], kwargs["file_id"], kwargs["chunk_size"])
    elif job_type == "db":
        dramatiq_db_ingestion.send(kwargs["job_id"], kwargs["db_type"], kwargs["db_config"], kwargs["chunk_size"])
    # Add more job types as needed

def check_redis_connection():
    """
    Check if Redis is available for Dramatiq broker connection
    """
    try:
        r = redis.Redis(host=redis_host, port=redis_port)
        return r.ping()
    except (redis.ConnectionError, redis.RedisError) as e:
        logger.error(f"Redis connection error: {e}")
        return False

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    # Check Redis connection
    if not check_redis_connection():
        logger.error(f"Cannot connect to Redis at {redis_host}:{redis_port}")
        logger.error("Dramatiq workers will not function without Redis. Exiting.")
        sys.exit(1)
    
    logger.info(f"Connected to Redis at {redis_host}:{redis_port}")
    logger.info("Starting Dramatiq workers for DataPuur...")
    
    # The actual worker processes are started by the dramatiq CLI tool
    # When this module is imported directly by dramatiq, it will use the actors defined here
    from dramatiq.cli import main as dramatiq_main
    sys.argv.insert(1, "api.datapuur_dramatiq")
    sys.exit(dramatiq_main())
