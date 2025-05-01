"""
Parallel API endpoints for DataPuur using Dramatiq for background job processing.
These endpoints replicate the existing ingestion endpoints but dispatch jobs to Dramatiq actors.
"""
from fastapi import APIRouter, Depends, HTTPException, status as http_status, Request, File, Form, UploadFile, Response
from sqlalchemy.orm import Session
from typing import Dict, List, Any
import uuid
from datetime import datetime
from .models import get_db, User, IngestionJob, Role
from .auth import has_permission, log_activity, has_any_permission, AVAILABLE_PERMISSIONS
from .datapuur_dramatiq import dramatiq_file_ingestion, dramatiq_db_ingestion
from .datapuur import get_uploaded_file, save_ingestion_job, get_ingestion_job, IngestionHistoryResponse, FileIngestionRequest, DatabaseConfig, JobStatus, save_uploaded_file
import json
from fastapi import Query
from sqlalchemy import or_
from datetime import datetime
import os
from fastapi.responses import FileResponse
from .data_models import DataMetrics, Activity, DashboardData

router = APIRouter(prefix="/api/datapuur", tags=["datapuur"])

@router.post("/ingest-file", status_code=http_status.HTTP_200_OK)
async def ingest_file_dramatiq(
    request: FileIngestionRequest,
    current_user: User = Depends(has_permission("datapuur:write")),
    db: Session = Depends(get_db)
):
    """Start file ingestion job using Dramatiq."""
    file_id = request.file_id
    file_name = request.file_name
    chunk_size = request.chunk_size
    file_info = get_uploaded_file(db, file_id)
    if not file_info:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="File not found")
    job_id = str(uuid.uuid4())
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
        "config": {"file_id": file_id, "chunk_size": chunk_size}
    }
    save_ingestion_job(db, job_id, job_data)
    dramatiq_file_ingestion.send(job_id, file_id, chunk_size)
    log_activity(db=db, username=current_user.username, action="File ingestion started [dramatiq]", details=f"Started ingestion for file: {file_name}")
    return {"job_id": job_id, "message": "File ingestion started [dramatiq]"}

@router.post("/ingest-db", status_code=http_status.HTTP_200_OK)
async def ingest_db_dramatiq(
    request: DatabaseConfig,
    current_user: User = Depends(has_permission("datapuur:write")),
    db: Session = Depends(get_db)
):
    """Start database ingestion job using Dramatiq."""
    db_type = request.type
    db_config = request.config
    chunk_size = request.chunk_size
    connection_name = request.connection_name
    required_fields = ["host", "port", "database", "username", "table"]
    for field in required_fields:
        if not db_config.get(field):
            raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=f"Missing required field: {field}")
    job_id = str(uuid.uuid4())
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
        "config": {"type": db_type, "database": db_config["database"], "table": db_config["table"]}
    }
    save_ingestion_job(db, job_id, job_data)
    dramatiq_db_ingestion.send(job_id, db_type, db_config, chunk_size)
    log_activity(db=db, username=current_user.username, action="Database ingestion started [dramatiq]", details=f"Started ingestion for table: {db_config['database']}.{db_config['table']}")
    return {"job_id": job_id, "message": "Database ingestion started [dramatiq]"}

@router.get("/job-status/{job_id}", response_model=JobStatus)
async def get_job_status_dramatiq(
    job_id: str,
    current_user: User = Depends(has_permission("datapuur:read")),
    db: Session = Depends(get_db)
):
    """Get status of an ingestion job (Dramatiq pipeline)."""
    job = get_ingestion_job(db, job_id)
    if not job:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Job not found")
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

