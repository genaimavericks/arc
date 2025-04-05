"""
Dataset Router for DataPuur Ingestion API.
This module implements the API endpoints for dataset management and processing.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional, Union
from fastapi.responses import FileResponse, JSONResponse
import uuid
from datetime import datetime
import json
import os
from pathlib import Path
import logging

from ...models import User, get_db, ActivityLog, UploadedFile, IngestionJob
from ...auth import get_current_active_user, has_permission, log_activity, has_any_permission
from ... import datapuur as legacy_datapuur  # Import the existing implementation
from .models import (
    DatasetStatus, DatasetCreate, DatasetResponse, DatasetListResponse,
    JobStatus, JobResponse, DownloadFormat, DatasetStatistics,
    SchemaResponse, PreviewResponse
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/datasets", tags=["ingestion-datasets"])

@router.post("/create", status_code=status.HTTP_201_CREATED, response_model=JobResponse)
async def create_dataset(
    request: DatasetCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(has_permission("datapuur:write")),
    db: Session = Depends(get_db)
):
    """
    Create dataset from source (starts ingestion).
    
    This endpoint wraps the existing file ingestion functionality.
    """
    # Get the source file
    source = legacy_datapuur.get_uploaded_file(db, request.source_id)
    
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source with ID {request.source_id} not found"
        )
    
    try:
        # Determine the type of ingestion based on source type
        if source.type in ["csv", "json"]:
            # Create a request object compatible with the legacy API
            ingestion_request = legacy_datapuur.FileIngestionRequest(
                file_id=source.id,
                file_name=request.name or source.filename,
                chunk_size=source.chunk_size
            )
            
            # Start the ingestion process
            result = legacy_datapuur.ingest_file(
                request=ingestion_request,
                background_tasks=background_tasks,
                current_user=current_user,
                db=db
            )
        elif source.type == "database":
            # Get connection info from the source
            if not source.connection_info:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Database source does not have connection information"
                )
            
            connection_info = json.loads(source.connection_info) if isinstance(source.connection_info, str) else source.connection_info
            
            # Create a request object compatible with the legacy API
            db_config = legacy_datapuur.DatabaseConfig(
                type=connection_info.get("type"),
                config=connection_info,
                chunk_size=source.chunk_size,
                connection_name=request.name or source.filename
            )
            
            # Start the ingestion process
            result = legacy_datapuur.ingest_database(
                request=db_config,
                background_tasks=background_tasks,
                current_user=current_user,
                db=db
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported source type: {source.type}"
            )
        
        # Create a response in our new format
        return JobResponse(
            id=result["job_id"],
            name=result["job_name"],
            type=result["job_type"],
            status=result["status"],
            progress=0,  # Initial progress
            start_time=datetime.now(),
            details=f"Processing {request.name or source.filename} from {source.type} source",
            config={
                "source_id": source.id,
                "source_name": source.filename,
                "source_type": source.type,
                "dataset_name": request.name or source.filename,
                "dataset_description": request.description
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating dataset: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating dataset: {str(e)}"
        )

@router.get("/", response_model=DatasetListResponse)
async def list_datasets(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    status: Optional[DatasetStatus] = Query(None),
    source_type: Optional[str] = Query(None, alias="type"),
    search: Optional[str] = Query(None),
    sort: str = Query("newest"),
    current_user: User = Depends(has_permission("datapuur:read")),
    db: Session = Depends(get_db)
):
    """
    List all datasets with filtering and pagination.
    
    This endpoint wraps the existing ingestion history functionality.
    """
    # Map our sort parameter to legacy sort parameter
    legacy_sort = sort
    if sort == "name_asc":
        legacy_sort = "name"
    elif sort == "name_desc":
        legacy_sort = "name_desc"
    elif sort == "newest":
        legacy_sort = "newest"
    elif sort == "oldest":
        legacy_sort = "oldest"
    
    # Map our status parameter to legacy status parameter
    legacy_status = ""
    if status:
        if status == DatasetStatus.PROCESSING:
            legacy_status = "running"
        elif status == DatasetStatus.AVAILABLE:
            legacy_status = "completed"
        elif status == DatasetStatus.ERROR:
            legacy_status = "error"
    
    # Delegate to the existing implementation
    result = legacy_datapuur.get_ingestion_history(
        page=page,
        limit=limit,
        sort=legacy_sort,
        type=source_type or "",
        source="",
        status=legacy_status,
        search=search or "",
        current_user=current_user,
        db=db
    )
    
    # Transform the results to our new model
    datasets = []
    for item in result.items:
        # Map status from legacy format to our new format
        dataset_status = DatasetStatus.PROCESSING
        if item.status == "completed":
            dataset_status = DatasetStatus.AVAILABLE
        elif item.status == "error":
            dataset_status = DatasetStatus.ERROR
        
        datasets.append(DatasetResponse(
            id=item.id,
            name=item.filename,
            description=None,  # Not available in legacy model
            created_at=datetime.fromisoformat(item.uploaded_at) if isinstance(item.uploaded_at, str) else item.uploaded_at,
            created_by=item.uploaded_by,
            status=dataset_status,
            source_id=item.id,  # In legacy model, the ingestion ID is the same as the source ID
            source_name=item.filename,
            source_type=item.source_type,
            file_path=None,  # Don't expose file paths
            schema=None,
            statistics=None,
            row_count=item.size if hasattr(item, "size") else None,
            preview_url=f"/api/datapuur/datasets/{item.id}/preview",
            download_url=f"/api/datapuur/datasets/{item.id}/download",
            visualization_url=None
        ))
    
    return DatasetListResponse(
        items=datasets,
        total=result.total,
        page=result.page,
        limit=result.limit
    )

@router.get("/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(
    dataset_id: str,
    current_user: User = Depends(has_permission("datapuur:read")),
    db: Session = Depends(get_db)
):
    """
    Get dataset details.
    
    This endpoint wraps existing functionality to get dataset details.
    """
    # Try to get the ingestion job
    job = legacy_datapuur.get_ingestion_job(db, dataset_id)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset with ID {dataset_id} not found"
        )
    
    # Get the source file if available
    source = None
    source_id = None
    config = None
    
    if job.config:
        try:
            config = json.loads(job.config) if isinstance(job.config, str) else job.config
            source_id = config.get("file_id")
            if source_id:
                source = legacy_datapuur.get_uploaded_file(db, source_id)
        except:
            pass
    
    # Map status from legacy format to our new format
    dataset_status = DatasetStatus.PROCESSING
    if job.status == "completed":
        dataset_status = DatasetStatus.AVAILABLE
    elif job.status in ["error", "failed"]:
        dataset_status = DatasetStatus.ERROR
    
    # Create a response with available information
    response = DatasetResponse(
        id=job.id,
        name=job.name,
        description=None,  # Not available in legacy model
        created_at=job.start_time,
        created_by=job.created_by if hasattr(job, "created_by") else current_user.username,
        status=dataset_status,
        source_id=source_id or "",
        source_name=source.filename if source else job.name,
        source_type=source.type if source else (config.get("type") if config else "unknown"),
        file_path=None,  # Don't expose file paths
        schema=None,
        statistics=None,
        row_count=None,
        preview_url=f"/api/datapuur/datasets/{job.id}/preview" if dataset_status == DatasetStatus.AVAILABLE else None,
        download_url=f"/api/datapuur/datasets/{job.id}/download" if dataset_status == DatasetStatus.AVAILABLE else None,
        visualization_url=None
    )
    
    return response

@router.delete("/{dataset_id}", status_code=status.HTTP_200_OK)
async def delete_dataset(
    dataset_id: str,
    current_user: User = Depends(has_permission("datapuur:manage")),
    db: Session = Depends(get_db)
):
    """
    Delete a dataset.
    
    This endpoint wraps the existing dataset deletion functionality.
    """
    # Delegate to the existing implementation
    return legacy_datapuur.delete_dataset_endpoint(
        dataset_id=dataset_id,
        current_user=current_user,
        db=db
    )

@router.get("/{dataset_id}/preview", response_model=PreviewResponse)
async def preview_dataset(
    dataset_id: str,
    current_user: User = Depends(has_permission("datapuur:read")),
    db: Session = Depends(get_db)
):
    """
    Preview dataset.
    
    This endpoint wraps the existing ingestion preview functionality.
    """
    # Delegate to the existing implementation
    result = legacy_datapuur.get_ingestion_preview(
        ingestion_id=dataset_id,
        current_user=current_user,
        db=db
    )
    
    return PreviewResponse(
        data=result.data,
        headers=result.headers,
        filename=result.filename,
        type=result.type
    )

@router.get("/{dataset_id}/schema", response_model=SchemaResponse)
async def get_dataset_schema(
    dataset_id: str,
    current_user: User = Depends(has_permission("datapuur:read")),
    db: Session = Depends(get_db)
):
    """
    Get dataset schema.
    
    This endpoint wraps the existing ingestion schema functionality.
    """
    # Delegate to the existing implementation
    result = legacy_datapuur.get_ingestion_schema(
        ingestion_id=dataset_id,
        current_user=current_user,
        db=db
    )
    
    # Transform to our new schema model
    fields = []
    for field in result.fields:
        fields.append({
            "name": field["name"],
            "type": field["type"],
            "nullable": field.get("nullable", False),
            "format": field.get("format"),
            "description": field.get("description"),
            "sample_values": field.get("sample_values")
        })
    
    return SchemaResponse(
        fields=fields,
        sample_values=result.sample_values
    )

@router.get("/{dataset_id}/statistics", response_model=DatasetStatistics)
async def get_dataset_statistics(
    dataset_id: str,
    current_user: User = Depends(has_permission("datapuur:read")),
    db: Session = Depends(get_db)
):
    """
    Get dataset statistics.
    
    This endpoint wraps the existing ingestion statistics functionality.
    """
    # Delegate to the existing implementation
    result = legacy_datapuur.get_ingestion_statistics(
        ingestion_id=dataset_id,
        current_user=current_user,
        db=db
    )
    
    return DatasetStatistics(
        row_count=result.row_count,
        column_count=result.column_count,
        null_percentage=result.null_percentage,
        memory_usage=result.memory_usage,
        processing_time=result.processing_time,
        data_density=result.data_density,
        completion_rate=result.completion_rate,
        error_rate=result.error_rate
    )

@router.get("/{dataset_id}/download")
async def download_dataset(
    dataset_id: str,
    format: DownloadFormat = Query(DownloadFormat.CSV),
    current_user: User = Depends(has_permission("datapuur:read")),
    db: Session = Depends(get_db)
):
    """
    Download dataset with format options.
    
    This endpoint wraps the existing ingestion download functionality.
    """
    # Delegate to the existing implementation
    return legacy_datapuur.download_ingestion(
        ingestion_id=dataset_id,
        format=format.value,
        current_user=current_user,
        db=db
    )

@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job_status(
    job_id: str,
    current_user: User = Depends(has_permission("datapuur:read")),
    db: Session = Depends(get_db)
):
    """
    Get ingestion job status.
    
    This endpoint wraps the existing job status functionality.
    """
    # Delegate to the existing implementation
    result = legacy_datapuur.get_job_status(
        job_id=job_id,
        current_user=current_user,
        db=db
    )
    
    # Map to our new model
    status_map = {
        "pending": JobStatus.PENDING,
        "running": JobStatus.RUNNING,
        "completed": JobStatus.COMPLETED,
        "failed": JobStatus.FAILED,
        "cancelled": JobStatus.CANCELLED,
        # Add any other status mappings as needed
    }
    
    job_status = status_map.get(result.status, JobStatus.RUNNING)
    
    return JobResponse(
        id=result.id,
        name=result.name,
        type=result.type,
        status=job_status,
        progress=result.progress,
        start_time=datetime.fromisoformat(result.start_time) if isinstance(result.start_time, str) else result.start_time,
        end_time=datetime.fromisoformat(result.end_time) if result.end_time and isinstance(result.end_time, str) else result.end_time,
        details=result.details,
        error=result.error,
        duration=result.duration,
        config=result.config
    )

@router.post("/jobs/{job_id}/cancel", status_code=status.HTTP_200_OK)
async def cancel_job(
    job_id: str,
    current_user: User = Depends(has_permission("datapuur:write")),
    db: Session = Depends(get_db)
):
    """
    Cancel ingestion job.
    
    This endpoint wraps the existing job cancellation functionality.
    """
    # Delegate to the existing implementation
    return legacy_datapuur.cancel_job(
        job_id=job_id,
        current_user=current_user,
        db=db
    )
