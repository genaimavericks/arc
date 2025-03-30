from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import asyncio
from datetime import datetime
import json
import os
from .agent.insights_data_agent import get_kg_answer, init_graph
from .visualization_analyzer import analyze_data_for_visualization, GraphData

router = APIRouter(prefix="/datainsights", tags=["Data Insights"])

# In-memory storage for query history (in production, use a database)
query_history = {}

# Directory to store query history and predefined queries as JSON files
HISTORY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "history")
QUERIES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "queries")
os.makedirs(HISTORY_DIR, exist_ok=True)
os.makedirs(QUERIES_DIR, exist_ok=True)

# Sample predefined queries by category
DEFAULT_PREDEFINED_QUERIES = {
    "general": [
        {"id": "general_1", "query": "What are the main entities in this knowledge graph?", "description": "Overview of main entities"}, 
        {"id": "general_2", "query": "How many nodes and relationships are in the graph?", "description": "Graph size statistics"}
    ],
    "relationships": [
        {"id": "rel_1", "query": "What are the most common relationships between entities?", "description": "Common relationship types"},
        {"id": "rel_2", "query": "Show me the most connected nodes in the graph", "description": "Nodes with most connections"}
    ],
    "domain": [
        {"id": "domain_1", "query": "What insights can you provide about this data?", "description": "General domain insights"},
        {"id": "domain_2", "query": "What are the key patterns or trends in this data?", "description": "Pattern identification"}
    ]
}

class QueryRequest(BaseModel):
    """Request model for the query endpoint."""
    query: str
    params: Optional[Dict[str, Any]] = None

class QueryResponse(BaseModel):
    """Response model for the query endpoint."""
    source_id: str
    query: str
    result: str
    intermediate_steps: Optional[Dict[str, Any]] = None
    visualization: Optional[GraphData] = None
    timestamp: datetime = datetime.now()

class HistoricalQuery(BaseModel):
    """Model for a historical query."""
    id: str
    source_id: str
    query: str
    result: str
    timestamp: datetime

class QueryHistoryResponse(BaseModel):
    """Response model for the query history endpoint."""
    source_id: str
    queries: List[HistoricalQuery]

class PredefinedQuery(BaseModel):
    """Model for a predefined query."""
    id: str
    query: str
    category: str
    description: Optional[str] = None

class PredefinedQueriesResponse(BaseModel):
    """Response model for the predefined queries endpoint."""
    source_id: str
    queries: List[PredefinedQuery]

print('$$$$$$$$$$$$$$- Loading data insights')
# API Routes
@router.get('/status')
async def get_status():
    """Return API status."""
    return {"status": "OK"}


@router.post("/{source_id}/visualize", response_model=GraphData)
async def analyze_data_visualization(source_id: str, data: Dict[str, Any]):
    """
    Analyze data and suggest appropriate visualization.
    
    Args:
        source_id: The ID of the data source
        data: The data to analyze
        
    Returns:
        GraphData: The visualization data
    """
    try:
        # Check if data is provided
        if not data:
            raise HTTPException(status_code=400, detail="No data provided for analysis")
        
        # Analyze data for visualization
        visualization = analyze_data_for_visualization(data)
        return visualization
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing data: {str(e)}")