@router.post("/cancel-job/{job_id}", status_code=http_status.HTTP_200_OK)
async def cancel_job_dramatiq(
    job_id: str,
    current_user: User = Depends(has_permission("datapuur:write")),
    db: Session = Depends(get_db)
):
    """Cancel an ingestion job (Dramatiq pipeline)."""
    job = get_ingestion_job(db, job_id)
    if not job:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.status not in ["running", "queued"]:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=f"Cannot cancel job with status: {job.status}")
    from pathlib import Path
    from datetime import datetime
    import os
    DATA_DIR = Path(os.path.dirname(__file__)) / "data"
    try:
        cancel_marker_path = DATA_DIR / f"cancel_{job_id}"
        with open(cancel_marker_path, 'w') as f:
            f.write('cancelled')
    except Exception as e:
        pass
    job.status = "cancelled"
    job.error = None
    job.details = f"{job.details} (Cancelled by user)"
    job.end_time = datetime.now()
    start_time = job.start_time
    end_time = job.end_time
    duration = end_time - start_time
    job.duration = str(duration)
    try:
        data_path = DATA_DIR / f"{job_id}.parquet"
        if data_path.exists():
            data_path.unlink()
    except Exception as e:
        pass
    try:
        from .profiler.models import ProfileResult
        profiles = db.query(ProfileResult).filter(ProfileResult.parquet_file_path == f"{job_id}.parquet").all()
        for profile in profiles:
            db.delete(profile)
    except Exception as e:
        pass
    db.commit()
    log_activity(db=db, username=current_user.username, action="Job cancelled [dramatiq]", details=f"Cancelled ingestion job: {job.name}")
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
async def get_ingestion_history_dramatiq(
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
    """Get history of ingestion jobs with filtering and pagination (Dramatiq pipeline)."""
    try:
        query = db.query(IngestionJob)
        query = query.filter(IngestionJob.type != "profile")
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
        if sort == "newest":
            query = query.order_by(IngestionJob.start_time.desc())
        else:
            query = query.order_by(IngestionJob.start_time)
        total = query.count()
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)
        jobs = query.all()
        items = []
        for job in jobs:
            config = json.loads(job.config) if job.config else {}
            file_info = None
            db_info = None
            if job.type == "file" and config and "file_id" in config:
                file_id = config["file_id"]
                file_info = get_uploaded_file(db, file_id) if file_id else None
            elif job.type == "database" and config:
                db_info = {
                    "type": config.get("type", "unknown"),
                    "name": config.get("database", "unknown"),
                    "table": config.get("table", "unknown")
                }
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
            if job.type == "database" and db_info:
                history_item["database_info"] = db_info
            items.append(history_item)
        log_activity(
            db=db,
            username=current_user.username,
            action="View ingestion history [dramatiq]",
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
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching ingestion history: {str(e)}"
        )

@router.get("/ingestion-preview/{ingestion_id}")
async def get_ingestion_preview_dramatiq(
    ingestion_id: str,
    current_user: User = Depends(has_permission("datapuur:read")),
    db: Session = Depends(get_db)
):
    """Get preview data for an ingestion (Dramatiq pipeline)."""
    job = get_ingestion_job(db, ingestion_id)
    if not job:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Ingestion not found"
        )
    
    # Check if job is completed
    if job.status != "completed":
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot preview ingestion with status: {job.status}"
        )
    
    try:
        # Get the parquet file path
        from pathlib import Path
        import pandas as pd
        import numpy as np
        import json
        
        DATA_DIR = Path(os.path.dirname(__file__)) / "data"
        parquet_path = DATA_DIR / f"{ingestion_id}.parquet"
        
        if not os.path.exists(parquet_path):
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
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
                            else:
                                try:
                                    record[col] = val
                                except:
                                    record[col] = str(val)
                        records.append(record)
                
                return {
                    "data": records,
                    "headers": preview_df.columns.tolist(),
                    "filename": file_info.filename if file_info else f"file_{file_id}",
                    "type": "json"
                }
        elif job.type == "database":
            # For database, treat like CSV for now
            # In a more complete implementation, might use different formatting based on database type
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
                "filename": job.name,
                "type": "database"
            }
        
        # Log activity
        log_activity(
            db=db,
            username=current_user.username,
            action="View ingestion preview [dramatiq]",
            details=f"Viewed preview for: {job.name}"
        )
        
        # Default case
        return {
            "data": [],
            "headers": [],
            "filename": job.name,
            "type": "unknown"
        }
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating preview: {str(e)}"
        )

