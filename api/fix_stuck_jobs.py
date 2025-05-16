"""
Script to fix stuck processing jobs that remain in 'running' state after completion.
This script identifies jobs that are likely completed but still show as running,
and updates their status to 'completed'.
"""
import sys
import os
import time
from datetime import datetime, timedelta

# Add the parent directory to the path so we can import from api
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.models import GraphIngestionJob, Schema, get_db

def fix_stuck_jobs(hours_threshold=1, dry_run=True):
    """
    Find and fix jobs that have been running for longer than the threshold
    and have a corresponding schema with db_loaded='yes'.
    
    Args:
        hours_threshold: Number of hours a job should be running to be considered stuck
        dry_run: If True, only print what would be done without making changes
    
    Returns:
        Number of jobs fixed
    """
    # Get database session
    db = next(get_db())
    
    try:
        # Calculate the time threshold
        threshold_time = datetime.now() - timedelta(hours=hours_threshold)
        
        # Find jobs that have been running for longer than the threshold
        stuck_jobs = db.query(GraphIngestionJob).filter(
            GraphIngestionJob.status == "running",
            GraphIngestionJob.started_at < threshold_time
        ).all()
        
        print(f"Found {len(stuck_jobs)} potentially stuck jobs")
        
        fixed_count = 0
        for job in stuck_jobs:
            # Check if this is a load_data job
            if job.job_type != "load_data":
                print(f"Skipping job {job.id} of type {job.job_type}")
                continue
            
            # Get the corresponding schema
            schema = db.query(Schema).filter(Schema.id == job.schema_id).first()
            if not schema:
                print(f"Schema not found for job {job.id}, schema_id {job.schema_id}")
                continue
            
            # Check if the schema has been loaded successfully
            if schema.db_loaded == 'yes':
                print(f"Job {job.id} for schema {schema.id} ({schema.name}) appears to be stuck")
                print(f"  Started at: {job.started_at}")
                print(f"  Schema db_loaded: {schema.db_loaded}")
                
                if not dry_run:
                    # Update the job status
                    job.status = "completed"
                    job.completed_at = datetime.now()
                    job.progress = 100
                    job.message = f"Job marked as completed by fix_stuck_jobs.py. Schema shows data was loaded successfully."
                    db.commit()
                    print(f"  ✅ Job status updated to 'completed'")
                else:
                    print(f"  [DRY RUN] Would update job status to 'completed'")
                
                fixed_count += 1
            else:
                print(f"Job {job.id} for schema {schema.id} is running but schema.db_loaded={schema.db_loaded}")
        
        return fixed_count
    
    except Exception as e:
        print(f"Error fixing stuck jobs: {str(e)}")
        db.rollback()
        return 0
    finally:
        db.close()

def fix_specific_job(job_id, force=False, dry_run=True):
    """
    Fix a specific job by ID.
    
    Args:
        job_id: ID of the job to fix
        force: If True, update the job status even if schema.db_loaded is not 'yes'
        dry_run: If True, only print what would be done without making changes
    
    Returns:
        True if job was fixed, False otherwise
    """
    # Get database session
    db = next(get_db())
    
    try:
        # Find the job
        job = db.query(GraphIngestionJob).filter(GraphIngestionJob.id == job_id).first()
        if not job:
            print(f"Job with ID {job_id} not found")
            return False
        
        print(f"Found job {job.id} of type {job.job_type}, status {job.status}")
        
        # Check if job is already completed or failed
        if job.status in ["completed", "failed", "cancelled"]:
            print(f"Job is already in {job.status} state, no action needed")
            return False
        
        # Get the corresponding schema
        schema = db.query(Schema).filter(Schema.id == job.schema_id).first()
        if not schema:
            print(f"Schema not found for job {job.id}, schema_id {job.schema_id}")
            return False
        
        # Check if the schema has been loaded successfully or if force is True
        if schema.db_loaded == 'yes' or force:
            print(f"Job {job.id} for schema {schema.id} ({schema.name})")
            print(f"  Started at: {job.started_at}")
            print(f"  Schema db_loaded: {schema.db_loaded}")
            
            if not dry_run:
                # Update the job status
                job.status = "completed"
                job.completed_at = datetime.now()
                job.progress = 100
                job.message = f"Job marked as completed by fix_stuck_jobs.py. {'Forced update.' if force else 'Schema shows data was loaded successfully.'}"
                db.commit()
                print(f"  ✅ Job status updated to 'completed'")
            else:
                print(f"  [DRY RUN] Would update job status to 'completed'")
            
            return True
        else:
            print(f"Job {job.id} for schema {schema.id} is running but schema.db_loaded={schema.db_loaded}")
            print("Use --force to update the job status anyway")
            return False
    
    except Exception as e:
        print(f"Error fixing job: {str(e)}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Fix stuck processing jobs")
    parser.add_argument("--job-id", help="ID of a specific job to fix")
    parser.add_argument("--hours", type=int, default=1, help="Hours threshold for stuck jobs (default: 1)")
    parser.add_argument("--force", action="store_true", help="Force update job status even if schema.db_loaded is not 'yes'")
    parser.add_argument("--apply", action="store_true", help="Apply changes (without this flag, runs in dry-run mode)")
    
    args = parser.parse_args()
    
    # Determine if we're in dry run mode
    dry_run = not args.apply
    if dry_run:
        print("Running in DRY RUN mode. Use --apply to actually make changes.")
    
    if args.job_id:
        # Fix a specific job
        success = fix_specific_job(args.job_id, force=args.force, dry_run=dry_run)
        if success and not dry_run:
            print("Job fixed successfully")
        elif not success and not dry_run:
            print("Failed to fix job")
    else:
        # Fix all stuck jobs
        fixed_count = fix_stuck_jobs(hours_threshold=args.hours, dry_run=dry_run)
        if fixed_count > 0 and not dry_run:
            print(f"Fixed {fixed_count} stuck jobs")
        elif fixed_count == 0:
            print("No stuck jobs found or fixed")
