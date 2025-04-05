"""
Source Router for DataPuur Ingestion API.
This module implements the API endpoints for source management and data acquisition.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File, Form, BackgroundTasks, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional, Union
from fastapi.responses import FileResponse, JSONResponse
import uuid
from datetime import datetime
import json
import os
import shutil
from pathlib import Path
import logging

from ...models import User, get_db, ActivityLog, UploadedFile
from ...auth import get_current_active_user, has_permission, log_activity, has_any_permission
from ... import datapuur as legacy_datapuur  # Import the existing implementation
from .models import (
    SourceType, SourceStatus, SourceCreate, SourceResponse, SourceListResponse,
    UploadResponse, ChunkUploadRequest, ChunkUploadResponse, CompleteUploadRequest,
    SchemaResponse, PreviewResponse, TestConnectionRequest, TestConnectionResponse,
    DatabaseConnectionInfo, JobResponse, JobStatus
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/sources", tags=["ingestion-sources"])

@router.post("/upload", status_code=status.HTTP_201_CREATED, response_model=UploadResponse)
async def upload_source_file(
    file: UploadFile = File(...),
    chunk_size: int = Form(1000),
    current_user: User = Depends(has_permission("datapuur:write")),
    db: Session = Depends(get_db)
):
    """
    Upload a source file (CSV/JSON) for data ingestion.
    
    This endpoint wraps the existing file upload functionality.
    """
    # Delegate to the existing implementation
    result = await legacy_datapuur.upload_file(
        file=file, 
        chunkSize=chunk_size,
        current_user=current_user,
        db=db
    )
    
    return UploadResponse(
        file_id=result["file_id"],
        message=result["message"]
    )

@router.post("/upload-chunk", status_code=status.HTTP_200_OK, response_model=ChunkUploadResponse)
async def upload_source_chunk(
    file: UploadFile = File(...),
    chunk_size: int = Form(1000),
    chunk_index: int = Form(...),
    total_chunks: int = Form(...),
    upload_id: str = Form(...),
    current_user: User = Depends(has_permission("datapuur:write")),
    db: Session = Depends(get_db)
):
    """
    Upload a chunk of a large file.
    
    This endpoint wraps the existing chunk upload functionality.
    """
    # Delegate to the existing implementation
    result = await legacy_datapuur.upload_chunk(
        file=file,
        chunkSize=chunk_size,
        chunkIndex=chunk_index,
        totalChunks=total_chunks,
        uploadId=upload_id,
        current_user=current_user,
        db=db
    )
    
    return ChunkUploadResponse(message=result["message"])

@router.post("/complete-upload", status_code=status.HTTP_200_OK, response_model=UploadResponse)
async def complete_source_upload(
    request: CompleteUploadRequest,
    req: Request,
    current_user: User = Depends(has_permission("datapuur:write")),
    db: Session = Depends(get_db)
):
    """
    Complete a chunked upload by combining all chunks into a single file.
    
    This endpoint wraps the existing complete chunked upload functionality.
    """
    # Wrap the request data for the existing implementation
    request_data = {
        "uploadId": request.upload_id,
        "fileName": request.file_name,
        "totalChunks": request.total_chunks,
        "chunkSize": request.chunk_size,
        "originalChunkSize": request.original_chunk_size
    }
    
    # Create a custom Request object with the data
    class CustomRequest:
        async def json(self):
            return request_data
    
    # Delegate to the existing implementation
    result = await legacy_datapuur.complete_chunked_upload(
        request=CustomRequest(),
        current_user=current_user,
        db=db
    )
    
    return UploadResponse(
        file_id=result["file_id"],
        message=result["message"]
    )

@router.get("/", response_model=SourceListResponse)
async def list_sources(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    source_type: Optional[SourceType] = Query(None, alias="type"),
    status: Optional[SourceStatus] = Query(None),
    search: Optional[str] = Query(None),
    sort: str = Query("newest"),
    current_user: User = Depends(has_permission("datapuur:read")),
    db: Session = Depends(get_db)
):
    """
    List all source files with filtering and pagination.
    
    This endpoint wraps the existing file history functionality.
    """
    # Delegate to the existing implementation
    result = legacy_datapuur.get_file_history(
        page=page,
        limit=limit,
        current_user=current_user,
        db=db
    )
    
    # Transform the items to match our new response model
    sources = []
    for item in result["items"]:
        source = SourceResponse(
            id=item.id,
            name=item.filename,
            type=item.type,
            status=item.status,
            created_at=datetime.fromisoformat(item.uploaded_at),
            created_by=item.uploaded_by,
            path=None,  # We don't expose the actual file path for security
            connection_info=item.database_info if hasattr(item, "database_info") else None,
            schema=None,
            preview_url=f"/api/datapuur/sources/{item.id}/preview",
            download_url=f"/api/datapuur/sources/{item.id}/download"
        )
        sources.append(source)
    
    return SourceListResponse(
        items=sources,
        total=result["total"],
        page=result["page"],
        limit=result["limit"]
    )

@router.get("/files", response_model=SourceListResponse)
async def get_file_history(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    sort: str = Query("newest"),
    type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: User = Depends(has_permission("datapuur:read")),
    db: Session = Depends(get_db)
):
    """
    Get history of uploaded files.
    
    This endpoint wraps the existing file history functionality.
    """
    # Delegate to the existing implementation
    result = legacy_datapuur.get_file_history(
        page=page,
        limit=limit,
        current_user=current_user,
        db=db
    )
    
    # Transform the items to match our new response model
    sources = []
    for item in result["items"]:
        source = SourceResponse(
            id=item.id,
            name=item.filename,
            type=item.type,
            status=SourceStatus.AVAILABLE,
            created_at=datetime.fromisoformat(item.uploaded_at) if isinstance(item.uploaded_at, str) else item.uploaded_at,
            created_by=item.uploaded_by,
            path=None,  # We don't expose the actual file path for security
            connection_info=None,
            schema=None,
            preview_url=f"/api/datapuur/sources/{item.id}/preview",
            download_url=f"/api/datapuur/sources/{item.id}/download"
        )
        sources.append(source)
    
    return SourceListResponse(
        items=sources,
        total=result["total"],
        page=result["page"],
        limit=result["limit"]
    )

@router.get("/{source_id}", response_model=SourceResponse)
async def get_source_details(
    source_id: str,
    current_user: User = Depends(has_permission("datapuur:read")),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a source.
    
    This endpoint wraps the existing source details functionality.
    """
    # Delegate to the existing implementation
    try:
        # First check if this is a proper file upload
        file = legacy_datapuur.get_uploaded_file(db, source_id)
        
        if not file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Source with ID {source_id} not found"
            )
            
        # Get schema information if available
        schema = None
        if file.schema:
            try:
                schema = json.loads(file.schema)
            except:
                schema = None
        
        return SourceResponse(
            id=file.id,
            name=file.filename,
            type=file.type,
            status="available",  # File exists, so it's available
            created_at=file.uploaded_at,
            created_by=file.uploaded_by,
            path=None,  # Don't expose actual file path
            connection_info=None,  # Not a database source
            schema=schema,
            preview_url=f"/api/datapuur/sources/{file.id}/preview",
            download_url=f"/api/datapuur/sources/{file.id}/download"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving source details: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving source details: {str(e)}"
        )