@router.get("/preview/{file_id}", status_code=http_status.HTTP_200_OK)
async def preview_file_dramatiq(
    file_id: str,
    current_user: User = Depends(has_permission("datapuur:read")),
    db: Session = Depends(get_db)
):
    """Preview a file (Dramatiq pipeline)."""
    file_info = get_uploaded_file(db, file_id)
    if not file_info:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="File not found")
    file_path = file_info.path
    if not os.path.exists(file_path):
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="File not found on disk")
    try:
        import pandas as pd
        import numpy as np
        import csv
        import json as _json
        # For CSV files
        if file_info.type == "csv":
            try:
                df = pd.read_csv(file_path, nrows=100)
                headers = df.columns.tolist()
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
                log_activity(db=db, username=current_user.username, action="File preview [dramatiq]", details=f"Previewed file: {file_info.filename}")
                return {"data": rows, "headers": headers, "filename": file_info.filename, "type": "csv"}
            except pd.errors.EmptyDataError:
                return {"data": [], "headers": [], "filename": file_info.filename, "type": "csv"}
            except Exception as e:
                with open(file_path, 'r', newline='', encoding='utf-8', errors='replace') as csvfile:
                    reader = csv.reader(csvfile)
                    try:
                        headers = next(reader)
                    except StopIteration:
                        headers = []
                    rows = []
                    for i, row in enumerate(reader):
                        if i >= 100:
                            break
                        rows.append(row)
                return {"data": rows, "headers": headers, "filename": file_info.filename, "type": "csv"}
        elif file_info.type == "json":
            try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as jsonfile:
                    try:
                        data = _json.load(jsonfile)
                    except _json.JSONDecodeError as e:
                        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=f"Invalid JSON file: {str(e)}")
                def flatten_json(nested_json, prefix=''):
                    flattened = {}
                    for key, value in nested_json.items():
                        if isinstance(value, dict):
                            flattened.update(flatten_json(value, f"{prefix}{key}_"))
                        elif isinstance(value, list):
                            if all(not isinstance(item, dict) for item in value):
                                flattened[f"{prefix}{key}"] = str(value)
                            else:
                                for i, item in enumerate(value):
                                    if isinstance(item, dict):
                                        flattened.update(flatten_json(item, f"{prefix}{key}_{i}_"))
                                    else:
                                        flattened[f"{prefix}{key}_{i}"] = item
                        else:
                            flattened[f"{prefix}{key}"] = value
                    return flattened
                if isinstance(data, list):
                    limited_data = data[:100]
                    flattened_data = []
                    for item in limited_data:
                        if isinstance(item, dict):
                            flattened_data.append(flatten_json(item))
                        else:
                            flattened_data.append({"value": item})
                elif isinstance(data, dict):
                    flattened_data = [flatten_json(data)]
                else:
                    flattened_data = [{"value": data}]
                log_activity(db=db, username=current_user.username, action="File preview [dramatiq]", details=f"Previewed file: {file_info.filename}")
                df = pd.DataFrame(flattened_data)
                return {"data": df.values.tolist() if not df.empty else [], "headers": df.columns.tolist(), "filename": file_info.filename, "type": "json"}
            except Exception as e:
                raise HTTPException(status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error previewing JSON file: {str(e)}")
        else:
            raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="Unsupported file type for preview")
    except Exception as e:
        raise HTTPException(status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error previewing file: {str(e)}")

@router.get("/download/{file_id}", status_code=http_status.HTTP_200_OK)
async def download_file_dramatiq(
    file_id: str,
    current_user: User = Depends(has_permission("datapuur:read")),
    db: Session = Depends(get_db)
):
    """Download a file (Dramatiq pipeline)."""
    file_info = get_uploaded_file(db, file_id)
    if not file_info:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="File not found")
    file_path = file_info.path
    if not os.path.exists(file_path):
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="File not found on disk")
    try:
        log_activity(db=db, username=current_user.username, action="File download [dramatiq]", details=f"Downloaded file: {file_info.filename}")
        return FileResponse(path=file_path, filename=file_info.filename, media_type="application/octet-stream")
    except Exception as e:
        raise HTTPException(status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error downloading file: {str(e)}")

@router.get("/ingestion-schema/{ingestion_id}", response_model=dict)
async def get_ingestion_schema_dramatiq(
    ingestion_id: str,
    current_user: User = Depends(has_permission("datapuur:read")),
    db: Session = Depends(get_db)
):
    """Get schema for an ingestion (Dramatiq pipeline)."""
    job = get_ingestion_job(db, ingestion_id)
    if not job:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Ingestion not found")
    if job.status != "completed":
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=f"Cannot get schema for ingestion with status: {job.status}")
    try:
        from pathlib import Path
        import pandas as pd
        import numpy as np
        DATA_DIR = Path(os.path.dirname(__file__)) / "data"
        parquet_path = DATA_DIR / f"{ingestion_id}.parquet"
        if not os.path.exists(parquet_path):
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Ingestion data file not found")
        df = pd.read_parquet(parquet_path)
        fields = []
        sample_values = []
        for column in df.columns:
            dtype = df[column].dtype
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
            nullable = bool(df[column].isna().any())
            sample = None
            non_null_values = df[column].dropna()
            if not non_null_values.empty:
                sample_value = non_null_values.iloc[0]
                if isinstance(sample_value, (np.integer, np.floating)):
                    sample = sample_value.item()
                elif isinstance(sample_value, np.bool_):
                    sample = bool(sample_value)
                elif pd.api.types.is_datetime64_dtype(dtype):
                    sample = str(sample_value)
                elif isinstance(sample_value, np.ndarray):
                    sample = sample_value.tolist()
                elif isinstance(sample_value, pd.Timestamp):
                    sample = str(sample_value)
                else:
                    sample = sample_value
            fields.append({"name": column, "type": field_type, "nullable": nullable})
            sample_values.append(sample)
        def convert_numpy_types(obj):
            import numpy as np
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
        converted_fields = convert_numpy_types(fields)
        converted_sample_values = convert_numpy_types(sample_values)
        return {"fields": converted_fields, "sample_values": converted_sample_values}
    except Exception as e:
        raise HTTPException(status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error generating schema: {str(e)}")

@router.get("/ingestion-statistics/{ingestion_id}", response_model=dict)
async def get_ingestion_statistics_dramatiq(
    ingestion_id: str,
    current_user: User = Depends(has_permission("datapuur:read")),
    db: Session = Depends(get_db)
):
    """Get statistics for an ingestion (Dramatiq pipeline)."""
    job = get_ingestion_job(db, ingestion_id)
    if not job:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Ingestion not found")
    if job.status != "completed":
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=f"Cannot get statistics for ingestion with status: {job.status}")
    try:
        from pathlib import Path
        import pandas as pd
        import numpy as np
        DATA_DIR = Path(os.path.dirname(__file__)) / "data"
        parquet_path = DATA_DIR / f"{ingestion_id}.parquet"
        if not os.path.exists(parquet_path):
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Ingestion data file not found")
        df = pd.read_parquet(parquet_path)
        row_count = len(df)
        column_count = len(df.columns)
        total_cells = row_count * column_count
        null_count = df.isna().sum().sum()
        null_percentage = (null_count / total_cells) * 100 if total_cells > 0 else 0
        if isinstance(null_percentage, (np.integer, np.floating)):
            null_percentage = null_percentage.item()
        memory_usage_bytes = df.memory_usage(deep=True).sum()
        if isinstance(memory_usage_bytes, (np.integer, np.floating)):
            memory_usage_bytes = memory_usage_bytes.item()
        if memory_usage_bytes < 1024:
            memory_usage = f"{memory_usage_bytes} B"
        elif memory_usage_bytes < 1024 * 1024:
            memory_usage = f"{memory_usage_bytes / 1024:.1f} KB"
        else:
            memory_usage = f"{memory_usage_bytes / (1024 * 1024):.1f} MB"
        processing_time = "Unknown"
        if job.duration:
            try:
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
            "error_rate": 0
        }
    except Exception as e:
        raise HTTPException(status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error generating statistics: {str(e)}")

@router.post("/upload", status_code=http_status.HTTP_201_CREATED)
async def upload_file_dramatiq(
    file: UploadFile = File(...),
    chunkSize: int = Form(1000),
    current_user: User = Depends(has_permission("datapuur:write")),
    db: Session = Depends(get_db)
):
    """Upload a file for data ingestion (Dramatiq pipeline)."""
    try:
        from pathlib import Path
        import shutil
        import uuid
        
        # Generate a unique file ID
        file_id = str(uuid.uuid4())
        
        # Get the file extension
        filename = file.filename
        file_extension = filename.split(".")[-1].lower() if "." in filename else ""
        
        # Create uploads directory if it doesn't exist
        UPLOAD_DIR = Path(os.path.dirname(__file__)) / "uploads"
        UPLOAD_DIR.mkdir(exist_ok=True)
        
        # Save the file
        file_path = UPLOAD_DIR / f"{file_id}.{file_extension}"
        try:
            with open(file_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
        finally:
            file.file.close()
        
        # Determine file type
        if file_extension in ["csv"]:
            file_type = "csv"
        elif file_extension in ["json"]:
            file_type = "json"
        else:
            file_type = "unknown"
        
        # Save file info to database
        file_data = {
            "filename": filename,
            "path": str(file_path),
            "type": file_type,
            "uploaded_by": current_user.username,
            "chunk_size": chunkSize
        }
        
        save_uploaded_file(db, file_id, file_data)
        
        # Initiate background processing via Dramatiq
        from .datapuur_jobs_orchestration import start_file_upload_pipeline
        start_file_upload_pipeline(file_id, str(file_path), filename, file_type, current_user.username)
        
        # Log activity
        log_activity(
            db=db,
            username=current_user.username,
            action="File upload [dramatiq]",
            details=f"Uploaded file: {filename}"
        )
        
        return {
            "id": file_id,
            "file_id": file_id,
            "filename": filename,
            "type": file_type,
            "size": os.path.getsize(file_path)
        }
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading file: {str(e)}"
        )

@router.get("/sources", response_model=list)
async def get_data_sources_dramatiq(
    current_user: User = Depends(has_any_permission(["datapuur:read", "kginsights:read"])),
    db: Session = Depends(get_db)
):
    """List all data sources (Dramatiq pipeline)."""
    try:
        from .models import IngestionJob
        from sqlalchemy import func
        
        # Query completed ingestion jobs (these are our data sources)
        sources = db.query(IngestionJob).filter(IngestionJob.status == "completed").all()
        
        result = []
        
        for source in sources:
            # Skip profile jobs
            if source.type == "profile":
                continue
                
            # Parse the config
            config = json.loads(source.config) if source.config else {}
            
            # Get row count estimate from associated profile if available
            row_count = 0
            profile = db.query(IngestionJob).filter(
                IngestionJob.type == "profile",
                IngestionJob.config.like(f'%"ingestion_job_id": "{source.id}"%')
            ).first()
            
            if profile and profile.status == "completed":
                try:
                    # Try to extract row count from profile data
                    DATA_DIR = Path(os.path.dirname(__file__)) / "data"
                    profile_path = DATA_DIR / f"profile_{source.id}.json"
                    if profile_path.exists():
                        with open(profile_path, 'r') as f:
                            profile_data = json.load(f)
                            # Take the count from the first column we find
                            for column, stats in profile_data.items():
                                if "count" in stats:
                                    row_count = stats["count"]
                                    break
                except:
                    pass
            
            # Build the source info
            source_info = {
                "id": source.id,
                "name": source.name,
                "type": source.type,
                "created_at": source.start_time.isoformat() if hasattr(source.start_time, 'isoformat') else str(source.start_time),
                "row_count": row_count,
                "source_type": "file" if source.type == "file" else "database",
            }
            
            # Add database info for database sources
            if source.type == "database" and config:
                source_info["database"] = {
                    "name": config.get("database", ""),
                    "table": config.get("table", "")
                }
            
            result.append(source_info)
        
        # Log activity
        log_activity(
            db=db,
            username=current_user.username,
            action="View data sources [dramatiq]",
            details=f"Retrieved {len(result)} data sources"
        )
        
        return result
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving data sources: {str(e)}"
        )

