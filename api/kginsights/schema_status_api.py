from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime
import json
from neo4j import GraphDatabase
from fastapi import APIRouter, Depends, HTTPException, status

from ..models import get_db, Schema, GraphIngestionJob, User
from ..auth import has_any_permission
from .neo4j_config import get_neo4j_connection_params

# Models
class SchemaStatus(BaseModel):
    schema_id: int
    name: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    has_data: bool
    was_cleaned: bool
    node_count: int = 0
    relationship_count: int = 0
    last_data_update: Optional[datetime] = None
    active_jobs: List[Dict[str, Any]] = []
    graph_data_stats: Dict[str, Any] = {}

# Router
router = APIRouter(prefix="/kginsights/schema-status", tags=["schema_status"])

# Helper functions
def get_neo4j_stats(schema_id: int, db: Session):
    """
    Get statistics about the schema's data in Neo4j
    """
    try:
        # Get schema from database
        schema_record = db.query(Schema).filter(Schema.id == schema_id).first()
        if not schema_record:
            raise HTTPException(status_code=404, detail=f"Schema with ID {schema_id} not found")
        
        # Check if data is loaded based on schema record db_loaded attribute
        has_data = getattr(schema_record, 'db_loaded', 'no').lower() == 'yes'
        
        # If data is not loaded, return early with default values
        if not has_data:
            return {
                "has_data": False,
                "node_count": 0,
                "relationship_count": 0,
                "node_counts": {},
                "relationship_counts": {}
            }
        
        # Parse schema data
        schema_data = json.loads(schema_record.schema)
        
        # Get the graph name from the schema if available
        graph_name = schema_data.get("graph_name", "default_graph")
        print(f"Using graph name: {graph_name}")
        
        # Get connection parameters for the specific graph using the centralized configuration
        connection_params = get_neo4j_connection_params(graph_name)
        if not connection_params:
            return {
                "has_data": False,
                "node_count": 0,
                "relationship_count": 0,
                "error": "Could not get Neo4j connection parameters"
            }
            
        uri = connection_params.get("uri")
        username = connection_params.get("username")
        password = connection_params.get("password")
        
        if not all([uri, username, password]):
            return {
                "has_data": False,
                "node_count": 0,
                "relationship_count": 0,
                "error": f"Missing required Neo4j connection parameters"
            }
        
        node_counts = {}
        relationship_counts = {}
        total_nodes = 0
        total_relationships = 0
        
        # Test connection first before running queries
        driver = GraphDatabase.driver(uri, auth=(username, password))
        try:
            # Verify connection is working with a simple query
            with driver.session() as session:
                session.run("RETURN 1 as test").single()
                
            with driver.session() as session:
                # Count nodes for each node type
                for node_type in schema_data.get("nodes", []):
                    label = node_type.get("label", "")
                    if not label:
                        continue
                    
                    query = f"MATCH (n:{label}) RETURN count(n) as count"
                    try:
                        result = session.run(query)
                        count = result.single()["count"]
                        node_counts[label] = count
                        total_nodes += count
                    except Exception as query_error:
                        print(f"Error querying node count for {label}: {str(query_error)}")
                        node_counts[label] = 0
                
                # Count relationships for each relationship type
                for rel_type in schema_data.get("relationships", []):
                    rel_label = rel_type.get("type", "")
                    start_node = rel_type.get("startNodeLabel", rel_type.get("startNode", ""))
                    end_node = rel_type.get("endNodeLabel", rel_type.get("endNode", ""))
                    
                    if not (rel_label and start_node and end_node):
                        continue
                    
                    query = f"MATCH (:{start_node})-[r:{rel_label}]->(:{end_node}) RETURN count(r) as count"
                    try:
                        result = session.run(query)
                        count = result.single()["count"]
                        relationship_counts[f"{start_node}-{rel_label}->{end_node}"] = count
                        total_relationships += count
                    except Exception as query_error:
                        print(f"Error querying relationship count for {start_node}-{rel_label}->{end_node}: {str(query_error)}")
                        relationship_counts[f"{start_node}-{rel_label}->{end_node}"] = 0
        except Exception as conn_error:
            print(f"Neo4j connection error: {str(conn_error)}")
            return {
                "has_data": False,
                "node_count": 0,
                "relationship_count": 0,
                "error": f"Neo4j connection error: {str(conn_error)}"
            }
        finally:
            driver.close()
            
        print(f"Total nodes: {total_nodes}")
        print(f"Total relationships: {total_relationships}")
        print(f"Node counts: {node_counts}")
        print(f"Relationship counts: {relationship_counts}")
        
        # Return with has_data based on schema record, not node count
        return {
            "has_data": has_data,  # Now using db_loaded attribute instead of node count
            "node_count": total_nodes,
            "relationship_count": total_relationships,
            "node_counts": node_counts,
            "relationship_counts": relationship_counts
        }
    except Exception as e:
        print(f"Error getting Neo4j stats: {str(e)}")
        
        # Get schema record to check db_loaded attribute even in error case
        try:
            schema_record = db.query(Schema).filter(Schema.id == schema_id).first()
            has_data = getattr(schema_record, 'db_loaded', 'no').lower() == 'yes' if schema_record else False
        except Exception:
            has_data = False
            
        return {
            "has_data": has_data,  # Use db_loaded attribute if available
            "node_count": 0,
            "relationship_count": 0,
            "error": str(e)
        }

