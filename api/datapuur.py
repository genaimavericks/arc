from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File, Form, BackgroundTasks, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional, Union
from fastapi.responses import FileResponse
import random
import uuid
from datetime import datetime, timedelta
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
import pandas as pd
import numpy as np
from pydantic import BaseModel, Field

from .models import User, get_db, ActivityLog, Role, UploadedFile, IngestionJob
from .auth import get_current_active_user, has_role, has_permission, log_activity, has_any_permission
from .data_models import DataSource, DataMetrics, Activity, DashboardData
from .models import get_db, SessionLocal

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Router
router = APIRouter(prefix="/api/datapuur", tags=["datapuur"])

# Create uploads directory if it doesn't exist
UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Create data directory if it doesn't exist
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

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
            uploaded_at=datetime.now(),
            chunk_size=file_data.get('chunk_size', 1000),
            schema=schema_json
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
                setattr(existing_job, key, datetime.fromisoformat(value))
            elif key == 'end_time' and value:
                setattr(existing_job, key, datetime.fromisoformat(value))
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
            start_time=datetime.fromisoformat(job_data['start_time']),
            end_time=datetime.fromisoformat(job_data['end_time']) if job_data.get('end_time') else None,
            details=job_data.get('details'),
            error=job_data.get('error'),
            duration=job_data.get('duration'),
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
        # Delete the dataset record
        db.delete(dataset)
        
        # Delete any processed data files
        data_path = DATA_DIR / f"{dataset_id}.parquet"
        if data_path.exists():
            data_path.unlink()
        
        # Delete associated profile records
        from .profiler.models import ProfileResult
        profile_results = db.query(ProfileResult).filter(ProfileResult.file_id == dataset_id).all()
        
        for profile in profile_results:
            db.delete(profile)
            logger.info(f"Deleted associated profile {profile.id} for dataset {dataset_id}")
        
        # Commit the changes
        db.commit()
        
        return True, "Dataset and associated profiles deleted successfully"
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
    duration: Optional[str] = None
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
        
        # Get sample data
        with engine.connect() as connection:
            result = connection.execute(f"SELECT * FROM {config['table']} LIMIT 1").fetchone()
            sample_data = dict(result) if result else {}
        
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
            
            schema["fields"].append({
                "name": col_name,
                "type": field_type,
                "nullable": not column.get("nullable", True),
                "sample": sample_data.get(col_name) if col_name in sample_data else None
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
            raise ValueError(f"File with ID {file_id} not found")
        
        file_path = file_info.path
        file_type = file_info.type
        
        # Create output file path
        output_file = DATA_DIR / f"{job_id}.parquet"
        
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
                                progress = min(int((batch_number * 10 * 1024 * 1024 / file_size) * 100), 99)
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
                        job.progress = 99
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
                    job.progress = min(int((processed_rows / total_rows) * 100), 99)
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
                        job.progress = min(int((processed_rows / total_rows) * 100), 99)
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
                                    progress = min(int((processed_items / total_items_estimate) * 100), 99)
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
                        
                    job.progress = 99
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
                    job.progress = 99
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
        
        # Calculate duration
        start_time = job.start_time
        end_time = job.end_time
        duration = end_time - start_time
        job.duration = str(duration)
        
        db_session.commit()
        
        logger.info(f"File ingestion completed for job {job_id}")
    
    except Exception as e:
        logger.error(f"Error processing file ingestion: {str(e)}")
        
        # Update job status to failed
        try:
            job = get_ingestion_job(db_session, job_id)
            job.status = "failed"
            job.error = str(e)
            job.end_time = datetime.now()
            db_session.commit()
        except:
            pass
    
    finally:
        # Close the database session
        db_session.close()

# Process database ingestion with database
def process_db_ingestion_with_db(job_id, db_type, db_config, chunk_size, db):
    """Process database ingestion in a background thread with database access"""
    try:
        # Get a new database session
        db_session = SessionLocal()
        
        # Update job status
        job = get_ingestion_job(db_session, job_id)
        job.status = "running"
        job.progress = 0
        db_session.commit()
        
        # Create connection string
        connection_string = create_connection_string(db_type, db_config)
        
        # Create output file path
        output_file = DATA_DIR / f"{job_id}.parquet"
        
        # Connect to database
        engine = create_engine(connection_string)
        
        try:
            # Get total row count
            with engine.connect() as conn:
                result = conn.execute(f"SELECT COUNT(*) FROM {db_config['table']}")
                total_rows = result.scalar()
            
            # Read data in chunks
            offset = 0
            processed_rows = 0
            
            while offset < total_rows:
                # Update progress
                job.progress = min(int((processed_rows / total_rows) * 100), 99)
                db_session.commit()
                
                # Read chunk
                query = f"SELECT * FROM {db_config['table']} LIMIT {chunk_size} OFFSET {offset}"
                chunk = pd.read_sql(query, engine)
                
                # Save chunk
                if offset == 0:
                    chunk.to_parquet(output_file, index=False)
                else:
                    # Read existing parquet file
                    if os.path.exists(output_file):
                        existing_df = pd.read_parquet(output_file)
                        # Concatenate with new chunk
                        combined_df = pd.concat([existing_df, chunk], ignore_index=True)
                        # Write back to the file
                        combined_df.to_parquet(output_file, index=False)
                    else:
                        chunk.to_parquet(output_file, index=False)
                
                # Update counters
                processed_rows += len(chunk)
                offset += chunk_size
                
                # Simulate processing time
                time.sleep(0.2)
            
            # Mark job as completed
            job.status = "completed"
            job.progress = 100
            job.end_time = datetime.now()
            
            # Calculate duration
            start_time = job.start_time
            end_time = job.end_time
            duration = end_time - start_time
            job.duration = str(duration)
            
            db_session.commit()
            
            logger.info(f"Database ingestion completed for job {job_id}")
        
        finally:
            engine.dispose()
    
    except Exception as e:
        logger.error(f"Error processing database ingestion: {str(e)}")
        
        # Update job status to failed
        try:
            job = get_ingestion_job(db_session, job_id)
            job.status = "failed"
            job.error = str(e)
            job.end_time = datetime.now()
            db_session.commit()
        except:
            pass
    
    finally:
        # Close the database session
        db_session.close()

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
    
    # Save the file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving file: {str(e)}"
        )
    finally:
        file.file.close()
    
    # Store file info in database
    file_data = {
        "filename": file.filename,
        "path": str(file_path),
        "type": file_ext,
        "uploaded_by": current_user.username,
        "uploaded_at": datetime.now(),
        "chunk_size": chunkSize
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
    current_user: User = Depends(has_permission("database:connect")),
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
    current_user: User = Depends(has_permission("database:read")),
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
            "duration": None,
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error starting ingestion: {str(e)}"
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
            "duration": None,
            "config": {
                "type": db_type,
                "database": db_config["database"],
                "table": db_config["table"]
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
        duration=job.duration,
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
    
    # Calculate duration
    start_time = job.start_time
    end_time = job.end_time
    duration = end_time - start_time
    job.duration = str(duration)
    
    # Delete any associated data files
    try:
        data_path = DATA_DIR / f"{job_id}.parquet"
        if data_path.exists():
            data_path.unlink()
            logger.info(f"Deleted data file for cancelled job: {job_id}")
    except Exception as e:
        logger.error(f"Error deleting data file for job {job_id}: {str(e)}")
    
    # Delete any associated profile data
    try:
        # First, check if there are any profiles associated with this job
        from .profiler.models import ProfileResult
        profiles = db.query(ProfileResult).filter(ProfileResult.parquet_file_path == f"{job_id}.parquet").all()
        
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
        duration=job.duration,
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
            
            # Create history item
            history_item = {
                "id": job.id,
                "filename": job.name,
                "type": "database" if job.type == "database" else file_info.type if file_info else "unknown",
                "size": os.path.getsize(file_info.path) if file_info and os.path.exists(file_info.path) else 0,
                "uploaded_at": job.start_time.strftime("%Y-%m-%d %H:%M:%S") if isinstance(job.start_time, datetime) else job.start_time,
                "uploaded_by": current_user.username,
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
        # Get the parquet file path
        parquet_path = DATA_DIR / f"{ingestion_id}.parquet"
        
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
                                clean_record[key] = float(value)
                            elif isinstance(value, np.bool_):
                                clean_record[key] = bool(value)
                            elif isinstance(value, (dict, list)):
                                # Ensure nested objects are properly serialized
                                clean_record[key] = json.loads(json.dumps(value))
                            else:
                                # Convert any other complex types to strings
                                try:
                                    json.dumps(value)  # Test if serializable
                                    clean_record[key] = value
                                except (TypeError, OverflowError):
                                    clean_record[key] = str(value)
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reading ingestion data: {str(e)}"
        )

@router.get("/ingestion-schema/{ingestion_id}", response_model=SchemaResponse)
async def get_ingestion_schema(
    ingestion_id: str,
    current_user: User = Depends(has_permission("datapuur:read")),  # Updated permission
    db: Session = Depends(get_db)
):
    """Get schema for an ingestion"""
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
            detail=f"Cannot get schema for ingestion with status: {job.status}"
        )
    
    try:
        # Get the parquet file path
        parquet_path = DATA_DIR / f"{ingestion_id}.parquet"
        
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
        # Get the parquet file path
        parquet_path = DATA_DIR / f"{ingestion_id}.parquet"
        
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
        # Get the parquet file path
        parquet_path = DATA_DIR / f"{ingestion_id}.parquet"
        
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
        if job.duration:
            try:
                # Parse duration string like "0:00:05.123456"
                duration_parts = job.duration.split(":")
                if len(duration_parts) >= 3:
                    hours = int(duration_parts[0])
                    minutes = int(duration_parts[1])
                    seconds = float(duration_parts[2])
                    
                    if hours > 0:
                        processing_time = f"{hours}h {minutes}m {seconds:.1f}s"
                    elif minutes > 0:
                        processing_time = f"{minutes}m {seconds:.1f}s"
                    else:
                        processing_time = f"{seconds:.1f}s"
            except:
                pass
        
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
        # Get the parquet file path
        parquet_path = DATA_DIR / f"{ingestion_id}.parquet"
        
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
            
        # Get uploaded_by information from the UploadedFile table if it's a file type
        uploaded_by = "Unknown"
        if job.type == "file":
            # Try to find the file record that matches this job
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
                
        sources.append(
            DataSource(
                id=job.id,
                name=job.name,
                type="File" if job.type == "file" else "Database",
                last_updated=job.end_time.strftime("%Y-%m-%d %H:%M:%S") if isinstance(job.end_time, datetime) else job.end_time,
                status="Active",
                uploaded_by=uploaded_by
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
                "path": file_info.path,
                "type": file_info.type,
                "uploaded_by": file_info.uploaded_by,
                "uploaded_at": file_info.uploaded_at.isoformat() if isinstance(file_info.uploaded_at, datetime) else file_info.uploaded_at,
                "chunk_size": file_info.chunk_size,
                "schema": file_info.schema
            }
    
    # For database sources, add database details
    elif job.type == "database" and config:
        source_details["database"] = {
            "type": config.get("type", "unknown"),
            "name": config.get("database", "unknown"),
            "table": config.get("table", "unknown")
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
    processing_time = 0.0
    
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
        
        # Calculate processing time
        if job.duration:
            try:
                # Parse duration string like "0:00:05.123456"
                duration_parts = job.duration.split(":")
                if len(duration_parts) >= 3:
                    hours = int(duration_parts[0])
                    minutes = int(duration_parts[1])
                    seconds = float(duration_parts[2])
                    
                    if hours > 0:
                        job_time = hours * 3600 + minutes * 60 + seconds
                    elif minutes > 0:
                        job_time = minutes * 60 + seconds
                    else:
                        job_time = seconds
                    
                    processing_time += job_time
            except:
                pass
    
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
        processing_time=round(processing_time, 2)
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
                "uploaded_at": file.uploaded_at,
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
        # For CSV files
        if file_info.type == "csv":
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
                "uploaded_at": datetime.now(),
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
            
            # Create a cancellation marker file to prevent further processing
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
    duration: Optional[str] = None
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
            "duration": request.duration,
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
                # For large JSON files, we need to be careful about memory usage
                # Read the file in chunks and only process the beginning
                with open(temp_path, 'r', encoding='utf-8', errors='replace') as jsonfile:
                    # Try to parse the JSON data
                    try:
                        data = json.load(jsonfile)
                    except json.JSONDecodeError:
                        logger.error("Invalid JSON file")
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid JSON file"
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
                    details=f"Previewed file: {file.filename}"
                )
                
                # Convert to DataFrame to get headers and rows for consistent display
                df = pd.DataFrame(flattened_data)
                
                # Return data in a format similar to CSV preview
                return {
                    "headers": df.columns.tolist(),
                    "rows": df.values.tolist() if not df.empty else []
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
