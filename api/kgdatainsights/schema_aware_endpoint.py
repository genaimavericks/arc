"""
Schema-Aware Query Endpoint
Provides a dedicated API endpoint for the schema-aware agent.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, Dict, Any
from datetime import datetime
import json
import os
import traceback

from .data_insights_api import (
    QueryRequest, 
    QueryResponse,
    query_history,
    HISTORY_DIR,
    analyze_data_for_visualization
)
from .agent.schema_aware_agent import get_schema_aware_assistant
from ..models import User
from ..auth import has_any_permission

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
        assistant = get_schema_aware_assistant(source_id)
        
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
                print(f"Analyzing intermediate steps for visualization: {json.dumps(intermediate_steps, default=str)[:300]}...")
                visualization = analyze_data_for_visualization(intermediate_steps)
                
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
                json.dump(query_history[source_id], f, indent=2)
        except Exception as e:
            print(f"Error saving query history: {str(e)}")
        
        # Return the response
        return QueryResponse(
            source_id=source_id,
            query=request.query,
            result=answer,
            intermediate_steps=intermediate_steps,
            visualization=visualization
        )
    except Exception as e:
        tb_str = traceback.format_exc()
        print(f"Error processing schema-aware query: {str(e)}\nTraceback: {tb_str}")
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")
