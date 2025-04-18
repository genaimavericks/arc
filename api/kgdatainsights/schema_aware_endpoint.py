"""
Schema-Aware Query Endpoint
Provides a dedicated API endpoint for the schema-aware agent.
"""

from fastapi import APIRouter, Depends, HTTPException, Response
from typing import Optional, Dict, Any, List, Union
from datetime import datetime, date
import json
import os
import traceback
from neo4j.time import Date, Time, DateTime
from pydantic.json import pydantic_encoder

from .data_insights_api import (
    QueryRequest, 
    QueryResponse,
    query_history,
    HISTORY_DIR,
    analyze_data_for_visualization
)
from .agent.schema_aware_agent import get_schema_aware_assistant
from ..models import User, Schema
from ..auth import has_any_permission
from ..database import SessionLocal

# Custom JSON encoder for Neo4j types
class Neo4jJsonEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles Neo4j temporal types"""
    
    def default(self, obj):
        # Handle Neo4j date types
        if isinstance(obj, Date):
            return obj.iso_format()  # Convert to ISO format string
        elif isinstance(obj, Time):
            return obj.iso_format()  # Convert to ISO format string
        elif isinstance(obj, DateTime):
            return obj.iso_format()  # Convert to ISO format string
        # Handle other special types
        try:
            return pydantic_encoder(obj)
        except TypeError:
            pass
        # Default handling
        try:
            return super().default(obj)
        except TypeError:
            return str(obj)  # Last resort: convert to string


# Helper function to convert Neo4j objects in dictionaries
def sanitize_neo4j_objects(data: Any) -> Any:
    """Recursively sanitize Neo4j objects in data structures"""
    if isinstance(data, dict):
        return {k: sanitize_neo4j_objects(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_neo4j_objects(item) for item in data]
    elif isinstance(data, (Date, Time, DateTime)):
        return data.iso_format()
    else:
        return data


# Create a router for schema-aware endpoints
router = APIRouter(prefix="/schema-insights", tags=["Schema-Aware Insights"])

@router.post("/{source_id}/query", response_model=QueryResponse)
async def process_schema_aware_query(
    source_id: str, 
    request: QueryRequest,
    current_user: User = Depends(has_any_permission(["kginsights:read"]))
):
    # Add detailed debug logging
    print(f"DEBUG: Processing schema-aware query for source_id='{source_id}', query='{request.query}'")
    print(f"DEBUG: User '{current_user.username}' requesting schema-aware query")
    """
    Process a query using the schema-aware agent and record it in query history.
    This endpoint automatically uses the schema-aware agent that manages Neo4j schema and prompt generation.
    
    Args:
        source_id: The ID of the data source (Neo4j database name from the configuration)
        request: The query request containing the query string
        
    Returns:
        QueryResponse: The response containing the query result with visualization if available
    """
    try:
        # Get or create the schema-aware assistant for this source
        # First fetch the schema for this source_id
        db = SessionLocal()
        result = db.query(Schema.db_id, Schema.schema).filter(Schema.db_id == source_id).first()
        
        if not result or not result.schema:
            return QueryResponse(
                schema_id=source_id,
                query=request.query,
                result="Knowledge graph schema is not available. Please ensure the schema is properly generated.",
                timestamp=datetime.now()
            )
        
        # Use source_id as both db_id and schema_id since it's the same in this context
        assistant = get_schema_aware_assistant(source_id, source_id, schema=result.schema)
        
        # Get the answer from the schema-aware agent
        result = assistant.query(request.query)
        
        # Extract the result and intermediate steps
        answer = result.get("result", "No result found")
        # Handle intermediate_steps - ensure it's a dictionary or None
        intermediate_steps = result.get("intermediate_steps")
        if intermediate_steps and not isinstance(intermediate_steps, dict):
            # Convert to dict if it's not already
            try:
                if isinstance(intermediate_steps, list):
                    intermediate_steps = {"steps": intermediate_steps}
                else:
                    intermediate_steps = {"data": str(intermediate_steps)}
            except Exception as e:
                print(f"Error converting intermediate_steps to dict: {e}")
                intermediate_steps = None
        
        # Create the response
        timestamp = datetime.now()
        
        # Analyze data for visualization if intermediate_steps exists
        visualization = None
        if intermediate_steps:
            try:
                # Use the custom Neo4j encoder for intermediate steps
                sanitized_steps = sanitize_neo4j_objects(intermediate_steps)
                print(f"Analyzing intermediate steps for visualization: {json.dumps(sanitized_steps, cls=Neo4jJsonEncoder)[:300]}...")
                visualization = analyze_data_for_visualization(sanitized_steps)
                
                # Log visualization result
                if visualization:
                    print(f"Visualization generated: {visualization.type}")
                else:
                    print("No visualization generated from data")
            except Exception as e:
                print(f"Error analyzing data for visualization: {e}")
        
        # Record the query in history
        item_id = f"{source_id}_{timestamp.strftime('%Y%m%d%H%M%S')}_{hash(request.query) % 1000}"
        history_item = {
            "id": item_id,
            "source_id": source_id,
            "query": request.query,
            "result": answer,
            "timestamp": timestamp.isoformat()
        }
        
        # Initialize history for this source if needed
        if source_id not in query_history:
            query_history[source_id] = []
            
        # Add to history
        query_history[source_id].append(history_item)
        
        # Save to disk
        try:
            history_file = os.path.join(HISTORY_DIR, f"{source_id}_history.json")
            with open(history_file, 'w') as f:
                # Use the custom encoder to handle Neo4j types
                json.dump(query_history[source_id], f, cls=Neo4jJsonEncoder, indent=2)
        except Exception as e:
            print(f"Error saving query history: {str(e)}")
        
        # Sanitize Neo4j objects in intermediate_steps for serialization
        if intermediate_steps:
            sanitized_intermediate_steps = sanitize_neo4j_objects(intermediate_steps)
        else:
            sanitized_intermediate_steps = None
        
        # Create response with sanitized data
        response = QueryResponse(
            source_id=source_id,
            query=request.query,
            result=answer,
            intermediate_steps=sanitized_intermediate_steps,
            visualization=visualization
        )
        
        # Log response for debugging
        print(f"Returned query result with sanitized Neo4j objects")
        
        return response
    except Exception as e:
        tb_str = traceback.format_exc()
        print(f"Error processing schema-aware query: {str(e)}\nTraceback: {tb_str}")
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")
