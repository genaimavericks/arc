from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
import pandas as pd
import io
import json
import logging
import os
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from api.db_config import get_db
from api.models import UploadedFile, User
from api.auth import get_current_user, has_permission, has_any_permission

router = APIRouter(prefix="/api/export", tags=["Export"])
logger = logging.getLogger(__name__)

# Helper function to get the most appropriate data file path
def get_data_file_path(dataset: UploadedFile) -> str:
    """
    Get the most appropriate data file path for a dataset.
    For database sources, this will be the parquet file in the data directory.
    For file sources, this will check if a corresponding parquet file exists and use it;
    otherwise, it will fall back to the original file.
    
    Args:
        dataset: The UploadedFile database record
        
    Returns:
        str: Path to the data file (parquet preferred, original file as fallback)
    """
    # For database-based sources, the path already points to the parquet file
    if dataset.type.lower() == 'database':
        return dataset.path
        
    # For file-based sources, look for corresponding parquet file
    original_path = dataset.path
    data_dir = os.path.join(os.path.dirname(os.path.dirname(original_path)), "data")
    
    # The parquet file is typically named after the job ID
    # Try to find a parquet file with the dataset ID as the name
    parquet_path = os.path.join(data_dir, f"{dataset.id}.parquet")
    
    if os.path.exists(parquet_path):
        logger.info(f"Using parquet file instead of original {dataset.type} file")
        return parquet_path
    
    # Fall back to original file if parquet doesn't exist
    logger.info(f"Parquet file not found, using original {dataset.type} file")
    return original_path

# Helper function to load dataset into a pandas DataFrame
def load_dataset_as_dataframe(file_path: str, file_type: str) -> pd.DataFrame:
    """
    Load a dataset file into a pandas DataFrame using the appropriate reader
    
    Args:
        file_path: Path to the data file
        file_type: Type of the file (csv, json, database)
        
    Returns:
        pd.DataFrame: The loaded DataFrame
        
    Raises:
        HTTPException: If the file type is unsupported or there's an error loading the file
    """
    try:
        # Check if the file is a parquet file based on extension
        if file_path.lower().endswith('.parquet'):
            return pd.read_parquet(file_path)
            
        # Otherwise use the appropriate reader based on file type
        if file_type.lower() == 'csv':
            return pd.read_csv(file_path)
        elif file_type.lower() == 'json':
            return pd.read_json(file_path)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_type}")
    except Exception as e:
        logger.error(f"Error loading dataset file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to load dataset: {str(e)}")

