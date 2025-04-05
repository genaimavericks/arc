"""
Models for the DataPuur Ingestion API.
This module defines all data models used by the API endpoints.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum
from uuid import UUID

# Source-related models
class SourceType(str, Enum):
    """Types of data sources"""
    CSV = "csv"
    JSON = "json"
    DATABASE = "database"

class SourceStatus(str, Enum):
    """Status of data sources"""
    AVAILABLE = "available"
    PROCESSING = "processing"
    ERROR = "error"

class DatabaseType(str, Enum):
    """Supported database types"""
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    MSSQL = "mssql"
    ORACLE = "oracle"
    SQLITE = "sqlite"

class DatabaseConnectionInfo(BaseModel):
    """Database connection configuration"""
    type: DatabaseType
    host: Optional[str] = None
    port: Optional[int] = None
    database: str
    username: Optional[str] = None
    password: Optional[str] = None
    connection_string: Optional[str] = None
    tables: Optional[List[str]] = None
    query: Optional[str] = None

class SourceCreate(BaseModel):
    """Model for creating a new source"""
    name: str
    type: SourceType
    connection_info: Optional[DatabaseConnectionInfo] = None

class SourceResponse(BaseModel):
    """Response model for source information"""
    id: str
    name: str
    type: SourceType
    status: SourceStatus
    created_at: datetime
    created_by: str
    path: Optional[str] = None
    connection_info: Optional[Dict[str, Any]] = None
    schema: Optional[Dict[str, Any]] = None
    preview_url: Optional[str] = None
    download_url: Optional[str] = None

class SourceListResponse(BaseModel):
    """Response model for listing sources"""
    items: List[SourceResponse]
    total: int
    page: int
    limit: int

class UploadResponse(BaseModel):
    """Response for file upload"""
    file_id: str
    message: str

class ChunkUploadRequest(BaseModel):
    """Request for chunk upload"""
    upload_id: str
    chunk_index: int
    total_chunks: int
    chunk_size: int
    original_chunk_size: int = 1000

class ChunkUploadResponse(BaseModel):
    """Response for chunk upload"""
    message: str

class CompleteUploadRequest(BaseModel):
    """Request to complete a chunked upload"""
    upload_id: str
    file_name: str
    total_chunks: int
    chunk_size: int
    original_chunk_size: int = 1000

# Source preview/inspection models
class SchemaField(BaseModel):
    """Schema field definition"""
    name: str
    type: str
    nullable: bool = False
    format: Optional[str] = None
    description: Optional[str] = None
    sample_values: Optional[List[Any]] = None

class SchemaResponse(BaseModel):
    """Response model for schema information"""
    fields: List[SchemaField]
    sample_values: Optional[List[Any]] = None

class PreviewResponse(BaseModel):
    """Response model for data preview"""
    data: Any
    headers: Optional[List[str]] = None
    filename: str
    type: str

# Database connection models
class TestConnectionRequest(BaseModel):
    """Request to test a database connection"""
    connection_info: DatabaseConnectionInfo

class TestConnectionResponse(BaseModel):
    """Response for connection test"""
    success: bool
    message: str
    tables: Optional[List[str]] = None

# Dataset-related models
class DatasetStatus(str, Enum):
    """Status of datasets"""
    PROCESSING = "processing"
    AVAILABLE = "available"
    ERROR = "error"

class DatasetCreate(BaseModel):
    """Model for creating a new dataset"""
    name: str
    description: Optional[str] = None
    source_id: str

class DatasetResponse(BaseModel):
    """Response model for dataset information"""
    id: str
    name: str
    description: Optional[str] = None
    created_at: datetime
    created_by: str
    status: DatasetStatus
    source_id: str
    source_name: str
    source_type: SourceType
    file_path: Optional[str] = None
    schema: Optional[Dict[str, Any]] = None
    statistics: Optional[Dict[str, Any]] = None
    row_count: Optional[int] = None
    preview_url: Optional[str] = None
    download_url: Optional[str] = None
    visualization_url: Optional[str] = None

class DatasetListResponse(BaseModel):
    """Response model for listing datasets"""
    items: List[DatasetResponse]
    total: int
    page: int
    limit: int

class DatasetStatistics(BaseModel):
    """Dataset statistics information"""
    row_count: int
    column_count: int
    null_percentage: float
    memory_usage: str
    processing_time: str
    data_density: Optional[float] = None
    completion_rate: Optional[float] = None
    error_rate: Optional[float] = None

# Job-related models
class JobStatus(str, Enum):
    """Status of processing jobs"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class JobResponse(BaseModel):
    """Response model for job information"""
    id: str
    name: str
    type: str
    status: JobStatus
    progress: int
    start_time: datetime
    end_time: Optional[datetime] = None
    details: str
    error: Optional[str] = None
    duration: Optional[str] = None
    config: Optional[Dict[str, Any]] = None

# Download format options
class DownloadFormat(str, Enum):
    """Supported download formats"""
    CSV = "csv"
    JSON = "json"
    PARQUET = "parquet"