@router.post("/{source_id}/query", response_model=QueryResponse)
async def process_query(source_id: str, request: QueryRequest):
    """
    Process a query against the knowledge graph and record it in the query history.
    
    Args:
        source_id: The ID of the data source
        request: The query request containing the query string
        
    Returns:
        QueryResponse: The response containing the query result
    """
    try:
        # Initialize the graph if needed
        await init_graph()
        
        # Get the answer from the knowledge graph
        result = get_kg_answer(request.query)
        
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
                visualization = analyze_data_for_visualization(intermediate_steps)
            except Exception as e:
                print(f"Error analyzing data for visualization: {e}")
        
        try:
            response = QueryResponse(
                source_id=source_id,
                query=request.query,
                result=answer,
                intermediate_steps=intermediate_steps,
                visualization=visualization,
                timestamp=timestamp
            )
        except Exception as e:
            print(f"Error creating QueryResponse: {e}")
            # Fallback to creating response without intermediate steps
            response = QueryResponse(
                source_id=source_id,
                query=request.query,
                result=answer,
                intermediate_steps=None,
                timestamp=timestamp
            )
        
        # Record the query in history
        await record_query_history(source_id, response)
        
        return response
    except Exception as e:
        print(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")

async def record_query_history(source_id: str, response: QueryResponse):
    """
    Record a query in the history for the given source_id.
    
    Args:
        source_id: The ID of the data source
        response: The query response to record
    """
    # Generate a unique ID for the query
    query_id = f"{len(query_history.get(source_id, []))+1}_{int(datetime.now().timestamp())}"
    
    # Create a historical query record
    historical_query = {
        "id": query_id,
        "source_id": source_id,
        "query": response.query,
        "result": response.result,
        "timestamp": response.timestamp.isoformat()
    }
    
    # Add to in-memory storage
    if source_id not in query_history:
        query_history[source_id] = []
    query_history[source_id].append(historical_query)
    
    # Limit history size (keep last 100 queries)
    if len(query_history[source_id]) > 100:
        query_history[source_id] = query_history[source_id][-100:]
    
    # Save to disk
    try:
        history_file = os.path.join(HISTORY_DIR, f"{source_id}_history.json")
        with open(history_file, 'w') as f:
            json.dump(query_history[source_id], f, indent=2)
    except Exception as e:
        print(f"Error saving query history: {str(e)}")

@router.get("/{source_id}/query/history", response_model=QueryHistoryResponse)
async def get_query_history(source_id: str, limit: int = Query(10, ge=1, le=100)):
    """
    Get the query history for a specific source_id.
    
    Args:
        source_id: The ID of the data source
        limit: Maximum number of queries to return (default: 10, max: 100)
        
    Returns:
        QueryHistoryResponse: The query history for the source_id
    """
    try:
        # Try to load history from disk if not in memory
        if source_id not in query_history:
            history_file = os.path.join(HISTORY_DIR, f"{source_id}_history.json")
            if os.path.exists(history_file):
                with open(history_file, 'r') as f:
                    query_history[source_id] = json.load(f)
        
        # Get the history for the source_id (or empty list if none)
        history = query_history.get(source_id, [])
        
        # Sort by timestamp (newest first) and limit
        sorted_history = sorted(history, key=lambda x: x["timestamp"], reverse=True)[:limit]
        
        # Convert to HistoricalQuery objects
        queries = [
            HistoricalQuery(
                id=item["id"],
                source_id=item["source_id"],
                query=item["query"],
                result=item["result"],
                timestamp=datetime.fromisoformat(item["timestamp"])
            )
            for item in sorted_history
        ]
        
        return QueryHistoryResponse(source_id=source_id, queries=queries)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving query history: {str(e)}")

@router.get("/{source_id}/query/canned", response_model=PredefinedQueriesResponse)
async def get_predefined_queries(source_id: str, category: Optional[str] = None):
    """
    Get a list of predefined (canned) queries for a specific source_id.
    
    Args:
        source_id: The ID of the data source
        category: Optional category to filter queries by
        
    Returns:
        PredefinedQueriesResponse: The list of predefined queries
    """
    try:
        # Check if there's a custom predefined queries file for this source_id
        queries_file = os.path.join(QUERIES_DIR, f"{source_id}_queries.json")
        predefined_queries = {}
        
        if os.path.exists(queries_file):
            # Load custom queries for this source_id
            with open(queries_file, 'r') as f:
                predefined_queries = json.load(f)
        else:
            # Use default predefined queries
            predefined_queries = DEFAULT_PREDEFINED_QUERIES
        
        # Flatten queries from all categories or filter by category
        result_queries = []
        
        if category and category in predefined_queries:
            # Filter by specific category
            for query in predefined_queries[category]:
                result_queries.append(
                    PredefinedQuery(
                        id=query["id"],
                        query=query["query"],
                        category=category,
                        description=query.get("description")
                    )
                )
        else:
            # Include all categories
            for cat, queries in predefined_queries.items():
                for query in queries:
                    result_queries.append(
                        PredefinedQuery(
                            id=query["id"],
                            query=query["query"],
                            category=cat,
                            description=query.get("description")
                        )
                    )
        
        return PredefinedQueriesResponse(source_id=source_id, queries=result_queries)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving predefined queries: {str(e)}")
