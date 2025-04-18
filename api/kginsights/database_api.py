from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, List, Optional
from ..auth import has_any_permission
from ..models import User, Schema
from ..db_config import SessionLocal, get_db
import json
import os
from pathlib import Path

# Models
class DatabaseConnectionParams(BaseModel):
    username: str
    database: str
    uri: str
    password: str

class DatabaseInfo(BaseModel):
    name: str
    connection_params: Optional[DatabaseConnectionParams] = None

class DatabaseListResponse(BaseModel):
    databases: List[str]
    
class ErrorResponse(BaseModel):
    error: str
    detail: str

# Router
router = APIRouter(prefix="/graph", tags=["graph"])

# Helper function to read the JSON config file
def get_database_config():
    try:
        json_path = Path(__file__).parent / "neo4j.databases.json"
        with open(json_path, 'r') as file:
            return json.load(file)
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error loading database configuration: {str(e)}"
        )

# Utility function to get connection params from JSON format
def parse_connection_params(params_dict):
    if not params_dict:
        return None
    
    # JSON format already has the correct structure
    # Just return the dictionary directly
    return params_dict

# API Routes

class SchemaDetails(BaseModel):
    """Schema details model for response"""
    id: int
    name: str

class SchemaListResponse(BaseModel):
    """Response model for schema list"""
    schemas: List[SchemaDetails]

@router.get("/db", response_model=DatabaseListResponse)
async def list_graphs(
    current_user: User = Depends(has_any_permission(["kginsights:read"]))
):
    """
    Get a list of all available knowledge graphs.
    
    Returns:
        List of graph names
    """
    try:
        config = get_database_config()
        return DatabaseListResponse(databases=list(config.keys()))
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error retrieving graph list: {str(e)}"
        )


@router.get("/schema", response_model=SchemaListResponse)
async def list_graphs(
    current_user: User = Depends(has_any_permission(["kginsights:read"])),
    db: SessionLocal = Depends(get_db)
):
    """
    Get a list of all loaded schemas for knowledge graphs.
    
    Returns:
        List of schema objects with id and name
    """
    try:
        # Query schemas with db_loaded='yes'
        loaded_schemas = db.query(Schema.id, Schema.name).filter(Schema.db_loaded == 'yes').all()
        
        # Map results to SchemaDetails model
        result = [SchemaDetails(id=schema.id, name=schema.name) for schema in loaded_schemas]
        
        # Return default empty result if no loaded schemas found
        if not result:
            result = [SchemaDetails(id=-100, name="empty")]
        
        print(f"DEBUG: Found {len(result)} loaded schemas")
        return SchemaListResponse(schemas=result)
    except Exception as e:
        print(f"ERROR: Failed to retrieve loaded schemas: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error retrieving loaded schemas: {str(e)}"
        )

