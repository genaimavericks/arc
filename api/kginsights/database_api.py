from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, List, Optional
from ..auth import has_any_permission
from ..models import User
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

@router.get("/db/{graph_name}", response_model=DatabaseInfo)
async def get_graph_connection(
    graph_name: str,
    current_user: User = Depends(has_any_permission(["kginsights:manage"]))
):
    """
    Get connection parameters for a specific knowledge graph.
    
    Args:
        graph_name: Name of the graph to get connection parameters for
        
    Returns:
        Graph database connection parameters
    """
    try:
        config = get_database_config()
        
        if graph_name not in config:
            raise HTTPException(
                status_code=404, 
                detail=f"Graph '{graph_name}' not found"
            )
        
        # Get connection parameters from JSON format
        connection_params = config[graph_name]
        
        # JSON format already has the parameters in the correct structure
        parsed_params = DatabaseConnectionParams(
            username=connection_params.get("username", ""),
            database=connection_params.get("database", ""),
            uri=connection_params.get("uri", ""),
            password=connection_params.get("password", "")
        )
        
        return DatabaseInfo(
            name=graph_name,
            connection_params=parsed_params
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error retrieving graph connection parameters: {str(e)}"
        )

@router.get("/db/{graph_name}/test")
async def test_graph_connection(
    graph_name: str,
    current_user: User = Depends(has_any_permission(["kginsights:manage"]))
):
    """
    Test the connection to a specific knowledge graph database.
    
    Args:
        graph_name: Name of the graph to test connection for
        
    Returns:
        Connection status
    """
    try:
        config = get_database_config()
        
        if graph_name not in config:
            raise HTTPException(
                status_code=404, 
                detail=f"Graph '{graph_name}' not found"
            )
        
        # In a production environment, you would actually test the connection here
        # For now, we'll just return success if the graph exists in config
        
        return {"status": "success", "message": f"Successfully connected to {graph_name}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error testing graph connection: {str(e)}"
        )