@router.delete("/{source_id}", status_code=status.HTTP_200_OK)
async def delete_source(
    source_id: str,
    current_user: User = Depends(has_permission("datapuur:manage")),
    db: Session = Depends(get_db)
):
    """
    Delete a source file.
    
    This endpoint would require access to the actual file deletion which 
    might be implemented in the existing codebase.
    """
    # Check if the file exists
    file = legacy_datapuur.get_uploaded_file(db, source_id)
    
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source with ID {source_id} not found"
        )
    
    try:
        # Delete the physical file
        if os.path.exists(file.path):
            os.remove(file.path)
        
        # Delete the file record from database
        db.delete(file)
        db.commit()
        
        # Log the activity
        log_activity(
            db=db,
            username=current_user.username,
            action="Delete source",
            details=f"Deleted source file: {file.filename}"
        )
        
        return {"success": True, "message": f"Source {file.filename} deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting source: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting source: {str(e)}"
        )

@router.get("/{source_id}/preview", response_model=PreviewResponse)
async def preview_source(
    source_id: str,
    current_user: User = Depends(has_permission("datapuur:read")),
    db: Session = Depends(get_db)
):
    """
    Preview source data.
    
    This endpoint wraps the existing file preview functionality.
    """
    # Delegate to the existing implementation
    result = legacy_datapuur.preview_file(
        file_id=source_id,
        current_user=current_user,
        db=db
    )
    
    return PreviewResponse(
        data=result.data,
        headers=result.headers,
        filename=result.filename,
        type=result.type
    )

