"""
Data Profiler Router for the RSW platform.
This module implements API endpoints for data profiling.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
import pandas as pd
import numpy as np
from typing import Dict, Any, List
import os
import uuid
import logging
import time
from sqlalchemy import desc
from pathlib import Path
from datetime import datetime

from ..models import User, get_db
from ..auth import has_permission, log_activity, has_any_permission
from .models import ProfileResult, ColumnProfile
from .schemas.profile import ProfileRequest, ProfileResponse, ProfileListResponse, ProfileSummaryResponse
from .services.engine import DataProfiler

# Set up logging
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
profiler_log_file = LOG_DIR / "profiler.log"

# Configure logger
logger = logging.getLogger("profiler")
logger.setLevel(logging.DEBUG)

# Create file handler
file_handler = logging.FileHandler(profiler_log_file)
file_handler.setLevel(logging.DEBUG)

# Create console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add handlers to logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Create data directory if it doesn't exist
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# Create router with prefix and tags
router = APIRouter(prefix="/api/profiler", tags=["data-profiler"])

def convert_numpy_types(obj: Any) -> Any:
    """
    Convert NumPy types to Python native types to ensure JSON serialization works.
    This is a recursive function that handles nested dictionaries and lists.
    """
    if isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return convert_numpy_types(obj.tolist())
    elif isinstance(obj, np.bool_):
        return bool(obj)
    else:
        return obj

@router.post("/profile-data", response_model=ProfileResponse)
async def profile_data(
    request: ProfileRequest,
    current_user: User = Depends(has_any_permission(["datapuur:read", "kginsights:read"])),
    db: Session = Depends(get_db)
) -> Dict:
    """
    Profile a data source using a direct file path.
    
    The profiling operation performs comprehensive analysis of data structure,
    statistics, and quality metrics.
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())[:8]  # Short ID for logging
    
    logger.info(f"[{request_id}] Profile request received for file_id: {request.file_id}, file_name: {request.file_name}")
    
    try:
        # Check if the file exists
        parquet_path = DATA_DIR / f"{request.file_path}"
        logger.debug(f"[{request_id}] Looking for parquet file at: {parquet_path}")
        
        if not os.path.exists(parquet_path):
            logger.error(f"[{request_id}] File not found at path: {parquet_path}")
            logger.debug(f"[{request_id}] Directory contents: {os.listdir(DATA_DIR)}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found at path: {parquet_path}"
            )
        
        logger.info(f"[{request_id}] Parquet file found, size: {os.path.getsize(parquet_path)} bytes")
        
        try:
            logger.debug(f"[{request_id}] Attempting to read parquet file")
            df = pd.read_parquet(parquet_path)
            logger.info(f"[{request_id}] Successfully read parquet file with shape: {df.shape}")
            logger.debug(f"[{request_id}] DataFrame columns: {df.columns.tolist()}")
            logger.debug(f"[{request_id}] DataFrame sample: {df.head(2).to_dict()}")
        except Exception as read_error:
            logger.error(f"[{request_id}] Error reading parquet file: {str(read_error)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to read parquet file: {str(read_error)}"
            )
            
        # Generate profile
        try:
            logger.info(f"[{request_id}] Starting profile generation")
            profile_start = time.time()
            profiler = DataProfiler(df)
            profile_summary, column_profiles = profiler.generate_profile()
            profile_duration = time.time() - profile_start
            logger.info(f"[{request_id}] Profile generation completed in {profile_duration:.2f} seconds")
            logger.debug(f"[{request_id}] Profile summary: {profile_summary}")
        except Exception as profile_error:
            logger.error(f"[{request_id}] Failed to generate profile: {str(profile_error)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate profile: {str(profile_error)}"
            )

        # Create database entry for profile result
        try:
            logger.debug(f"[{request_id}] Creating database entry for profile result")
            profile_id = str(uuid.uuid4())
            file_id = request.file_id
            
            # Convert NumPy types in profile_summary to Python native types
            profile_summary = convert_numpy_types(profile_summary)
            
            # Convert NumPy types in column profiles to Python native types
            column_profiles_json = convert_numpy_types(column_profiles)
            
            profile_result = ProfileResult(
                id=profile_id,
                file_id=file_id,
                file_name=request.file_name,
                parquet_file_path=str(request.file_path),  # Save the parquet file path
                total_rows=profile_summary["total_rows"],
                total_columns=profile_summary["total_columns"],
                data_quality_score=profile_summary["data_quality_score"],
                column_profiles=column_profiles_json  # Store column profiles as JSON
            )
            db.add(profile_result)
            
            # Log the number of column profiles saved
            logger.debug(f"[{request_id}] Saved {len(column_profiles_json)} column profiles as JSON")
            
            db.commit()
            logger.info(f"[{request_id}] Successfully saved profile data to database with {len(column_profiles_json)} column profiles")
        except Exception as db_error:
            logger.error(f"[{request_id}] Database error: {str(db_error)}")
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save profile to database: {str(db_error)}"
            )
        
        # Log the activity
        log_activity(
            db=db,
            username=current_user.username,
            action="Data Profile",
            details=f"Generated profile for {request.file_name} (file_id: {file_id})"
        )

        # Prepare response
        response = {
            "id": profile_result.id,
            "file_id": file_id,
            "file_name": request.file_name,
            **profile_summary,
            "columns": column_profiles,
            "created_at": profile_result.created_at
        }

        total_duration = time.time() - start_time
        logger.info(f"[{request_id}] Profile request completed in {total_duration:.2f} seconds")
        return response

    except Exception as e:
        db.rollback()
        # Log the specific error for debugging
        logger.error(f"[{request_id}] Profiler error: {str(e)}", exc_info=True)
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/profiles", response_model=ProfileListResponse)
async def list_profiles(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    file_id: str = Query(None),
    search: str = Query(None),
    current_user: User = Depends(has_any_permission(["datapuur:read", "kginsights:read"])),
    db: Session = Depends(get_db)
):
    """
    List all data profiles with optional filtering.
    
    Returns a paginated list of profile summaries.
    """
    request_id = str(uuid.uuid4())[:8]
    logger.info(f"[{request_id}] List profiles request received. page={page}, limit={limit}, file_id={file_id}, search={search}")
    
    try:
        # Build query
        query = db.query(ProfileResult)
        
        # Apply filters
        if file_id:
            query = query.filter(ProfileResult.file_id == file_id)
        
        if search:
            query = query.filter(ProfileResult.file_name.ilike(f"%{search}%"))
        
        # Count total
        total = query.count()
        logger.debug(f"[{request_id}] Found {total} profiles matching criteria")
        
        # Paginate results
        results = query.order_by(desc(ProfileResult.created_at)).offset((page - 1) * limit).limit(limit).all()
        
        # Prepare response
        profiles = []
        for profile in results:
            profiles.append({
                "id": profile.id,
                "file_id": profile.file_id,
                "file_name": profile.file_name,
                "total_rows": profile.total_rows,
                "total_columns": profile.total_columns,
                "data_quality_score": profile.data_quality_score * 100 if profile.data_quality_score is not None else None,
                "created_at": profile.created_at
            })
        
        logger.info(f"[{request_id}] Returning {len(profiles)} profiles")
        return {
            "items": profiles,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit
        }
    
    except Exception as e:
        logger.error(f"[{request_id}] Error listing profiles: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/profiles/{profile_id}", response_model=ProfileResponse)
