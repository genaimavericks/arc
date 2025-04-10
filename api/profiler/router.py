"""
Data Profiler Router for the RSW platform.
This module implements API endpoints for data profiling.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import pandas as pd
import numpy as np
from typing import Dict, Any, List
import os
import uuid
import logging
import time
import json
import csv
from io import StringIO
from fastapi.responses import StreamingResponse
from sqlalchemy import desc
from pathlib import Path
from datetime import datetime

from ..models import User, get_db
from ..auth import has_permission, log_activity, has_any_permission
from .models import ProfileResult, ColumnProfile
from .schemas.profile import ProfileRequest, ProfileResponse, ProfileListResponse, ProfileSummaryResponse
from .services.engine import DataProfiler
from pathlib import Path  # Import Path for directory handling

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
        
        # Check if this file is from a cancelled upload
        # Extract job_id from the file_path (which is typically the job_id.parquet)
        job_id = os.path.splitext(request.file_path)[0]  # Remove .parquet extension
        
        # Check if there's a cancellation marker for this job
        cancel_marker = Path(__file__).parent.parent / "uploads" / f"cancel_{job_id}"
        if cancel_marker.exists():
            logger.info(f"[{request_id}] Cancellation marker found for job {job_id}, aborting profile generation")
            return {
                "id": str(uuid.uuid4()),
                "status": "cancelled",
                "message": "Profile generation cancelled because the associated upload was cancelled",
                "file_id": request.file_id,
                "file_name": request.file_name,
                "created_at": datetime.now().isoformat(),
                "summary": {"status": "cancelled"},
                "columns": []
            }
        
        # Also check if there's a cancellation marker in localStorage format
        # This is a more generic check for any upload ID that might be associated with this file
        upload_cancel_markers = list((Path(__file__).parent.parent / "uploads").glob("cancel_upload-*"))
        for marker in upload_cancel_markers:
            marker_name = marker.name
            upload_id = marker_name.replace("cancel_", "")
            
            # Check if this upload ID is associated with the file
            # This is a heuristic and may need adjustment based on how upload IDs are stored
            if upload_id in job_id:
                logger.info(f"[{request_id}] Upload cancellation marker found for upload {upload_id}, aborting profile generation")
                return {
                    "id": str(uuid.uuid4()),
                    "status": "cancelled",
                    "message": "Profile generation cancelled because the associated upload was cancelled",
                    "file_id": request.file_id,
                    "file_name": request.file_name,
                    "created_at": datetime.now().isoformat(),
                    "summary": {"status": "cancelled"},
                    "columns": []
                }
        
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
            
            # Detect exact and fuzzy duplicates
            logger.info(f"[{request_id}] Starting duplicate detection")
            try:
                # Track time for duplicate detection
                dup_start = time.time()
                
                # Detect exact duplicates (much faster operation)
                exact_duplicates = profiler.detect_exact_duplicates()
                profile_summary["exact_duplicates_count"] = exact_duplicates["count"]
                
                # Detect fuzzy duplicates (more intensive operation)
                fuzzy_duplicates = profiler.detect_fuzzy_duplicates(threshold=0.9)
                profile_summary["fuzzy_duplicates_count"] = fuzzy_duplicates["count"]
                
                # Create duplicate groups dictionary for storage
                duplicate_groups = {
                    "exact": exact_duplicates["values"],
                    "fuzzy": fuzzy_duplicates["values"]
                }
                
                dup_duration = time.time() - dup_start
                logger.info(f"[{request_id}] Duplicate detection completed in {dup_duration:.2f} seconds")
            except Exception as dup_error:
                logger.warning(f"[{request_id}] Error in duplicate detection: {str(dup_error)}")
                # Set default values if duplicate detection fails
                profile_summary["exact_duplicates_count"] = 0
                profile_summary["fuzzy_duplicates_count"] = 0
                duplicate_groups = {"exact": [], "fuzzy": []}
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
            
            # Log detailed information about column profiles for debugging
            logger.info(f"[{request_id}] Column profiles structure type: {type(column_profiles_json)}")
            
            if isinstance(column_profiles_json, list) and column_profiles_json:
                # Log sample column profile
                sample_column = column_profiles_json[0]
                logger.info(f"[{request_id}] Sample column profile keys: {list(sample_column.keys()) if isinstance(sample_column, dict) else 'Not a dict'}")
                
                # Specifically check for quality metrics
                if isinstance(sample_column, dict):
                    quality_metrics = {k: sample_column.get(k) for k in ['quality_score', 'completeness', 'uniqueness', 'validity'] if k in sample_column}
                    logger.info(f"[{request_id}] Quality metrics in sample column: {quality_metrics}")
                    
                    # If quality metrics are missing, log a warning
                    missing_metrics = [k for k in ['quality_score', 'completeness', 'uniqueness', 'validity'] if k not in sample_column]
                    if missing_metrics:
                        logger.warning(f"[{request_id}] Missing quality metrics in column profiles: {missing_metrics}")
            elif isinstance(column_profiles_json, dict) and column_profiles_json:
                # If it's a dictionary of columns
                sample_key = list(column_profiles_json.keys())[0]
                sample_column = column_profiles_json[sample_key]
                logger.info(f"[{request_id}] Sample column profile keys: {list(sample_column.keys()) if isinstance(sample_column, dict) else 'Not a dict'}")
                
                # Check for quality metrics
                if isinstance(sample_column, dict):
                    quality_metrics = {k: sample_column.get(k) for k in ['quality_score', 'completeness', 'uniqueness', 'validity'] if k in sample_column}
                    logger.info(f"[{request_id}] Quality metrics in sample column: {quality_metrics}")
                    
                    # If quality metrics are missing, log a warning
                    missing_metrics = [k for k in ['quality_score', 'completeness', 'uniqueness', 'validity'] if k not in sample_column]
                    if missing_metrics:
                        logger.warning(f"[{request_id}] Missing quality metrics in column profiles: {missing_metrics}")
            
            profile_result = ProfileResult(
                id=profile_id,
                file_id=file_id,
                file_name=request.file_name,
                parquet_file_path=str(request.file_path),  # Save the parquet file path
                total_rows=profile_summary["total_rows"],
                total_columns=profile_summary["total_columns"],
                data_quality_score=profile_summary["data_quality_score"],
                column_profiles=column_profiles_json,  # Store column profiles as JSON
                exact_duplicates_count=profile_summary["exact_duplicates_count"],
                fuzzy_duplicates_count=profile_summary["fuzzy_duplicates_count"],
                duplicate_groups=duplicate_groups
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
        
        # Record the activity in the activity log
        log_activity(
            db=db,
            username=current_user.username,
            action="Data Profile",
            details=f"Generated profile for {request.file_name} (file_id: {file_id})"
        )

        # Ensure columns are in dictionary format keyed by column_name
        column_dict = {}
        if isinstance(column_profiles, list):
            for col in column_profiles:
                if isinstance(col, dict) and "column_name" in col:
                    column_dict[col["column_name"]] = col
        else:
            # If it's already a dictionary or another format, use as is
            column_dict = column_profiles

        # Prepare response
        response_data = {
            "id": profile_result.id,
            "file_id": request.file_id,
            "file_name": request.file_name,
            **profile_summary,
            "columns": column_dict,
            "created_at": profile_result.created_at,
            "exact_duplicates_count": profile_summary["exact_duplicates_count"],
            "fuzzy_duplicates_count": profile_summary["fuzzy_duplicates_count"],
            "duplicate_groups": duplicate_groups
        }

        # Convert any NumPy types to Python native types for serialization
        response_data = convert_numpy_types(response_data)

        total_duration = time.time() - start_time
        logger.info(f"[{request_id}] Profile request completed in {total_duration:.2f} seconds")
        return response_data

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
                "created_at": profile.created_at,
                "exact_duplicates_count": profile.exact_duplicates_count,
                "fuzzy_duplicates_count": profile.fuzzy_duplicates_count
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
        
        # Log the column profiles data for debugging
        logger.info(f"[{request_id}] Column profiles data structure type: {type(column_profiles)}")
        if column_profiles:
            # Log the keys/structure
            if isinstance(column_profiles, dict):
                logger.info(f"[{request_id}] Column profiles keys: {list(column_profiles.keys())[:5]}...")
                # Log a sample column profile
                sample_key = list(column_profiles.keys())[0] if column_profiles else None
                if sample_key:
                    logger.info(f"[{request_id}] Sample column profile for key '{sample_key}': {column_profiles[sample_key]}")
                    logger.info(f"[{request_id}] Sample column profile keys: {list(column_profiles[sample_key].keys()) if isinstance(column_profiles[sample_key], dict) else 'Not a dict'}")
                    # Check for quality metrics
                    if isinstance(column_profiles[sample_key], dict):
                        quality_metrics = {k: column_profiles[sample_key].get(k) for k in ['quality_score', 'completeness', 'uniqueness', 'validity'] if k in column_profiles[sample_key]}
                        logger.info(f"[{request_id}] Quality metrics found in sample: {quality_metrics}")
            elif isinstance(column_profiles, list):
                logger.info(f"[{request_id}] Column profiles is a list with {len(column_profiles)} items")
                if column_profiles:
                    logger.info(f"[{request_id}] Sample column profile: {column_profiles[0]}")
                    logger.info(f"[{request_id}] Sample column profile keys: {list(column_profiles[0].keys()) if isinstance(column_profiles[0], dict) else 'Not a dict'}")
                    # Check for quality metrics
                    if isinstance(column_profiles[0], dict):
                        quality_metrics = {k: column_profiles[0].get(k) for k in ['quality_score', 'completeness', 'uniqueness', 'validity'] if k in column_profiles[0]}
                        logger.info(f"[{request_id}] Quality metrics found in sample: {quality_metrics}")
        
        # Ensure quality metrics are present in column profiles
        if column_profiles:
            if isinstance(column_profiles, dict):
                for key, column in column_profiles.items():
                    if isinstance(column, dict):
                        # If any quality metrics are missing, log a warning and add default values
                        missing_metrics = [k for k in ['quality_score', 'completeness', 'uniqueness', 'validity'] if k not in column]
                        if missing_metrics:
                            logger.warning(f"[{request_id}] Missing quality metrics in column '{key}': {missing_metrics}")
                            # Set default values for missing metrics
                            for metric in missing_metrics:
                                column[metric] = 0.7 if metric == 'quality_score' else 0.0
                            
                            # Update the column_profiles dictionary with the fixed column data
                            column_profiles[key] = column
            
            elif isinstance(column_profiles, list):
                for i, column in enumerate(column_profiles):
                    if isinstance(column, dict):
                        # If any quality metrics are missing, log a warning and add default values
                        missing_metrics = [k for k in ['quality_score', 'completeness', 'uniqueness', 'validity'] if k not in column]
                        if missing_metrics:
                            logger.warning(f"[{request_id}] Missing quality metrics in column at index {i}: {missing_metrics}")
                            # Set default values for missing metrics
                            for metric in missing_metrics:
                                column[metric] = 0.7 if metric == 'quality_score' else 0.0
                            
                            # Update the column_profiles list with the fixed column data
                            column_profiles[i] = column
                
                # Convert list to dictionary format for consistency with the frontend expectation
                column_dict = {}
                for i, column in enumerate(column_profiles):
                    column_dict[str(i)] = column
                column_profiles = column_dict
        
        # Log a sample column with quality metrics
        if column_profiles:
            if isinstance(column_profiles, dict) and column_profiles:
                sample_key = list(column_profiles.keys())[0]
                sample_column = column_profiles[sample_key]
                if isinstance(sample_column, dict):
                    quality_metrics = {k: sample_column.get(k) for k in ['quality_score', 'completeness', 'uniqueness', 'validity'] if k in sample_column}
                    logger.debug(f"[{request_id}] API Response with quality metrics sample:")
                    logger.debug(f"[{request_id}] Sample column quality metrics: {', '.join([f'{k}={v}' for k, v in quality_metrics.items()])}")
            elif isinstance(column_profiles, list) and column_profiles:
                sample_column = column_profiles[0]
                if isinstance(sample_column, dict):
                    quality_metrics = {k: sample_column.get(k) for k in ['quality_score', 'completeness', 'uniqueness', 'validity'] if k in sample_column}
                    logger.debug(f"[{request_id}] API Response with quality metrics sample:")
                    logger.debug(f"[{request_id}] Sample column quality metrics: {', '.join([f'{k}={v}' for k, v in quality_metrics.items()])}")
        
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
        
        # Ensure columns are in dictionary format keyed by column_name
        column_dict = {}
        if isinstance(column_profiles, list):
            for col in column_profiles:
                if isinstance(col, dict) and "column_name" in col:
                    column_dict[col["column_name"]] = col
        else:
            # If it's already a dictionary or another format, use as is
            column_dict = column_profiles
        
        # Prepare the response
        response = {
            "id": profile_result.id,
            "file_id": profile_result.file_id,
            "file_name": profile_result.file_name,
            "total_rows": profile_result.total_rows,
            "total_columns": profile_result.total_columns,
            "data_quality_score": profile_result.data_quality_score * 100 if profile_result.data_quality_score is not None else None,
            "columns": column_dict,
            "original_headers": original_headers,
            "created_at": profile_result.created_at,
            "exact_duplicates_count": profile_result.exact_duplicates_count,
            "fuzzy_duplicates_count": profile_result.fuzzy_duplicates_count,
            "duplicate_groups": profile_result.duplicate_groups
        }
        
        # Convert any NumPy types to Python native types for serialization
        response = convert_numpy_types(response)
        
        logger.info(f"[{request_id}] Successfully retrieved profile with {len(column_dict)} columns")
        logger.debug(f"[{request_id}] API Response: {response}")
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
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"detail": f"No profile found for file ID {file_id}"}
            )
        
        logger.info(f"[{request_id}] Found profile {profile_result.id} for file {file_id}")
        
        # Get column profiles from JSON
        column_profiles = profile_result.column_profiles
        
        # Ensure columns are in dictionary format keyed by column_name
        column_dict = {}
        if isinstance(column_profiles, list):
            for col in column_profiles:
                if isinstance(col, dict) and "column_name" in col:
                    column_dict[col["column_name"]] = col
        else:
            # If it's already a dictionary or another format, use as is
            column_dict = column_profiles
        
        # Return the profile data
        response_data = {
            "id": profile_result.id,
            "file_id": profile_result.file_id,
            "file_name": profile_result.file_name,
            "total_rows": profile_result.total_rows,
            "total_columns": profile_result.total_columns,
            "data_quality_score": profile_result.data_quality_score * 100 if profile_result.data_quality_score is not None else None,
            "created_at": profile_result.created_at,
            "exact_duplicates_count": profile_result.exact_duplicates_count,
            "fuzzy_duplicates_count": profile_result.fuzzy_duplicates_count,
            "columns": column_dict
        }
        
        # Convert any NumPy types to Python native types for serialization
        response_data = convert_numpy_types(response_data)
        
        return response_data
    
    except Exception as e:
        logger.error(f"[{request_id}] Error retrieving profile by file ID: {str(e)}", exc_info=True)
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/profiles/{profile_id}/export")
async def export_profile(
    profile_id: str,
    format: str = Query(..., regex="^(csv|json)$"),
    current_user: User = Depends(has_any_permission(["datapuur:read", "kginsights:read"])),
    db: Session = Depends(get_db)
):
    """
    Export a data profile in CSV or JSON format.
    
    Args:
        profile_id: The ID of the profile to export
        format: The export format, either 'csv' or 'json'
        
    Returns:
        A downloadable file in the specified format
    """
    # Log the export request
    logger.info(f"Export request received for profile_id: {profile_id}, format: {format}")
    
    try:
        # Reuse existing get_profile function to retrieve the profile data
        profile_data = await get_profile(profile_id, current_user, db)
        
        # Get the file name for the download
        file_name = profile_data.get("file_name", "profile").replace(" ", "_")
        
        # Log audit trail
        log_activity(
            db=db,
            user_id=current_user.id,
            activity_type="profile_export",
            resource_id=profile_id,
            resource_type="profile",
            details=f"Exported profile in {format} format"
        )
            
        # Create export based on format
        if format == 'json':
            # For JSON, simply return the profile data as a downloadable file
            return create_json_response(profile_data, f"{file_name}_profile.json")
        else:
            # For CSV, convert the hierarchical data to a flat format
            return create_csv_response(profile_data, f"{file_name}_profile.csv")
            
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error exporting profile {profile_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export profile: {str(e)}"
        )

def create_json_response(data: Dict, filename: str) -> StreamingResponse:
    """Create a downloadable JSON response"""
    # Convert data to JSON string with proper formatting
    json_str = json.dumps(data, indent=2)
    
    # Create a streaming response
    return StreamingResponse(
        iter([json_str]), 
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
    
def create_csv_response(data: Dict, filename: str) -> StreamingResponse:
    """Create a downloadable CSV response with flattened data"""
    # Create a CSV string buffer
    csv_buffer = StringIO()
    writer = csv.writer(csv_buffer)
    
    # Write the header information
    writer.writerow(["Profile Summary"])
    writer.writerow(["ID", data["id"]])
    writer.writerow(["File Name", data["file_name"]])
    writer.writerow(["Total Rows", data["total_rows"]])
    writer.writerow(["Total Columns", data["total_columns"]])
    writer.writerow(["Data Quality Score", f"{data['data_quality_score']:.2f}%"])
    writer.writerow(["Created At", data["created_at"]])
    writer.writerow(["Exact Duplicates", data["exact_duplicates_count"]])
    writer.writerow(["Fuzzy Duplicates", data["fuzzy_duplicates_count"]])
    writer.writerow([])  # Empty row for separation
    
    # Column profiles section
    writer.writerow(["Column Profiles"])
    
    # Create header row for column data
    column_headers = ["Column Name", "Data Type", "Count", "Null Count", "Unique Count", 
                     "Quality Score", "Completeness", "Uniqueness", "Validity", 
                     "Min Value", "Max Value", "Mean", "Median", "Mode", "Std Dev"]
    writer.writerow(column_headers)
    
    # Process columns
    columns_data = data["columns"]
    if isinstance(columns_data, dict):
        # Handle dictionary format
        for col_name, col_data in columns_data.items():
            # Extract column profile row
            column_row = extract_column_row(col_name, col_data)
            writer.writerow(column_row)
    elif isinstance(columns_data, list):
        # Handle array format
        for i, col_data in enumerate(columns_data):
            col_name = col_data.get("column_name", col_data.get("name", f"Column {i}"))
            column_row = extract_column_row(col_name, col_data)
            writer.writerow(column_row)
    
    # Get the CSV data and create a streaming response
    csv_buffer.seek(0)
    
    return StreamingResponse(
        iter([csv_buffer.getvalue()]), 
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
    
def extract_column_row(col_name: str, col_data: Dict) -> List:
    """Extract column data into a row for CSV export"""
    return [
        col_name,
        col_data.get("data_type", ""),
        col_data.get("count", 0),
        col_data.get("null_count", 0),
        col_data.get("unique_count", 0),
        f"{col_data.get('quality_score', 0):.2f}%",
        f"{col_data.get('completeness', 0):.2f}",
        f"{col_data.get('uniqueness', 0):.2f}",
        f"{col_data.get('validity', 0):.2f}",
        col_data.get("min_value", ""),
        col_data.get("max_value", ""),
        col_data.get("mean_value", ""),
        col_data.get("median_value", ""),
        col_data.get("mode_value", ""),
        col_data.get("std_dev", "")
    ]

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
