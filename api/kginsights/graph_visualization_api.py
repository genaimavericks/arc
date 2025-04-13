from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import json

# Renamed to avoid conflict with Pydantic models if any
from ..models import get_db, Schema, User 
from ..auth import has_any_permission

# Models
class GraphNodeData(BaseModel):
    id: str
    label: str
    type: str
    properties: Dict[str, Any] = {}
    x: Optional[float] = None
    y: Optional[float] = None
    color: Optional[str] = None
    size: Optional[int] = None

class GraphEdgeData(BaseModel):
    id: str
    source: str
    target: str
    label: str
    properties: Dict[str, Any] = {}
    color: Optional[str] = None
    width: Optional[int] = None

class GraphData(BaseModel):
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]

class GraphStats(BaseModel):
    nodes: int
    edges: int
    metadata: Dict[str, Any] = {}

# Router
router = APIRouter(prefix="/kginsights/graph-visualization", tags=["graph_visualization"])

# API Routes
@router.get("/{schema_id}", response_model=GraphData)
async def get_graph_visualization(
    schema_id: int,
    current_user: User = Depends(has_any_permission(["kginsights:read"])),
    db: Session = Depends(get_db)
):
    """
    Get graph visualization data representing the SCHEMA structure 
    by parsing the JSON definition stored in the database.
    Returns node types and relationship types defined in the schema.
    """
    print(f"Fetching schema structure visualization for schema_id: {schema_id} by parsing JSON")

    # Fetch the schema record
    schema = db.query(Schema).filter(Schema.id == schema_id).first()

    if not schema:
        print(f"Schema with ID {schema_id} not found.")
        raise HTTPException(status_code=404, detail=f"Schema with ID {schema_id} not found")

    if not schema.schema:
        print(f"Schema JSON for ID {schema_id} is empty.")
        raise HTTPException(status_code=404, detail=f"Schema definition (JSON) not found for schema ID {schema_id}")

    try:
        schema_json = json.loads(schema.schema)
    except json.JSONDecodeError as e:
        print(f"Error decoding schema JSON for ID {schema_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error reading schema definition for schema ID {schema_id}")

    nodes_data = []
    edges_data = []
    node_id_map = {} # Map node label to generated graph node ID

    # Process Node Types from JSON
    json_nodes = schema_json.get("nodes", [])
    print(f"Processing {len(json_nodes)} node types from JSON...")
    for i, node_def in enumerate(json_nodes):
        node_label = node_def.get("label")
        if not node_label:
            print(f"Warning: Skipping node definition at index {i} due to missing label.")
            continue
            
        # Use label for ID generation to ensure edges can find nodes
        node_id = f"nodetype-{node_label}"
        node_id_map[node_label] = node_id # Map label to graph node ID
        
        properties = node_def.get("properties", {})
        nodes_data.append({
            "id": node_id,
            "label": node_label,
            "properties": properties,
            # Keep metadata simple for schema viz
            "metadata": {"type": "node_type", "source": "schema_json"}
        })

    # Process Relationship Types from JSON
    json_relationships = schema_json.get("relationships", [])
    print(f"Processing {len(json_relationships)} relationship types from JSON...")
    
    # If there are no relationships in the schema, create a placeholder node
    # to ensure the graph visualization still renders something
    if len(nodes_data) > 0 and len(json_relationships) == 0:
        print("No relationships found in schema. Creating a self-referential placeholder for visualization.")
        # Use the first node as a placeholder if there are no relationships
        first_node = nodes_data[0]
        placeholder_edge_id = f"placeholder-edge-{first_node['id']}"
        edges_data.append({
            "id": placeholder_edge_id,
            "source": first_node['id'],
            "target": first_node['id'],
            "label": "self",
            "properties": {},
            "metadata": {"type": "placeholder", "source": "generated"}
        })
    
    # Process actual relationships if any
    for i, rel_def in enumerate(json_relationships):
        rel_type = rel_def.get("type") # Assuming 'type' key for relationship label
        
        # Try different possible key names for start/end nodes
        start_node_label = rel_def.get("startNodeLabel", rel_def.get("startNode", rel_def.get("from", rel_def.get("source", ""))))
        end_node_label = rel_def.get("endNodeLabel", rel_def.get("endNode", rel_def.get("to", rel_def.get("target", ""))))

        if not rel_type:
            print(f"Warning: Skipping relationship definition at index {i} due to missing type.")
            continue
            
        if not start_node_label or not end_node_label:
            print(f"Warning: Relationship '{rel_type}' is missing start or end node label.")
            continue

        start_node_graph_id = node_id_map.get(start_node_label)
        end_node_graph_id = node_id_map.get(end_node_label)

        if not start_node_graph_id or not end_node_graph_id:
            print(f"Warning: Skipping relationship type '{rel_type}' due to missing start/end node label mapping ('{start_node_label}' -> '{end_node_label}').")
            continue
            
        properties = rel_def.get("properties", {})
        # Generate a unique edge ID
        edge_id = f"reltype-{start_node_graph_id}-{rel_type}-{end_node_graph_id}"
        edges_data.append({
            "id": edge_id,
            "source": start_node_graph_id,
            "target": end_node_graph_id,
            "label": rel_type,
            "properties": properties,
            # Keep metadata simple for schema viz
            "metadata": {"type": "relationship_type", "source": "schema_json"} 
        })

    print(f"Returning {len(nodes_data)} node types and {len(edges_data)} relationship types from JSON schema.")
    return GraphData(nodes=nodes_data, edges=edges_data)


@router.get("/{schema_id}/stats", response_model=GraphStats)
async def get_graph_stats(
    schema_id: int,
    current_user: User = Depends(has_any_permission(["kginsights:read"])),
    db: Session = Depends(get_db)
):
    """
    Get graph statistics for a specific schema
    """
    schema = db.query(Schema).filter(Schema.id == schema_id).first()
    if not schema:
        raise HTTPException(status_code=404, detail=f"Schema with ID {schema_id} not found")
        
    # Get stats from parsed JSON for consistency 
    nodes_count = 0
    edges_count = 0
    if schema.schema:
        try:
            schema_json = json.loads(schema.schema)
            nodes_count = len(schema_json.get("nodes", []))
            edges_count = len(schema_json.get("relationships", []))
        except json.JSONDecodeError:
             # If JSON is invalid, return 0 counts perhaps?
             pass 
             
    return GraphStats(nodes=nodes_count, edges=edges_count)
