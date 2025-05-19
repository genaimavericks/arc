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
from api.auth import get_current_user

router = APIRouter(prefix="/api/export", tags=["Export"])
logger = logging.getLogger(__name__)

@router.get("/download")
async def download_dataset(
    dataset_id: str,
    file_format: str = Query("csv", regex="^(csv|json)$"),
    column: Optional[str] = None,
    operator: Optional[str] = None,
    value: Optional[str] = None,
    max_rows: Optional[int] = Query(None, ge=1, description="Maximum number of rows to include in the download"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
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
        
        # Check if file exists
        if not os.path.exists(dataset.path):
            raise HTTPException(status_code=404, detail="Dataset file not found")
        
        # Load the data using pandas
        if dataset.type.lower() == 'csv':
            df = pd.read_csv(dataset.path)
        elif dataset.type.lower() == 'json':
            df = pd.read_json(dataset.path)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {dataset.type}")
        
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
                        # Try string comparison as fallback
                        str_col_data = col_data.astype(str)
                        if operator == "eq":
                            filtered_df = df[str_col_data == str(value)]
                        elif operator == "neq":
                            filtered_df = df[str_col_data != str(value)]
                        elif operator == "contains":
                            filtered_df = df[str_col_data.str.contains(str(value), case=False, na=False)]
                    
                    df = filtered_df
                except (ValueError, TypeError) as e:
                    logger.warning(f"Numeric conversion failed: {str(e)}, using string comparison")
                    # If conversion fails, use string comparison
                    str_col_data = col_data.astype(str)
                    if operator == "eq":
                        df = df[str_col_data == str(value)]
                    elif operator == "neq":
                        df = df[str_col_data != str(value)]
                    elif operator == "contains":
                        df = df[str_col_data.str.contains(str(value), case=False, na=False)]
                    else:
                        # Other operators don't make sense for non-numeric comparison
                        raise HTTPException(status_code=400, detail=f"Operator '{operator}' not supported for non-numeric values")
            else:
                # String comparison for non-numeric columns
                str_col_data = col_data.astype(str)
                str_value = str(value)
                
                logger.info(f"String comparison: column={column}, value={str_value}")
                
                if operator == "eq":
                    df = df[str_col_data.str.lower() == str_value.lower()]
                elif operator == "neq":
                    df = df[str_col_data.str.lower() != str_value.lower()]
                elif operator == "contains":
                    df = df[str_col_data.str.contains(str_value, case=False, na=False)]
                else:
                    # Other operators don't make sense for non-numeric comparison
                    raise HTTPException(status_code=400, detail=f"Operator '{operator}' not supported for string values")
            
            logger.info(f"DataFrame after filtering: {len(df)} rows")
            
            # If no rows match the filter, return an empty DataFrame with the same columns
            if len(df) == 0:
                logger.warning("Filter returned no results")
                # Return empty DataFrame with same columns instead of raising an error
                df = pd.DataFrame(columns=df.columns)
        
        # Apply max_rows limit if specified
        if max_rows is not None and len(df) > 0:
            logger.info(f"Limiting output to {max_rows} rows (from {len(df)} total rows)")
            df = df.head(max_rows)
        
        # Prepare the file for download
        buffer = io.BytesIO()
        
        # Convert to the requested format
        filename = os.path.splitext(dataset.filename)[0]
        if column and operator and value:
            filename = f"{filename}_filtered"
        
        if file_format.lower() == 'csv':
            df.to_csv(buffer, index=False)
            media_type = "text/csv"
            filename = f"{filename}.csv"
        else:  # json
            df.to_json(buffer, orient='records')
            media_type = "application/json"
            filename = f"{filename}.json"
        
        # Reset buffer position
        buffer.seek(0)
        
        # Return the file as a streaming response
        return StreamingResponse(
            buffer, 
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    
    except Exception as e:
        logger.error(f"Error downloading dataset: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error downloading dataset: {str(e)}")


@router.get("/datasets")
async def get_datasets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = None
):
    """
    Get a list of available datasets for export.
    """
    try:
        # Query uploaded files that are available for export
        query = db.query(UploadedFile)
        
        # Apply search filter if provided
        if search:
            query = query.filter(UploadedFile.filename.ilike(f"%{search}%"))
        
        # Apply sorting (newest first)
        query = query.order_by(UploadedFile.uploaded_at.desc())
        
        # Get total count before pagination
        total = query.count()
        
        # Apply pagination
        query = query.offset((page - 1) * limit).limit(limit)
        
        # Execute query
        datasets = query.all()
        
        # Convert to response format
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
                        "uploaded_at": dataset.uploaded_at.isoformat(),
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
            "total": total,
            "page": page,
            "limit": limit,
            "datasets": result
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
    current_user: User = Depends(get_current_user)
):
    """
    Get a paginated preview of a dataset.
    """
    try:
        dataset = db.query(UploadedFile).filter(UploadedFile.id == dataset_id).first()
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")
        
        # Get the data path from the dataset
        data_path = dataset.path
        
        # Load the data using pandas
        if dataset.type.lower() == 'csv':
            df = pd.read_csv(data_path)
        elif dataset.type.lower() == 'json':
            df = pd.read_json(data_path)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {dataset.type}")
        
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
    current_user: User = Depends(get_current_user)
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
        
        # Get the data path from the dataset
        data_path = dataset.path
        
        # Load the data using pandas
        if dataset.type.lower() == 'csv':
            df = pd.read_csv(data_path)
        elif dataset.type.lower() == 'json':
            df = pd.read_json(data_path)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {dataset.type}")
        
        # Check if column exists
        if column not in df.columns:
            raise HTTPException(status_code=400, detail=f"Column '{column}' not found in dataset")
        
        # Handle data types properly for comparison
        try:
            # Convert column to appropriate type for comparison
            col_data = df[column]
            
            # Determine the data type for comparison
            if pd.api.types.is_numeric_dtype(col_data):
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
                        # For numeric columns, convert to string for contains operation
                        filtered_df = df[col_data.astype(str).str.contains(value, na=False)]
                except (ValueError, TypeError):
                    # If conversion fails, use string comparison
                    logger.warning(f"Could not convert value '{value}' to numeric for column '{column}'. Using string comparison.")
                    if operator == "contains":
                        filtered_df = df[col_data.astype(str).str.contains(value, na=False)]
                    else:
                        # Default to empty result for incompatible types
                        filtered_df = df[df.index.isin([])]
            else:
                # For non-numeric columns, use string operations
                if operator == "eq":
                    filtered_df = df[col_data.astype(str) == value]
                elif operator == "neq":
                    filtered_df = df[col_data.astype(str) != value]
                elif operator == "gt":
                    filtered_df = df[col_data.astype(str) > value]
                elif operator == "lt":
                    filtered_df = df[col_data.astype(str) < value]
                elif operator == "gte":
                    filtered_df = df[col_data.astype(str) >= value]
                elif operator == "lte":
                    filtered_df = df[col_data.astype(str) <= value]
                elif operator == "contains":
                    filtered_df = df[col_data.astype(str).str.contains(value, na=False)]
        except Exception as e:
            logger.error(f"Error applying filter: {str(e)}")
            # Return empty dataframe if filtering fails
            filtered_df = df.iloc[0:0]
        
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
    format: str = Query("csv", regex="^(csv)$"),
    column: Optional[str] = None,
    value: Optional[str] = None,
    operator: str = Query("eq", regex="^(eq|neq|gt|lt|gte|lte|contains)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Download a dataset as CSV. Optionally apply filters.
    """
    try:
        dataset = db.query(UploadedFile).filter(UploadedFile.id == dataset_id).first()
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")
        
        # Get the data path from the dataset
        data_path = dataset.path
        
        # Load the data using pandas
        if dataset.type.lower() == 'csv':
            df = pd.read_csv(data_path)
        elif dataset.type.lower() == 'json':
            df = pd.read_json(data_path)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {dataset.type}")
        
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
        
        # Convert to CSV
        output = io.StringIO()
        df.to_csv(output, index=False)
        
        # Create a streaming response
        response = StreamingResponse(
            iter([output.getvalue()]), 
            media_type="text/csv"
        )
        
        # Set the content disposition header for download
        filename = f"{dataset.filename.split('.')[0]}_export.csv"
        response.headers["Content-Disposition"] = f"attachment; filename={filename}"
        
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading dataset: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to download dataset: {str(e)}")