@router.get("/{source_id}/schema", response_model=SchemaResponse)
async def get_source_schema(
    source_id: str,
    current_user: User = Depends(has_permission("datapuur:read")),
    db: Session = Depends(get_db)
):
    """
    Get schema of source data.
    
    This endpoint wraps the existing file schema functionality.
    """
    # Delegate to the existing implementation
    result = legacy_datapuur.get_file_schema(
        file_id=source_id,
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

@router.get("/{source_id}/download")
async def download_source(
    source_id: str,
    current_user: User = Depends(has_permission("datapuur:read")),
    db: Session = Depends(get_db)
):
    """
    Download original source.
    
    This endpoint wraps the existing file download functionality.
    """
    # Delegate to the existing implementation
    return legacy_datapuur.download_file(
        file_id=source_id,
        current_user=current_user,
        db=db
    )

@router.get("/history", response_model=SourceListResponse)
async def get_ingestion_history(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    sort: str = Query("newest"),
    type: str = Query(""),
    source: str = Query(""),
    status: str = Query(""),
    search: str = Query(""),
    current_user: User = Depends(has_permission("datapuur:read")),
    db: Session = Depends(get_db)
):
    """
    Get history of ingestion operations.
    
    This endpoint wraps the existing ingestion history functionality.
    """
    # Delegate to the existing implementation
    result = legacy_datapuur.get_ingestion_history(
        page=page,
        limit=limit,
        sort=sort,
        type=type,
        source=source,
        status=status,
        search=search,
        current_user=current_user,
        db=db
    )
    
    # Transform the items to match our new response model
    sources = []
    for item in result.items:
        source = SourceResponse(
            id=item.id,
            name=item.filename,
            type=item.source_type,
            status=SourceStatus(item.status) if hasattr(item, "status") else SourceStatus.AVAILABLE,
            created_at=datetime.fromisoformat(item.uploaded_at) if isinstance(item.uploaded_at, str) else item.uploaded_at,
            created_by=item.uploaded_by,
            path=None,  # We don't expose the actual file path for security
            connection_info=item.database_info if hasattr(item, "database_info") else None,
            schema=None,
            preview_url=f"/api/datapuur/sources/{item.id}/preview",
            download_url=f"/api/datapuur/sources/{item.id}/download"
        )
        sources.append(source)
    
    return SourceListResponse(
        items=sources,
        total=result.total,
        page=result.page,
        limit=result.limit
    )

@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_ingestion_job_status(
    job_id: str,
    current_user: User = Depends(has_permission("datapuur:read")),
    db: Session = Depends(get_db)
):
    """
    Get status of an ingestion job.
    
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
async def cancel_ingestion_job(
    job_id: str,
    current_user: User = Depends(has_permission("datapuur:write")),
    db: Session = Depends(get_db)
):
    """
    Cancel an ingestion job.
    
    This endpoint wraps the existing job cancellation functionality.
    """
    # Delegate to the existing implementation
    return legacy_datapuur.cancel_job(
        job_id=job_id,
        current_user=current_user,
        db=db
    )

@router.post("/db-connect", status_code=status.HTTP_201_CREATED, response_model=SourceResponse)
async def create_db_connection(
    connection: DatabaseConnectionInfo,
    current_user: User = Depends(has_permission("datapuur:write")),
    db: Session = Depends(get_db)
):
    """
    Create a database connection source.
    
    This endpoint creates a new source entry for a database connection.
    """
    # First test the connection
    test_result = await test_db_connection(
        TestConnectionRequest(connection_info=connection),
        current_user=current_user,
        db=db
    )
    
    if not test_result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Database connection failed: {test_result.message}"
        )
    
    # Generate a unique ID for the connection
    connection_id = str(uuid.uuid4())
    
    # Create a name for the connection if not provided
    connection_name = f"{connection.type.value} - {connection.database} ({datetime.now().strftime('%Y-%m-%d')})"
    
    # Create a connection config to save
    connection_info = connection.dict()
    
    # Create a source entry in the database
    file_data = {
        "filename": connection_name,
        "path": None,  # No physical file
        "type": "database",
        "uploaded_by": current_user.username,
        "uploaded_at": datetime.now(),
        "connection_info": connection_info
    }
    
    # Save to the database
    legacy_datapuur.save_uploaded_file(db, connection_id, file_data)
    
    # Log the activity
    log_activity(
        db=db,
        username=current_user.username,
        action="Database connection",
        details=f"Created database connection to {connection.type.value} database: {connection.database}"
    )
    
    return SourceResponse(
        id=connection_id,
        name=connection_name,
        type=SourceType.DATABASE,
        status=SourceStatus.AVAILABLE,
        created_at=datetime.now(),
        created_by=current_user.username,
        path=None,
        connection_info=connection_info,
        schema=None,
        preview_url=f"/api/datapuur/sources/{connection_id}/preview",
        download_url=None  # No download for database connections
    )

@router.post("/db-test", status_code=status.HTTP_200_OK, response_model=TestConnectionResponse)
async def test_db_connection(
    request: TestConnectionRequest,
    current_user: User = Depends(has_permission("datapuur:write")),
    db: Session = Depends(get_db)
):
    """
    Test database connection.
    
    This endpoint wraps the existing database connection test functionality.
    """
    try:
        # Convert our model to the format expected by the legacy function
        connection_info = request.connection_info.dict()
        
        # Delegate to the existing implementation
        result = legacy_datapuur.test_database_connection(
            connection_info=connection_info,
            current_user=current_user,
            db=db
        )
        
        return TestConnectionResponse(
            success=result["success"],
            message=result["message"],
            tables=result.get("tables")
        )
    except Exception as e:
        logger.error(f"Error testing database connection: {str(e)}")
        return TestConnectionResponse(
            success=False,
            message=f"Error testing database connection: {str(e)}"
        )

@router.post("/db-schema", status_code=status.HTTP_200_OK, response_model=SchemaResponse)
async def get_db_schema(
    request: TestConnectionRequest,
    current_user: User = Depends(has_permission("datapuur:read")),
    db: Session = Depends(get_db)
):
    """
    Get schema from database connection.
    
    This endpoint wraps the existing database schema functionality.
    """
    try:
        # Convert our model to the format expected by the legacy function
        connection_info = request.connection_info.dict()
        
        # Delegate to the existing implementation
        result = legacy_datapuur.get_database_schema(
            connection_info=connection_info,
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
    except Exception as e:
        logger.error(f"Error getting database schema: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting database schema: {str(e)}"
        )
