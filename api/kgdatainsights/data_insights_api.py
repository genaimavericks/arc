from fastapi import APIRouter, HTTPException, Depends, Query, Response, status, Body
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import asyncio
from datetime import datetime
import json
import os
from pathlib import Path
from .agent.insights_data_agent import get_kg_answer, init_graph
from .agent.schema_aware_agent import get_schema_aware_assistant
from .visualization_analyzer import analyze_data_for_visualization, GraphData
from ..models import User
from ..auth import has_any_permission
from neo4j.time import Date, Time, DateTime
from pydantic.json import pydantic_encoder
from ..db_config import SessionLocal
from ..models import Schema

router = APIRouter(prefix="/datainsights", tags=["Data Insights"])

# In-memory storage for query history (in production, use a database)
query_history = {}

# Directory to store query history and predefined queries as JSON files
# Output directories
OUTPUT_DIR = Path("runtime-data/output/kgdatainsights")
HISTORY_DIR = OUTPUT_DIR / "history"
QUERIES_DIR = OUTPUT_DIR / "queries"
PROMPT_DIR = OUTPUT_DIR / "prompts"

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

class QueryRequest(BaseModel):
    """Request model for the query endpoint."""
    query: str
    params: Optional[Dict[str, Any]] = None

class QueryResponse(BaseModel):
    """Response model for the query endpoint."""
    schema_id: str
    query: str
    result: str
    intermediate_steps: Optional[Dict[str, Any]] = None
    visualization: Optional[GraphData] = None
    timestamp: datetime = datetime.now()

class HistoricalQuery(BaseModel):
    """Model for a historical query."""
    id: str
    schema_id: str
    query: str
    result: str
    timestamp: datetime

class QueryHistoryResponse(BaseModel):
    """Response model for the query history endpoint."""
    schema_id: str
    queries: List[HistoricalQuery]

class DeleteHistoryResponse(BaseModel):
    """Response model for delete history endpoints."""
    schema_id: str
    message: str
    deleted_count: int

class PredefinedQuery(BaseModel):
    """Model for a predefined query."""
    id: str
    query: str
    category: str
    description: Optional[str] = None

class PredefinedQueriesResponse(BaseModel):
    """Response model for the predefined queries endpoint."""
    schema_id: str
    queries: List[PredefinedQuery]

class GeneratePromptsResponse(BaseModel):
    schema_id: str
    message: str

print('$$$$$$$$$$$$$$- Loading data insights')
# API Routes
@router.get('/status')
async def get_status():
    """Return API status."""
    return {"status": "OK"}


@router.post("/{schema_id}/visualize", response_model=GraphData)
async def analyze_data_visualization(
    schema_id: str, 
    data: Dict[str, Any],
    current_user: User = Depends(has_any_permission(["kginsights:read"]))
):
    """
    Analyze data and suggest appropriate visualization.
    
    Args:
        schema_id: The ID of the schema to use
        data: The data to analyze
        
    Returns:
        GraphData: The visualization data
    """
    try:
        # Check if data is provided
        if not data:
            raise HTTPException(status_code=400, detail="No data provided for analysis")
        
        # Log the input data for debugging
        print(f"Visualization input data: {json.dumps(data, default=str)[:500]}...")
        
        # Analyze data for visualization
        visualization = analyze_data_for_visualization(data)
        
        # Log the output for debugging
        print(f"Visualization result: {json.dumps(visualization.dict(), default=str)[:500]}...")
        
        return visualization
    except Exception as e:
        print(f"Visualization analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error analyzing data: {str(e)}")