async def get_profile(
    profile_id: str,
    current_user: User = Depends(has_any_permission(["datapuur:read", "kginsights:read"])),
    db: Session = Depends(get_db)
):
    """
    Get a specific data profile by ID.
    
    Returns the complete profile data including column statistics.
    """
    request_id = str(uuid.uuid4())[:8]
    logger.info(f"[{request_id}] Get profile request received for profile_id: {profile_id}")
    
    try:
        # Get profile result
        profile_result = db.query(ProfileResult).filter(ProfileResult.id == profile_id).first()
        
        if not profile_result:
            logger.warning(f"[{request_id}] Profile with ID {profile_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Profile with ID {profile_id} not found"
            )
        
        logger.debug(f"[{request_id}] Found profile: {profile_result.id}, file: {profile_result.file_name}")
        
        # Get column profiles from JSON
        column_profiles = profile_result.column_profiles
        
        # Extract original column headers if they exist in the column profiles
        original_headers = []
        
        # Try to extract column names from the profile data
        if column_profiles:
            # Check if column_profiles is a dictionary or a list
            if isinstance(column_profiles, dict):
                # Handle dictionary format
                for key in sorted([int(k) for k in column_profiles.keys() if k.isdigit()]):
                    column_key = str(key)
                    column_data = column_profiles[column_key]
                    
                    # Try different ways to get the column name
                    if isinstance(column_data, dict):
                        # First check for a 'column_name' field (most common in this dataset)
                        if "column_name" in column_data:
                            original_headers.append(column_data["column_name"])
                        # Then check for a 'name' field
                        elif "name" in column_data:
                            original_headers.append(column_data["name"])
                        # If no name found, use a generic name
                        else:
                            original_headers.append(f"Column {key}")
                    else:
                        original_headers.append(f"Column {key}")
            
            elif isinstance(column_profiles, list):
                # Handle list format - this is the format we're seeing in the data
                for i, column in enumerate(column_profiles):
                    if isinstance(column, dict):
                        # First check for a 'column_name' field (most common in this dataset)
                        if "column_name" in column:
                            original_headers.append(column["column_name"])
                        # Then check for a 'name' field
                        elif "name" in column:
                            original_headers.append(column["name"])
                        # If no name found, use a generic name
                        else:
                            original_headers.append(f"Column {i}")
                    else:
                        original_headers.append(f"Column {i}")
        
        # Log the extracted headers for debugging
        logger.debug(f"[{request_id}] Extracted column headers: {original_headers[:5]}...")
        
        # Prepare response
        response = {
            "id": profile_result.id,
            "file_id": profile_result.file_id,
            "file_name": profile_result.file_name,
            "total_rows": profile_result.total_rows,
            "total_columns": profile_result.total_columns,
            "data_quality_score": profile_result.data_quality_score * 100 if profile_result.data_quality_score is not None else None,
            "columns": column_profiles,
            "original_headers": original_headers,
            "created_at": profile_result.created_at
        }
        
        logger.info(f"[{request_id}] Successfully retrieved profile with {len(column_profiles)} columns")
        return response
    
    except Exception as e:
        logger.error(f"[{request_id}] Error retrieving profile: {str(e)}", exc_info=True)
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/profiles/file/{file_id}", response_model=ProfileSummaryResponse)
async def get_profile_by_file_id(
    file_id: str,
    current_user: User = Depends(has_any_permission(["datapuur:read", "kginsights:read"])),
    db: Session = Depends(get_db)
):
    """
    Get the latest profile for a specific file by file ID.
    
    Returns a summary of the profile.
    """
    request_id = str(uuid.uuid4())[:8]
    logger.info(f"[{request_id}] Get profile by file_id request received for file_id: {file_id}")
    
    try:
        # Get latest profile result for this file
        profile_result = db.query(ProfileResult).filter(
            ProfileResult.file_id == file_id
        ).order_by(desc(ProfileResult.created_at)).first()
        
        if not profile_result:
            logger.warning(f"[{request_id}] No profile found for file ID {file_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No profile found for file ID {file_id}"
            )
        
        logger.info(f"[{request_id}] Found profile {profile_result.id} for file {file_id}")
        
        # Prepare response
        return {
            "id": profile_result.id,
            "file_id": profile_result.file_id,
            "file_name": profile_result.file_name,
            "total_rows": profile_result.total_rows,
            "total_columns": profile_result.total_columns,
            "data_quality_score": profile_result.data_quality_score * 100 if profile_result.data_quality_score is not None else None,
            "created_at": profile_result.created_at
        }
    
    except Exception as e:
        logger.error(f"[{request_id}] Error retrieving profile by file ID: {str(e)}", exc_info=True)
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/profiles/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(
    profile_id: str,
    current_user: User = Depends(has_permission("datapuur:manage")),
    db: Session = Depends(get_db)
):
    """
    Delete a data profile by ID.
    
    Requires datapuur:manage permission.
    """
    request_id = str(uuid.uuid4())[:8]
    logger.info(f"[{request_id}] Delete profile request received for profile_id: {profile_id}")
    
    try:
        # Get profile result
        profile_result = db.query(ProfileResult).filter(ProfileResult.id == profile_id).first()
        
        if not profile_result:
            logger.warning(f"[{request_id}] Profile with ID {profile_id} not found for deletion")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Profile with ID {profile_id} not found"
            )
        
        logger.debug(f"[{request_id}] Deleting profile {profile_id} for file {profile_result.file_name}")
        
        # Delete profile result
        db.delete(profile_result)
        db.commit()
        logger.info(f"[{request_id}] Successfully deleted profile {profile_id}")
        
        # Log the activity
        log_activity(
            db=db,
            username=current_user.username,
            action="Delete Data Profile",
            details=f"Deleted profile for {profile_result.file_name} (ID: {profile_id})"
        )
        
        return None
    
    except Exception as e:
        db.rollback()
        logger.error(f"[{request_id}] Error deleting profile: {str(e)}", exc_info=True)
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    logger.debug("Health check endpoint called")
    return {"status": "healthy"}