@router.get("/sources/{source_id}", response_model=dict)
async def get_source_details_dramatiq(
    source_id: str,
    current_user: User = Depends(has_any_permission(["datapuur:read", "kginsights:read"])),
    db: Session = Depends(get_db)
):
    """Get details for a specific data source (Dramatiq pipeline)."""
    try:
        job = get_ingestion_job(db, source_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Source not found with ID: {source_id}")
        
        # Parse config
        config = json.loads(job.config) if job.config else {}
        
        # Basic details
        source_details = {
            "id": job.id,
            "name": job.name,
            "type": job.type,
            "status": job.status,
            "created_at": job.start_time.isoformat() if job.start_time else None,
            "details": job.details,
            "preview_url": f"/api/datapuur/ingestion-preview/{job.id}",
            "download_url": f"/api/datapuur/ingestion-download/{job.id}"
        }
        
        # For file sources, add file details
        if job.type == "file" and config and "file_id" in config:
            file_id = config["file_id"]
            file_info = get_uploaded_file(db, file_id)
            
            if file_info:
                source_details["file"] = {
                    "id": file_id,
                    "filename": file_info.filename,
                    "type": file_info.type,
                    "path": file_info.path
                }
                # Include schema if available
                if hasattr(file_info, 'schema') and file_info.schema:
                    source_details["file"]["schema"] = json.loads(file_info.schema) if isinstance(file_info.schema, str) else file_info.schema
        
        # For database sources, add database details
        elif job.type == "database" and config:
            source_details["database"] = {
                "type": config.get("type", "unknown"),
                "name": config.get("database", "unknown"),
                "table": config.get("table", "unknown")
            }
        
        # Log activity
        log_activity(
            db=db,
            username=current_user.username,
            action="Data source details [dramatiq]",
            details=f"Viewed source: {job.name} (ID: {source_id})"
        )
        
        return source_details
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving source details: {str(e)}"
        )