@router.get("/download")
async def download_dataset(
    dataset_id: str,
    file_format: str = Query("csv", regex="^(csv|json)$"),
    column: Optional[str] = None,
    operator: Optional[str] = None,
    value: Optional[str] = None,
    max_rows: Optional[int] = Query(None, ge=1, description="Maximum number of rows to include in the download"),
    db: Session = Depends(get_db),
    current_user: User = Depends(has_permission("datapuur:read"))
):
    """
    Download a dataset in the specified format.
    If filter parameters are provided, the downloaded data will be filtered.
    """
    try:
        # Get the dataset
        dataset = db.query(UploadedFile).filter(UploadedFile.id == dataset_id).first()
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")
        
        # Get the appropriate data file path and load the dataset
        data_path = get_data_file_path(dataset)
        
        # Check if file exists
        if not os.path.exists(data_path):
            raise HTTPException(status_code=404, detail="Dataset file not found")
        
        # Load the data using our helper function
        df = load_dataset_as_dataframe(data_path, dataset.type)
        
        # Handle NaN values to avoid comparison issues for all cases
        df = df.fillna('')
        
        # Apply filter if filter parameters are provided
        if column and operator and value is not None:
            # Check if column exists
            if column not in df.columns:
                raise HTTPException(status_code=400, detail=f"Column '{column}' not found in dataset")
            
            # Add debug logging
            logger.info(f"Filtering dataset: column={column}, operator={operator}, value={value}")
            logger.info(f"DataFrame before filtering: {len(df)} rows")
            
            # Filter the data using the same logic as in filter_dataset endpoint
            col_data = df[column]
            
            # Determine the data type for comparison
            if pd.api.types.is_numeric_dtype(col_data) and not pd.api.types.is_bool_dtype(col_data):
                try:
                    # Try to convert value to numeric for comparison
                    numeric_value = pd.to_numeric(value)
                    # Apply filter based on operator with numeric comparison
                    if operator == "eq":
                        filtered_df = df[col_data == numeric_value]
                    elif operator == "neq":
                        filtered_df = df[col_data != numeric_value]
                    elif operator == "gt":
                        filtered_df = df[col_data > numeric_value]
                    elif operator == "lt":
                        filtered_df = df[col_data < numeric_value]
                    elif operator == "gte":
                        filtered_df = df[col_data >= numeric_value]
                    elif operator == "lte":
                        filtered_df = df[col_data <= numeric_value]
                    elif operator == "contains":
                        # For numeric columns, contains is treated as equality
                        filtered_df = df[col_data == numeric_value]
                    
                    # Check if we got any results
                    if len(filtered_df) == 0:
                        logger.warning(f"Numeric filtering returned no results, trying string comparison")
                        # If no results, try string comparison as fallback
                        str_col_data = col_data.astype(str)
                        str_value = str(value)
                        
                        if operator == "eq":
                            filtered_df = df[str_col_data == str_value]
                        elif operator == "neq":
                            filtered_df = df[str_col_data != str_value]
                        elif operator == "contains":
                            filtered_df = df[str_col_data.str.contains(str_value, na=False)]
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed numeric comparison: {str(e)}, falling back to string")
                    # Fall back to string comparison
                    str_col_data = col_data.astype(str)
                    str_value = str(value)
                    
                    if operator == "eq":
                        filtered_df = df[str_col_data == str_value]
                    elif operator == "neq":
                        filtered_df = df[str_col_data != str_value]
                    elif operator == "contains":
                        filtered_df = df[str_col_data.str.contains(str_value, na=False)]
                    else:
                        # For other operators, we can't do meaningful string comparison
                        # so we'll return an empty DataFrame
                        filtered_df = df.head(0)
            else:
                # For non-numeric columns, do string comparison
                str_col_data = col_data.astype(str)
                str_value = str(value)
                
                if operator == "eq":
                    filtered_df = df[str_col_data == str_value]
                elif operator == "neq":
                    filtered_df = df[str_col_data != str_value]
                elif operator == "contains":
                    filtered_df = df[str_col_data.str.contains(str_value, na=False)]
                else:
                    # For other operators with non-numeric data, return error
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Operator '{operator}' not supported for non-numeric column '{column}'"
                    )
            
            # Use the filtered DataFrame
            df = filtered_df
            logger.info(f"DataFrame after filtering: {len(df)} rows")
        
        # Apply row limit if specified
        if max_rows is not None and max_rows > 0:
            df = df.head(max_rows)
            logger.info(f"Applied row limit: {max_rows}, resulting in {len(df)} rows")
        
        # Convert to the requested format
        if file_format.lower() == 'csv':
            output = io.StringIO()
            df.to_csv(output, index=False)
            content = output.getvalue()
            media_type = "text/csv"
            filename = f"{dataset.dataset or dataset.filename.split('.')[0]}_export.csv"
        elif file_format.lower() == 'json':
            # Convert to JSON
            json_str = df.to_json(orient='records', date_format='iso')
            content = json_str
            media_type = "application/json"
            filename = f"{dataset.dataset or dataset.filename.split('.')[0]}_export.json"
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported export format: {file_format}")
        
        # Create a streaming response
        response = StreamingResponse(
            iter([content]), 
            media_type=media_type
        )
        
        # Set the content disposition header for download
        response.headers["Content-Disposition"] = f"attachment; filename={filename}"
        
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading dataset: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to download dataset: {str(e)}")

@router.get("/datasets")
async def get_datasets(
    db: Session = Depends(get_db),
    current_user: User = Depends(has_permission("datapuur:read")),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = None
):
    """
    Get a list of available datasets for export.
    """
    try:
        # Query for uploaded files
        query = db.query(UploadedFile)
        
        # Apply search filter if provided
        if search:
            # Search by filename, type, or uploaded_by
            query = query.filter(
                (UploadedFile.filename.ilike(f"%{search}%")) |
                (UploadedFile.type.ilike(f"%{search}%")) |
                (UploadedFile.uploaded_by.ilike(f"%{search}%")) |
                (UploadedFile.dataset.ilike(f"%{search}%"))
            )
        
        # Get total count for pagination
        total_count = query.count()
        
        # Apply pagination
        offset = (page - 1) * limit
        datasets = query.order_by(UploadedFile.uploaded_at.desc()).offset(offset).limit(limit).all()
        
        # Format the results
        result = []
        for dataset in datasets:
            # Only include files that actually exist on disk
            if dataset.path and os.path.exists(dataset.path):
                try:
                    file_size = os.path.getsize(dataset.path)
                    result.append({
                        "id": dataset.id,
                        "name": dataset.filename,
                        "type": dataset.type,
                        "size": file_size,
                        "uploaded_at": dataset.uploaded_at,
                        "uploaded_by": dataset.uploaded_by,
                        "source_type": "file",
                        "row_count": dataset.chunk_size if hasattr(dataset, "chunk_size") else None,
                        "status": "available",
                        "preview_url": f"/api/export/datasets/{dataset.id}/preview",
                        "download_url": f"/api/export/datasets/{dataset.id}/download"
                    })
                except (OSError, IOError) as e:
                    # Skip files that cause errors when checking size
                    logger.warning(f"Error checking file {dataset.path}: {str(e)}")
                    continue
        
        return {
            "datasets": result,
            "total": total_count,
            "page": page,
            "limit": limit
        }
    except Exception as e:
        logger.error(f"Error fetching datasets: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch datasets: {str(e)}")

