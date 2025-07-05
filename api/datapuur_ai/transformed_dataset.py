"""
DataPuur AI Transformed Dataset Router - API endpoints for transformed datasets
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
import pandas as pd
import json
import os
from sqlalchemy.orm import Session
from typing import List
import logging
from pathlib import Path
from datetime import datetime

from api.models import User, get_db
from api.auth import has_any_permission, log_activity
from .models import TransformedDataset
from .schemas import (
    TransformedDatasetResponse, DatasetMetadataUpdate
)

logger = logging.getLogger(__name__)

# Create data directory if it doesn't exist
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# Create router
router = APIRouter(tags=["datapuur-ai-transformed-datasets"])

# Maximum number of rows to return in preview
MAX_PREVIEW_ROWS = 100


@router.get("/transformed-datasets", response_model=List[TransformedDatasetResponse])
async def list_transformed_datasets(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(has_any_permission(["datapuur:read"])),
    db: Session = Depends(get_db)
):
    """List all transformed datasets"""
    try:
        offset = (page - 1) * limit
        datasets = db.query(TransformedDataset).order_by(
            TransformedDataset.created_at.desc()
        ).offset(offset).limit(limit).all()
        
        # Convert SQLAlchemy models to Pydantic models to ensure proper serialization
        return [
            TransformedDatasetResponse(
                id=dataset.id,
                name=dataset.name,
                description=dataset.description,
                source_file_path=dataset.source_file_path,
                source_file_id=dataset.source_file_id,
                transformed_file_path=dataset.transformed_file_path,
                transformation_plan_id=dataset.transformation_plan_id,
                job_id=dataset.job_id,
                metadata=dataset.dataset_metadata if isinstance(dataset.dataset_metadata, dict) else {},
                column_metadata=dataset.column_metadata if isinstance(dataset.column_metadata, dict) else {},
                row_count=dataset.row_count,
                column_count=dataset.column_count,
                file_size_bytes=dataset.file_size_bytes,
                data_summary=dataset.data_summary,
                created_at=dataset.created_at,
                created_by=dataset.created_by,
                updated_at=dataset.updated_at
            )
            for dataset in datasets
        ]
    except Exception as e:
        logger.error(f"Error listing transformed datasets: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list datasets: {str(e)}")


@router.get("/transformed-datasets/{dataset_id}", response_model=TransformedDatasetResponse)
async def get_transformed_dataset(
    dataset_id: str,
    current_user: User = Depends(has_any_permission(["datapuur:read"])),
    db: Session = Depends(get_db)
):
    """Get a specific transformed dataset by ID"""
    dataset = db.query(TransformedDataset).filter(TransformedDataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Transformed dataset not found")
    
    # Convert SQLAlchemy model to Pydantic model for proper serialization
    return TransformedDatasetResponse(
        id=dataset.id,
        name=dataset.name,
        description=dataset.description,
        source_file_path=dataset.source_file_path,
        source_file_id=dataset.source_file_id,
        transformed_file_path=dataset.transformed_file_path,
        transformation_plan_id=dataset.transformation_plan_id,
        job_id=dataset.job_id,
        metadata=dataset.dataset_metadata if isinstance(dataset.dataset_metadata, dict) else {},
        column_metadata=dataset.column_metadata if isinstance(dataset.column_metadata, dict) else {},
        row_count=dataset.row_count,
        column_count=dataset.column_count,
        file_size_bytes=dataset.file_size_bytes,
        data_summary=dataset.data_summary,
        created_at=dataset.created_at,
        created_by=dataset.created_by,
        updated_at=dataset.updated_at
    )


@router.put("/transformed-datasets/{dataset_id}/metadata", response_model=TransformedDatasetResponse)
async def update_dataset_metadata(
    dataset_id: str,
    metadata_update: DatasetMetadataUpdate,
    current_user: User = Depends(has_any_permission(["datapuur:write"])),
    db: Session = Depends(get_db)
):
    """Update metadata for a transformed dataset"""
    dataset = db.query(TransformedDataset).filter(TransformedDataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Transformed dataset not found")
    
    # Update metadata fields
    if metadata_update.metadata:
        dataset.dataset_metadata = {**dataset.dataset_metadata, **metadata_update.metadata}
    
    if metadata_update.column_metadata:
        dataset.column_metadata = {**dataset.column_metadata, **metadata_update.column_metadata}
    
    if metadata_update.description:
        dataset.description = metadata_update.description
    
    dataset.updated_at = datetime.utcnow()
    db.commit()
    
    # Convert SQLAlchemy model to Pydantic model for proper serialization
    return TransformedDatasetResponse(
        id=dataset.id,
        name=dataset.name,
        description=dataset.description,
        source_file_path=dataset.source_file_path,
        source_file_id=dataset.source_file_id,
        transformed_file_path=dataset.transformed_file_path,
        transformation_plan_id=dataset.transformation_plan_id,
        job_id=dataset.job_id,
        metadata=dataset.dataset_metadata if isinstance(dataset.dataset_metadata, dict) else {},
        column_metadata=dataset.column_metadata if isinstance(dataset.column_metadata, dict) else {},
        row_count=dataset.row_count,
        column_count=dataset.column_count,
        file_size_bytes=dataset.file_size_bytes,
        data_summary=dataset.data_summary,
        created_at=dataset.created_at,
        created_by=dataset.created_by,
        updated_at=dataset.updated_at
    )


@router.get("/download/{dataset_id}")
async def download_transformed_file(
    dataset_id: str,
    current_user: User = Depends(has_any_permission(["datapuur:read"])),
    db: Session = Depends(get_db)
):
    """Download transformed dataset as CSV file"""
    try:
        # Retrieve the transformed dataset record
        dataset = db.query(TransformedDataset).filter(TransformedDataset.id == dataset_id).first()
        if not dataset:
            raise HTTPException(status_code=404, detail="Transformed dataset not found")
            
        # Get the file path from the dataset record
        if not dataset.transformed_file_path:
            raise HTTPException(status_code=404, detail="No transformed file available for this dataset")
            
        # Construct file path
        file_path = Path(dataset.transformed_file_path)
        
        if not file_path.exists():
            # Try with relative path
            file_path = Path(__file__).parent.parent / "data" / file_path.name
            if not file_path.exists():
                raise HTTPException(status_code=404, detail="Transformed dataset file not found")
        
        # Generate a descriptive filename with timestamp
        csv_filename = f"{dataset.name.replace(' ', '_')}_{dataset_id}.csv"
        
        # Log the download
        log_activity(
            db,
            current_user.username,
            "download_transformed_dataset",
            {"dataset_id": dataset_id, "dataset_name": dataset.name}
        )
        
        # Return file as CSV
        return FileResponse(
            path=str(file_path),
            filename=csv_filename,
            media_type="text/csv"
        )
    except Exception as e:
        logger.error(f"Error downloading transformed dataset {dataset_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transformed-datasets/{dataset_id}/preview")
async def preview_transformed_dataset(
    dataset_id: str,
    rows: int = Query(50, ge=1, le=MAX_PREVIEW_ROWS),
    current_user: User = Depends(has_any_permission(["datapuur:read"])),
    db: Session = Depends(get_db)
):
    """Preview data from a transformed dataset"""
    try:
        # Retrieve the transformed dataset record
        dataset = db.query(TransformedDataset).filter(TransformedDataset.id == dataset_id).first()
        if not dataset:
            raise HTTPException(status_code=404, detail="Transformed dataset not found")
            
        # Get the file path from the dataset record
        if not dataset.transformed_file_path:
            raise HTTPException(status_code=404, detail="No transformed file available for this dataset")
            
        # Construct file path
        file_path = Path(dataset.transformed_file_path)
        
        if not file_path.exists():
            # Try with relative path
            file_path = Path(__file__).parent.parent / "data" / file_path.name
            if not file_path.exists():
                raise HTTPException(status_code=404, detail="Transformed dataset file not found")
        
        # Read the Parquet file with pandas
        df = pd.read_parquet(file_path)
        
        # Get a preview of the data (first N rows)
        preview_df = df.head(rows)
        
        # Convert to records format (list of dictionaries)
        records = preview_df.to_dict(orient='records')
        
        # Log the preview request
        log_activity(
            db,
            current_user.username,
            "preview_transformed_dataset",
            {"dataset_id": dataset_id, "dataset_name": dataset.name, "rows": rows}
        )
        
        # Return preview data
        return {
            "data": records,
            "total_rows": len(df),
            "preview_rows": len(records)
        }
    except Exception as e:
        logger.error(f"Error previewing transformed dataset {dataset_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/transformed-datasets/{dataset_id}")
async def delete_transformed_dataset(
    dataset_id: str,
    current_user: User = Depends(has_any_permission(["datapuur:write", "datapuur:manage"])),
    db: Session = Depends(get_db)
):
    """Delete a transformed dataset"""
    try:
        # Retrieve the transformed dataset record
        dataset = db.query(TransformedDataset).filter(TransformedDataset.id == dataset_id).first()
        if not dataset:
            raise HTTPException(status_code=404, detail="Transformed dataset not found")
        
        # Get the file path from the dataset record
        file_path = None
        if dataset.transformed_file_path:
            # Construct file path
            file_path = Path(dataset.transformed_file_path)
            
            if not file_path.exists():
                # Try with relative path
                file_path = Path(__file__).parent.parent / "data" / file_path.name
        
        # Delete the file if it exists
        try:
            if file_path and file_path.exists():
                os.remove(file_path)
                logger.info(f"Deleted transformed dataset file: {file_path}")
        except Exception as file_error:
            logger.error(f"Error deleting file {file_path}: {str(file_error)}")
            # Continue with database deletion even if file deletion fails
        
        # Delete the database record
        dataset_name = dataset.name
        db.delete(dataset)
        db.commit()
        
        # Log the deletion
        log_activity(
            db,
            current_user.username,
            "delete_transformed_dataset",
            {"dataset_id": dataset_id, "dataset_name": dataset_name}
        )
        
        return JSONResponse(
            status_code=200,
            content={"message": f"Transformed dataset '{dataset_name}' deleted successfully"}
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting transformed dataset {dataset_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transformed-datasets/{dataset_id}/schema")
async def get_transformed_dataset_schema(
    dataset_id: str,
    current_user: User = Depends(has_any_permission(["datapuur:read"])),
    db: Session = Depends(get_db)
):
    """Get schema information for a transformed dataset"""
    try:
        # Retrieve the transformed dataset record
        dataset = db.query(TransformedDataset).filter(TransformedDataset.id == dataset_id).first()
        if not dataset:
            raise HTTPException(status_code=404, detail="Transformed dataset not found")
            
        # Get the file path from the dataset record
        if not dataset.transformed_file_path:
            raise HTTPException(status_code=404, detail="No transformed file available for this dataset")
            
        # Construct file path
        file_path = Path(dataset.transformed_file_path)
        
        if not file_path.exists():
            # Try with relative path
            file_path = Path(__file__).parent.parent / "data" / file_path.name
            if not file_path.exists():
                raise HTTPException(status_code=404, detail="Transformed dataset file not found")
        
        # Read the Parquet file with pandas
        df = pd.read_parquet(file_path)  # Read Parquet file
        df = df.head(5)  # Only need a few rows to get schema
        
        # Get column information
        columns = []
        for column_name in df.columns:
            column_data = {
                "name": column_name,
                "type": str(df[column_name].dtype),
                "sample_values": df[column_name].head(3).tolist()
            }
            columns.append(column_data)
        
        # If column metadata exists in the dataset record, incorporate it
        if dataset.column_metadata and isinstance(dataset.column_metadata, dict):
            for column in columns:
                if column["name"] in dataset.column_metadata:
                    column.update(dataset.column_metadata[column["name"]])
        
        # Log the schema request
        log_activity(
            db,
            current_user.username,
            "get_transformed_dataset_schema",
            {"dataset_id": dataset_id, "dataset_name": dataset.name}
        )
        
        # Return schema information
        return {
            "dataset_id": dataset_id,
            "dataset_name": dataset.name,
            "columns": columns,
            "row_count": dataset.row_count or 0,
            "column_count": dataset.column_count or len(columns)
        }
    except Exception as e:
        logger.error(f"Error getting schema for transformed dataset {dataset_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
