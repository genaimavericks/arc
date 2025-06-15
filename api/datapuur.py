from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File, Form, BackgroundTasks, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional, Union
from fastapi.responses import FileResponse
import random
import uuid
from datetime import datetime, timedelta, timezone, date
import json
import csv
import os
import tempfile
import shutil
from pathlib import Path
import sqlalchemy
from sqlalchemy import create_engine, MetaData, Table, inspect, desc, func, and_, or_
import requests
import asyncio
import threading
import time
import logging
import traceback
import pandas as pd
import numpy as np
from pydantic import BaseModel, Field

from .models import User, get_db, ActivityLog, Role, UploadedFile, IngestionJob, DatabaseConnection
from .auth import get_current_active_user, has_role, has_permission, log_activity, has_any_permission
from .data_models import DataSource, DataMetrics, Activity, DashboardData
from .models import get_db, SessionLocal

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Helper function for consistent timestamp creation
def create_timezone_aware_timestamp():
    """
    Creates a timezone-aware timestamp in ISO format with UTC timezone.
    Used for consistent timestamp handling across all ingestion types.
    
    Returns:
        str: ISO formatted timestamp with timezone information
    """
    return datetime.now(timezone.utc).isoformat()

# Create a structured error response
def create_error_response(error_code, message, details=None, suggestion=None):
    """
    Create a structured error response for improved error handling.
    
    Args:
        error_code: Machine-readable error code
        message: Human-readable short message
        details: Detailed explanation of the error
        suggestion: Actionable suggestion for users
        
    Returns:
        Dictionary with structured error information
    """
    return {
        "error": {
            "code": error_code,
            "message": message,
            "details": details,
            "suggestion": suggestion,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    }

# Validate file before processing
def validate_file_before_processing(file_path, file_type):
    """
    Validate file before processing to provide early feedback.
    
    Args:
        file_path: Path to the file to validate
        file_type: Type of the file (csv, json, etc.)
        
    Returns:
        List of validation errors, empty if the file is valid
    """
    errors = []
    
    if file_type == "csv":
        try:
            # Read just a few rows to validate structure
            with open(file_path, 'r', encoding='utf-8') as f:
                header = f.readline().strip()
                if not header:
                    errors.append("CSV file appears to be empty")
                elif header.count(',') == 0:
                    errors.append("CSV file doesn't contain any commas, might not be properly formatted")
                
                # Try to read a few more lines to validate data
                sample_rows = [f.readline() for _ in range(5) if f.readline()]
                if not sample_rows and header:
                    errors.append("CSV file only contains a header row with no data")
        except UnicodeDecodeError:
            errors.append("File encoding not recognized. Please use UTF-8 encoding.")
        except Exception as e:
            errors.append(f"File validation error: {str(e)}")
    
    elif file_type == "json":
        try:
            # Check if the file is a valid JSON
            with open(file_path, 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                    
                    # Validate JSON structure for data ingestion
                    if not isinstance(data, list):
                        errors.append("JSON file must contain an array of objects")
                    elif len(data) == 0:
                        errors.append("JSON file contains an empty array")
                    elif any(not isinstance(item, dict) for item in data[:10]):
                        errors.append("JSON file must contain an array of objects (dictionaries)")
                    
                except json.JSONDecodeError as e:
                    errors.append(f"Invalid JSON structure: {str(e)}")
        except Exception as e:
            errors.append(f"File validation error: {str(e)}")
    
    return errors

# Router
router = APIRouter(prefix="/api/datapuur", tags=["datapuur"])

# Create uploads directory if it doesn't exist
UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Create data directory if it doesn't exist
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Log directory paths for debugging
logger.info(f"Upload directory: {UPLOAD_DIR}")
logger.info(f"Data directory: {DATA_DIR}")

# Functions to interact with the database
def get_uploaded_file(db, file_id):
    """Get uploaded file from database"""
    return db.query(UploadedFile).filter(UploadedFile.id == file_id).first()

def get_all_uploaded_files(db):
    """Get all uploaded files from database"""
    return db.query(UploadedFile).all()

def save_uploaded_file(db, file_id, file_data):
    """Save uploaded file to database"""
    # Check if file already exists
    existing_file = get_uploaded_file(db, file_id)
    
    if existing_file:
        # Update existing file
        for key, value in file_data.items():
            if key == 'schema' and value:
                setattr(existing_file, key, json.dumps(value))
            else:
                setattr(existing_file, key, value)
    else:
        # Create new file
        schema_json = json.dumps(file_data.get('schema')) if file_data.get('schema') else None
        new_file = UploadedFile(
            id=file_id,
            filename=file_data['filename'],
            path=file_data['path'],
            type=file_data['type'],
            uploaded_by=file_data['uploaded_by'],
            uploaded_at=datetime.now(timezone.utc),
            chunk_size=file_data.get('chunk_size', 1000),
            schema=schema_json,
            dataset=file_data.get('dataset')  # Include the dataset field
        )
        db.add(new_file)
    
    db.commit()
    return True

def get_ingestion_job(db, job_id):
    """Get ingestion job from database"""
    return db.query(IngestionJob).filter(IngestionJob.id == job_id).first()

def get_all_ingestion_jobs(db):
    """Get all ingestion jobs from database"""
    return db.query(IngestionJob).all()

def save_ingestion_job(db, job_id, job_data):
    """Save ingestion job to database"""
    # Check if job already exists
    existing_job = get_ingestion_job(db, job_id)
    
    if existing_job:
        # Update existing job
        for key, value in job_data.items():
            if key == 'config' and value:
                setattr(existing_job, key, json.dumps(value))
            elif key == 'start_time' and value:
                # Ensure timestamp has timezone information
                dt = datetime.fromisoformat(value)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                setattr(existing_job, key, dt)
            elif key == 'end_time' and value:
                # Ensure timestamp has timezone information
                dt = datetime.fromisoformat(value)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                setattr(existing_job, key, dt)
            else:
                setattr(existing_job, key, value)
    else:
        # Create new job
        config_json = json.dumps(job_data.get('config')) if job_data.get('config') else None
        new_job = IngestionJob(
            id=job_id,
            name=job_data['name'],
            type=job_data['type'],
            status=job_data['status'],
            progress=job_data.get('progress', 0),
            start_time=datetime.fromisoformat(job_data['start_time']).replace(tzinfo=timezone.utc) if datetime.fromisoformat(job_data['start_time']).tzinfo is None else datetime.fromisoformat(job_data['start_time']),
            end_time=datetime.fromisoformat(job_data['end_time']).replace(tzinfo=timezone.utc) if job_data.get('end_time') and datetime.fromisoformat(job_data['end_time']).tzinfo is None else (datetime.fromisoformat(job_data['end_time']) if job_data.get('end_time') else None),
            details=job_data.get('details'),
            error=job_data.get('error'),
            config=config_json
        )
        db.add(new_job)
    
    db.commit()
    return True

def delete_dataset(db, dataset_id):
    """Delete a dataset and its associated data"""
    # Find the dataset in the ingestion jobs
    dataset = db.query(IngestionJob).filter(IngestionJob.id == dataset_id).first()
    
    if not dataset:
        return False, "Dataset not found"
    
    try:
        # Check if this is a file-based dataset and extract the file_id
        uploaded_file = None
        if dataset.type == "file" and dataset.config:
            try:
                config_data = json.loads(dataset.config)
                if "file_id" in config_data:
                    file_id = config_data["file_id"]
                    # Find the associated uploaded file
                    uploaded_file = db.query(UploadedFile).filter(UploadedFile.id == file_id).first()
            except json.JSONDecodeError:
                logger.warning(f"Could not parse config JSON for dataset {dataset_id}")
        
        # Delete the dataset record
        db.delete(dataset)
        
        # Delete any processed data files
        if 'file_id' in locals() and file_id:
            data_path = DATA_DIR / f"{file_id}.parquet"
            if data_path.exists():
                data_path.unlink()
                logger.info(f"Deleted parquet file for dataset {dataset_id} (file_id: {file_id})")
            
            # Delete associated profile records using file_id
            from .profiler.models import ProfileResult
            profile_results = db.query(ProfileResult).filter(ProfileResult.file_id == file_id).all()
            logger.info(f"Found {len(profile_results)} profile results for file_id {file_id}")
        else:
            # Fallback to using dataset_id for backward compatibility
            data_path = DATA_DIR / f"{dataset_id}.parquet"
            if data_path.exists():
                data_path.unlink()
                logger.info(f"Deleted parquet file for dataset {dataset_id} (using dataset_id)")
            
            # Delete associated profile records using dataset_id for backward compatibility
            from .profiler.models import ProfileResult
            profile_results = db.query(ProfileResult).filter(ProfileResult.file_id == dataset_id).all()
            logger.info(f"Found {len(profile_results)} profile results for dataset_id {dataset_id}")
        
        for profile in profile_results:
            db.delete(profile)
            logger.info(f"Deleted associated profile {profile.id} for dataset {dataset_id}")
        
        # Delete the uploaded file record and the actual file from disk if found
        if uploaded_file:
            # Delete the physical file from disk
            if uploaded_file.path and os.path.exists(uploaded_file.path):
                try:
                    os.remove(uploaded_file.path)
                    logger.info(f"Deleted physical file {uploaded_file.path} for dataset {dataset_id}")
                except OSError as e:
                    logger.error(f"Error deleting physical file {uploaded_file.path}: {str(e)}")
            
            # Delete the uploaded file record
            db.delete(uploaded_file)
            logger.info(f"Deleted uploaded file record {uploaded_file.id} for dataset {dataset_id}")
        
        # Commit the changes
        db.commit()
        
        return True, "Dataset, associated profiles, and uploaded files deleted successfully"
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting dataset: {str(e)}")
        return False, f"Error deleting dataset: {str(e)}"

# Models for API requests
class DatabaseConfig(BaseModel):
    type: str
    config: Dict[str, Any]
    chunk_size: int = 1000
    connection_name: str

class FileIngestionRequest(BaseModel):
    file_id: str
    file_name: str
    chunk_size: int = 1000

class JobStatus(BaseModel):
    id: str
    name: str
    type: str
    status: str
    progress: int
    start_time: str
    end_time: Optional[str] = None
    details: str
    error: Optional[str] = None
    config: Optional[Dict[str, Any]] = None

# New models for ingestion history
class IngestionHistoryItem(BaseModel):
    id: str
    filename: str
    type: str
    size: int
    uploaded_at: str
    uploaded_by: str
    preview_url: Optional[str] = None
    download_url: Optional[str] = None
    status: str
    source_type: str
    database_info: Optional[Dict[str, str]] = None

class IngestionHistoryResponse(BaseModel):
    items: List[IngestionHistoryItem]
    total: int
    page: int
    limit: int

class SchemaResponse(BaseModel):
    fields: List[Dict[str, Any]]
    sample_values: Optional[List[Any]] = None

class PreviewResponse(BaseModel):
    data: Any
    headers: Optional[List[str]] = None
    filename: str
    type: str

class StatisticsResponse(BaseModel):
    row_count: int
    column_count: int
    null_percentage: float
    memory_usage: str
    processing_time: str
    data_density: Optional[float] = None
    completion_rate: Optional[float] = None
    error_rate: Optional[float] = None

# Helper functions
def detect_csv_schema(file_path, chunk_size=1000):
    """Detect schema from a CSV file"""
    schema = {"name": Path(file_path).stem, "fields": []}
    field_types = {}
    sample_values = {}
    
    with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
        # Read header
        reader = csv.reader(csvfile)
        headers = next(reader)
        
        # Initialize field types dictionary
        for header in headers:
            field_types[header] = set()
            sample_values[header] = None
        
        # Process rows in chunks
        row_count = 0
        for row in reader:
            if row_count >= chunk_size:
                break
                
            for i, value in enumerate(row):
                if i < len(headers):
                    header = headers[i]
                    
                    # Store sample value if not already set
                    if sample_values[header] is None and value:
                        sample_values[header] = value
                    
                    # Detect type
                    if not value:
                        continue
                    
                    # Try to convert to different types
                    try:
                        int(value)
                        field_types[header].add("integer")
                        continue
                    except ValueError:
                        pass
                    
                    try:
                        float(value)
                        field_types[header].add("float")
                        continue
                    except ValueError:
                        pass
                    
                    if value.lower() in ('true', 'false'):
                        field_types[header].add("boolean")
                        continue
                    
                    # Try date formats
                    try:
                        datetime.strptime(value, '%Y-%m-%d')
                        field_types[header].add("date")
                        continue
                    except ValueError:
                        pass
                    
                    try:
                        datetime.strptime(value, '%Y-%m-%dT%H:%M:%S')
                        field_types[header].add("datetime")
                        continue
                    except ValueError:
                        pass
                    
                    # Default to string
                    field_types[header].add("string")
            
            row_count += 1
    
    # Determine final type for each field
    for header in headers:
        types = field_types[header]
        if "string" in types:
            field_type = "string"
        elif "datetime" in types:
            field_type = "datetime"
        elif "date" in types:
            field_type = "date"
        elif "boolean" in types:
            field_type = "boolean"
        elif "float" in types:
            field_type = "float"
        elif "integer" in types:
            field_type = "integer"
        else:
            field_type = "string"  # Default
        
        schema["fields"].append({
            "name": header,
            "type": field_type,
            "nullable": True,  # Assume nullable by default
            "sample": sample_values[header]
        })
    
    return schema

def detect_json_schema(file_path, chunk_size=1000):
    """Detect schema from a JSON file"""
    with open(file_path, 'r', encoding='utf-8') as jsonfile:
        try:
            data = json.load(jsonfile)
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON file")
    
    schema = {"name": Path(file_path).stem, "fields": []}
    
    # Handle array of objects
    if isinstance(data, list):
        if not data:
            return schema
        
        # Limit to chunk_size
        data = data[:chunk_size]
        
        # Use the first object to initialize field tracking
        first_obj = data[0]
        if not isinstance(first_obj, dict):
            schema["fields"].append({
                "name": "value",
                "type": get_json_type(first_obj),
                "nullable": False,
                "sample": first_obj
            })
            return schema
        
        field_types = {key: set() for key in first_obj.keys()}
        sample_values = {key: None for key in first_obj.keys()}
        
        # Process each object
        for obj in data:
            if not isinstance(obj, dict):
                continue
                
            for key, value in obj.items():
                if key in field_types:
                    field_types[key].add(get_json_type(value))
                    
                    # Store sample value if not already set
                    if sample_values[key] is None and value is not None:
                        sample_values[key] = value
        
        # Create schema fields
        for key in field_types:
            types = field_types[key]
            
            # Determine the most specific type
            if "object" in types:
                field_type = "object"
            elif "array" in types:
                field_type = "array"
            elif "string" in types:
                field_type = "string"
            elif "boolean" in types:
                field_type = "boolean"
            elif "float" in types:
                field_type = "float"
            elif "integer" in types:
                field_type = "integer"
            elif "null" in types:
                field_type = "null"
            else:
                field_type = "string"  # Default
            
            schema["fields"].append({
                "name": key,
                "type": field_type,
                "nullable": "null" in types,
                "sample": sample_values[key]
            })
    
    # Handle single object
    elif isinstance(data, dict):
        for key, value in data.items():
            schema["fields"].append({
                "name": key,
                "type": get_json_type(value),
                "nullable": value is None,
                "sample": value
            })
    
    return schema

def get_json_type(value):
    """Determine the JSON type of a value"""
    if value is None:
        return "null"
    elif isinstance(value, bool):
        return "boolean"
    elif isinstance(value, int):
        return "integer"
    elif isinstance(value, float):
        return "float"
    elif isinstance(value, str):
        # Check if it might be a date
        try:
            datetime.strptime(value, '%Y-%m-%d')
            return "date"
        except ValueError:
            pass
        
        try:
            datetime.strptime(value, '%Y-%m-%dT%H:%M:%S')
            return "datetime"
        except ValueError:
            pass
        
        return "string"
    elif isinstance(value, list):
        return "array"
    elif isinstance(value, dict):
        return "object"
    else:
        return "string"  # Default

def get_db_schema(db_type, config, chunk_size=1000):
    """Get schema from a database table"""
    connection_string = create_connection_string(db_type, config)
    
    try:
        engine = create_engine(connection_string)
        inspector = inspect(engine)
        
        # Check if table exists
        if config["table"] not in inspector.get_table_names():
            raise ValueError(f"Table '{config['table']}' not found in database")
        
        # Get table columns
        columns = inspector.get_columns(config["table"])
        column_names = [col["name"] for col in columns]
        
        # Get sample data
        with engine.connect() as connection:
            query = sqlalchemy.text(f"SELECT * FROM {config['table']} LIMIT 1")
            result = connection.execute(query).fetchone()
            
            # Manual conversion using column names - most reliable method
            sample_data = {}
            if result:
                for i, value in enumerate(result):
                    if i < len(column_names):
                        col_name = column_names[i]
                        # Convert datetime objects to strings for JSON serialization
                        if isinstance(value, (datetime, date)):
                            sample_data[col_name] = value.isoformat()
                        else:
                            sample_data[col_name] = value
        
        schema = {
            "name": config["table"],
            "fields": []
        }
        
        for column in columns:
            col_name = column["name"]
            col_type = str(column["type"]).lower()
            
            # Map SQL types to our schema types
            if "int" in col_type:
                field_type = "integer"
            elif "float" in col_type or "double" in col_type or "decimal" in col_type:
                field_type = "float"
            elif "bool" in col_type:
                field_type = "boolean"
            elif "date" in col_type and "time" in col_type:
                field_type = "datetime"
            elif "date" in col_type:
                field_type = "date"
            elif "json" in col_type:
                field_type = "object"
            else:
                field_type = "string"
            
            # Get sample value, ensuring it's JSON serializable
            sample_value = sample_data.get(col_name) if col_name in sample_data else None
            
            schema["fields"].append({
                "name": col_name,
                "type": field_type,
                "nullable": not column.get("nullable", True),
                "sample": sample_value
            })
        
        return schema
    
    except Exception as e:
        raise ValueError(f"Error connecting to database: {str(e)}")

def create_connection_string(db_type, config):
    """Create a database connection string"""
    if db_type == "mysql":
        return f"mysql+pymysql://{config['username']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
    elif db_type == "postgresql":
        return f"postgresql://{config['username']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
    elif db_type == "mssql":
        return f"mssql+pyodbc://{config['username']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}?driver=ODBC+Driver+17+for+SQL+Server"
    else:
        raise ValueError(f"Unsupported database type: {db_type}")

# Database Connection Endpoints

@router.get("/db-connections", status_code=status.HTTP_200_OK)
async def get_database_connections(
    current_user: User = Depends(has_permission("datapuur:read")),
    db: Session = Depends(get_db)
):
    """Get all saved database connections for the current user"""
    try:
        connections = get_db_connections(db, current_user.username)
        
        # Convert connections to dict and parse config JSON
        result = []
        for conn in connections:
            conn_dict = {
                "id": conn.id,
                "name": conn.name,
                "type": conn.type,
                "config": json.loads(conn.config),
                "username": conn.username,
                "created_at": conn.created_at.isoformat() if conn.created_at else None,
                "updated_at": conn.updated_at.isoformat() if conn.updated_at else None
            }
            # Mask password for security
            if "password" in conn_dict["config"]:
                conn_dict["config"]["password"] = "********"
            result.append(conn_dict)
        
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving database connections: {str(e)}"
        )

@router.post("/db-connections", status_code=status.HTTP_201_CREATED)
async def create_database_connection(
    connection: dict,
    current_user: User = Depends(has_permission("datapuur:write")),
    db: Session = Depends(get_db)
):
    """Save a new database connection"""
    try:
        # Validate required fields
        required_fields = ["name", "type", "config"]
        for field in required_fields:
            if field not in connection:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing required field: {field}"
                )
        
        # Add username to connection data
        connection["username"] = current_user.username
        
        # Save connection
        conn = save_db_connection(db, connection)
        
        # Log activity
        log_activity(
            db=db,
            username=current_user.username,
            action="Database connection saved",
            details=f"Saved connection: {connection['name']} ({connection['type']})"
        )
        
        return {
            "id": conn.id,
            "name": conn.name,
            "message": "Database connection saved successfully"
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving database connection: {str(e)}"
        )