@router.get("/dashboard", response_model=Dict[str, Any])
async def get_dashboard_data_dramatiq(
    current_user: User = Depends(has_permission("datapuur:read")),
    db: Session = Depends(get_db),
    response: Response = None
):
    """Get dashboard data for DataPuur (Dramatiq pipeline)."""
    # Import the original implementation functions
    from .datapuur import get_data_metrics, get_activities
    from .models import IngestionJob
    from sqlalchemy import desc
        
    # Get real metrics and activities
    metrics = await get_data_metrics(current_user, db)
    activities = await get_activities(current_user, db)
        
    # Query jobs
    completed_jobs = db.query(IngestionJob).filter(IngestionJob.status == "completed").all()
    failed_jobs = db.query(IngestionJob).filter(IngestionJob.status == "failed").all()
    running_jobs = db.query(IngestionJob).filter(IngestionJob.status.in_(["running", "queued"])).all()
        
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

    response_data = {
            "metrics": metrics.dict(),
            "recent_activities": [a.dict() for a in sorted(
        activities, 
        key=lambda x: x.time, 
        reverse=True
            )[:4]],
        "chart_data": chart_data
    }
    
    # Log API response for debugging
    print("==== DRAMATIQ API DASHBOARD RESPONSE ====")
    print(f"Metrics: {response_data['metrics']}")
    print(f"Chart data: {response_data['chart_data']}")
    print(f"Recent activities count: {len(response_data['recent_activities'])}")
    
    return response_data
    