@router.post("/{schema_id}/query", response_model=QueryResponse)
async def process_query(
    schema_id: str, 
    request: QueryRequest,
    use_schema_aware: bool = Query(True, description="Use the schema-aware agent instead of default agent"),
    current_user: User = Depends(has_any_permission(["kginsights:read"]))
):
    """
    Process a query against the knowledge graph and record it in the query history.
    
    Args:
        schema_id: The ID of the schema to use
        request: The query request containing the query string
        use_schema_aware: Whether to use the schema-aware agent
        
    Returns:
        QueryResponse: The response containing the query result
    """
    try:
        # if schema id is zero or less then return result
        if int(schema_id) <= 0:
            return QueryResponse(
                schema_id=schema_id,
                query=request.query,
                result="Knowledge graph is not created and loaded with data. Generate Graph with appropriate data to use Insights agen",
                timestamp=datetime.now()
            )

        print('Calling data insights api' + str(use_schema_aware))
        # If using schema-aware agent
        if use_schema_aware:
            # Get or create the schema-aware assistant for this schema_id
            # fetch db_id from Schema table
            db = SessionLocal()
            result = db.query(Schema.db_id, Schema.schema).filter(Schema.id == schema_id).first()
            
            # Extract db_id value from the result tuple
            db_id = result.db_id if result else None
            if not db_id:
                return QueryResponse(
                    schema_id=schema_id,
                    query=request.query,
                    result="Knowledge graph is not created and loaded with data. Generate Graph with appropriate data to use Insights agen",
                    timestamp=datetime.now()
                )
            schema = result.schema if result else None
            if not schema:
                return QueryResponse(
                    schema_id=schema_id,
                    query=request.query,
                    result="Knowledge graph is not created and loaded with data. Generate Graph with appropriate data to use Insights agen",
                    timestamp=datetime.now()
                )

            prompt_file = PROMPT_DIR / f"prompt_{db_id}_{schema_id}.json"
            cypher_queries = None
            if prompt_file.exists():
                with open(prompt_file, 'r') as f:
                    prompts = json.load(f)
                    cypher_queries = prompts.get('sample_cyphers')

            print(f"Cypher queries: {cypher_queries}")

            # Fetch or create schema-aware assistant
            print('Fetching schema aware assistant for schema ID ' + schema_id)
            assistant = get_schema_aware_assistant(db_id, schema_id, schema=schema)
            
            # Get the answer from the schema-aware agent
            print('Calling query')
            result = assistant.query(request.query, cypher_queries)
            print('Returned query result' + str(result))
        else:
            # Initialize the graph if needed
            await init_graph()
            
            # Get the answer from the legacy knowledge graph agent
            result = get_kg_answer(request.query)
        
        # Extract the result and intermediate steps
        print('Returned query result' + str(result))
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
        sanitized_steps = None
        if intermediate_steps:
            try:
                sanitized_steps = sanitize_neo4j_objects(intermediate_steps)
                print(f"Analyzing intermediate steps for visualization: {json.dumps(sanitized_steps, cls=Neo4jJsonEncoder)[:300]}...")
                visualization = analyze_data_for_visualization(sanitized_steps)
                
                # Log visualization result
                if visualization and visualization.type != "none":
                    print(f"Visualization generated: {visualization.type}, title: {visualization.title}")
                    # Check if we have the necessary data for the chart type
                    if visualization.type in ["bar", "line", "histogram"] and (not visualization.x_axis or not visualization.y_axis):
                        print("WARNING: Missing axis data for chart visualization!")
                    elif visualization.type == "pie" and (not visualization.labels or not visualization.values):
                        print("WARNING: Missing labels/values for pie chart!")
                else:
                    print("No suitable visualization found for the data")
            except Exception as e:
                print(f"Error analyzing data for visualization: {e}")
        
        try:
            response = QueryResponse(
                schema_id=schema_id,
                query=request.query,
                result=answer,
                intermediate_steps=sanitized_steps,
                visualization=visualization,
                timestamp=timestamp
            )
        except Exception as e:
            print(f"Error creating QueryResponse: {e}")
            # Fallback to creating response without intermediate steps
            response = QueryResponse(
                schema_id=schema_id,
                query=request.query,
                result=answer,
                intermediate_steps=None,
                timestamp=timestamp
            )
        
        # Record the query in history
        await record_query_history(schema_id, response)
        
        return response
    except Exception as e:
        print(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")

async def record_query_history(schema_id: str, response: QueryResponse):
    """
    Record a query in the history for the given schema_id.
    
    Args:
        schema_id: The ID of the schema to use
        response: The query response to record
    """
    # Generate a unique ID for the query
    query_id = f"{len(query_history.get(schema_id, []))+1}_{int(datetime.now().timestamp())}"
    
    # Create a historical query record
    historical_query = {
        "id": query_id,
        "schema_id": schema_id,
        "query": response.query,
        "result": response.result,
        "timestamp": response.timestamp.isoformat()
    }
    
    # Add to in-memory storage
    if schema_id not in query_history:
        query_history[schema_id] = []
    query_history[schema_id].append(historical_query)
    
    # Limit history size (keep last 100 queries)
    if len(query_history[schema_id]) > 100:
        query_history[schema_id] = query_history[schema_id][-100:]
    
    # Save to disk
    try:
        history_file = os.path.join(HISTORY_DIR, f"{schema_id}_history.json")
        with open(history_file, 'w') as f:
            json.dump(query_history[schema_id], f, indent=2)
    except Exception as e:
        print(f"Error saving query history: {str(e)}")

@router.get("/{schema_id}/query/history", response_model=QueryHistoryResponse)
async def get_query_history(
    schema_id: str, 
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(has_any_permission(["kginsights:read"]))
):
    """
    Get the query history for a specific schema_id.
    
    Args:
        schema_id: The ID of the schema to use
        limit: Maximum number of queries to return (default: 10, max: 100)
        
    Returns:
        QueryHistoryResponse: The query history for the schema_id
    """
    try:
        # Try to load history from disk if not in memory
        if schema_id not in query_history:
            history_file = os.path.join(HISTORY_DIR, f"{schema_id}_history.json")
            if os.path.exists(history_file):
                with open(history_file, 'r') as f:
                    query_history[schema_id] = json.load(f)
        
        # Get the history for the schema_id (or empty list if none)
        history = query_history.get(schema_id, [])
        
        # Sort by timestamp (newest first) and limit
        sorted_history = sorted(history, key=lambda x: x["timestamp"], reverse=True)[:limit]
        
        # Convert to HistoricalQuery objects
        queries = [
            HistoricalQuery(
                id=item["id"],
                schema_id=item["schema_id"],
                query=item["query"],
                result=item["result"],
                timestamp=datetime.fromisoformat(item["timestamp"])
            )
            for item in sorted_history
        ]
        
        return QueryHistoryResponse(schema_id=schema_id, queries=queries)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving query history: {str(e)}")

@router.delete("/{schema_id}/query/history/{history_id}", response_model=DeleteHistoryResponse)
async def delete_history_item(
    schema_id: str,
    history_id: str,
    current_user: User = Depends(has_any_permission(["kginsights:write"]))
):
    """
    Delete a specific history item by ID.
    
    Args:
        schema_id: The ID of the schema to use
        history_id: The ID of the history item to delete
        
    Returns:
        DeleteHistoryResponse: Message confirming deletion
    """
    try:
        # Try to load history from disk if not in memory
        if schema_id not in query_history:
            history_file = os.path.join(HISTORY_DIR, f"{schema_id}_history.json")
            if os.path.exists(history_file):
                with open(history_file, 'r') as f:
                    query_history[schema_id] = json.load(f)
            else:
                # No history file exists
                return DeleteHistoryResponse(
                    schema_id=schema_id,
                    message=f"No history item found with ID {history_id}",
                    deleted_count=0
                )
        
        # Get the history for the schema_id (or empty list if none)
        history = query_history.get(schema_id, [])
        
        # Check if history item exists
        original_length = len(history)
        query_history[schema_id] = [item for item in history if item["id"] != history_id]
        deleted_count = original_length - len(query_history[schema_id])
        
        if deleted_count == 0:
            return DeleteHistoryResponse(
                schema_id=schema_id,
                message=f"No history item found with ID {history_id}",
                deleted_count=0
            )
        
        # Save updated history back to disk
        history_file = os.path.join(HISTORY_DIR, f"{schema_id}_history.json")
        with open(history_file, 'w') as f:
            json.dump(query_history[schema_id], f, cls=Neo4jJsonEncoder)
        
        return DeleteHistoryResponse(
            schema_id=schema_id,
            message=f"Successfully deleted history item {history_id}",
            deleted_count=deleted_count
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting history item: {str(e)}")

@router.delete("/{schema_id}/query/history", response_model=DeleteHistoryResponse)
async def delete_all_history(
    schema_id: str,
    current_user: User = Depends(has_any_permission(["kginsights:write"]))
):
    """
    Delete all history for a schema ID.
    
    Args:
        schema_id: The ID of the schema to use
        
    Returns:
        DeleteHistoryResponse: Message confirming deletion with count of deleted items
    """
    try:
        # Try to load history from disk if not in memory
        if schema_id not in query_history:
            history_file = os.path.join(HISTORY_DIR, f"{schema_id}_history.json")
            if os.path.exists(history_file):
                with open(history_file, 'r') as f:
                    query_history[schema_id] = json.load(f)
            else:
                # No history file exists, nothing to delete
                return DeleteHistoryResponse(
                    schema_id=schema_id,
                    message="No history exists for this source",
                    deleted_count=0
                )
        
        # Get the history for the schema_id (or empty list if none)
        history = query_history.get(schema_id, [])
        deleted_count = len(history)
        
        # Clear the history
        query_history[schema_id] = []
        
        # Save empty history back to disk
        history_file = os.path.join(HISTORY_DIR, f"{schema_id}_history.json")
        with open(history_file, 'w') as f:
            json.dump([], f)
        
        return DeleteHistoryResponse(
            schema_id=schema_id,
            message=f"Successfully deleted all history items",
            deleted_count=deleted_count
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting history: {str(e)}")

@router.get("/{schema_id}/query/canned", response_model=PredefinedQueriesResponse)
async def get_predefined_queries(
    schema_id: str, 
    category: Optional[str] = None,
    current_user: User = Depends(has_any_permission(["kginsights:read"]))
):
    """
    Get a list of predefined (canned) queries for a specific schema_id.
    
    Args:
        schema_id: The ID of the schema to use
        category: Optional category to filter queries by
        
    Returns:
        PredefinedQueriesResponse: The list of predefined queries
    """
    try:
        # Check if there's a custom predefined queries file for this schema_id
        queries_file = os.path.join(QUERIES_DIR, f"{schema_id}_queries.json")
        predefined_queries = {}
        
        if os.path.exists(queries_file):
            # Load custom queries for this schema_id
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
        
        return PredefinedQueriesResponse(schema_id=schema_id, queries=result_queries)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving predefined queries: {str(e)}")

@router.post("/{schema_id}/generate-prompts", response_model=GeneratePromptsResponse)
async def generate_prompts_for_schema(
    schema_id: str,
    current_user: User = Depends(has_any_permission(["kginsights:write"]))
):
    """
    Generate and save cypher prompt template, QA prompt template, and sample queries for the given schema_id
    using the existing SchemaAwareGraphAssistant logic. This will overwrite any existing prompts/queries files for this schema.
    """
    try:
        db = SessionLocal()
        schema_record = db.query(Schema).filter(Schema.id == schema_id).first()
        if not schema_record or not schema_record.schema or not schema_record.db_id:
            raise HTTPException(status_code=404, detail="Schema not found or incomplete for given schema_id")
        assistant = get_schema_aware_assistant(schema_record.db_id, schema_id, schema_record.schema)
        # This will trigger prompt and query file generation via _ensure_prompt
        assistant._ensure_prompt()
        return GeneratePromptsResponse(schema_id=schema_id, message="Prompts and sample queries generated and saved successfully.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating prompts: {str(e)}")
    finally:
        if 'db' in locals():
            db.close()