@router.delete("/db-connections/{connection_id}", status_code=status.HTTP_200_OK)
async def delete_database_connection(
    connection_id: str,
    current_user: User = Depends(has_permission("datapuur:write")),
    db: Session = Depends(get_db)
):
    """Delete a database connection"""
    try:
        # Check if connection exists and belongs to user
        connection = get_db_connection(db, connection_id)
        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Database connection not found"
            )
        
        if connection.username != current_user.username and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to delete this connection"
            )
        
        # Delete connection
        delete_db_connection(db, connection_id)
        
        # Log activity
        log_activity(
            db=db,
            username=current_user.username,
            action="Database connection deleted",
            details=f"Deleted connection: {connection.name} ({connection.type})"
        )
        
        return {"message": "Database connection deleted successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting database connection: {str(e)}"
        )

# Process file ingestion with database
def process_file_ingestion_with_db(job_id, file_id, chunk_size, db):
    """Process file ingestion in a background thread with database access"""
    try:
        # Get a new database session
        db_session = SessionLocal()
        
        # Update job status
        job = get_ingestion_job(db_session, job_id)
        job.status = "running"
        job.progress = 0
        db_session.commit()
        
        # Get file info
        file_info = get_uploaded_file(db_session, file_id)
        if not file_info:
            error_data = create_error_response(
                error_code="FILE_NOT_FOUND",
                message="File not found",
                details=f"File with ID {file_id} not found in the database",
                suggestion="Check that the file was properly uploaded before ingestion"
            )
            logger.error(f"File with ID {file_id} not found")
            job.status = "failed"
            job.error = json.dumps(error_data)
            job.end_time = datetime.now(timezone.utc)
            db_session.commit()
            return error_data
        
        file_path = file_info.path
        file_type = file_info.type
        
        # Validate file before processing
        validation_errors = validate_file_before_processing(file_path, file_type)
        if validation_errors:
            error_details = "\n- " + "\n- ".join(validation_errors)
            error_data = create_error_response(
                error_code="FILE_VALIDATION_ERROR",
                message="File validation failed",
                details=f"The file failed validation checks: {error_details}",
                suggestion="Please correct the file format and try again"
            )
            logger.error(f"File validation failed for {file_path}: {error_details}")
            job.status = "failed"
            job.error = json.dumps(error_data)
            job.end_time = datetime.now(timezone.utc)
            db_session.commit()
            return error_data
        
        # Create output file path using file_id for better traceability
        output_file = DATA_DIR / f"{file_id}.parquet"
        
        # Helper function to check if job has been cancelled
        def check_job_cancelled():
            # Refresh job from database to get latest status
            nonlocal job
            db_session.refresh(job)
            
            # Check if job has been marked as cancelled in the database
            if job.status == "cancelled":
                logger.info(f"Job {job_id} has been cancelled in the database, stopping processing")
                return True
                
            # Check for cancellation marker file
            cancel_marker_path = DATA_DIR / f"cancel_{job_id}"
            if cancel_marker_path.exists():
                logger.info(f"Cancellation marker found for job {job_id}, stopping processing")
                # Update job status to cancelled since we found a marker
                job.status = "cancelled"
                job.end_time = datetime.now()
                job.details = f"{job.details} (Cancelled by user)"
                db_session.commit()
                return True
                
            return False
        
        # Process file based on type
        if file_type == "csv":
            try:
                # Optimize for large files by using a more efficient approach
                # First, determine the file size to estimate progress better
                file_size = os.path.getsize(file_path)
                
                # For very large files (>100MB), use a more optimized approach
                if file_size > 100 * 1024 * 1024:  # 100MB
                    # Update job status
                    job.details = f"Processing large file ({file_size / (1024 * 1024):.2f} MB) with optimized engine"
                    db_session.commit()
                    
                    # Check for cancellation before starting large file processing
                    if check_job_cancelled():
                        logger.info(f"Job {job_id} was cancelled before starting large file processing, stopping")
                        return
                        
                    # Use pyarrow for better performance with large files
                    import pyarrow as pa
                    import pyarrow.csv as csv
                    import pyarrow.parquet as pq
                    
                    # Read the CSV file in a memory-efficient way
                    read_options = csv.ReadOptions(block_size=10 * 1024 * 1024)  # 10MB chunks
                    convert_options = csv.ConvertOptions(
                        strings_can_be_null=True,
                        timestamp_parsers=["%Y-%m-%d", "%Y/%m/%d", "%m-%d-%Y", "%m/%d/%Y"]  # Common date formats
                    )
                    
                    # Create a CSV reader that processes the file in chunks
                    with csv.open_csv(file_path, read_options=read_options, convert_options=convert_options) as reader:
                        # Read and process the file in batches
                        batch_number = 0
                        table_batches = []
                        
                        for batch in reader:
                            batch_number += 1
                            # Convert RecordBatch to Table before appending
                            if isinstance(batch, pa.RecordBatch):
                                batch = pa.Table.from_batches([batch])
                            table_batches.append(batch)
                            
                            # Update progress every few batches
                            if batch_number % 5 == 0:
                                # Check for cancellation during batch processing
                                if check_job_cancelled():
                                    logger.info(f"Job {job_id} was cancelled during batch processing, stopping")
                                    return
                                    
                                # Estimate progress based on batches processed
                                progress = int((batch_number * 10 * 1024 * 1024 / file_size) * 100)
                                job.progress = progress
                                job.details = f"Processing batch {batch_number} ({progress}% complete)"
                                db_session.commit()
                        
                        # Combine all batches into a single table
                        if table_batches:
                            table = pa.concat_tables(table_batches)
                            # Write to parquet with compression
                            pq.write_table(table, output_file, compression='snappy')
                        else:
                            raise ValueError("No data was read from the CSV file")
                        
                        # Final update
                        job.progress = 100
                        job.details = f"Finalizing file processing..."
                        db_session.commit()
                        
                        # Check for cancellation after finalizing
                        if check_job_cancelled():
                            logger.info(f"Job {job_id} was cancelled after finalizing, stopping")
                            return
                else:
                    # For smaller files, use pandas with optimized settings
                    # Read CSV in chunks with all columns as string type initially
                    chunk_iterator = pd.read_csv(
                        file_path, 
                        chunksize=chunk_size,
                        dtype=str,  # Read all columns as strings initially to prevent type conversion errors
                        keep_default_na=False,  # Don't convert empty strings to NaN
                        low_memory=True,  # Use less memory
                        engine='c'  # Use the faster C engine
                    )
                    
                    # Count lines more efficiently for large files
                    total_rows = 0
                    with open(file_path, 'r') as f:
                        # Count lines in chunks to avoid loading the entire file
                        chunk_size = 1024 * 1024  # 1MB chunks
                        while True:
                            chunk = f.read(chunk_size)
                            if not chunk:
                                break
                            total_rows += chunk.count('\n')
                    
                    # Subtract 1 for header if file has content
                    if total_rows > 0:
                        total_rows -= 1
                    
                    processed_rows = 0
                    
                    # Process first chunk
                    first_chunk = next(chunk_iterator)
                    
                    # Try to convert numeric columns safely
                    for col in first_chunk.columns:
                        # Only attempt numeric conversion on specific columns we know should be numeric
                        # This prevents errors when trying to convert IDs or other string values to numbers
                        if col in ['MonthlyCharges', 'TotalCharges']:
                            first_chunk[col] = pd.to_numeric(first_chunk[col], errors='coerce')
                    
                    # Write directly to parquet with compression
                    first_chunk.to_parquet(output_file, index=False, compression='snappy')
                    processed_rows += len(first_chunk)
                    
                    # Update progress
                    job.progress = int((processed_rows / total_rows) * 100)
                    db_session.commit()
                    
                    # Process remaining chunks more efficiently
                    for chunk in chunk_iterator:
                        # Check for cancellation before processing each chunk
                        if check_job_cancelled():
                            logger.info(f"Job {job_id} was cancelled during processing, stopping")
                            return
                                
                        # Try to convert numeric columns safely
                        for col in chunk.columns:
                            if col in ['MonthlyCharges', 'TotalCharges']:
                                chunk[col] = pd.to_numeric(chunk[col], errors='coerce')
                        
                        # Append to parquet file using pyarrow instead of unsupported append parameter
                        import pyarrow as pa
                        import pyarrow.parquet as pq
                        
                        # Check if this is the first append after initial write
                        if processed_rows == len(first_chunk):
                            # Read the existing parquet file
                            existing_table = pq.read_table(output_file)
                            # Convert chunk to pyarrow table
                            chunk_table = pa.Table.from_pandas(chunk)
                            # Concatenate tables
                            combined_table = pa.concat_tables([existing_table, chunk_table])
                            # Write back to the file
                            pq.write_table(combined_table, output_file, compression='snappy')
                        else:
                            # For subsequent appends, read the entire file again
                            try:
                                existing_table = pq.read_table(output_file)
                                chunk_table = pa.Table.from_pandas(chunk)
                                combined_table = pa.concat_tables([existing_table, chunk_table])
                                pq.write_table(combined_table, output_file, compression='snappy')
                            except Exception as e:
                                logger.error(f"Error appending to parquet file: {str(e)}")
                                raise
                        
                        processed_rows += len(chunk)
                        
                        # Update progress
                        job.progress = int((processed_rows / total_rows) * 100)
                        job.details = f"Processed {processed_rows} of {total_rows} rows ({job.progress}%)"
                        db_session.commit()
                        
                        # Check for cancellation after updating progress
                        if check_job_cancelled():
                            logger.info(f"Job {job_id} was cancelled after updating progress, stopping")
                            return
            except Exception as e:
                logger.error(f"Error processing CSV file: {str(e)}")
                raise ValueError(f"Error processing CSV file: {str(e)}")
        
        elif file_type == "json":
            try:
                # Check if job has been cancelled before starting
                if check_job_cancelled():
                    logger.info(f"Job {job_id} has been cancelled before starting JSON processing, stopping")
                    return
                    
                # Get file size to determine processing approach
                file_size = os.path.getsize(file_path)
                
                # For very large files (>50MB), use a streaming approach
                if file_size > 50 * 1024 * 1024:  # 50MB
                    # Update job status
                    job.details = f"Processing large JSON file ({file_size / (1024 * 1024):.2f} MB) with optimized engine"
                    db_session.commit()
                    
                    # Use ijson for streaming JSON parsing
                    import ijson
                    
                    # Initialize an empty DataFrame
                    df = None
                    processed_items = 0
                    total_items_estimate = max(1, file_size // 1000)  # Rough estimate based on file size
                    
                    # Function to efficiently flatten JSON with iteration instead of recursion
                    def flatten_json_iterative(nested_json, prefix=''):
                        items = []
                        if isinstance(nested_json, dict):
                            items = nested_json.items()
                        
                        flattened = {}
                        for key, value in items:
                            new_key = f"{prefix}{key}"
                            if isinstance(value, dict):
                                flattened.update(flatten_json_iterative(value, f"{new_key}_"))
                            elif isinstance(value, list):
                                if all(not isinstance(item, dict) for item in value):
                                    flattened[new_key] = str(value)
                                else:
                                    for i, item in enumerate(value):
                                        if isinstance(item, dict):
                                            flattened.update(flatten_json_iterative(item, f"{new_key}_{i}_"))
                                        else:
                                            flattened[f"{new_key}_{i}"] = item
                            else:
                                flattened[new_key] = value
                        return flattened
                    
                    # Process the file in a streaming manner
                    with open(file_path, 'rb') as f:
                        # Check if the JSON is an array at the root
                        parser = ijson.parse(f)
                        prefix, event, value = next(parser)
                        f.seek(0)  # Reset file position
                        
                        if prefix == '' and event == 'start_array':
                            # It's an array of objects, process each item
                            batch_size = 1000
                            batch = []
                            
                            for item in ijson.items(f, 'item'):
                                if isinstance(item, dict):
                                    batch.append(flatten_json_iterative(item))
                                else:
                                    batch.append({"value": item})
                                
                                processed_items += 1
                                
                                # Check for cancellation periodically
                                if processed_items % 1000 == 0 and check_job_cancelled():
                                    logger.info(f"Job {job_id} was cancelled during JSON processing, stopping")
                                    return
                                
                                # Process in batches for better performance
                                if len(batch) >= batch_size:
                                    # Check for cancellation before processing batch
                                    if check_job_cancelled():
                                        logger.info(f"Job {job_id} was cancelled before processing JSON batch, stopping")
                                        return
                                    
                                    batch_df = pd.DataFrame(batch)
                                    
                                    # Convert numeric columns
                                    for col in batch_df.columns:
                                        if batch_df[col].dtype == object:
                                            try:
                                                numeric_values = pd.to_numeric(batch_df[col], errors='coerce')
                                                if numeric_values.notna().sum() / len(numeric_values) > 0.8:
                                                    batch_df[col] = numeric_values
                                            except:
                                                pass
                                    
                                    # Save or append to parquet
                                    if df is None:
                                        batch_df.to_parquet(output_file, index=False, compression='snappy')
                                        df = batch_df  # Just to mark that we've started writing
                                    else:
                                        # Use pyarrow for efficient appending
                                        import pyarrow as pa
                                        import pyarrow.parquet as pq
                                        
                                        existing_table = pq.read_table(output_file)
                                        batch_table = pa.Table.from_pandas(batch_df)
                                        combined_table = pa.concat_tables([existing_table, batch_table])
                                        pq.write_table(combined_table, output_file, compression='snappy')
                                    
                                    # Update progress
                                    progress = int((processed_items / total_items_estimate) * 100)
                                    job.progress = progress
                                    job.details = f"Processed {processed_items} items ({progress}% estimated)"
                                    db_session.commit()
                                    
                                    # Clear batch
                                    batch = []
                            
                            # Process any remaining items
                            if batch:
                                # Check for cancellation before processing remaining batch
                                if check_job_cancelled():
                                    logger.info(f"Job {job_id} was cancelled before processing remaining JSON batch, stopping")
                                    return
                                        
                                batch_df = pd.DataFrame(batch)
                                
                                # Convert numeric columns
                                for col in batch_df.columns:
                                    if batch_df[col].dtype == object:  # Only attempt conversion on object (string) columns
                                        # Check if column contains numeric data by trying conversion
                                        try:
                                            # If more than 80% of non-null values can be converted to numeric, treat as numeric
                                            non_null_values = batch_df[col].dropna()
                                            if len(non_null_values) > 0:
                                                numeric_count = sum(pd.to_numeric(non_null_values, errors='coerce').notna())
                                                if numeric_count / len(non_null_values) > 0.8:
                                                    batch_df.loc[:, col] = pd.to_numeric(batch_df[col], errors='coerce')
                                        except:
                                            pass
                                
                                # Save or append to parquet
                                if df is None:
                                    batch_df.to_parquet(output_file, index=False, compression='snappy')
                                else:
                                    import pyarrow as pa
                                    import pyarrow.parquet as pq
                                    
                                    existing_table = pq.read_table(output_file)
                                    batch_table = pa.Table.from_pandas(batch_df)
                                    combined_table = pa.concat_tables([existing_table, batch_table])
                                    pq.write_table(combined_table, output_file, compression='snappy')
                        else:
                            # It's a single object, process it directly
                            # Check for cancellation before processing single object
                            if check_job_cancelled():
                                logger.info(f"Job {job_id} was cancelled before processing single JSON object, stopping")
                                return
                                
                            f.seek(0)  # Reset file position
                            data = json.load(f)
                            
                            if isinstance(data, dict):
                                flattened_data = flatten_json_iterative(data)
                                df = pd.DataFrame([flattened_data])
                            else:
                                df = pd.DataFrame([{"value": data}])
                            
                            # Save to parquet
                            df.to_parquet(output_file, index=False, compression='snappy')
                    
                    # Update progress
                    # Check for cancellation before finalizing
                    if check_job_cancelled():
                        logger.info(f"Job {job_id} was cancelled before finalizing JSON processing, stopping")
                        return
                        
                    job.progress = 100
                    job.details = f"Finalizing JSON processing..."
                    db_session.commit()
                else:
                    # For smaller files, use the standard approach but with optimizations
                    # Check for cancellation before processing small file
                    if check_job_cancelled():
                        logger.info(f"Job {job_id} was cancelled before processing small JSON file, stopping")
                        return
                        
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Function to flatten nested JSON more efficiently
                    def flatten_json(nested_json, prefix=''):
                        flattened = {}
                        for key, value in nested_json.items():
                            if isinstance(value, dict):
                                # Recursively flatten nested dictionaries
                                flattened.update(flatten_json(value, f"{prefix}{key}_"))
                            elif isinstance(value, list):
                                # Handle lists by converting them to strings if they contain simple types
                                # or by flattening if they contain dictionaries
                                if all(not isinstance(item, dict) for item in value):
                                    # For lists of simple types, convert to string
                                    flattened[f"{prefix}{key}"] = str(value)
                                else:
                                    # For lists of dictionaries, flatten each item
                                    for i, item in enumerate(value):
                                        if isinstance(item, dict):
                                            flattened.update(flatten_json(item, f"{prefix}{key}_{i}_"))
                                        else:
                                            flattened[f"{prefix}{key}_{i}"] = item
                            else:
                                # For simple types, just add them with the prefix
                                flattened[f"{prefix}{key}"] = value
                        return flattened
                    
                    # Convert to DataFrame - ensure data is always a list
                    if isinstance(data, list):
                        # Handle empty list case
                        if len(data) == 0:
                            # Create empty DataFrame with default columns
                            df = pd.DataFrame(columns=['data'])
                        else:
                            # Flatten each item in the list if it's a dictionary
                            flattened_data = []
                            for item in data:
                                if isinstance(item, dict):
                                    flattened_data.append(flatten_json(item))
                                else:
                                    flattened_data.append({"value": item})
                            
                            # Convert list of flattened dictionaries to DataFrame
                            df = pd.DataFrame(flattened_data)
                            
                            # Ensure all columns have consistent types by inferring types
                            for col in df.columns:
                                # Try to convert numeric columns
                                if df[col].dtype == object:  # Only attempt conversion on object (string) columns
                                    # Check if column contains numeric data by trying conversion
                                    try:
                                        # If more than 80% of non-null values can be converted to numeric, treat as numeric
                                        non_null_values = df[col].dropna()
                                        if len(non_null_values) > 0:
                                            numeric_count = sum(pd.to_numeric(non_null_values, errors='coerce').notna())
                                            if numeric_count / len(non_null_values) > 0.8:
                                                df.loc[:, col] = pd.to_numeric(df[col], errors='coerce')
                                    except:
                                        pass
                                
                                # Check if column contains boolean data
                                # Look for columns with values that match boolean patterns
                                if all(str(val).lower() in ['true', 'false', '1', '0', 'yes', 'no', 'y', 'n', '', 'nan', 'none', 'null'] 
                                      for val in df[col].dropna().astype(str)):
                                    # Convert to boolean using .loc to avoid SettingWithCopyWarning
                                    df.loc[:, col] = df[col].map(
                                        lambda x: True if pd.notna(x) and str(x).lower() in ['true', '1', 'yes', 'y'] 
                                        else False if pd.notna(x) and str(x).lower() in ['false', '0', 'no', 'n']
                                        else None
                                    )
                    else:
                        # If data is not a list (e.g., single object), flatten it and convert to a single-row DataFrame
                        flattened_data = flatten_json(data) if isinstance(data, dict) else {"value": data}
                        df = pd.DataFrame([flattened_data])
                    
                    # Save to parquet with compression for better performance
                    df.to_parquet(output_file, index=False, compression='snappy')
                    
                    # Update progress in a single step without sleep
                    job.progress = 100
                    job.details = "JSON processing completed"
                    db_session.commit()
            except Exception as e:
                logger.error(f"Error processing JSON file: {str(e)}")
                raise ValueError(f"Error processing JSON file: {str(e)}")
        
        # Mark job as completed
        # Final check for cancellation before marking as completed
        if check_job_cancelled():
            logger.info(f"Job {job_id} was cancelled before marking as completed, stopping")
            return
            
        job.status = "completed"
        job.progress = 100
        job.end_time = datetime.now()
        
        db_session.commit()
        
        logger.info(f"File ingestion completed for job {job_id}")
    
    except pd.errors.ParserError as e:
        # Handle CSV parsing errors
        logger.error(f"CSV parsing error in job {job_id}: {str(e)}\nTraceback: {traceback.format_exc()}")
        error_data = create_error_response(
            error_code="CSV_PARSE_ERROR",
            message="CSV parsing error",
            details=f"Could not parse the CSV file: {str(e)}",
            suggestion="Check that your CSV file is properly formatted with consistent delimiters and valid data."
        )
        try:
            job = get_ingestion_job(db_session, job_id)
            job.status = "failed"
            job.error = json.dumps(error_data)
            job.end_time = datetime.now(timezone.utc)
            db_session.commit()
        except Exception as commit_error:
            logger.error(f"Failed to update job status: {str(commit_error)}")
    
    except json.JSONDecodeError as e:
        # Handle JSON parsing errors
        logger.error(f"JSON parsing error in job {job_id}: {str(e)}\nTraceback: {traceback.format_exc()}")
        error_data = create_error_response(
            error_code="JSON_PARSE_ERROR",
            message="JSON parsing error",
            details=f"Could not parse the JSON file: {str(e)}",
            suggestion="Check that your JSON file contains valid JSON data in the expected format."
        )
        try:
            job = get_ingestion_job(db_session, job_id)
            job.status = "failed"
            job.error = json.dumps(error_data)
            job.end_time = datetime.now(timezone.utc)
            db_session.commit()
        except Exception as commit_error:
            logger.error(f"Failed to update job status: {str(commit_error)}")
    
    except MemoryError as e:
        # Handle memory limitation errors
        logger.error(f"Memory error in job {job_id}: {str(e)}\nTraceback: {traceback.format_exc()}")
        error_data = create_error_response(
            error_code="MEMORY_ERROR",
            message="Memory limit exceeded",
            details="The system ran out of memory while processing this file.",
            suggestion="Try reducing the chunk size or splitting the file into smaller parts."
        )
        try:
            job = get_ingestion_job(db_session, job_id)
            job.status = "failed"
            job.error = json.dumps(error_data)
            job.end_time = datetime.now(timezone.utc)
            db_session.commit()
        except Exception as commit_error:
            logger.error(f"Failed to update job status: {str(commit_error)}")
    
    except Exception as e:
        # Handle other general errors with more context
        error_msg = str(e)
        logger.error(f"Error processing file ingestion for job {job_id}: {error_msg}\nTraceback: {traceback.format_exc()}")
        
        # Categorize common errors by message patterns
        if "duplicate key" in error_msg.lower():
            error_data = create_error_response(
                error_code="DUPLICATE_KEY_ERROR",
                message="Duplicate data error",
                details=f"The data contains duplicate keys: {error_msg}",
                suggestion="Ensure your data has unique identifiers for each row."
            )
        elif any(phrase in error_msg.lower() for phrase in ["type conversion", "cannot convert", "invalid literal"]):
            error_data = create_error_response(
                error_code="DATA_TYPE_ERROR",
                message="Data type conversion error",
                details=f"Could not convert data to appropriate types: {error_msg}",
                suggestion="Check that your data values match the expected column types."
            )
        elif any(phrase in error_msg.lower() for phrase in ["file not found", "no such file", "does not exist"]):
            error_data = create_error_response(
                error_code="FILE_ACCESS_ERROR",
                message="File not accessible",
                details=f"Could not access the file: {error_msg}",
                suggestion="Verify that the file exists and is accessible to the application."
            )
        else:
            # Generic fallback with as much detail as possible
            error_data = create_error_response(
                error_code="PROCESSING_ERROR",
                message="Data processing error",
                details=f"Error details: {error_msg}",
                suggestion="Check the logs for more information or contact support."
            )
        
        # Update job status to failed
        try:
            job = get_ingestion_job(db_session, job_id)
            job.status = "failed"
            job.error = json.dumps(error_data)
            job.end_time = datetime.now(timezone.utc)
            db_session.commit()
        except Exception as commit_error:
            logger.error(f"Failed to update job status: {str(commit_error)}")

    
    finally:
        # Close the database session
        db_session.close()

# Process database ingestion with database
def process_db_ingestion_with_db(job_id, db_type, db_config, chunk_size, db):
    """Process database ingestion in a background thread with database access"""
    try:
        # Create a new database session
        db_session = SessionLocal()
        
        # Define temp_dir at the beginning to ensure it's available in all scopes
        temp_dir = DATA_DIR / f"temp_{job_id}"
        
        # Ensure the temp directory exists
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Define output_file at the beginning to ensure it's available in all scopes
        output_file = DATA_DIR / f"{job_id}.parquet"
        
        # Define file_id for ProfileResult - use job_id as file_id for database ingestion
        file_id = job_id
        
        # Create a connection string display for the profile name
        connection_string_display = f"{db_config.get('database', 'db')}.{db_config.get('table', 'table')}"
        
        # Update job status
        job = get_ingestion_job(db_session, job_id)
        job.status = "running"
        job.progress = 0
        job.details = "Initializing SQL database connection"
        db_session.commit()
        
        # Function to check if job is cancelled
        def check_job_cancelled():
            # Refresh job from database to get latest status
            nonlocal job
            db_session.refresh(job)
            
            # Check if job has been marked as cancelled in the database
            if job.status == "cancelled":
                logger.info(f"Job {job_id} has been cancelled in the database, stopping processing")
                return True
                
            # Check for cancellation marker file
            cancel_marker_path = DATA_DIR / f"cancel_{job_id}"
            if cancel_marker_path.exists():
                logger.info(f"Cancellation marker found for job {job_id}, stopping processing")
                # Update job status to cancelled since we found a marker
                job.status = "cancelled"
                job.end_time = datetime.now()
                job.details = f"{job.details} (Cancelled by user)"
                db_session.commit()
                return True
                
            return False
        
        # Create connection string
        connection_string = create_connection_string(db_type, db_config)
        
        # Sanitize table name for SQL injection prevention
        table_name = db_config['table']
        if not table_name.isalnum() and not all(c.isalnum() or c in ['_', '.'] for c in table_name):
            raise ValueError(f"Invalid table name: {table_name}. Table names must contain only alphanumeric characters, underscores, or dots.")
        
        # Create an entry in the uploaded_files table for consistency with file-based ingestion
        try:
            # Extract username from job config if available
            username = "Unknown"
            if job.config:
                try:
                    config_data = json.loads(job.config)
                    if "username" in config_data:
                        username = config_data["username"]
                except json.JSONDecodeError:
                    pass
                    
            # Create a record in the uploaded_files table with a unique ID
            file_id = str(uuid.uuid4())
            
            # Create output file path using file_id for better traceability
            output_file = DATA_DIR / f"{file_id}.parquet"
            
            # Create temporary directory for parquet chunks
            temp_dir = DATA_DIR / f"temp_{job_id}"
            temp_dir.mkdir(exist_ok=True)
            
            # Format the connection details for the filename field (host:port:database)
            host = db_config.get('host', 'localhost')
            port = db_config.get('port', '')
            database_name = db_config.get('database', 'unknown')
            connection_string_display = f"{host}:{port}:{database_name}"
            
            db_file_record = UploadedFile(
                id=file_id,
                filename=connection_string_display,  # Store connection details in filename field
                path=str(output_file),  # Path to the output parquet file
                type="database",
                uploaded_by=username,
                uploaded_at=datetime.now(timezone.utc),
                chunk_size=chunk_size,
                dataset=db_config['table']  # Store table name in dataset field
            )
            db_session.add(db_file_record)
            db_session.commit()
            
            # Update job config to include the file_id reference
            if job.config:
                try:
                    config_data = json.loads(job.config)
                    config_data["file_id"] = file_id
                    job.config = json.dumps(config_data)
                    db_session.commit()
                except json.JSONDecodeError:
                    logger.warning(f"Could not update job config with file_id for job {job_id}")
        except Exception as e:
            logger.warning(f"Error creating uploaded_files entry for database ingestion: {str(e)}")
            # Continue with processing even if this fails - it's not critical
        
        start_time = time.time()
        
        # Connect to database
        engine = create_engine(connection_string)
        
        try:
            # Get total row count (with error handling for different SQL dialects)
            total_rows = 0
            row_count_query = ""
            
            job.details = "Calculating total row count"
            db_session.commit()
            
            try:
                if db_type == "mysql":
                    row_count_query = f"SELECT COUNT(*) FROM {table_name}"
                elif db_type == "postgresql":
                    row_count_query = f"SELECT COUNT(*) FROM {table_name}"
                elif db_type == "mssql":
                    row_count_query = f"SELECT COUNT(*) FROM {table_name}"
                
                with engine.connect() as conn:
                    result = conn.execute(sqlalchemy.text(row_count_query))
                    total_rows = result.scalar()
                    
                logger.info(f"Total rows to extract: {total_rows}")
            except Exception as e:
                logger.warning(f"Could not get exact row count: {str(e)}")
                logger.warning("Continuing with extraction without knowing total row count")
                total_rows = 0  # Will use a different progress calculation
            
            # Check if job was cancelled during preparation
            if check_job_cancelled():
                logger.info(f"Job {job_id} was cancelled during preparation, stopping")
                return
            
            # Read data in chunks and save directly to parquet files
            offset = 0
            processed_rows = 0
            chunk_files = []
            chunk_number = 0
            
            job.details = "Starting data extraction from SQL database"
            db_session.commit()
            
            # Keep track of schema information from first chunk for consistency
            schema = None
            
            while True:
                # Check for cancellation
                if check_job_cancelled():
                    logger.info(f"Job {job_id} was cancelled during processing, stopping")
                    
                    # Clean up temporary files
                    for chunk_file in chunk_files:
                        if os.path.exists(chunk_file):
                            os.unlink(chunk_file)
                    
                    if temp_dir.exists():
                        shutil.rmtree(temp_dir)
                    
                    return
                
                # Update progress
                if total_rows > 0:
                    progress = int((processed_rows / total_rows) * 100)
                    job.progress = min(progress, 99)  # Cap at 99% until complete
                else:
                    # If total_rows unknown, use a sliding scale
                    job.progress = min(10 + (chunk_number * 5), 99)  # Cap at 99%
                
                job.details = f"Extracting data (offset: {offset}, processed: {processed_rows} rows)"
                db_session.commit()
                
                # Construct query with proper handling for different SQL dialects
                query = ""
                try:
                    if db_type == "mysql" or db_type == "postgresql":
                        query = f"SELECT * FROM {table_name} LIMIT {chunk_size} OFFSET {offset}"
                    elif db_type == "mssql":
                        # MSSQL uses different OFFSET/FETCH syntax
                        query = f"SELECT * FROM {table_name} ORDER BY (SELECT NULL) OFFSET {offset} ROWS FETCH NEXT {chunk_size} ROWS ONLY"
                    
                    # Read chunk safely using parameterized query
                    chunk = pd.read_sql(sqlalchemy.text(query), engine)
                except Exception as e:
                    # Try a different approach if the standard approach fails
                    logger.warning(f"Error with standard query: {str(e)}. Trying alternative approach.")
                    try:
                        # Simpler query without OFFSET for compatibility
                        if chunk_number == 0:
                            query = f"SELECT TOP {chunk_size} * FROM {table_name}"
                        else:
                            # This might not work for all databases, but it's a fallback
                            query = f"SELECT * FROM {table_name} LIMIT {chunk_size}"
                        
                        chunk = pd.read_sql(sqlalchemy.text(query), engine)
                    except Exception as inner_e:
                        # If all approaches fail, report and exit
                        error_msg = f"Failed to extract data: {str(inner_e)}"
                        logger.error(error_msg)
                        raise ValueError(error_msg)
                
                # If no rows returned, we've reached the end
                if len(chunk) == 0:
                    break
                
                # Save first chunk schema for consistency (but don't depend on it)
                if chunk_number == 0:
                    try:
                        # Use iloc to avoid FutureWarning about Series.__getitem__
                        schema = str(chunk.dtypes.iloc[0]) if len(chunk.dtypes) > 0 else None
                    except Exception as schema_error:
                        logger.warning(f"Non-critical schema detection error: {str(schema_error)}")
                        schema = None
                
                # Convert datetime columns to string to avoid serialization issues
                try:
                    for col in chunk.select_dtypes(include=['datetime64']).columns:
                        logger.info(f"Converting datetime column '{col}' to string")
                        chunk[col] = chunk[col].astype(str)
                except Exception as dt_error:
                    logger.warning(f"Error handling datetime columns: {str(dt_error)}")
                
                # Save chunk to a temporary parquet file
                chunk_file = temp_dir / f"chunk_{chunk_number}.parquet"
                chunk.to_parquet(chunk_file, index=False)
                chunk_files.append(chunk_file)
                
                # Update counters
                processed_rows += len(chunk)
                offset += chunk_size
                chunk_number += 1
                
                # Add a small delay to prevent database overload
                time.sleep(0.1)
            
            # Check if any data was extracted
            if not chunk_files:
                raise ValueError("No data was extracted from the database. The table might be empty.")
            
            # Now combine all chunk files into a single parquet file
            job.details = "Combining extracted data chunks into final parquet file"
            job.progress = 99
            db_session.commit()
            
            # If only one chunk, just rename it
            if len(chunk_files) == 1:
                shutil.move(str(chunk_files[0]), str(output_file))
            else:
                # Read and combine all chunks
                dfs = [pd.read_parquet(chunk_file) for chunk_file in chunk_files]
                combined_df = pd.concat(dfs, ignore_index=True)
                combined_df.to_parquet(output_file, index=False)
                
                # Clean up temporary files
                for chunk_file in chunk_files:
                    if os.path.exists(chunk_file):
                        os.unlink(chunk_file)
            
            # Clean up temporary directory
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Mark job as completed
            job.status = "completed"
            job.progress = 100
            job.end_time = datetime.now()
            job.details = f"Completed. Extracted {processed_rows} rows in {processing_time:.2f} seconds."
            logger.info(f"Database ingestion completed for job {job_id}. Processed {processed_rows} rows.")
            
            # Automatically generate profiling data after ingestion is completed
            try:
                print(f"Generating automatic profiling data for job {job_id}")
                
                # Read the parquet file for profiling
                df = pd.read_parquet(output_file)
                print(df)
                # 1. Generate schema information
                columns_info = []
                for column in df.columns:
                    dtype = df[column].dtype
                    # Convert nullable from NumPy bool_ to Python bool
                    nullable = bool(df[column].isna().any())
                    
                    # Get a sample value (safely handling empty dataframes)
                    sample_value = None
                    sample = None
                    
                    if len(df) > 0:
                        non_null_values = df[column].dropna()
                        if len(non_null_values) > 0:
                            sample_value = non_null_values.iloc[0]
                            
                            # Convert NumPy types to native Python types for JSON serialization
                            if isinstance(sample_value, (np.integer, np.floating)):
                                sample = sample_value.item()
                            elif isinstance(sample_value, np.bool_):  # Handle NumPy boolean type
                                sample = bool(sample_value)
                            elif pd.api.types.is_datetime64_dtype(dtype):
                                sample = str(sample_value)
                            elif isinstance(sample_value, np.ndarray):
                                sample = sample_value.tolist()  # Convert NumPy array to list
                            elif isinstance(sample_value, pd.Timestamp):
                                sample = str(sample_value)
                            else:
                                sample = sample_value
                    
                    columns_info.append({
                        "name": column,
                        "dtype": str(dtype),
                        "nullable": nullable,
                        "sample": sample,
                        "sample_type": type(sample).__name__ if sample is not None else None
                    })
                
                schema_data = {
                    "columns_count": len(df.columns),
                    "rows_count": len(df),
                    "columns": columns_info
                }
                
                # 2. Generate statistics
                row_count = len(df)
                column_count = len(df.columns)
                
                # Calculate null percentage
                total_cells = row_count * column_count
                null_count = df.isna().sum().sum()
                null_percentage = (null_count / total_cells) * 100 if total_cells > 0 else 0
                
                # Convert null_percentage from NumPy type to Python native type if needed
                if isinstance(null_percentage, (np.integer, np.floating)):
                    null_percentage = null_percentage.item()
                
                # Calculate memory usage
                memory_usage_bytes = df.memory_usage(deep=True).sum()
                if isinstance(memory_usage_bytes, (np.integer, np.floating)):
                    memory_usage_bytes = memory_usage_bytes.item()
                    
                if memory_usage_bytes < 1024:
                    memory_usage = f"{memory_usage_bytes} B"
                elif memory_usage_bytes < 1024 * 1024:
                    memory_usage = f"{memory_usage_bytes / 1024:.1f} KB"
                else:
                    memory_usage = f"{memory_usage_bytes / (1024 * 1024):.1f} MB"
                
                # Calculate data density (rows per KB)
                data_density = (row_count / (memory_usage_bytes / 1024)) if memory_usage_bytes > 0 else 0
                if isinstance(data_density, (np.integer, np.floating)):
                    data_density = data_density.item()
                    
                completion_rate = 100 - null_percentage
                if isinstance(completion_rate, (np.integer, np.floating)):
                    completion_rate = completion_rate.item()
                
                stats_data = {
                    "row_count": row_count,
                    "column_count": column_count,
                    "null_percentage": null_percentage,
                    "memory_usage": memory_usage,
                    "processing_time": f"{processing_time:.2f}s",
                    "data_density": data_density,
                    "completion_rate": completion_rate,
                    "error_rate": 0  # Placeholder, could be calculated from data quality checks
                }
                
                # 3. Store profiling data in job metadata
                if job.config:
                    try:
                        config_data = json.loads(job.config)
                        config_data["schema"] = schema_data
                        config_data["statistics"] = stats_data
                        job.config = json.dumps(config_data)
                        
                        # 4. Also create a ProfileResult record so it shows up in the profiles API
                        from .profiler.models import ProfileResult
                        import uuid
                        
                        # Create a profile ID
                        profile_id = str(uuid.uuid4())
                        
                        # Create column profiles in the format expected by ProfileResult
                        column_profiles_data = {}
                        for col_info in columns_info:
                            column_profiles_data[col_info["name"]] = {
                                "name": col_info["name"],
                                "type": col_info["dtype"],
                                "nullable": col_info["nullable"],
                                "sample": col_info["sample"],
                                "stats": {}
                            }
                        
                        # Create the ProfileResult record
                        profile_result = ProfileResult(
                            id=profile_id,
                            file_id=file_id,  # Use the file_id created for this database ingestion
                            file_name=connection_string_display,  # Use the connection string as the file name
                            parquet_file_path=str(output_file),
                            total_rows=row_count,
                            total_columns=column_count,
                            data_quality_score=completion_rate / 100 if completion_rate is not None else 0.0,
                            column_profiles=column_profiles_data,
                            exact_duplicates_count=0,  # We don't calculate duplicates for DB ingestion
                            fuzzy_duplicates_count=0,
                            duplicate_groups={"exact": [], "fuzzy": []}
                            # Removed status parameter as it doesn't exist in the model
                        )
                        db_session.add(profile_result)
                        db_session.commit()
                        print(f"Successfully stored profiling data for job {job_id} and created ProfileResult record {profile_id}")
                    except json.JSONDecodeError:
                        print(f"Could not update job config with profiling data for job {job_id}")
                    except Exception as profile_record_error:
                        print(f"Error creating ProfileResult record: {str(profile_record_error)}")
                        # Don't fail the job if creating the ProfileResult fails
                
            except Exception as profiling_error:
                print(f"Error generating profiling data for job {job_id}: {str(profiling_error)}")
                # Don't raise the exception - we don't want to fail the job if profiling fails
        
        finally:
            engine.dispose()
    
    except Exception as e:
        print(f"Error processing database ingestion: {str(e)}")
        
        # Clean up temporary directory if it exists
        # temp_dir is already defined at the beginning of the function
        if temp_dir.exists():
            try:
                shutil.rmtree(temp_dir)
            except Exception as cleanup_error:
                logger.error(f"Error cleaning up temporary directory: {str(cleanup_error)}")
        
        # Update job status to failed
        try:
            job = get_ingestion_job(db_session, job_id)
            job.status = "failed"
            job.error = str(e)
            job.end_time = datetime.now()
            db_session.commit()
        except Exception as update_error:
            logger.error(f"Error updating job status: {str(update_error)}")
    
    finally:
        # Close the database session
        db_session.close()

# Database Connections Functions
def get_db_connections(db, username):
    """Get all saved database connections for a user"""
    return db.query(DatabaseConnection).filter(DatabaseConnection.username == username).all()

def get_db_connection(db, connection_id):
    """Get a database connection by ID"""
    return db.query(DatabaseConnection).filter(DatabaseConnection.id == connection_id).first()

def save_db_connection(db, connection_data):
    """Save a new database connection"""
    connection = DatabaseConnection(
        id=connection_data.get("id", str(uuid.uuid4())),
        name=connection_data.get("name"),
        type=connection_data.get("type"),
        config=json.dumps(connection_data.get("config")),
        username=connection_data.get("username")
    )
    db.add(connection)
    db.commit()
    return connection

def update_db_connection(db, connection_id, connection_data):
    """Update an existing database connection"""
    connection = get_db_connection(db, connection_id)
    if not connection:
        return None
    
    if "name" in connection_data:
        connection.name = connection_data["name"]
    if "type" in connection_data:
        connection.type = connection_data["type"]
    if "config" in connection_data:
        connection.config = json.dumps(connection_data["config"])
    
    db.commit()
    return connection

def delete_db_connection(db, connection_id):
    """Delete a database connection"""
    connection = get_db_connection(db, connection_id)
    if not connection:
        return False
    
    db.delete(connection)
    db.commit()
    return True

# API Routes
@router.post("/upload", status_code=status.HTTP_200_OK)
async def upload_file(
    file: UploadFile = File(...),
    chunkSize: int = Form(1000),
    current_user: User = Depends(has_permission("datapuur:write")),  # Updated permission
    db: Session = Depends(get_db)
):
    """Upload a file for data ingestion"""
    # Validate file type
    file_ext = file.filename.split('.')[-1].lower()
    if file_ext not in ['csv', 'json']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV and JSON files are supported"
        )
    
    # Generate a unique file ID
    file_id = str(uuid.uuid4())
    file_path = UPLOAD_DIR / f"{file_id}.{file_ext}"
    
    # Ensure the upload directory exists
    try:
        if not UPLOAD_DIR.exists():
            logger.info(f"Creating upload directory: {UPLOAD_DIR}")
            UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        
        # Log the directory path for debugging
        logger.info(f"Saving file to: {file_path}")
        
        # Save the file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Verify the file was saved correctly
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found after save: {file_path}")
            
    except Exception as e:
        logger.error(f"Error saving file: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving file: {str(e)}"
        )
    finally:
        file.file.close()
    
    # Store file info in database
    # Extract filename without extension for dataset field
    filename_without_ext = os.path.splitext(file.filename)[0]
    
    file_data = {
        "filename": file.filename,
        "path": str(file_path),
        "type": file_ext,
        "uploaded_by": current_user.username,
        "uploaded_at": datetime.now(timezone.utc),
        "chunk_size": chunkSize,
        "dataset": filename_without_ext  # Store filename without extension as dataset name
    }
    save_uploaded_file(db, file_id, file_data)
    
    # Log activity
    log_activity(
        db=db,
        username=current_user.username,
        action="File upload",
        details=f"Uploaded file: {file.filename} ({file_ext.upper()})"
    )
    
    return {"file_id": file_id, "message": "File uploaded successfully"}

