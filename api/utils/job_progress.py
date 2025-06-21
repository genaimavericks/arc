"""
Job progress tracking utilities for multi-stage jobs
"""
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from api.models import GraphIngestionJob
from datetime import datetime
import json
from api.utils.thread_pool import run_in_threadpool
from api.kginsights.constants import DATA_LOADING_STAGES

class JobProgressTracker:
    """
    Utility class to track and update job progress across multiple stages
    """
    def __init__(self, job_id: str, db: Session):
        """
        Initialize the job progress tracker
        
        Args:
            job_id: ID of the job to track
            db: Database session
        """
        self.job_id = job_id
        self.db = db
        self.stages = DATA_LOADING_STAGES
        
    async def initialize_job(self):
        """
        Initialize job with stages information
        
        Returns:
            bool: True if successful, False otherwise
        """
        job = await run_in_threadpool(lambda: self._get_job())
        if job:
            job.stages = json.dumps(self.stages)
            job.progress = 0
            job.status = "running"
            job.started_at = datetime.now()
            job.message = "Job initialized with multi-stage tracking"
            await run_in_threadpool(lambda: self.db.commit())
            return True
        return False
    
    async def update_stage(self, stage_id: str, progress: int = 0, message: Optional[str] = None):
        """
        Update job to a new stage with specific progress
        
        Args:
            stage_id: ID of the stage (must match a key in DATA_LOADING_STAGES)
            progress: Progress within this stage (0-100)
            message: Optional custom message
            
        Returns:
            bool: True if successful, False otherwise
        """
        if stage_id not in self.stages:
            print(f"Warning: Unknown stage ID: {stage_id}")
            return False
            
        job = await run_in_threadpool(lambda: self._get_job())
        if not job:
            return False
            
        # Update job with stage info
        job.current_stage = stage_id
        job.stage_progress = progress
        
        # Calculate overall progress based on stage weights
        total_weight = sum(stage["weight"] for stage in self.stages.values())
        completed_weight = 0
        
        # Add weight from completed stages
        stage_keys = list(self.stages.keys())
        current_stage_index = stage_keys.index(stage_id)
        
        # Add full weight for completed stages
        for i, stage_key in enumerate(stage_keys):
            if i < current_stage_index:
                completed_weight += self.stages[stage_key]["weight"]
        
        # Add partial weight for current stage
        completed_weight += (self.stages[stage_id]["weight"] * progress / 100)
        
        # Calculate overall progress percentage
        job.progress = int((completed_weight / total_weight) * 100)
        
        # Update message
        if message:
            job.message = message
        else:
            job.message = f"{self.stages[stage_id]['name']}: {progress}%"
            
        # Update timestamp
        job.updated_at = datetime.now()
            
        await run_in_threadpool(lambda: self.db.commit())
        return True
    
    async def complete_job(self, result: Dict[str, Any] = None):
        """
        Mark job as completed with results
        
        Args:
            result: Optional dictionary with job results
            
        Returns:
            bool: True if successful, False otherwise
        """
        job = await run_in_threadpool(lambda: self._get_job())
        if not job:
            return False
            
        job.status = "completed"
        job.completed_at = datetime.now()
        job.progress = 100
        job.message = "Job completed successfully"
        
        if result:
            # Store node and relationship counts
            job.node_count = result.get("nodes_created", 0)
            job.relationship_count = result.get("relationships_created", 0)
            
            # Store detailed results
            job_result = {}
            if "node_counts" in result:
                job_result["node_counts"] = result["node_counts"]
            if "relationship_counts" in result:
                job_result["relationship_counts"] = result["relationship_counts"]
                
            if job_result:
                job.result = json.dumps(job_result)
                
        await run_in_threadpool(lambda: self.db.commit())
        return True
    
    async def fail_job(self, error_message: str):
        """
        Mark job as failed with error message
        
        Args:
            error_message: Error message to store
            
        Returns:
            bool: True if successful, False otherwise
        """
        job = await run_in_threadpool(lambda: self._get_job())
        if not job:
            return False
            
        job.status = "failed"
        job.error = error_message
        job.message = f"Job failed: {error_message}"
        job.completed_at = datetime.now()
        await run_in_threadpool(lambda: self.db.commit())
        return True
    
    def _get_job(self):
        """Get job from database"""
        return self.db.query(GraphIngestionJob).filter(GraphIngestionJob.id == self.job_id).first()