def get_schema_jobs(schema_id: int, db: Session):
    """
    Get active jobs for this schema
    """
    jobs = db.query(GraphIngestionJob).filter(
        GraphIngestionJob.schema_id == schema_id,
        GraphIngestionJob.status.in_(["pending", "running"])
    ).all()
    
    return [{
        "id": job.id,
        "type": job.job_type,
        "status": job.status,
        "progress": float(job.progress) / 100 if job.progress is not None else 0.0,  
        "message": job.message or "",
        "created_at": job.created_at.isoformat()
    } for job in jobs]

def get_last_successful_job(schema_id: int, db: Session):
    """
    Get the timestamp of the last successful job for this schema
    """
    job = db.query(GraphIngestionJob).filter(
        GraphIngestionJob.schema_id == schema_id,
        GraphIngestionJob.status == "completed"
    ).order_by(GraphIngestionJob.updated_at.desc()).first()
    
    return job.updated_at if job else None

# API Routes
@router.get("/{schema_id}", response_model=SchemaStatus)
async def get_schema_status(
    schema_id: int,
    current_user: User = Depends(has_any_permission(["kginsights:read"])),
    db: Session = Depends(get_db)
):
    """
    Get detailed status for a specific schema
    """
    schema = db.query(Schema).filter(Schema.id == schema_id).first()
    if not schema:
        raise HTTPException(status_code=404, detail=f"Schema with ID {schema_id} not found")
    
    # Get Neo4j stats directly from the database
    neo4j_stats = get_neo4j_stats(schema_id, db)
    print(f"Neo4j stats: {neo4j_stats}")
    
    # Get active jobs
    active_jobs = get_schema_jobs(schema_id, db)
    print(f"Active jobs: {active_jobs}")
    
    # Get last update time from job history
    last_update = get_last_successful_job(schema_id, db)
    print(f"Last update: {last_update}")
    
    # Determine if schema has data based on Neo4j stats
    has_data = neo4j_stats.get("has_data", False)
    
    # Get node and relationship counts directly from Neo4j
    node_count = neo4j_stats.get("node_count", 0)
    relationship_count = neo4j_stats.get("relationship_count", 0)
    node_counts = neo4j_stats.get("node_counts", {})
    relationship_counts = neo4j_stats.get("relationship_counts", {})
    
    # Determine if data was cleaned based on job history
    # Check if there's a successful clean job after the last load
    last_load_job = db.query(GraphIngestionJob)\
        .filter(GraphIngestionJob.schema_id == schema_id,
               GraphIngestionJob.status == "completed",
               GraphIngestionJob.job_type == "load_data")\
        .order_by(GraphIngestionJob.updated_at.desc())\
        .first()
    
    was_cleaned = False
    if last_load_job:
        last_clean_job = db.query(GraphIngestionJob)\
            .filter(GraphIngestionJob.schema_id == schema_id,
                   GraphIngestionJob.status == "completed",
                   GraphIngestionJob.job_type == "clean_data",
                   GraphIngestionJob.updated_at > last_load_job.updated_at)\
            .order_by(GraphIngestionJob.updated_at.desc())\
            .first()
        
        was_cleaned = last_clean_job is not None
    
    return SchemaStatus(
        schema_id=schema.id,
        name=schema.name,
        created_at=schema.created_at,
        updated_at=schema.updated_at,
        has_data=has_data,
        was_cleaned=was_cleaned,
        node_count=node_count,
        relationship_count=relationship_count,
        last_data_update=last_update,
        active_jobs=active_jobs,
        graph_data_stats={
            "node_counts": node_counts,
            "relationship_counts": relationship_counts
        }
    )