@router.get("/schema/{file_id}", status_code=status.HTTP_200_OK)
async def get_file_schema(
    file_id: str,
    current_user: User = Depends(has_permission("schema:read")),
    db: Session = Depends(get_db)
):
    """Get schema for an uploaded file"""
    file_info = get_uploaded_file(db, file_id)
    if not file_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    file_path = file_info.path
    chunk_size = file_info.chunk_size
    
    try:
        if file_info.type == "csv":
            schema = detect_csv_schema(file_path, chunk_size)
        elif file_info.type == "json":
            schema = detect_json_schema(file_path, chunk_size)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported file type"
            )
        
        # Store schema in database
        file_data = {
            "schema": schema
        }
        save_uploaded_file(db, file_id, file_data)
        
        # Log activity
        log_activity(
            db=db,
            username=current_user.username,
            action="Schema detection",
            details=f"Detected schema for file: {file_info.filename}"
        )
        
        return {"schema": schema}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error detecting schema: {str(e)}"
        )

@router.post("/test-connection", status_code=status.HTTP_200_OK)
async def test_database_connection(
    connection_info: dict,
    current_user: User = Depends(has_permission("datapuur:write")),  # Updated permission
    db: Session = Depends(get_db)
):
    """Test a database connection"""
    try:
        db_type = connection_info.get("type")
        config = connection_info.get("config", {})
        
        # Validate required fields
        required_fields = ["host", "port", "database", "username"]
        for field in required_fields:
            if not config.get(field):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing required field: {field}"
                )
        
        # Create connection string
        connection_string = create_connection_string(db_type, config)
        
        # Test connection
        engine = create_engine(connection_string)
        with engine.connect() as connection:
            # Just test the connection
            pass
        
        # Log activity
        log_activity(
            db=db,
            username=current_user.username,
            action="Database connection test",
            details=f"Tested connection to {db_type} database: {config['database']}"
        )
        
        return {"message": "Connection successful"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Connection failed: {str(e)}"
        )