@router.get("/metrics", response_model=Dict[str, Any])
async def get_data_metrics_dramatiq(
    current_user: User = Depends(has_permission("datapuur:read")),
    db: Session = Depends(get_db)
):
    """Get metrics data for DataPuur (Dramatiq pipeline)."""
    try:
        from .models import IngestionJob
        
        # Query jobs
        completed_jobs = db.query(IngestionJob).filter(IngestionJob.status == "completed").all()
        failed_jobs = db.query(IngestionJob).filter(IngestionJob.status == "failed").all()
        
        # Calculate metrics
        total_records = 0
        processed_records = 0
        failed_records = 0
        processing_time = 0.0
        
        # Process completed jobs
        for job in completed_jobs:
            if job.type == "profile":
                continue
                
            # Estimate record counts (replace with actual counts if available)
            if job.type == "file":
                processed_records += 10000
                total_records += 10000
            elif job.type == "database":
                processed_records += 20000
                total_records += 20000
            
            # Calculate processing time
            if job.start_time and job.end_time:
                processing_time += (job.end_time - job.start_time).total_seconds()
        
        # Process failed jobs
        for job in failed_jobs:
            if job.type == "profile":
                continue
                
            # Estimate failed records
            if job.type == "file":
                failed_records += 5000
                total_records += 5000
            elif job.type == "database":
                failed_records += 10000
                total_records += 10000
        
        # Return as simple dictionary instead of using DataMetrics model
        metrics_response = {
            "total_records": total_records,
            "processed_records": processed_records,
            "failed_records": failed_records,
            "processing_time": round(processing_time, 2)
        }
        
        # Log API metrics response for debugging
        print("==== DRAMATIQ API METRICS RESPONSE ====")
        print(f"Metrics: {metrics_response}")
        
        return metrics_response
    except Exception as e:
        raise HTTPException(status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error retrieving metrics: {str(e)}")

@router.get("/activities", response_model=List[Dict[str, Any]])
async def get_activities_dramatiq(
    current_user: User = Depends(has_permission("datapuur:read")),
    db: Session = Depends(get_db)
):
    """Get recent activity data for DataPuur (Dramatiq pipeline)."""
    try:
        from .models import ActivityLog
        from sqlalchemy import desc
        
        # Query recent activities
        logs = db.query(ActivityLog).order_by(desc(ActivityLog.timestamp)).limit(20).all()
        
        activities = []
        for log in logs:
            activities.append({
                "id": str(log.id),
                "user": log.username,
                "action": log.action,
                "timestamp": log.timestamp.isoformat() if hasattr(log.timestamp, 'isoformat') else str(log.timestamp),
                "details": log.details,
                "status": "success" if "failed" not in log.action.lower() else "error"
            })
        
        # Log API activities response for debugging
        print("==== DRAMATIQ API ACTIVITIES RESPONSE ====")
        print(f"Activities count: {len(activities)}")
        if activities:
            print(f"First activity: {activities[0]}")
        
        return activities
    except Exception as e:
        raise HTTPException(status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error retrieving activities: {str(e)}")

@router.delete("/delete-dataset/{dataset_id}", status_code=http_status.HTTP_200_OK)
async def delete_dataset_endpoint_dramatiq(
    dataset_id: str,
    current_user: User = Depends(has_permission("datapuur:manage")),
    db: Session = Depends(get_db)
):
    """Delete a dataset and all associated data (Dramatiq pipeline).
    
    This endpoint requires the 'datapuur:manage' permission, which is restricted
    to admin role.
    """
    try:
        # Find the dataset
        job = get_ingestion_job(db, dataset_id)
        if not job:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Dataset not found")
        
        # Delete from database and file system
        from pathlib import Path
        DATA_DIR = Path(os.path.dirname(__file__)) / "data"
        
        # Delete the job record
        db.delete(job)
        
        # Delete any processed data files
        data_path = DATA_DIR / f"{dataset_id}.parquet"
        if data_path.exists():
            os.unlink(data_path)
        
        # Delete any profile data
        profile_path = DATA_DIR / f"profile_{dataset_id}.json"
        if profile_path.exists():
            os.unlink(profile_path)
        
        # Delete associated profile records
        from .models import IngestionJob
        profile_jobs = db.query(IngestionJob).filter(
            IngestionJob.type == "profile",
            IngestionJob.config.like(f'%"{dataset_id}"%')
        ).all()
        
        for profile in profile_jobs:
            db.delete(profile)
        
        # Commit changes
        db.commit()
        
        # Log activity
        log_activity(
            db=db,
            username=current_user.username,
            action="Dataset deleted [dramatiq]",
            details=f"Deleted dataset: {job.name} (ID: {dataset_id})"
        )
        
        return {"message": "Dataset and associated data deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error deleting dataset: {str(e)}")

# Admin-only endpoints for job management
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
            # For file ingestion jobs, we might want to delete associated files
            file_path = os.path.join(os.path.dirname(__file__), "data", f"{job_id}.parquet")
            if os.path.exists(file_path):
                os.remove(file_path)
        
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
