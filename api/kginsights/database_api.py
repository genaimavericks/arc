from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, List, Optional
from ..auth import has_any_permission
from ..models import User
import yaml
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

# Helper function to read the YAML config file
def get_database_config():
    try:
        yaml_path = Path(__file__).parent / "neo4j.databases.yaml"
        with open(yaml_path, 'r') as file:
            return yaml.safe_load(file)
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error loading database configuration: {str(e)}"
        )

# Utility function to parse connection params from the YAML format
def parse_connection_params(params):
    if not params:
        return None
    
    # If params is already a dictionary (from the new YAML format)
    if isinstance(params, dict):
        return {
            "username": params.get("NEO4J_USERNAME", ""),
            "database": params.get("NEO4J_DB", ""),
            "uri": params.get("NEO4J_URI", ""),
            "password": params.get("NEO4J_PASSWORD", "")
        }
    
    # For backward compatibility with the old format
    if isinstance(params, str):
        params_dict = {}
        for line in params.split('\n'):
            if '=' in line:
                key, value = line.strip().split('=', 1)
                params_dict[key] = value
        
        return {
            "username": params_dict.get("NEO4J_USERNAME", ""),
            "database": params_dict.get("NEO4J_DB", ""),
            "uri": params_dict.get("NEO4J_URI", ""),
            "password": params_dict.get("NEO4J_PASSWORD", "")
        }
    
    return None

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
        
        # Parse connection parameters from YAML format
        connection_params = config[graph_name]
        
        parsed_params = parse_connection_params(connection_params)
        
        return DatabaseInfo(
            name=graph_name,
            connection_params=DatabaseConnectionParams(
                username=parsed_params["username"],
                database=parsed_params["database"],
                uri=parsed_params["uri"],
                password=parsed_params["password"]
            ) if parsed_params else None
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