@router.post("/db-schema", status_code=status.HTTP_200_OK)
async def get_database_schema(
    connection_info: dict,
    current_user: User = Depends(has_permission("datapuur:read")),  # Updated permission
    db: Session = Depends(get_db)
):
    """Get schema from a database table"""
    try:
        db_type = connection_info.get("type")
        config = connection_info.get("config", {})
        chunk_size = connection_info.get("chunkSize", 1000)
        
        # Validate required fields
        required_fields = ["host", "port", "database", "username", "table"]
        for field in required_fields:
            if not config.get(field):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing required field: {field}"
                )
        
        # Get schema
        schema = get_db_schema(db_type, config, chunk_size)
        
        # Log activity
        log_activity(
            db=db,
            username=current_user.username,
            action="Database schema detection",
            details=f"Detected schema for table: {config['database']}.{config['table']}"
        )
        
        return {"schema": schema}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error fetching schema: {str(e)}"
        )

@router.post("/ingest-file", status_code=status.HTTP_200_OK)
async def ingest_file(
    request: FileIngestionRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(has_permission("datapuur:write")),  # Updated permission
    db: Session = Depends(get_db)
):
    """Start file ingestion job"""
    try:
        file_id = request.file_id
        file_name = request.file_name
        chunk_size = request.chunk_size
        
        # Check if file exists
        file_info = get_uploaded_file(db, file_id)
        if not file_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        # Check if this file was part of a cancelled upload
        # Extract upload ID from the file path if it's from a chunked upload
        file_path = getattr(file_info, 'path', '')
        if file_path:
            # Try to extract upload ID from the file path or metadata
            upload_id = None
            if hasattr(file_info, 'metadata') and file_info.metadata:
                try:
                    metadata = json.loads(file_info.metadata)
                    upload_id = metadata.get('upload_id')
                except:
                    pass
            
            # If we couldn't get it from metadata, try to extract from filename
            if not upload_id and 'upload-' in file_path:
                try:
                    # Extract upload ID from path - this is a heuristic and may need adjustment
                    filename = os.path.basename(file_path)
                    parts = filename.split('_')
                    for part in parts:
                        if part.startswith('upload-'):
                            upload_id = part
                            break
                except:
                    pass
            
            # If we have an upload ID, check for cancellation marker
            if upload_id:
                cancel_marker = UPLOAD_DIR / f"cancel_{upload_id}"
                if cancel_marker.exists():
                    # This upload was cancelled, don't proceed with ingestion
                    return {
                        "cancelled": True, 
                        "message": "Ingestion cancelled as the upload was marked for cancellation"
                    }
        
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # Create job in database
        job_data = {
            "id": job_id,
            "name": file_name,
            "type": "file",
            "status": "queued",
            "progress": 0,
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "details": f"File: {file_name}",
            "error": None,
            "config": {
                "file_id": file_id,
                "chunk_size": chunk_size
            }
        }
        save_ingestion_job(db, job_id, job_data)
        
        # Start background task with database session
        background_tasks.add_task(process_file_ingestion_with_db, job_id, file_id, chunk_size, db)
        
        # Log activity
        log_activity(
            db=db,
            username=current_user.username,
            action="File ingestion started",
            details=f"Started ingestion for file: {file_name}"
        )
        
        return {"job_id": job_id, "message": "File ingestion started"}
    except Exception as e:
        # Create a structured error response with more context
        error_resp = create_error_response(
            error_code="INGESTION_INIT_ERROR",
            message="Error starting ingestion process",
            details=str(e),
            suggestion="Check that the file exists and is accessible"
        )
        logger.error(f"Error starting ingestion: {str(e)}\nTraceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_resp
        )

@router.post("/ingest-db", status_code=status.HTTP_200_OK)
async def ingest_database(
    request: DatabaseConfig,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(has_permission("datapuur:write")),  # Updated permission
    db: Session = Depends(get_db)
):
    """Start database ingestion job"""
    try:
        db_type = request.type
        db_config = request.config
        chunk_size = request.chunk_size
        connection_name = request.connection_name
        
        # Validate required fields
        required_fields = ["host", "port", "database", "username", "table"]
        for field in required_fields:
            if not db_config.get(field):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing required field: {field}"
                )
        
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # Create job in database
        job_data = {
            "id": job_id,
            "name": connection_name,
            "type": "database",
            "status": "queued",
            "progress": 0,
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "details": f"DB: {db_config['database']}.{db_config['table']}",
            "error": None,
            "config": {
                "type": db_type,
                "database": db_config["database"],
                "table": db_config["table"],
                "username": current_user.username  # Store the user who initiated the ingestion
            }
        }
        save_ingestion_job(db, job_id, job_data)
        
        # Start background task with database session
        background_tasks.add_task(process_db_ingestion_with_db, job_id, db_type, db_config, chunk_size, db)
        
        # Log activity
        log_activity(
            db=db,
            username=current_user.username,
            action="Database ingestion started",
            details=f"Started ingestion for table: {db_config['database']}.{db_config['table']}"
        )
        
        return {"job_id": job_id, "message": "Database ingestion started"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error starting ingestion: {str(e)}"
        )

@router.get("/job-status/{job_id}", response_model=JobStatus)
async def get_job_status(
    job_id: str,
    current_user: User = Depends(has_permission("datapuur:read")),  # Updated permission
    db: Session = Depends(get_db)
):
    """Get status of an ingestion job"""
    job = get_ingestion_job(db, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Convert database model to response model
    config = json.loads(job.config) if job.config else None
    
    return JobStatus(
        id=job.id,
        name=job.name,
        type=job.type,
        status=job.status,
        progress=job.progress,
        start_time=job.start_time.isoformat() if job.start_time else None,
        end_time=job.end_time.isoformat() if job.end_time else None,
        details=job.details,
        error=job.error,
        config=config
    )

@router.post("/cancel-job/{job_id}", status_code=status.HTTP_200_OK)
async def cancel_job(
    job_id: str,
    current_user: User = Depends(has_permission("datapuur:write")),  # Updated permission
    db: Session = Depends(get_db)
):
    """Cancel an ingestion job"""
    job = get_ingestion_job(db, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Only cancel running or queued jobs
    if job.status not in ["running", "queued"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel job with status: {job.status}"
        )
    
    # Create a cancellation marker file to signal to any ongoing processes that they should stop
    try:
        cancel_marker_path = DATA_DIR / f"cancel_{job_id}"
        with open(cancel_marker_path, 'w') as f:
            f.write('cancelled')
        logger.info(f"Created cancellation marker for job {job_id}")
    except Exception as e:
        logger.error(f"Error creating cancellation marker: {str(e)}")
    
    # Update job status
    job.status = "cancelled"  # Changed from "failed" to "cancelled"
    job.error = None  # Remove error message since cancellation is not an error
    job.details = f"{job.details} (Cancelled by user)"  # Add cancellation info to details
    job.end_time = datetime.now()
    
    # Extract file_id from job config if available
    file_id = None
    try:
        if job.config:
            config_data = json.loads(job.config)
            if "file_id" in config_data:
                file_id = config_data["file_id"]
                logger.info(f"Found file_id {file_id} in job config for job {job_id}")
    except json.JSONDecodeError:
        logger.warning(f"Could not parse config JSON for job {job_id}")
    
    # Delete any associated data files
    try:
        if file_id:
            # Use file_id for parquet file naming
            data_path = DATA_DIR / f"{file_id}.parquet"
            if data_path.exists():
                data_path.unlink()
                logger.info(f"Deleted data file for cancelled job: {job_id} (file_id: {file_id})")
        else:
            # Fallback to job_id for backward compatibility
            data_path = DATA_DIR / f"{job_id}.parquet"
            if data_path.exists():
                data_path.unlink()
                logger.info(f"Deleted data file for cancelled job: {job_id} (using job_id)")
    except Exception as e:
        logger.error(f"Error deleting data file for job {job_id}: {str(e)}")
    
    # Delete any associated profile data
    try:
        # First, check if there are any profiles associated with this job
        from .profiler.models import ProfileResult
        
        if file_id:
            # Use file_id to find associated profiles
            profiles = db.query(ProfileResult).filter(ProfileResult.file_id == file_id).all()
            logger.info(f"Found {len(profiles)} profiles for file_id {file_id}")
        else:
            # Fallback to job_id for backward compatibility
            profiles = db.query(ProfileResult).filter(ProfileResult.parquet_file_path == f"{job_id}.parquet").all()
            logger.info(f"Found {len(profiles)} profiles for job_id {job_id}")

        
        for profile in profiles:
            # Delete the profile
            db.delete(profile)
            logger.info(f"Deleted profile {profile.id} for cancelled job: {job_id}")
    except Exception as e:
        logger.error(f"Error deleting profiles for job {job_id}: {str(e)}")
    
    db.commit()
    
    # Log activity
    log_activity(
        db=db,
        username=current_user.username,
        action="Job cancelled",
        details=f"Cancelled ingestion job: {job.name}"
    )
    
    # Convert database model to response model
    config = json.loads(job.config) if job.config else None
    
    return JobStatus(
        id=job.id,
        name=job.name,
        type=job.type,
        status=job.status,
        progress=job.progress,
        start_time=job.start_time.isoformat() if job.start_time else None,
        end_time=job.end_time.isoformat() if job.end_time else None,
        details=job.details,
        error=job.error,
        config=config
    )

@router.get("/ingestion-history", response_model=IngestionHistoryResponse)
async def get_ingestion_history(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    sort: str = Query("newest"),
    type: str = Query(""),
    source: str = Query(""),
    status: str = Query(""),
    search: str = Query(""),
    current_user: User = Depends(has_permission("datapuur:read")),  # Updated permission
    db: Session = Depends(get_db)
):
    """Get history of ingestion jobs with filtering and pagination"""
    try:
        # Build query
        query = db.query(IngestionJob)
        
        # Filter out records of type 'profile'
        query = query.filter(IngestionJob.type != "profile")
        
        # Apply filters
        if type:
            query = query.filter(IngestionJob.type == type)
        
        if source:
            source_type = "database" if source == "database" else "file"
            query = query.filter(IngestionJob.type == source_type)
        
        if status:
            query = query.filter(IngestionJob.status == status)
        
        if search:
            search_lower = f"%{search.lower()}%"
            query = query.filter(
                or_(
                    IngestionJob.name.ilike(search_lower),
                    IngestionJob.details.ilike(search_lower)
                )
            )
        
        # Apply sorting
        if sort == "newest":
            query = query.order_by(IngestionJob.start_time.desc())
        else:
            query = query.order_by(IngestionJob.start_time)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)
        
        # Execute query
        jobs = query.all()
        
        # Convert to response format
        items = []
        for job in jobs:
            # Get file info if it's a file ingestion
            file_info = None
            config = json.loads(job.config) if job.config else {}
            
            if job.type == "file" and config and "file_id" in config:
                file_id = config["file_id"]
                file_info = get_uploaded_file(db, file_id) if file_id else None
            # Get database info if it's a database ingestion
            elif job.type == "database" and config:
                db_info = {
                    "type": config.get("type", "unknown"),
                    "name": config.get("database", "unknown"),
                    "table": config.get("table", "unknown")
                }
            
            # Determine file size based on job type
            file_size = 0
            if job.type == "file" and file_info and os.path.exists(file_info.path):
                # For file ingestion, use the original file size
                file_size = os.path.getsize(file_info.path)
            elif job.type == "database" and job.status == "completed":
                # For database ingestion, look for the generated parquet file
                try:
                    # Construct the path to the expected parquet file
                    data_folder = os.path.join(os.getcwd(), "data")
                    # Get file_id from job config
                    file_id = None
                    if config and "file_id" in config:
                        file_id = config["file_id"]
                    
                    # Use file_id if available, otherwise fall back to job.id for backward compatibility
                    parquet_file = os.path.join(data_folder, f"{file_id if file_id else job.id}.parquet")
                    
                    # Check if the file exists and get its size
                    if os.path.exists(parquet_file):
                        file_size = os.path.getsize(parquet_file)
                except Exception as e:
                    logger.error(f"Error getting parquet file size for job {job.id}: {str(e)}")
            
            # Create history item
            history_item = {
                "id": job.id,
                "filename": job.name,
                "type": "database" if job.type == "database" else file_info.type if file_info else "unknown",
                "size": file_size,
                "uploaded_at": job.start_time.astimezone(timezone.utc).isoformat() if isinstance(job.start_time, datetime) else job.start_time,
                "uploaded_by": config.get("username", current_user.username) if job.type == "database" and config else (file_info.uploaded_by if file_info else current_user.username),
                "preview_url": f"/api/datapuur/ingestion-preview/{job.id}",
                "download_url": f"/api/datapuur/ingestion-download/{job.id}",
                "status": job.status if job.status != "queued" else "processing",
                "source_type": "database" if job.type == "database" else "file",
            }
            
            # Add database info if it's a database ingestion
            if job.type == "database" and config:
                history_item["database_info"] = db_info
            
            items.append(history_item)
        
        # Log activity
        log_activity(
            db=db,
            username=current_user.username,
            action="View ingestion history",
            details=f"Viewed ingestion history (page {page})"
        )
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "limit": limit
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching ingestion history: {str(e)}"
        )