@router.get("/datasets/{dataset_id}/preview")
async def get_dataset_preview(
    dataset_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(has_permission("datapuur:read"))
):
    """
    Get a paginated preview of a dataset.
    """
    try:
        dataset = db.query(UploadedFile).filter(UploadedFile.id == dataset_id).first()
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")
        
        # Get the appropriate data file path using our helper function
        data_path = get_data_file_path(dataset)
        
        # Check if file exists
        if not os.path.exists(data_path):
            raise HTTPException(status_code=404, detail="Dataset file not found")
            
        # Load the data using our helper function
        df = load_dataset_as_dataframe(data_path, dataset.type)
        
        # Calculate pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        
        # Get total rows
        total_rows = len(df)
        total_pages = (total_rows + page_size - 1) // page_size
        
        # Get the paginated data
        if start_idx >= total_rows:
            paginated_data = []
            columns = df.columns.tolist() if not df.empty else []
        else:
            paginated_df = df.iloc[start_idx:min(end_idx, total_rows)]
            # Convert to list of dictionaries with proper handling of all data types
            # First replace NaN, NaT, etc. with None
            paginated_df = paginated_df.replace({pd.NA: None})
            # Convert any remaining problematic types
            paginated_data = json.loads(paginated_df.to_json(orient='records', date_format='iso'))
            columns = df.columns.tolist()
        
        return {
            "columns": columns,
            "data": paginated_data,
            "page": page,
            "page_size": page_size,
            "total_rows": total_rows,
            "total_pages": total_pages
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching dataset preview: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch dataset preview: {str(e)}")

@router.get("/datasets/{dataset_id}/filter")
async def filter_dataset(
    dataset_id: str,
    column: str,
    value: str,
    operator: str = Query("eq", regex="^(eq|neq|gt|lt|gte|lte|contains)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(has_permission("datapuur:read"))
):
    """
    Filter a dataset based on column values.
    Supported operators: eq (equals), neq (not equals), gt (greater than),
    lt (less than), gte (greater than or equal), lte (less than or equal),
    contains (string contains)
    """
    try:
        dataset = db.query(UploadedFile).filter(UploadedFile.id == dataset_id).first()
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")
        
        # Get the appropriate data file path using our helper function
        data_path = get_data_file_path(dataset)
        
        # Check if file exists
        if not os.path.exists(data_path):
            raise HTTPException(status_code=404, detail="Dataset file not found")
            
        # Load the data using our helper function
        df = load_dataset_as_dataframe(data_path, dataset.type)
        
        # Handle NaN values to avoid comparison issues
        df = df.fillna('')
        
        # Check if column exists
        if column not in df.columns:
            raise HTTPException(status_code=400, detail=f"Column '{column}' not found in dataset")
        
        # Apply filter based on operator
        col_data = df[column]
        
        # Determine the data type for comparison
        if pd.api.types.is_numeric_dtype(col_data) and not pd.api.types.is_bool_dtype(col_data):
            try:
                # Try to convert value to numeric for comparison
                numeric_value = pd.to_numeric(value)
                # Apply filter based on operator with numeric comparison
                if operator == "eq":
                    filtered_df = df[col_data == numeric_value]
                elif operator == "neq":
                    filtered_df = df[col_data != numeric_value]
                elif operator == "gt":
                    filtered_df = df[col_data > numeric_value]
                elif operator == "lt":
                    filtered_df = df[col_data < numeric_value]
                elif operator == "gte":
                    filtered_df = df[col_data >= numeric_value]
                elif operator == "lte":
                    filtered_df = df[col_data <= numeric_value]
                elif operator == "contains":
                    # For numeric columns, contains is treated as equality
                    filtered_df = df[col_data == numeric_value]
                
                # Check if we got any results
                if len(filtered_df) == 0:
                    # If no results, try string comparison as fallback
                    str_col_data = col_data.astype(str)
                    str_value = str(value)
                    
                    if operator == "eq":
                        filtered_df = df[str_col_data == str_value]
                    elif operator == "neq":
                        filtered_df = df[str_col_data != str_value]
                    elif operator == "contains":
                        filtered_df = df[str_col_data.str.contains(str_value, na=False)]
            except (ValueError, TypeError):
                # Fall back to string comparison
                str_col_data = col_data.astype(str)
                str_value = str(value)
                
                if operator == "eq":
                    filtered_df = df[str_col_data == str_value]
                elif operator == "neq":
                    filtered_df = df[str_col_data != str_value]
                elif operator == "contains":
                    filtered_df = df[str_col_data.str.contains(str_value, na=False)]
                else:
                    # For other operators, we can't do meaningful string comparison
                    # so we'll return an empty DataFrame
                    filtered_df = df.head(0)
        else:
            # For non-numeric columns, do string comparison
            str_col_data = col_data.astype(str)
            str_value = str(value)
            
            if operator == "eq":
                filtered_df = df[str_col_data == str_value]
            elif operator == "neq":
                filtered_df = df[str_col_data != str_value]
            elif operator == "contains":
                filtered_df = df[str_col_data.str.contains(str_value, na=False)]
            else:
                # For other operators with non-numeric data, return error
                raise HTTPException(
                    status_code=400, 
                    detail=f"Operator '{operator}' not supported for non-numeric column '{column}'"
                )
        
        # Calculate pagination
        total_rows = len(filtered_df)
        total_pages = (total_rows + page_size - 1) // page_size
        
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        
        # Get the paginated data
        if start_idx >= total_rows:
            paginated_data = []
        else:
            paginated_df = filtered_df.iloc[start_idx:min(end_idx, total_rows)]
            # Convert to list of dictionaries with proper handling of all data types
            # First replace NaN, NaT, etc. with None
            paginated_df = paginated_df.replace({pd.NA: None})
            # Convert any remaining problematic types
            paginated_data = json.loads(paginated_df.to_json(orient='records', date_format='iso'))
        
        return {
            "columns": df.columns.tolist(),
            "data": paginated_data,
            "page": page,
            "page_size": page_size,
            "total_rows": total_rows,
            "total_pages": total_pages,
            "filter": {
                "column": column,
                "operator": operator,
                "value": value
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error filtering dataset: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to filter dataset: {str(e)}")

@router.get("/datasets/{dataset_id}/download")
async def download_dataset(
    dataset_id: str,
    format: str = Query("csv", regex="^(csv|json)$"),
    column: Optional[str] = None,
    operator: str = Query("eq", regex="^(eq|neq|gt|lt|gte|lte|contains)$"),
    value: Optional[str] = None,
    max_rows: Optional[int] = Query(None, ge=1, description="Maximum number of rows to include in the download"),
    db: Session = Depends(get_db),
    current_user: User = Depends(has_permission("datapuur:read"))
):
    """
    Download a dataset as CSV or JSON. Optionally apply filters and row limits.
    """
    try:
        dataset = db.query(UploadedFile).filter(UploadedFile.id == dataset_id).first()
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")
        
        # Get the appropriate data file path using our helper function
        data_path = get_data_file_path(dataset)
        
        # Check if file exists
        if not os.path.exists(data_path):
            raise HTTPException(status_code=404, detail="Dataset file not found")
            
        # Load the data using our helper function
        df = load_dataset_as_dataframe(data_path, dataset.type)
        
        # Apply filter if provided
        if column and value:
            if column not in df.columns:
                raise HTTPException(status_code=400, detail=f"Column '{column}' not found in dataset")
            
            # Apply filter based on operator
            if operator == "eq":
                df = df[df[column] == value]
            elif operator == "neq":
                df = df[df[column] != value]
            elif operator == "gt":
                df = df[df[column] > value]
            elif operator == "lt":
                df = df[df[column] < value]
            elif operator == "gte":
                df = df[df[column] >= value]
            elif operator == "lte":
                df = df[df[column] <= value]
            elif operator == "contains":
                df = df[df[column].astype(str).str.contains(value, na=False)]
        
        # Apply row limit if specified
        if max_rows is not None and max_rows > 0:
            df = df.head(max_rows)
        
        # Use the dataset name (with fallback to filename without extension) for the export file
        filename_base = dataset.dataset if dataset.dataset else os.path.splitext(dataset.filename)[0]
        
        # Convert to the requested format
        if format.lower() == 'csv':
            output = io.StringIO()
            df.to_csv(output, index=False)
            
            # Create a streaming response
            response = StreamingResponse(
                iter([output.getvalue()]), 
                media_type="text/csv"
            )
            
            # Set the content disposition header for download
            response.headers["Content-Disposition"] = f"attachment; filename={filename_base}_export.csv"
        elif format.lower() == 'json':
            # Convert to JSON
            json_str = df.to_json(orient='records', date_format='iso')
            
            # Create a streaming response
            response = StreamingResponse(
                iter([json_str]), 
                media_type="application/json"
            )
            
            # Set the content disposition header for download
            response.headers["Content-Disposition"] = f"attachment; filename={filename_base}_export.json"
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported export format: {format}")
        
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading dataset: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to download dataset: {str(e)}")