@router.get("/file-preview/{file_id}", response_model=PreviewResponse)
async def get_file_preview(
    file_id: str,
    current_user: User = Depends(has_permission("datapuur:read")),
    db: Session = Depends(get_db)
):
    """Get preview data for a file by file_id"""
    try:
        # Find the job associated with this file_id
        from sqlalchemy import desc
        file_info = get_uploaded_file(db, file_id)
        if not file_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
            
        # Log file info for debugging
        logging.info(f"Found file: {file_info.id}, {file_info.filename}")
            
        # Look for jobs with this file_id in their config
        jobs = db.query(IngestionJob)\
            .filter(IngestionJob.type == "file")\
            .filter(IngestionJob.status == "completed")\
            .order_by(desc(IngestionJob.start_time))\
            .all()
            
        logging.info(f"Found {len(jobs)} completed ingestion jobs to check")
            
        # Find the job with this file_id in config
        target_job = None
        for j in jobs:
            if not j.config:
                continue
            
            try:
                config = json.loads(j.config) if isinstance(j.config, str) else j.config
                # Try multiple possible keys where file_id might be stored
                file_id_in_config = config.get("file_id") or config.get("fileId") or \
                                  config.get("file", {}).get("id") if isinstance(config.get("file"), dict) else None
                
                # Log for debugging
                if file_id_in_config:
                    logging.info(f"Job {j.id} has file_id: {file_id_in_config}")
                
                if file_id_in_config == file_id:
                    target_job = j
                    break
            except (json.JSONDecodeError, AttributeError) as e:
                logging.error(f"Error parsing job config for job {j.id}: {str(e)}")
                continue
        
        if not target_job:
            # Fall back to most recent job if specific job for this file not found
            # This is a temporary workaround until we have better job-file mapping
            if jobs:
                logging.warning(f"No job found with matching file_id {file_id}, falling back to most recent job")
                target_job = jobs[0]
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No completed ingestion found for this file"
                )
        
        logging.info(f"Using job ID {target_job.id} for preview of file {file_id}")
        
        # Forward to the existing preview endpoint with job ID
        return await get_ingestion_preview(target_job.id, current_user, db)
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in get_file_preview: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting file preview: {str(e)}"
        )

@router.get("/ingestion-preview/{ingestion_id}", response_model=PreviewResponse)
async def get_ingestion_preview(
    ingestion_id: str,
    current_user: User = Depends(has_permission("datapuur:read")),  # Updated permission
    db: Session = Depends(get_db)
):
    """Get preview data for an ingestion"""
    job = get_ingestion_job(db, ingestion_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ingestion not found"
        )
    
    # Check if job is completed
    if job.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot preview ingestion with status: {job.status}"
        )
    try:
        # Extract file_id from job config if available
        file_id = None
        if job.config:
            try:
                config = json.loads(job.config)
                file_id = config.get("file_id")
                if file_id:
                    logger.info(f"Found file_id {file_id} in job config for ingestion {ingestion_id}")
            except json.JSONDecodeError:
                logger.warning(f"Could not parse config JSON for ingestion {ingestion_id}")
        
        # Get the parquet file path using file_id if available
        if file_id:
            parquet_path = DATA_DIR / f"{file_id}.parquet"
            logger.info(f"Looking for parquet file with file_id: {file_id}")
        else:
            # Fallback to ingestion_id for backward compatibility
            parquet_path = DATA_DIR / f"{ingestion_id}.parquet"
            logger.info(f"Falling back to ingestion_id for parquet file: {ingestion_id}")        
        if not os.path.exists(parquet_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ingestion data file not found"
            )
        
        # Read the parquet file
        df = pd.read_parquet(parquet_path)
        
        # Limit to first 100 rows for preview
        preview_df = df.head(100).copy()  # Create an explicit copy to avoid SettingWithCopyWarning
        
        # Convert to appropriate format based on job type
        if job.type == "file":
            config = json.loads(job.config) if job.config else {}
            file_id = config.get("file_id")
            file_info = get_uploaded_file(db, file_id) if file_id else None
            file_type = file_info.type if file_info else "unknown"
            
            if file_type == "csv":
                # For CSV, return as list of lists with headers
                headers = preview_df.columns.tolist()
                # Convert NumPy types to Python native types
                rows = []
                for row in preview_df.values:
                    python_row = []
                    for item in row:
                        if pd.isna(item):
                            python_row.append(None)
                        elif isinstance(item, (np.integer, np.floating)):
                            python_row.append(item.item())
                        else:
                            python_row.append(item)
                    rows.append(python_row)
                
                return {
                    "data": rows,
                    "headers": headers,
                    "filename": file_info.filename if file_info else f"file_{file_id}",
                    "type": "csv"
                }
            elif file_type == "json":
                # For JSON, always return a list of dictionaries
                
                # Handle empty DataFrame case
                if preview_df.empty:
                    return {
                        "data": [],  # Empty array
                        "headers": [],
                        "filename": file_info.filename if file_info else f"file_{file_id}",
                        "type": "json"
                    }
                
                # Convert to records and ensure all values have proper Python types
                try:
                    # First attempt - standard conversion
                    records = []
                    for record in preview_df.to_dict(orient='records'):
                        clean_record = {}
                        for key, value in record.items():
                            if pd.isna(value):
                                clean_record[key] = None
                            elif isinstance(value, (np.integer, np.floating)):
                                clean_record[key] = value.item()  # Convert NumPy scalar to Python native type
                            elif isinstance(value, np.bool_):
                                clean_record[key] = bool(value)  # Convert NumPy boolean to Python boolean
                            elif isinstance(value, (dict, list)):
                                # Ensure nested objects are properly serialized
                                clean_record[key] = json.loads(json.dumps(value))
                            else:
                                clean_record[key] = value
                        records.append(clean_record)
                except Exception as e:
                    # Fallback - if any error occurs, create a simpler structure
                    print(f"Error in preview conversion: {str(e)}")
                    records = []
                    for i, row in preview_df.iterrows():
                        record = {}
                        for col in preview_df.columns:
                            val = row[col]
                            if pd.isna(val):
                                record[col] = None
                            elif isinstance(val, (np.integer, np.floating)):
                                record[col] = float(val)
                            elif isinstance(val, np.bool_):
                                record[col] = bool(val)
                            else:
                                record[col] = str(val)
                        records.append(record)
                
                # CRITICAL: Force records to be a list if it's not already
                if not isinstance(records, list):
                    records = [records] if records else []
                
                # Verify each record is a dict
                for i, record in enumerate(records):
                    if not isinstance(record, dict):
                        records[i] = {"value": record}
                
                # Ensure the data is JSON serializable by converting to and from JSON
                try:
                    # This will catch any non-serializable objects
                    json_string = json.dumps(records)
                    # Parse it back to ensure we have valid JSON objects
                    records = json.loads(json_string)
                except Exception as e:
                    print(f"JSON serialization error: {str(e)}")
                    # Fallback to a simpler structure if serialization fails
                    records = [{"error": "Data could not be serialized", "index": i} for i in range(len(records))]
                
                # Log the structure for debugging
                print(f"Preview response structure: data is a {type(records).__name__} with {len(records)} items")
                
                return {
                    "data": records,
                    "headers": preview_df.columns.tolist(),
                    "filename": file_info.filename if file_info else f"file_{file_id}",
                    "type": "json"
                }
        elif job.type == "database":
            # For database, return as list of dictionaries
            config = json.loads(job.config) if job.config else {}
            connection_name = config.get("connection_name", "Database Connection")
            
            # Convert DataFrame to records and then handle NumPy types
            records = []
            for record in preview_df.to_dict(orient='records'):
                clean_record = {}
                for key, value in record.items():
                    if pd.isna(value):
                        clean_record[key] = None
                    elif isinstance(value, (np.integer, np.floating)):
                        clean_record[key] = value.item()  # Convert NumPy scalar to Python native type
                    elif isinstance(value, np.bool_):
                        clean_record[key] = bool(value)  # Convert NumPy boolean to Python boolean
                    else:
                        clean_record[key] = value
                records.append(clean_record)
            
            return {
                "data": records,
                "headers": preview_df.columns.tolist(),
                "filename": connection_name,
                "type": "database"
            }
        else:
            # Generic table format as fallback
            headers = preview_df.columns.tolist()
            rows = []
            for row in preview_df.values:
                python_row = []
                for item in row:
                    if pd.isna(item):
                        python_row.append(None)
                    elif isinstance(item, (np.integer, np.floating)):
                        python_row.append(item.item())
                    else:
                        python_row.append(item)
                rows.append(python_row)
            
            return {
                "data": rows,
                "headers": headers,
                "filename": f"ingestion_{ingestion_id}",
                "type": "table"
            }
    except Exception as e:
        # Log the specific parquet reading error
        print(f"Error reading parquet file: {str(e)}")

@router.get("/ingestion-schema/{ingestion_id}", response_model=SchemaResponse)
async def get_ingestion_schema(
    ingestion_id: str,
    current_user: User = Depends(has_permission("datapuur:read")),  # Updated permission
    db: Session = Depends(get_db)
):
    """Get schema for an ingestion or uploaded file"""
    # First, try to find an UploadedFile with the given ID
    file_info = get_uploaded_file(db, ingestion_id)
    file_id = None
    job = None
    
    if file_info:
        # If we found an UploadedFile, use its ID as the file_id
        file_id = file_info.id
        logger.info(f"Found UploadedFile with ID {file_id}")
    else:
        # If not found, try to find an IngestionJob with the given ID
        job = get_ingestion_job(db, ingestion_id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Neither uploaded file nor ingestion job found with the provided ID"
            )
        
        # Check if job is completed
        if job.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot get schema for ingestion with status: {job.status}"
            )
        
        # Extract file_id from job config if available
        if job.config:
            try:
                config = json.loads(job.config)
                file_id = config.get("file_id")
                if file_id:
                    logger.info(f"Found file_id {file_id} in job config for ingestion {ingestion_id}")
            except json.JSONDecodeError:
                logger.warning(f"Could not parse config JSON for ingestion {ingestion_id}")
        
    # Try to determine the appropriate parquet file path
    try:
        # Get the parquet file path using file_id if available
        if file_id:
            parquet_path = DATA_DIR / f"{file_id}.parquet"
            logger.info(f"Looking for parquet file with file_id: {file_id}")
        else:
            # Fallback to ingestion_id for backward compatibility
            parquet_path = DATA_DIR / f"{ingestion_id}.parquet"
            logger.info(f"Falling back to ingestion_id for parquet file: {ingestion_id}")
            
        if not os.path.exists(parquet_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ingestion data file not found"
            )
        
        # Read the parquet file metadata
        df = pd.read_parquet(parquet_path)
        
        # Generate schema
        fields = []
        sample_values = []
        
        for column in df.columns:
            dtype = df[column].dtype
            
            # Determine field type
            if pd.api.types.is_integer_dtype(dtype):
                field_type = "integer"
            elif pd.api.types.is_float_dtype(dtype):
                field_type = "float"
            elif pd.api.types.is_bool_dtype(dtype):
                field_type = "boolean"
            elif pd.api.types.is_datetime64_dtype(dtype):
                field_type = "datetime"
            else:
                field_type = "string"
            
            # Check nullability - convert numpy.bool_ to Python bool
            nullable = bool(df[column].isna().any())
            
            # Get sample value
            sample = None
            non_null_values = df[column].dropna()
            if not non_null_values.empty:
                sample_value = non_null_values.iloc[0]
                
                # Convert NumPy types to Python native types
                if isinstance(sample_value, (np.integer, np.floating)):
                    sample = sample_value.item()  # Convert NumPy scalar to Python native type
                elif isinstance(sample_value, np.bool_):
                    sample = bool(sample_value)  # Convert NumPy boolean to Python boolean
                elif pd.api.types.is_datetime64_dtype(dtype):
                    sample = str(sample_value)
                elif isinstance(sample_value, np.ndarray):
                    sample = sample_value.tolist()  # Convert NumPy array to list
                elif isinstance(sample_value, pd.Timestamp):
                    sample = str(sample_value)
                else:
                    sample = sample_value
                    
            fields.append({
                "name": column,
                "type": field_type,
                "nullable": nullable
            })
            
            sample_values.append(sample)
        
        # Log the schema data being returned
        logger.info(f"Schema data for ingestion {ingestion_id}: {len(fields)} fields")
        
        # Return schema data - ensure all NumPy types are converted to Python native types
        def convert_numpy_types(obj):
            if isinstance(obj, np.bool_):
                return bool(obj)
            elif isinstance(obj, (np.integer, np.floating)):
                return obj.item()
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, dict):
                return {k: convert_numpy_types(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy_types(i) for i in obj]
            else:
                return obj
                
        # Apply conversion to both fields and sample_values
        converted_fields = convert_numpy_types(fields)
        converted_sample_values = convert_numpy_types(sample_values)
        
        return {
            "fields": converted_fields,
            "sample_values": converted_sample_values
        }
    except Exception as e:
        logger.error(f"Error generating schema: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating schema: {str(e)}"
        )

@router.get("/debug-schema/{ingestion_id}")
async def debug_schema(
    ingestion_id: str,
    current_user: User = Depends(has_permission("datapuur:read")),  # Updated permission
    db: Session = Depends(get_db)
):
    """Debug endpoint to check schema data directly"""
    try:
        # First, try to find an UploadedFile with the given ID
        file_info = get_uploaded_file(db, ingestion_id)
        file_id = None
        job = None
        
        if file_info:
            # If we found an UploadedFile, use its ID as the file_id
            file_id = file_info.id
            logger.info(f"Found UploadedFile with ID {file_id}")
        else:
            # If not found, try to find an IngestionJob with the given ID
            job = get_ingestion_job(db, ingestion_id)
            if not job:
                return {"error": "Neither uploaded file nor ingestion job found with the provided ID"}
            
            # Extract file_id from job config if available
            if job.config:
                try:
                    config = json.loads(job.config)
                    file_id = config.get("file_id")
                    if file_id:
                        logger.info(f"Found file_id {file_id} in job config for ingestion {ingestion_id}")
                except json.JSONDecodeError:
                    logger.warning(f"Could not parse config JSON for ingestion {ingestion_id}")
        
        # Get the parquet file path using file_id if available
        if file_id:
            parquet_path = DATA_DIR / f"{file_id}.parquet"
            logger.info(f"Looking for parquet file with file_id: {file_id}")
        else:
            # Fallback to ingestion_id for backward compatibility
            parquet_path = DATA_DIR / f"{ingestion_id}.parquet"
            logger.info(f"Falling back to ingestion_id for parquet file: {ingestion_id}")
        
        if not os.path.exists(parquet_path):
            return {"error": "Ingestion data file not found"}
        
        # Read the parquet file metadata
        df = pd.read_parquet(parquet_path)
        
        # Get column info
        columns_info = []
        for column in df.columns:
            dtype = df[column].dtype
            
            # Determine field type
            if pd.api.types.is_integer_dtype(dtype):
                field_type = "integer"
            elif pd.api.types.is_float_dtype(dtype):
                field_type = "float"
            elif pd.api.types.is_bool_dtype(dtype):
                field_type = "boolean"
            elif pd.api.types.is_datetime64_dtype(dtype):
                field_type = "datetime"
            else:
                field_type = "string"
            
            # Check nullability - convert numpy.bool_ to Python bool
            nullable = bool(df[column].isna().any())
            
            # Get sample value
            sample = None
            non_null_values = df[column].dropna()
            if not non_null_values.empty:
                sample_value = non_null_values.iloc[0]
                
                # Convert NumPy types to Python native types
                if isinstance(sample_value, (np.integer, np.floating)):
                    sample = sample_value.item()  # Convert NumPy scalar to Python native type
                elif isinstance(sample_value, np.bool_):
                    sample = bool(sample_value)  # Convert NumPy boolean to Python boolean
                elif pd.api.types.is_datetime64_dtype(dtype):
                    sample = str(sample_value)
                elif isinstance(sample_value, np.ndarray):
                    sample = sample_value.tolist()  # Convert NumPy array to list
                elif isinstance(sample_value, pd.Timestamp):
                    sample = str(sample_value)
                else:
                    sample = sample_value
                    
            columns_info.append({
                "name": column,
                "dtype": str(dtype),
                "nullable": nullable,
                "sample": sample,
                "sample_type": type(sample).__name__
            })
        
        return {
            "columns_count": len(df.columns),
            "rows_count": len(df),
            "columns": columns_info
        }
    except Exception as e:
        return {"error": str(e)}

@router.get("/ingestion-statistics/{ingestion_id}", response_model=StatisticsResponse)
async def get_ingestion_statistics(
    ingestion_id: str,
    current_user: User = Depends(has_permission("datapuur:read")),  # Updated permission
    db: Session = Depends(get_db)
):
    """Get statistics for an ingestion"""
    job = get_ingestion_job(db, ingestion_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ingestion not found"
        )
    
    # Check if job is completed
    if job.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot get statistics for ingestion with status: {job.status}"
        )
    
    try:
        # Extract file_id from job config if available
        file_id = None
        if job.config:
            try:
                config = json.loads(job.config)
                file_id = config.get("file_id")
                if file_id:
                    logger.info(f"Found file_id {file_id} in job config for ingestion {ingestion_id}")
            except json.JSONDecodeError:
                logger.warning(f"Could not parse config JSON for ingestion {ingestion_id}")
        
        # Get the parquet file path using file_id if available
        if file_id:
            parquet_path = DATA_DIR / f"{file_id}.parquet"
            logger.info(f"Looking for parquet file with file_id: {file_id}")
        else:
            # Fallback to ingestion_id for backward compatibility
            parquet_path = DATA_DIR / f"{ingestion_id}.parquet"
            logger.info(f"Falling back to ingestion_id for parquet file: {ingestion_id}")
        
        if not os.path.exists(parquet_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ingestion data file not found"
            )
        
        # Read the parquet file
        df = pd.read_parquet(parquet_path)
        
        # Calculate statistics
        row_count = len(df)
        column_count = len(df.columns)
        
        # Calculate null percentage
        total_cells = row_count * column_count
        null_count = df.isna().sum().sum()
        null_percentage = (null_count / total_cells) * 100 if total_cells > 0 else 0
        
        # Convert null_percentage from NumPy type to Python native type if needed
        if isinstance(null_percentage, (np.integer, np.floating)):
            null_percentage = null_percentage.item()
        
        # Calculate memory usage
        memory_usage_bytes = df.memory_usage(deep=True).sum()
        if isinstance(memory_usage_bytes, (np.integer, np.floating)):
            memory_usage_bytes = memory_usage_bytes.item()
            
        if memory_usage_bytes < 1024:
            memory_usage = f"{memory_usage_bytes} B"
        elif memory_usage_bytes < 1024 * 1024:
            memory_usage = f"{memory_usage_bytes / 1024:.1f} KB"
        else:
            memory_usage = f"{memory_usage_bytes / (1024 * 1024):.1f} MB"
        
        # Get processing time from job
        processing_time = "Unknown"
        
        # Calculate data density (rows per KB)
        data_density = (row_count / (memory_usage_bytes / 1024)) if memory_usage_bytes > 0 else 0
        if isinstance(data_density, (np.integer, np.floating)):
            data_density = data_density.item()
            
        completion_rate = 100 - null_percentage
        if isinstance(completion_rate, (np.integer, np.floating)):
            completion_rate = completion_rate.item()
        
        return {
            "row_count": row_count,
            "column_count": column_count,
            "null_percentage": null_percentage,
            "memory_usage": memory_usage,
            "processing_time": processing_time,
            "data_density": data_density,
            "completion_rate": completion_rate,
            "error_rate": 0  # Placeholder, could be calculated from data quality checks
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating statistics: {str(e)}"
        )

@router.get("/ingestion-download/{ingestion_id}")
async def download_ingestion(
    ingestion_id: str,
    format: str = Query("csv", regex="^(csv|json|parquet)$"),
    current_user: User = Depends(has_permission("datapuur:read")),  # Updated permission
    db: Session = Depends(get_db)
):
    """Download ingestion data in specified format"""
    job = get_ingestion_job(db, ingestion_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ingestion not found"
        )
    
    # Check if job is completed
    if job.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot download ingestion with status: {job.status}"
        )
    
    try:
        # Extract file_id from job config if available
        file_id = None
        if job.config:
            try:
                config = json.loads(job.config)
                file_id = config.get("file_id")
                if file_id:
                    logger.info(f"Found file_id {file_id} in job config for ingestion {ingestion_id}")
            except json.JSONDecodeError:
                logger.warning(f"Could not parse config JSON for ingestion {ingestion_id}")
        
        # Get the parquet file path using file_id if available
        if file_id:
            parquet_path = DATA_DIR / f"{file_id}.parquet"
            logger.info(f"Looking for parquet file with file_id: {file_id}")
        else:
            # Fallback to ingestion_id for backward compatibility
            parquet_path = DATA_DIR / f"{ingestion_id}.parquet"
            logger.info(f"Falling back to ingestion_id for parquet file: {ingestion_id}")
        
        if not os.path.exists(parquet_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ingestion data file not found"
            )
        
        # Read the parquet file
        df = pd.read_parquet(parquet_path)
        
        # Create a temporary file for the download
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{format}") as temp_file:
            temp_path = temp_file.name
            
            # Convert to requested format
            if format == "csv":
                df.to_csv(temp_path, index=False)
                media_type = "text/csv"
            elif format == "json":
                df.to_json(temp_path, orient="records", lines=False)
                media_type = "application/json"
            else:  # parquet
                df.to_parquet(temp_path, index=False)
                media_type = "application/octet-stream"
        
        # Log activity
        log_activity(
            db=db,
            username=current_user.username,
            action="Ingestion download",
            details=f"Downloaded ingestion data: {job.name} ({format})"
        )
        
        # Return the file
        return FileResponse(
            path=temp_path,
            filename=f"{job.name}.{format}",
            media_type=media_type,
            background=BackgroundTasks().add_task(lambda: os.unlink(temp_path))
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error downloading ingestion: {str(e)}"
        )

# Original routes from the template - updated to use database
@router.get("/sources", response_model=List[DataSource])
async def get_data_sources(
    current_user: User = Depends(has_any_permission(["datapuur:read", "kginsights:read"])),
    db: Session = Depends(get_db)
):
    # Get real data sources from ingestion jobs
    sources = []
    
    # Query completed jobs
    completed_jobs = db.query(IngestionJob).filter(IngestionJob.status == "completed").all()
    
    # Add sources
    for job in completed_jobs:
        if job.type == "profile":
            continue
            
        # Get uploaded_by information based on job type
        uploaded_by = "Unknown"
        
        if job.type == "file":
            # For file-based ingestion: Try to find the file record that matches this job
            file_info = None
            if job.config:
                try:
                    config_data = json.loads(job.config)
                    if "file_id" in config_data:
                        file_info = db.query(UploadedFile).filter(UploadedFile.id == config_data["file_id"]).first()
                except json.JSONDecodeError:
                    pass
                    
            if file_info and file_info.uploaded_by:
                uploaded_by = file_info.uploaded_by
        else:
            # For database-based ingestion: Check activity log for who initiated this job
            activity = db.query(ActivityLog).filter(
                ActivityLog.action.like("Database ingestion started%"),
                ActivityLog.details.like(f"%{job.id}%")
            ).first()
            
            if activity and activity.username:
                uploaded_by = activity.username
            elif job.config:
                # Alternative: Check if username is stored in job config
                try:
                    config_data = json.loads(job.config)
                    if "username" in config_data:
                        uploaded_by = config_data["username"]
                except json.JSONDecodeError:
                    pass
                
        # Determine the last_updated timestamp based on job type
        # Ensure all timestamps are in the same format with timezone information
        file_info = None
        
        # Try to get file_info regardless of job type
        if job.config:
            try:
                config_data = json.loads(job.config)
                if "file_id" in config_data:
                    file_info = db.query(UploadedFile).filter(UploadedFile.id == config_data["file_id"]).first()
            except json.JSONDecodeError:
                pass
            
        # Determine the last_updated timestamp
        if file_info and file_info.uploaded_at:
            last_updated = file_info.uploaded_at.isoformat()
            dataset_value = file_info.dataset if hasattr(file_info, 'dataset') else None
        else:
            # Fall back to job timestamps if no file record is available
            if isinstance(job.end_time, datetime):
                dt = job.end_time
            elif job.end_time:
                # Try to parse the string as datetime if it's a string
                try:
                    dt = datetime.fromisoformat(job.end_time)
                except (ValueError, TypeError):
                    dt = job.start_time if isinstance(job.start_time, datetime) else datetime.now()
            else:
                dt = job.start_time if isinstance(job.start_time, datetime) else datetime.now()
                
            # Add timezone if missing
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
                
            last_updated = dt.isoformat()
            dataset_value = None
            
        # Create a name_for_display field that gets the dataset name from job name if dataset is None
        name_for_display = job.name
        
        # Extract dataset name from job configuration if available
        if job.type == "database" and job.config:
            try:
                config_data = json.loads(job.config)
                if "table" in config_data:
                    dataset_value = config_data["table"]
                    # Use table name as display name
                    name_for_display = dataset_value
            except json.JSONDecodeError:
                pass
        elif job.type == "file" and not dataset_value and job.name:
            # For file types without dataset, extract filename without extension
            dataset_value = os.path.splitext(job.name)[0]
            
        # Get file size and row count information
        file_size = 0
        row_count = None
        created_at = None
        
        # For file-based ingestion, get file size from the file_info
        if file_info and hasattr(file_info, 'path') and file_info.path and os.path.exists(file_info.path):
            try:
                file_size = os.path.getsize(file_info.path)
            except OSError:
                logger.warning(f"Could not get file size for {file_info.path}")
                
        # For both file and database ingestion, try to get row count from parquet file
        data_path = None
        if file_info:
            data_path = DATA_DIR / f"{file_info.id}.parquet"
        else:
            data_path = DATA_DIR / f"{job.id}.parquet"
            
        if data_path and data_path.exists():
            try:
                # Use pandas to get row count from parquet file
                import pandas as pd
                df = pd.read_parquet(data_path)
                row_count = len(df)
            except Exception as e:
                logger.warning(f"Could not get row count from parquet file: {str(e)}")
                
        # Set created_at from file_info or job start_time
        if file_info and file_info.uploaded_at:
            created_at = file_info.uploaded_at.isoformat()
        elif isinstance(job.start_time, datetime):
            created_at = job.start_time.isoformat()
        else:
            # Default to last_updated if no other timestamp is available
            created_at = last_updated
            
        sources.append(
            DataSource(
                id=file_info.id,
                name=name_for_display,
                type="File" if job.type == "file" else "Database",
                last_updated=last_updated,
                status="Active",
                uploaded_by=uploaded_by,
                dataset=dataset_value,
                file_size=file_size,  # Add file size
                row_count=row_count,  # Add row count
                created_at=created_at  # Add created date
            )
        )
    
    # If no sources, return empty list
    if not sources:
        return []
    
    return sources

@router.get("/sources/{source_id}", response_model=dict)
async def get_source_details(
    source_id: str,
    current_user: User = Depends(has_any_permission(["datapuur:read", "kginsights:read"])),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific data source by its ID.
    Includes file system information for direct access by authorized clients.
    """
    # Query the job
    job = db.query(IngestionJob).filter(IngestionJob.id == source_id).first()
    
    if not job:
        raise HTTPException(status_code=404, detail=f"Source not found with ID: {source_id}")
    
    # Extract config
    config = json.loads(job.config) if job.config and isinstance(job.config, str) else {}
    
    # Base source details
    source_details = {
        "id": job.id,
        "name": job.name,
        "type": job.type,
        "status": job.status,
        "created_at": job.start_time.isoformat() if isinstance(job.start_time, datetime) else job.start_time,
        "completed_at": job.end_time.isoformat() if isinstance(job.end_time, datetime) else job.end_time,
        "config": config
    }
    
    # For file-based sources, add all file details from the UploadedFile model
    if job.type == "file" and "file_id" in config:
        file_id = config["file_id"]
        file_info = db.query(UploadedFile).filter(UploadedFile.id == file_id).first()
        
        if file_info:
            # Add all file details from the UploadedFile model
            source_details["file"] = {
                "id": file_info.id,
                "filename": file_info.filename,
                "dataset": file_info.dataset,
                "path": file_info.path,
                "type": file_info.type,
                "uploaded_by": file_info.uploaded_by,
                "uploaded_at": file_info.uploaded_at.astimezone(timezone.utc).isoformat() if isinstance(file_info.uploaded_at, datetime) else file_info.uploaded_at,
                "chunk_size": file_info.chunk_size,
                "schema": file_info.schema
            }
    
    # For database sources, add database details and file info if available
    elif job.type == "database" and config:
        source_details["database"] = {
            "type": config.get("type", "unknown"),
            "name": config.get("database", "unknown"),
            "table": config.get("table", "unknown")
        }
        
        # Add file details for database sources if available (from our new fix)
        if "file_id" in config:
            file_id = config["file_id"]
            file_info = db.query(UploadedFile).filter(UploadedFile.id == file_id).first()
            
            if file_info:
                # Add file details for database sources too for consistency
                source_details["file"] = {
                    "id": file_info.id,
                    "filename": file_info.filename,
                    "dataset": file_info.dataset,
                    "path": file_info.path,
                    "type": file_info.type,
                    "uploaded_by": file_info.uploaded_by,
                    "uploaded_at": file_info.uploaded_at.astimezone(timezone.utc).isoformat() if isinstance(file_info.uploaded_at, datetime) else file_info.uploaded_at,
                    "chunk_size": file_info.chunk_size,
                    "schema": file_info.schema
                }
    
    # Log this access for security monitoring
    log_activity(db, current_user.username, "Data access", f"Accessed detailed source information for {job.name} (ID: {source_id})")
    
    return source_details

@router.get("/metrics", response_model=DataMetrics)
async def get_data_metrics(
    current_user: User = Depends(has_permission("datapuur:read")),  # Updated permission
    db: Session = Depends(get_db)
):
    # Calculate real metrics from ingestion jobs
    total_records = 0
    processed_records = 0
    failed_records = 0
    
    # Query jobs
    completed_jobs = db.query(IngestionJob).filter(IngestionJob.status == "completed").all()
    failed_jobs = db.query(IngestionJob).filter(IngestionJob.status == "failed").all()
    
    # Estimate records based on job type
    for job in completed_jobs:
        # In a real system, you would get actual record counts
        # Here we're just estimating based on job type
        if job.type == "file":
            total_records += 10000
            processed_records += 10000
        elif job.type == "database":
            total_records += 5000
            processed_records += 5000
        
    # Estimate failed records
    for job in failed_jobs:
        if job.type == "file":
            total_records += 10000
            failed_records += 10000
        elif job.type == "database":
            total_records += 5000
            failed_records += 5000
    
    # If no metrics, return default values
    if total_records == 0:
        return DataMetrics(
            total_records=0,
            processed_records=0,
            failed_records=0,
            processing_time=0.0
        )
    
    return DataMetrics(
        total_records=total_records,
        processed_records=processed_records,
        failed_records=failed_records,
        processing_time=0.0
    )

@router.get("/activities", response_model=List[Activity])
async def get_activities(
    current_user: User = Depends(has_permission("datapuur:read")),  # Updated permission
    db: Session = Depends(get_db)
):
    # Get real activities from ingestion jobs
    activities = []
    
    # Query jobs
    jobs = db.query(IngestionJob).all()
    
    # Add job activities
    for job in jobs:
        status = "success" if job.status == "completed" else "error" if job.status == "failed" else "processing"
        
        activities.append(
            Activity(
                id=job.id,
                action=f"{job.type.capitalize()} ingestion: {job.name}",
                time=job.start_time.strftime("%Y-%m-%d %H:%M:%S") if isinstance(job.start_time, datetime) else job.start_time,
                status=status
            )
        )
    
    # Sort activities by time (most recent first)
    sorted_activities = sorted(
        activities, 
        key=lambda x: x.time, 
        reverse=True
    )
    
    return sorted_activities

@router.get("/dashboard", response_model=Dict[str, Any])
async def get_dashboard_data(
    current_user: User = Depends(has_permission("datapuur:read")),  # Updated permission
    db: Session = Depends(get_db)
):
    # Get real metrics and activities
    metrics = await get_data_metrics(current_user, db)
    activities = await get_activities(current_user, db)
    
    # Query jobs
    completed_jobs = db.query(IngestionJob).filter(IngestionJob.status == "completed").all()
    failed_jobs = db.query(IngestionJob).filter(IngestionJob.status == "failed").all()
    running_jobs = db.query(IngestionJob).filter(IngestionJob.status == "running").all()
    
    # Get all jobs except failed ones for the dashboard
    valid_jobs = db.query(IngestionJob).filter(IngestionJob.status != "failed").all()
    
    # Count job types - only count completed jobs
    file_jobs = len([job for job in completed_jobs if job.type == "file"])
    db_jobs = len([job for job in completed_jobs if job.type == "database"])
    
    # Create chart data
    chart_data = {
        "bar_chart": [
            file_jobs * 10, 
            db_jobs * 10, 
            0,  # No API jobs 
            len(completed_jobs) * 10, 
            len(failed_jobs) * 10, 
            len(running_jobs) * 10, 
            len(valid_jobs) * 5  # Use valid_jobs instead of all_jobs
        ],
        "pie_chart": [
            {"label": "File", "value": max(file_jobs, 1), "color": "#8B5CF6"},
            {"label": "Database", "value": max(db_jobs, 1), "color": "#EC4899"},
            {"label": "Other", "value": 1, "color": "#10B981"}
        ],
        "line_chart": {
            "current": [
                len(completed_jobs), 
                len(completed_jobs) + len(running_jobs), 
                len(valid_jobs), 
                len(valid_jobs) + 2, 
                len(valid_jobs) + 5,
                len(valid_jobs) + 7
            ],
            "previous": [
                max(len(completed_jobs) - 2, 0), 
                max(len(completed_jobs) + len(running_jobs) - 3, 0), 
                max(len(valid_jobs) - 4, 0), 
                max(len(valid_jobs) - 3, 0), 
                max(len(valid_jobs) - 1, 0),
                max(len(valid_jobs), 0)
            ]
        }
    }
    
    return {
        "metrics": metrics.dict(),
        "recent_activities": [a.dict() for a in sorted(
            activities, 
            key=lambda x: x.time, 
            reverse=True
        )[:4]],
        "chart_data": chart_data
    }

@router.get("/file-history", status_code=status.HTTP_200_OK)
async def get_file_history(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(has_permission("datapuur:read")),  # Updated permission
    db: Session = Depends(get_db)
):
    """Get history of uploaded files"""
    try:
        # Build query
        query = db.query(UploadedFile)
        
        # Apply sorting (newest first)
        query = query.order_by(UploadedFile.uploaded_at.desc())
        
        # Get total count
        total_files = query.count()
        
        # Apply pagination
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)
        
        # Execute query
        files = query.all()
        
        # Convert to response format
        paginated_files = []
        for file in files:
            paginated_files.append({
                "id": file.id,
                "filename": file.filename,
                "type": file.type,
                "size": os.path.getsize(file.path) if os.path.exists(file.path) else 0,
                "uploaded_at": file.uploaded_at.astimezone(timezone.utc).isoformat() if isinstance(file.uploaded_at, datetime) else file.uploaded_at,
                "uploaded_by": file.uploaded_by,
                "preview_url": f"/api/datapuur/preview/{file.id}",
                "download_url": f"/api/datapuur/download/{file.id}",
                "status": "available"
            })
        
        # Log activity
        log_activity(
            db=db,
            username=current_user.username,
            action="View file history",
            details=f"Viewed file upload history (page {page})"
        )
        
        return {
            "files": paginated_files,
            "total": total_files,
            "page": page,
            "limit": limit
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching file history: {str(e)}"
        )

@router.get("/preview/{file_id}", status_code=status.HTTP_200_OK)
async def preview_file(
    file_id: str,
    current_user: User = Depends(has_permission("datapuur:read")),  # Updated permission
    db: Session = Depends(get_db)
):
    """Preview a file"""
    # First try to find the file directly using the file_id as an UploadedFile.id
    print(file_id)
    file_info = get_uploaded_file(db, file_id)
    
    # Only print file_info details if it exists
    if file_info:
        logger.debug(f"Found file_info: {file_info.id}")
        logger.debug(f"filename: {file_info.filename}")
        logger.debug(f"path: {file_info.path}")
        logger.debug(f"type: {file_info.type}")
    else:
        logger.debug(f"No file found with ID: {file_id}, will try to find ingestion job")

    # If not found, check if the file_id is an IngestionJob.id
    if not file_info:
        # Try to find the ingestion job
        job = db.query(IngestionJob).filter(IngestionJob.id == file_id).first()
        
        if job and job.config:
            try:
                # Extract file_id from job config
                config_data = json.loads(job.config)
                if "file_id" in config_data:
                    # Get the file using the file_id from the job config
                    file_info = get_uploaded_file(db, config_data["file_id"])
            except json.JSONDecodeError:
                logger.warning(f"Could not parse job config for job {file_id}")
    
    # If still not found, return 404
    if not file_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    file_path = file_info.path
    
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on disk"
        )
    
    try:
        # For parquet files
        if file_info.type == "parquet" or file_path.endswith(".parquet"):
            try:
                # Use pandas to efficiently read only the first 100 rows
                df = pd.read_parquet(file_path, engine="pyarrow")
                df = df.head(100)  # Limit to first 100 rows
                
                # Convert to list format for response
                headers = df.columns.tolist()
                # Convert NumPy types to Python native types
                rows = []
                for row in df.values:
                    python_row = []
                    for item in row:
                        if pd.isna(item):
                            python_row.append(None)
                        elif isinstance(item, (np.integer, np.floating)):
                            python_row.append(item.item())
                        else:
                            python_row.append(item)
                    rows.append(python_row)
                
                # Log activity
                log_activity(
                    db=db,
                    username=current_user.username,
                    action="File preview",
                    details=f"Previewed parquet file: {file_info.filename}"
                )
                
                return {
                    "data": rows,
                    "headers": headers,
                    "filename": file_info.filename,
                    "type": "parquet"
                }
            except Exception as e:
                logger.error(f"Error previewing parquet file: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error previewing parquet file: {str(e)}"
                )
        
        # For CSV files
        elif file_info.type == "csv":
            try:
                # Use pandas to efficiently read only the first 100 rows
                # This is much more memory-efficient for large files
                df = pd.read_csv(file_path, nrows=100)
                
                # Convert to list format for response
                headers = df.columns.tolist()
                # Convert NumPy types to Python native types
                rows = []
                for row in df.values:
                    python_row = []
                    for item in row:
                        if pd.isna(item):
                            python_row.append(None)
                        elif isinstance(item, (np.integer, np.floating)):
                            python_row.append(item.item())
                        else:
                            python_row.append(item)
                    rows.append(python_row)
                
                # Log activity
                log_activity(
                    db=db,
                    username=current_user.username,
                    action="File preview",
                    details=f"Previewed file: {file_info.filename}"
                )
                
                return {
                    "data": rows,
                    "headers": headers,
                    "filename": file_info.filename,
                    "type": "csv"
                }
            except pd.errors.EmptyDataError:
                # Handle empty CSV files
                return {
                    "data": [],  # Empty array
                    "headers": [],
                    "filename": file_info.filename,
                    "type": "csv"
                }
            except Exception as e:
                print("Exception", e)
                # If pandas fails (which is unlikely), fall back to a more robust method
                # for extremely large files using csv module with iteration
                logger.warning(f"Pandas CSV preview failed, falling back to csv module: {str(e)}")
                with open(file_path, 'r', newline='', encoding='utf-8', errors='replace') as csvfile:
                    # Use csv.reader with iteration to avoid loading the entire file
                    reader = csv.reader(csvfile)
                    try:
                        headers = next(reader)
                    except StopIteration:
                        headers = []
                    
                    rows = []
                    for i, row in enumerate(reader):
                        if i >= 100:  # Limit to 100 rows
                            break
                        rows.append(row)
                
                return {
                    "data": rows,
                    "headers": headers,
                    "filename": file_info.filename,
                    "type": "csv"
                }
        
        # For JSON files
        elif file_info.type == "json":
            try:
                # For large JSON files, we need to be careful about memory usage
                # Read the file in chunks and only process the beginning
                with open(file_path, 'r', encoding='utf-8', errors='replace') as jsonfile:
                    # Try to parse the JSON data
                    try:
                        data = json.load(jsonfile)
                    except json.JSONDecodeError as e:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Invalid JSON file: {str(e)}"
                        )
                
                # Function to flatten nested JSON
                def flatten_json(nested_json, prefix=''):
                    flattened = {}
                    for key, value in nested_json.items():
                        if isinstance(value, dict):
                            # Recursively flatten nested dictionaries
                            flattened.update(flatten_json(value, f"{prefix}{key}_"))
                        elif isinstance(value, list):
                            # Handle lists by converting them to strings if they contain simple types
                            # or by flattening if they contain dictionaries
                            if all(not isinstance(item, dict) for item in value):
                                # For lists of simple types, convert to string
                                flattened[f"{prefix}{key}"] = str(value)
                            else:
                                # For lists of dictionaries, flatten each item
                                for i, item in enumerate(value):
                                    if isinstance(item, dict):
                                        flattened.update(flatten_json(item, f"{prefix}{key}_{i}_"))
                                    else:
                                        flattened[f"{prefix}{key}_{i}"] = item
                        else:
                            # For simple types, just add them with the prefix
                            flattened[f"{prefix}{key}"] = value
                    return flattened
                
                # If it's an array, limit to first 100 items and flatten each item
                if isinstance(data, list):
                    limited_data = data[:100]  # Limit to first 100 items
                    flattened_data = []
                    for item in limited_data:
                        if isinstance(item, dict):
                            flattened_data.append(flatten_json(item))
                        else:
                            flattened_data.append({"value": item})
                # If it's a single object, flatten it
                elif isinstance(data, dict):
                    flattened_data = [flatten_json(data)]
                else:
                    flattened_data = [{"value": data}]
                
                # Log activity
                log_activity(
                    db=db,
                    username=current_user.username,
                    action="File preview",
                    details=f"Previewed file: {file_info.filename}"
                )
                
                # Convert to DataFrame to get headers and rows for consistent display
                df = pd.DataFrame(flattened_data)
                
                # Return data in a format similar to CSV preview
                return {
                    "data": df.values.tolist() if not df.empty else [],
                    "headers": df.columns.tolist(),
                    "filename": file_info.filename,
                    "type": "json"
                }
            except Exception as e:
                logger.error(f"Error previewing JSON file: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error previewing JSON file: {str(e)}"
                )
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported file type for preview"
            )
    
    except Exception as e:
        print(f"Error previewing file: {str(e)}")
        print(f"File info: {file_info}")
        print(f"File path: {file_path}")
        print(f"Exception details: {traceback.format_exc()}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error previewing file: {str(e)}"
        )

@router.get("/download/{file_id}", status_code=status.HTTP_200_OK)
async def download_file(
    file_id: str,
    current_user: User = Depends(has_permission("datapuur:read")),  # Updated permission
    db: Session = Depends(get_db)
):
    """Download a file"""
    # First try to find the file directly using the file_id as an UploadedFile.id
    file_info = get_uploaded_file(db, file_id)
    
    # If not found, check if the file_id is an IngestionJob.id
    if not file_info:
        # Try to find the ingestion job
        job = db.query(IngestionJob).filter(IngestionJob.id == file_id).first()
        
        if job and job.config:
            try:
                # Extract file_id from job config
                config_data = json.loads(job.config)
                if "file_id" in config_data:
                    # Get the file using the file_id from the job config
                    file_info = get_uploaded_file(db, config_data["file_id"])
            except json.JSONDecodeError:
                logger.warning(f"Could not parse job config for job {file_id}")
    
    # If still not found, return 404
    if not file_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    file_path = file_info.path
    
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on disk"
        )
    
    try:
        # Log activity
        log_activity(
            db=db,
            username=current_user.username,
            action="File download",
            details=f"Downloaded file: {file_info.filename}"
        )
        
        return FileResponse(
            path=file_path,
            filename=file_info.filename,
            media_type="application/octet-stream"
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error downloading file: {str(e)}"
        )

# Add new endpoint for chunked uploads
@router.post("/upload-chunk", status_code=status.HTTP_200_OK)
async def upload_chunk(
    file: UploadFile = File(...),
    chunkSize: int = Form(1000),
    chunkIndex: int = Form(...),
    totalChunks: int = Form(...),
    uploadId: str = Form(...),
    current_user: User = Depends(has_permission("datapuur:write")),  # Updated permission
    db: Session = Depends(get_db)
):
    """Upload a chunk of a large file"""
    logger.info(f"Received chunk {chunkIndex + 1} of {totalChunks} for upload ID: {uploadId}")
    
    # Create a directory for this upload if it doesn't exist
    chunks_dir = UPLOAD_DIR / "chunks" / uploadId
    
    try:
        # Ensure the upload directory exists
        if not UPLOAD_DIR.exists():
            logger.info(f"Creating upload directory: {UPLOAD_DIR}")
            UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

         # Ensure the chunks parent directory exists
        chunks_parent = UPLOAD_DIR / "chunks"
        if not chunks_parent.exists():
            logger.info(f"Creating chunks parent directory: {chunks_parent}")
            chunks_parent.mkdir(parents=True, exist_ok=True)
        
        # Create the specific chunks directory for this upload
        if not chunks_dir.exists():
            logger.info(f"Creating chunks directory for upload ID {uploadId}: {chunks_dir}")
            chunks_dir.mkdir(parents=True, exist_ok=True)
        
        # Log the directory structure
        logger.info(f"Directory structure: UPLOAD_DIR={UPLOAD_DIR}, chunks_parent={chunks_parent}, chunks_dir={chunks_dir}")
        
        # Save the chunk
        chunk_path = chunks_dir / f"chunk_{chunkIndex}"
        logger.info(f"Saving chunk {chunkIndex + 1} to {chunk_path}")
        
        with open(chunk_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Verify the chunk was saved correctly
        if not chunk_path.exists():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save chunk {chunkIndex + 1}: File not found after save"
            )
        
        chunk_size = os.path.getsize(chunk_path)
        logger.info(f"Chunk {chunkIndex + 1} saved successfully, size: {chunk_size} bytes")
        
    except Exception as e:
        logger.error(f"Error saving chunk {chunkIndex + 1}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving chunk: {str(e)}"
        )
    finally:
        file.file.close()
    
    return {"message": f"Chunk {chunkIndex + 1} of {totalChunks} uploaded successfully"}

@router.get("/file-schema/{file_id}", response_model=SchemaResponse)
async def get_file_schema(
    file_id: str,
    current_user: User = Depends(has_permission("datapuur:read")),
    db: Session = Depends(get_db)
):
    """Get schema for a file based on file_id"""
    file_info = get_uploaded_file(db, file_id)
    if not file_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    file_path = file_info.path
    
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on disk"
        )
    
    try:
        fields = []
        sample_values = []
        
        # For CSV files
        if file_info.type.lower() == "csv":
            # Use pandas to read the file and extract schema
            df = pd.read_csv(file_path, nrows=5)  # Only need a few rows to get schema
            
            for column in df.columns:
                dtype = df[column].dtype
                
                # Determine field type
                if pd.api.types.is_integer_dtype(dtype):
                    field_type = "integer"
                elif pd.api.types.is_float_dtype(dtype):
                    field_type = "float"
                elif pd.api.types.is_bool_dtype(dtype):
                    field_type = "boolean"
                elif pd.api.types.is_datetime64_dtype(dtype):
                    field_type = "datetime"
                else:
                    field_type = "string"
                
                # Check nullability
                nullable = bool(df[column].isna().any())
                
                # Get sample value
                sample = None
                non_null_values = df[column].dropna()
                if not non_null_values.empty:
                    sample_value = non_null_values.iloc[0]
                    
                    # Convert NumPy types to Python native types
                    if isinstance(sample_value, (np.integer, np.floating)):
                        sample = sample_value.item()  # Convert NumPy scalar to Python native type
                    elif isinstance(sample_value, np.bool_):
                        sample = bool(sample_value)  # Convert NumPy boolean to Python boolean
                    elif pd.api.types.is_datetime64_dtype(dtype):
                        sample = str(sample_value)
                    elif isinstance(sample_value, np.ndarray):
                        sample = sample_value.tolist()  # Convert NumPy array to list
                    elif isinstance(sample_value, pd.Timestamp):
                        sample = str(sample_value)
                    else:
                        sample = sample_value
                        
                fields.append({
                    "name": column,
                    "type": field_type,
                    "nullable": nullable
                })
                
                sample_values.append(sample)
        
        # For JSON files
        elif file_info.type.lower() == "json":
            with open(file_path, 'r', encoding='utf-8', errors='replace') as jsonfile:
                try:
                    data = json.load(jsonfile)
                    
                    # If the data is a list of objects, infer schema from the first item
                    if isinstance(data, list) and data and isinstance(data[0], dict):
                        first_item = data[0]
                        for key, value in first_item.items():
                            field_type = "string"
                            if isinstance(value, int):
                                field_type = "integer"
                            elif isinstance(value, float):
                                field_type = "float"
                            elif isinstance(value, bool):
                                field_type = "boolean"
                                
                            fields.append({
                                "name": key,
                                "type": field_type,
                                "nullable": True  # Assume nullable for JSON
                            })
                            
                            sample_values.append(value)
                    else:
                        # For simple JSON or complex nested structures, provide basic info
                        fields.append({
                            "name": "json_content",
                            "type": "object",
                            "nullable": False
                        })
                        sample_values.append(None)
                        
                except json.JSONDecodeError as e:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid JSON file: {str(e)}"
                    )
        
        # Log the schema data being returned
        logger.info(f"Schema data for file {file_id}: {len(fields)} fields")
        
        # Return schema data - ensure all NumPy types are converted to Python native types
        def convert_numpy_types(obj):
            if isinstance(obj, np.bool_):
                return bool(obj)
            elif isinstance(obj, (np.integer, np.floating)):
                return obj.item()
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, dict):
                return {k: convert_numpy_types(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy_types(i) for i in obj]
            else:
                return obj
                
        # Apply conversion to both fields and sample_values
        converted_fields = convert_numpy_types(fields)
        converted_sample_values = convert_numpy_types(sample_values)
        
        # Log activity
        log_activity(
            db=db,
            username=current_user.username,
            action="Get file schema",
            details=f"Retrieved schema for file: {file_info.filename}"
        )
        
        return {
            "fields": converted_fields,
            "sample_values": converted_sample_values,
            "file_id": file_id,
            "file_name": file_info.filename
        }
    except Exception as e:
        logger.error(f"Error generating schema for file {file_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating schema: {str(e)}"
        )


@router.get("/source-file/{file_id}", status_code=status.HTTP_200_OK)
async def get_source_file_details(
    file_id: str,
    current_user: User = Depends(has_permission("datapuur:read")),
    db: Session = Depends(get_db)
):
    """
    Get source file details by file_id for knowledge graph generation
    """
    try:
        # Get file info from database
        file_info = db.query(UploadedFile).filter(UploadedFile.id == file_id).first()
        
        if not file_info:
            raise HTTPException(status_code=404, detail=f"File with ID {file_id} not found")
        
        # Get file path
        file_path = file_info.path
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"File not found at {file_path}")
        
        # Build response with necessary details for KG generation
        response = {
            "id": file_info.id,
            "filename": file_info.filename,
            "filepath": file_info.path,
            "full_path": file_path,
            "file_type": file_info.type,
            "uploaded_by": file_info.uploaded_by,
            "uploaded_at": file_info.uploaded_at,
            "status": "available"
        }
        
        # Log activity
        log_activity(
            db=db,
            username=current_user.username,
            action="Get source file details",
            details=f"Retrieved file details for KG generation: {file_info.filename}"
        )
        
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving source file details: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get file details: {str(e)}")


@router.post("/complete-chunked-upload", status_code=status.HTTP_200_OK)
async def complete_chunked_upload(
    request: Request,
    current_user: User = Depends(has_permission("datapuur:write")),  # Updated permission
    db: Session = Depends(get_db)
):
    """Complete a chunked upload by combining all chunks into a single file"""
    # Parse request body
    try:
        data = await request.json()
        upload_id = data.get("uploadId")
        file_name = data.get("fileName")
        total_chunks = data.get("totalChunks")
        chunk_size = data.get("chunkSize")
        original_chunk_size = data.get("originalChunkSize", 1000)
        
        logger.info(f"Starting chunked upload completion for {file_name}, ID: {upload_id}, chunks: {total_chunks}")
        
        if not all([upload_id, file_name, total_chunks, chunk_size]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required parameters"
            )
        
        # Check if this upload was cancelled
        cancel_marker = UPLOAD_DIR / f"cancel_{upload_id}"
        if cancel_marker.exists():
            # The upload was cancelled, clean up any chunks and return appropriate response
            chunks_dir = UPLOAD_DIR / "chunks" / upload_id
            if chunks_dir.exists():
                try:
                    shutil.rmtree(chunks_dir)
                except Exception as e:
                    logger.error(f"Error cleaning up chunks after cancellation: {str(e)}")
            
            # Remove the cancellation marker
            try:
                os.remove(cancel_marker)
            except Exception as e:
                logger.error(f"Error removing cancellation marker: {str(e)}")
            
            # Return a response indicating the upload was cancelled
            return {"cancelled": True, "message": "Upload was cancelled by the user"}
        
        # Get file extension
        file_ext = file_name.split('.')[-1].lower()
        if file_ext not in ['csv', 'json']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only CSV and JSON files are supported"
            )
        
        # Generate a unique file ID
        file_id = str(uuid.uuid4())
        file_path = UPLOAD_DIR / f"{file_id}.{file_ext}"
        
        # Combine chunks into a single file
        chunks_dir = UPLOAD_DIR / "chunks" / upload_id
        
        # Check if chunks directory exists
        if not chunks_dir.exists():
            # Check all possible paths that might have been used
            alternative_paths = [
                UPLOAD_DIR / f"chunks_{upload_id}",  # Old format
                UPLOAD_DIR / upload_id,              # Another possible format
                UPLOAD_DIR / "chunks" / upload_id    # Current format
            ]
            
            found_dir = None
            for path in alternative_paths:
                if path.exists():
                    logger.info(f"Found chunks directory at alternative path: {path}")
                    found_dir = path
                    chunks_dir = path
                    break
            
            if found_dir is None:
                # Check if this was a cancelled upload
                if cancel_marker.exists():
                    try:
                        os.remove(cancel_marker)
                    except Exception as e:
                        logger.error(f"Error removing cancellation marker: {str(e)}")
                    return {"cancelled": True, "message": "Upload was cancelled by the user"}
                else:
                    # List all directories in UPLOAD_DIR to help debug
                    try:
                        upload_contents = list(UPLOAD_DIR.iterdir())
                        chunks_parent = UPLOAD_DIR / "chunks"
                        chunks_contents = list(chunks_parent.iterdir()) if chunks_parent.exists() else []
                        
                        logger.error(f"Chunks directory not found at {chunks_dir}")
                        logger.error(f"UPLOAD_DIR contents: {upload_contents}")
                        logger.error(f"Chunks parent directory exists: {chunks_parent.exists()}")
                        if chunks_parent.exists():
                            logger.error(f"Chunks parent directory contents: {chunks_contents}")
                    except Exception as e:
                        logger.error(f"Error listing directory contents: {str(e)}")
                    
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Chunks directory not found. Upload may have been cancelled or failed."
                    )
        
        logger.info(f"Found chunks directory for {upload_id}, combining {total_chunks} chunks")
        
        # Check if all chunks exist before starting to combine them
        for i in range(total_chunks):
            chunk_path = chunks_dir / f"chunk_{i}"
            if not chunk_path.exists():
                # Check if this was a cancelled upload
                if cancel_marker.exists():
                    try:
                        os.remove(cancel_marker)
                    except Exception as e:
                        logger.error(f"Error removing cancellation marker: {str(e)}")
                    return {"cancelled": True, "message": "Upload was cancelled by the user"}
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Chunk {i + 1} is missing"
                    )
        
        # Now that we've verified all chunks exist, combine them
        try:
            # Use buffered I/O for better performance with large files
            with open(file_path, "wb", buffering=8192) as outfile:
                for i in range(total_chunks):
                    chunk_path = chunks_dir / f"chunk_{i}"
                    logger.info(f"Processing chunk {i+1}/{total_chunks} from {chunk_path}")
                    
                    # Use buffered reading for better performance
                    with open(chunk_path, "rb", buffering=8192) as infile:
                        # Copy in smaller chunks to avoid memory issues
                        bytes_copied = 0
                        while True:
                            buffer = infile.read(1024 * 1024)  # Read 1MB at a time
                            if not buffer:
                                break
                            outfile.write(buffer)
                            bytes_copied += len(buffer)
                        logger.info(f"Copied {bytes_copied} bytes from chunk {i+1}")
            
            logger.info(f"All chunks combined successfully into {file_path}")
            
            # Clean up chunks
            try:
                shutil.rmtree(chunks_dir)
                logger.info(f"Cleaned up chunks directory {chunks_dir}")
            except Exception as e:
                logger.warning(f"Failed to clean up chunks directory: {str(e)}")
            
            # Get actual file size
            actual_file_size = os.path.getsize(file_path)
            logger.info(f"Final file size: {actual_file_size} bytes")
            
            # Store file info in database
            file_data = {
                "filename": file_name,
                "path": str(file_path),
                "type": file_ext,
                "uploaded_by": current_user.username,
                "uploaded_at": datetime.now(timezone.utc),
                "chunk_size": original_chunk_size
            }
            
            try:
                save_uploaded_file(db, file_id, file_data)
                logger.info(f"File information saved to database with ID {file_id}")
            except Exception as db_error:
                logger.error(f"Database error while saving file info: {str(db_error)}")
                raise
            
            # Log activity
            try:
                log_activity(
                    db=db,
                    username=current_user.username,
                    action="File upload (chunked)",
                    details=f"Uploaded file: {file_name} ({file_ext.upper()}) using chunked upload"
                )
                logger.info(f"Activity logged for chunked upload of {file_name}")
            except Exception as log_error:
                logger.error(f"Error logging activity: {str(log_error)}")
                # Don't raise here, as the file is already saved
            
            return {"file_id": file_id, "message": "File uploaded successfully"}
            
        except Exception as combine_error:
            logger.error(f"Error while combining chunks: {str(combine_error)}")
            # Re-raise to be caught by the outer exception handler
            raise
            
    except Exception as e:
        error_msg = str(e) if str(e) else repr(e)
        logger.error(f"Error completing chunked upload: {error_msg}", exc_info=True)
        # Clean up any partial files
        try:
            if 'file_path' in locals() and file_path.exists():
                os.remove(file_path)
                logger.info(f"Cleaned up partial file {file_path}")
        except Exception as cleanup_error:
            logger.error(f"Error during cleanup after failure: {str(cleanup_error)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error completing chunked upload: {error_msg}"
        )

# Add endpoint for cancelling chunked uploads
@router.post("/cancel-chunked-upload", status_code=status.HTTP_200_OK)
async def cancel_chunked_upload(
    request: Request,
    current_user: User = Depends(has_permission("datapuur:write")),  # Updated permission
    db: Session = Depends(get_db)
):
    """Cancel a chunked upload by removing all uploaded chunks"""
    # Parse the request body
    body = await request.json()
    upload_id = body.get("uploadId")
    
    if not upload_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload ID is required"
        )
    
    # Create the chunks directory path based on the upload ID
    chunks_dir = UPLOAD_DIR / "chunks" / upload_id
    
    # Check if the chunks directory exists
    if chunks_dir.exists():
        try:
            # Remove all chunks
            shutil.rmtree(chunks_dir)
            
            # Create a cancellation marker file to signal to any ongoing processes that they should stop
            # This will be checked by the complete_chunked_upload endpoint
            cancel_marker = UPLOAD_DIR / f"cancel_{upload_id}"
            with open(cancel_marker, 'w') as f:
                f.write('cancelled')
            
            # Log activity
            log_activity(
                db=db,
                username=current_user.username,
                action="Upload cancelled",
                details=f"Cancelled chunked upload: {upload_id}"
            )
            
            return {"success": True, "message": "Upload cancelled successfully"}
        except Exception as e:
            logger.error(f"Error cancelling chunked upload: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error cancelling upload: {str(e)}"
            )
    else:
        # If the directory doesn't exist, the upload might have been completed or never started
        # Still create a cancellation marker to prevent any pending processing
        try:
            cancel_marker = UPLOAD_DIR / f"cancel_{upload_id}"
            with open(cancel_marker, 'w') as f:
                f.write('cancelled')
            return {"success": True, "message": "No active upload found with this ID"}
        except Exception as e:
            logger.error(f"Error creating cancellation marker: {str(e)}")
            return {"success": True, "message": "No active upload found with this ID"}

# Delete a dataset
@router.delete("/delete-file/{file_id}")
def delete_file_endpoint(
    file_id: str,
    current_user: User = Depends(has_permission("datapuur:manage")),
    db: Session = Depends(get_db)
):
    """
    Delete a file and its associated datasets by file_id.
    
    This endpoint requires the 'datapuur:manage' permission, which is restricted
    to admin role.
    """
    try:
        # Find the job associated with this file_id
        from sqlalchemy import desc
        file_info = get_uploaded_file(db, file_id)
        if not file_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
            
        # Log the activity
        log_activity(
            db=db,
            username=current_user.username,
            action="Delete file",
            details=f"Deleting file with ID: {file_id}"
        )
        
        # Look for jobs with this file_id in their config
        jobs = db.query(IngestionJob)\
            .filter(IngestionJob.type == "file")\
            .all()
            
        # Find the job(s) with this file_id in config
        deleted_job_ids = []
        for job in jobs:
            if not job.config:
                continue
            
            try:
                config = json.loads(job.config)
                if config.get("file_id") == file_id:
                    # Call the delete function for each matching job
                    success, message = delete_dataset(db, job.id)
                    if success:
                        deleted_job_ids.append(job.id)
            except json.JSONDecodeError:
                continue
        
        if not deleted_job_ids:
            # Even if no jobs found, try to delete the file record directly
            if file_info:
                db.delete(file_info)
                db.commit()
                return {"success": True, "message": "File record deleted successfully"}
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No datasets found associated with this file"
                )
        
        return {
            "success": True, 
            "message": f"Successfully deleted file and {len(deleted_job_ids)} associated datasets",
            "deleted_job_ids": deleted_job_ids
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting file: {str(e)}"
        )

@router.delete("/delete-dataset/{dataset_id}")
def delete_dataset_endpoint(
    dataset_id: str,
    current_user: User = Depends(has_permission("datapuur:manage")),  # Updated permission
    db: Session = Depends(get_db)
):
    """
    Delete a dataset and all its associated data.
    
    This endpoint requires the 'datapuur:manage' permission, which is restricted
    to admin role.
    """
    # Log the activity
    log_activity(
        db=db,
        username=current_user.username,
        action="Delete dataset",
        details=f"Deleted dataset with ID: {dataset_id}"
    )
    
    # Call the delete function
    success, message = delete_dataset(db, dataset_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if "not found" in message.lower() 
            else status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=message
        )
    
    return {"success": True, "message": message}

# Create data directory if it doesn't exist
DATA_DIR.mkdir(exist_ok=True)

# Schema for creating a job
class CreateJobRequest(BaseModel):
    job_id: str
    job_type: str
    status: str = "completed"
    details: Dict = {}
    name: Optional[str] = None
    progress: Optional[int] = 100
    error: Optional[str] = None
    config: Optional[Dict] = None

@router.post("/create-job", status_code=status.HTTP_201_CREATED)
async def create_job(
    request: CreateJobRequest,
    current_user: User = Depends(has_permission("datapuur:write")),  # Using write permission
    db: Session = Depends(get_db)
):
    """Create a job entry in the system for tracking purposes"""
    try:
        # Generate timestamps
        now = datetime.now().isoformat()
        
        # Prepare job data
        job_data = {
            "name": request.name or f"{request.job_type.capitalize()} Job",
            "type": request.job_type,
            "status": request.status,
            "progress": request.progress,
            "start_time": now,
            "end_time": now if request.status == "completed" else None,
            "details": json.dumps(request.details) if request.details else None,
            "error": request.error,
            "config": request.config
        }
        
        # Save job to database
        save_ingestion_job(db, request.job_id, job_data)
        
        # Log activity
        log_activity(
            db=db,
            username=current_user.username,
            action=f"Create {request.job_type} Job",
            details=f"Created job with ID: {request.job_id}"
        )
        
        return {"id": request.job_id, "status": "created"}
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create job: {str(e)}"
        )

# Add endpoint for previewing files directly from the client
@router.post("/preview-file")
async def preview_file_direct(
    file: UploadFile = File(...),
    current_user: User = Depends(has_permission("datapuur:read")),
    db: Session = Depends(get_db)
):
    """
    Preview a file directly from the client without requiring the file to be uploaded first.
    Returns headers and a sample of rows from the file.
    """
    try:
        # Create a temporary file to store the uploaded content
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            # Read the file content in chunks to handle large files
            chunk_size = 1024 * 1024  # 1MB chunks
            
            # Only read the first 10MB for preview purposes
            max_size = 10 * 1024 * 1024  # 10MB
            total_read = 0
            
            while total_read < max_size:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                
                # Write the chunk to the temporary file
                temp_file.write(chunk)
                total_read += len(chunk)
                
                # If we've read enough for a preview, stop
                if total_read >= max_size:
                    logger.info(f"Preview size limit reached at {total_read} bytes. File may be larger.")
                    break
            
            temp_path = temp_file.name
        
        file_extension = file.filename.split('.')[-1].lower()
        
        # Process based on file type
        if file_extension == 'csv':
            # Read CSV file with optimizations for large files
            try:
                # Only read first 100 rows for preview
                df = pd.read_csv(temp_path, nrows=100)
                # Handle empty values in the DataFrame
                df = df.replace({np.nan: None})
                
                # Convert to list of lists for JSON serialization
                headers = df.columns.tolist()
                
                # Get a sample of rows (first 50 rows)
                sample_rows = []
                for _, row in df.iterrows():
                    # Convert each row to a list of values
                    row_values = []
                    for val in row:
                        # Handle special types for JSON serialization
                        if isinstance(val, (np.integer, np.floating)):
                            val = val.item()  # Convert numpy types to native Python types
                        row_values.append(val)
                    sample_rows.append(row_values)
                
                # Clean up the temporary file
                os.unlink(temp_path)
                
                return {
                    "headers": headers,
                    "rows": sample_rows
                }
            except Exception as e:
                logger.error(f"Error processing CSV file: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Error processing CSV file: {str(e)}"
                )
        
        elif file_extension == 'json':
            # Read JSON file
            try:
                # Import ijson for streaming JSON parsing
                import ijson
                
                preview_records = []
                max_records = 50  # Limit to first 50 records for preview
                
                # Check if the file starts with an array
                with open(temp_path, 'r', encoding='utf-8', errors='replace') as f:
                    # Read just enough to determine if it's an array
                    first_char = f.read(1).strip()
                
                # If it's an array (starts with '['), use ijson for streaming parse
                if first_char == '[':
                    try:
                        # Reopen the file for streaming parse
                        with open(temp_path, 'r', encoding='utf-8', errors='replace') as f:
                            # Use ijson to stream parse the JSON array
                            parser = ijson.items(f, 'item')
                            
                            # Get the first few items for preview
                            for i, item in enumerate(parser):
                                if i >= max_records:
                                    break
                                preview_records.append(item)
                    except Exception as e:
                        logger.error(f"Error streaming JSON file: {str(e)}")
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Error processing JSON file: {str(e)}"
                        )
                else:
                    # If it's not an array, read a limited amount to avoid memory issues
                    with open(temp_path, 'r', encoding='utf-8', errors='replace') as f:
                        # Read only the first 1MB of the file
                        json_data = f.read(1024 * 1024)
                    
                    try:
                        # Try to parse as a single JSON object
                        data = json.loads(json_data)
                        preview_records = [data]
                    except json.JSONDecodeError:
                        logger.error("Invalid JSON file")
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid JSON file"
                        )
                
                # If we didn't get any records, the file might be malformed
                if not preview_records:
                    logger.error("Invalid JSON file structure or empty array")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid JSON file structure or empty array"
                    )
                
                # Function to flatten nested JSON
                def flatten_json(nested_json, prefix=''):
                    flattened = {}
                    for key, value in nested_json.items():
                        if isinstance(value, dict):
                            # Recursively flatten nested dictionaries
                            flattened.update(flatten_json(value, f"{prefix}{key}_"))
                        elif isinstance(value, list):
                            # Handle lists by converting them to strings if they contain simple types
                            # or by flattening if they contain dictionaries
                            if all(not isinstance(item, dict) for item in value):
                                # For lists of simple types, convert to string
                                flattened[f"{prefix}{key}"] = str(value)
                            else:
                                # For lists of dictionaries, flatten each item
                                for i, item in enumerate(value):
                                    if isinstance(item, dict):
                                        flattened.update(flatten_json(item, f"{prefix}{key}_{i}_"))
                                    else:
                                        flattened[f"{prefix}{key}_{i}"] = item
                        else:
                            # For simple types, just add them with the prefix
                            flattened[f"{prefix}{key}"] = value
                    return flattened
                
                # Convert records to a format suitable for display
                flattened_data = []
                for item in preview_records:
                    if isinstance(item, dict):
                        flattened_data.append(flatten_json(item))
                    else:
                        flattened_data.append({"value": item})
                
                # Log activity
                log_activity(
                    db=db,
                    username=current_user.username,
                    action="File preview",
                    details=f"Previewed file: {file.filename}"
                )
                
                # Convert to DataFrame to get headers and rows for consistent display
                df = pd.DataFrame(flattened_data)
                
                # Clean up the temporary file
                os.unlink(temp_path)
                
                # Return data in a format similar to CSV preview
                return {
                    "headers": df.columns.tolist() if not df.empty else [],
                    "rows": df.replace({np.nan: None}).values.tolist() if not df.empty else []
                }
            except Exception as e:
                logger.error(f"Error processing JSON file: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Error processing JSON file: {str(e)}"
                )
        
        else:
            # Clean up the temporary file
            os.unlink(temp_path)
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type: {file_extension}. Only CSV and JSON files are supported."
            )
    
    except Exception as e:
        logger.error(f"Error previewing file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error previewing file: {str(e)}"
        )
        
@router.get("/admin/jobs", response_model=List[Dict[str, Any]])
async def get_all_jobs_admin(
    current_user: User = Depends(has_permission("datapuur:manage")),
    db: Session = Depends(get_db)
):
    """
    Get all jobs in the system (admin only, requires datapuur:manage permission).
    Returns detailed information about all jobs for admin monitoring.
    """
    try:
        from .models import IngestionJob
        
        # Get all jobs from the database
        jobs = db.query(IngestionJob).all()
        
        # Convert to response format
        job_list = []
        for job in jobs:
            job_data = {
                "id": job.id or "",  # Ensure we never return null for string fields
                "name": job.name or "",
                "type": job.type or "",
                "status": job.status or "",
                "createdAt": job.start_time.isoformat() if job.start_time else "",
                "updatedAt": job.end_time.isoformat() if job.end_time else "",
                "progress": job.progress or 0,
                "details": job.details or "",
                "error": job.error or ""
            }
            job_list.append(job_data)
        
        # Log this admin activity
        log_activity(
            db=db,
            username=current_user.username,
            action="Admin job management",
            details="Retrieved all system jobs"
        )
        
        return job_list
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving jobs: {str(e)}"
        )

@router.post("/admin/jobs/{job_id}/stop", response_model=Dict[str, Any])
async def stop_job_admin(
    job_id: str,
    current_user: User = Depends(has_permission("datapuur:manage")),
    db: Session = Depends(get_db)
):
    """
    Stop a running job (admin only, requires datapuur:manage permission).
    Used by admins to forcibly stop jobs that might be stuck or problematic.
    """
    try:
        from .models import IngestionJob
        
        # Get the job
        job = db.query(IngestionJob).filter(IngestionJob.id == job_id).first()
        if not job:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Job not found with ID: {job_id}"
            )
        
        # Check if job can be stopped
        if job.status not in ["running", "queued"]:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Job with status '{job.status}' cannot be stopped"
            )
        
        # Update job status to cancelled
        job.status = "cancelled"
        job.end_time = datetime.now()
        job.details = f"{job.details} (Stopped by admin: {current_user.username})"
        db.commit()
        
        # Log this admin activity
        log_activity(
            db=db,
            username=current_user.username,
            action="Admin job management",
            details=f"Stopped job {job_id}"
        )
        
        return {
            "id": job.id,
            "status": job.status,
            "message": "Job stopped successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error stopping job: {str(e)}"
        )

@router.delete("/admin/jobs/{job_id}", response_model=Dict[str, Any])
async def delete_job_admin(
    job_id: str,
    current_user: User = Depends(has_permission("datapuur:manage")),
    db: Session = Depends(get_db)
):
    """
    Delete a job and its associated resources (admin only, requires datapuur:manage permission).
    Used by admins to clean up the system by removing old or failed jobs.
    """
    try:
        from .models import IngestionJob
        
        # Get the job
        job = db.query(IngestionJob).filter(IngestionJob.id == job_id).first()
        if not job:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Job not found with ID: {job_id}"
            )
        
        # If the job has associated files, may need to delete them as well
        # This is job-type specific
        if job.type == "file":
            # Get file_id from job config
            file_id = None
            config = json.loads(job.config) if job.config else {}
            if config and "file_id" in config:
                file_id = config["file_id"]
                
            # For file ingestion jobs, delete associated parquet file
            file_path = os.path.join(os.path.dirname(__file__), "data", f"{file_id if file_id else job_id}.parquet")
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Deleted parquet file for job {job_id} (file_id: {file_id})")
            else:
                logger.warning(f"Parquet file not found for job {job_id} (file_id: {file_id})")
                
            # Also check for any profile results associated with this file
            try:
                from .profiler.models import ProfileResult
                profiles = db.query(ProfileResult).filter(ProfileResult.file_id == file_id).all() if file_id else []
                for profile in profiles:
                    db.delete(profile)
                if profiles:
                    logger.info(f"Deleted {len(profiles)} profile results for file_id {file_id}")
            except Exception as e:
                logger.error(f"Error deleting profile results: {str(e)}")

        
        # Delete the job from the database
        db.delete(job)
        db.commit()
        
        # Log this admin activity
        log_activity(
            db=db,
            username=current_user.username,
            action="Admin job management",
            details=f"Deleted job {job_id}"
        )
        
        return {
            "id": job_id,
            "message": "Job deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting job: {str(e)}"
        )   