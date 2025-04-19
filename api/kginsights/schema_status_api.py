from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime
import json
from neo4j import GraphDatabase

from ..models import get_db, Schema, GraphIngestionJob, User
from ..auth import has_any_permission
from .database_api import get_database_config, parse_connection_params

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
        
        # Parse schema data
        schema_data = json.loads(schema_record.schema)
        
        # Get database connection info
        db_config = get_database_config()
        
        # Connect to Neo4j
        uri, username, password = parse_connection_params(db_config)
        
        node_counts = {}
        relationship_counts = {}
        total_nodes = 0
        total_relationships = 0
        
        with GraphDatabase.driver(uri, auth=(username, password)) as driver:
            with driver.session() as session:
                # Count nodes for each node type
                for node_type in schema_data.get("nodes", []):
                    label = node_type.get("label", "")
                    if not label:
                        continue
                    
                    query = f"MATCH (n:{label}) RETURN count(n) as count"
                    result = session.run(query)
                    count = result.single()["count"]
                    node_counts[label] = count
                    total_nodes += count
                
                # Count relationships for each relationship type
                for rel_type in schema_data.get("relationships", []):
                    rel_label = rel_type.get("type", "")
                    start_node = rel_type.get("startNodeLabel", rel_type.get("startNode", ""))
                    end_node = rel_type.get("endNodeLabel", rel_type.get("endNode", ""))
                    
                    if not (rel_label and start_node and end_node):
                        continue
                    
                    query = f"MATCH (:{start_node})-[r:{rel_label}]->(:{end_node}) RETURN count(r) as count"
                    result = session.run(query)
                    count = result.single()["count"]
                    relationship_counts[f"{start_node}-{rel_label}->{end_node}"] = count
                    total_relationships += count
        
        return {
            "has_data": total_nodes > 0,
            "node_count": total_nodes,
            "relationship_count": total_relationships,
            "node_counts": node_counts,
            "relationship_counts": relationship_counts
        }
    except Exception as e:
        return {
            "has_data": False,
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
    
    # Get Neo4j stats
    neo4j_stats = get_neo4j_stats(schema_id, db)
    
    # Get active jobs
    active_jobs = get_schema_jobs(schema_id, db)
    
    # Get last update time
    last_update = get_last_successful_job(schema_id, db)
    
    # Get the most recent successful load job to get node and relationship counts
    last_load_job = db.query(GraphIngestionJob)\
        .filter(GraphIngestionJob.schema_id == schema_id,
               GraphIngestionJob.status == "completed",
               GraphIngestionJob.job_type == "load_data")\
        .order_by(GraphIngestionJob.updated_at.desc())\
        .first()
    
    # Determine if schema has data based on successful load jobs
    has_data = last_update is not None and any(
        job.job_type == "load_data" and job.status == "completed" 
        for job in db.query(GraphIngestionJob)
        .filter(GraphIngestionJob.schema_id == schema_id, 
                GraphIngestionJob.status == "completed",
                GraphIngestionJob.job_type == "load_data")
        .all()
    )
    
    # Determine if data was cleaned based on successful clean jobs after last load
    was_cleaned = False
    if has_data:
        last_load_job = db.query(GraphIngestionJob)\
            .filter(GraphIngestionJob.schema_id == schema_id,
                   GraphIngestionJob.status == "completed",
                   GraphIngestionJob.job_type == "load_data")\
            .order_by(GraphIngestionJob.updated_at.desc())\
            .first()
        
        if last_load_job:
            # Check if there's a successful clean job after the last load
            last_clean_job = db.query(GraphIngestionJob)\
                .filter(GraphIngestionJob.schema_id == schema_id,
                       GraphIngestionJob.status == "completed",
                       GraphIngestionJob.job_type == "clean_data",
                       GraphIngestionJob.updated_at > last_load_job.updated_at)\
                .order_by(GraphIngestionJob.updated_at.desc())\
                .first()
            
            was_cleaned = last_clean_job is not None
    
    # Determine node and relationship counts
    node_count = 0
    relationship_count = 0
    node_counts = {}
    relationship_counts = {}
    
    # Check if there's a successful clean job after the last load job
    if was_cleaned and last_clean_job:
        print(f"DEBUG: Found last_clean_job with ID {last_clean_job.id} for schema {schema_id}")
        print(f"DEBUG: Clean job attributes: status={last_clean_job.status}, job_type={last_clean_job.job_type}")
        
        # If data was cleaned, we should use the clean job's counts (which should be 0)
        if hasattr(last_clean_job, 'node_count') and hasattr(last_clean_job, 'relationship_count'):
            print(f"DEBUG: Using counts from clean job: node_count={last_clean_job.node_count}, relationship_count={last_clean_job.relationship_count}")
            node_count = last_clean_job.node_count or 0
            relationship_count = last_clean_job.relationship_count or 0
            
            # Try to get detailed counts from clean job result (should be empty)
            if hasattr(last_clean_job, 'result') and last_clean_job.result:
                try:
                    job_result = json.loads(last_clean_job.result)
                    node_counts = job_result.get("node_counts", {})
                    relationship_counts = job_result.get("relationship_counts", {})
                    print(f"DEBUG: Successfully parsed clean job result JSON")
                except (json.JSONDecodeError, TypeError) as e:
                    print(f"DEBUG: Error parsing clean job result JSON: {str(e)}")
                    # Empty counts since data was cleaned
                    node_counts = {}
                    relationship_counts = {}
            else:
                print(f"DEBUG: Clean job has no result attribute or result is empty")
                node_counts = {}
                relationship_counts = {}
                
            # Override has_data flag since data was cleaned
            has_data = False
            print(f"DEBUG: Setting has_data=False because data was cleaned")
            
            # Return early with zero counts
            print(f"DEBUG: Final counts after clean job: node_count={node_count}, relationship_count={relationship_count}")
            
            # Verify with Neo4j stats
            if neo4j_stats.get("node_count", 0) > 0 or neo4j_stats.get("relationship_count", 0) > 0:
                print(f"WARNING: Neo4j still has data after clean job: nodes={neo4j_stats.get('node_count', 0)}, relationships={neo4j_stats.get('relationship_count', 0)}")
        else:
            print(f"DEBUG: Clean job doesn't have node_count or relationship_count attributes, using Neo4j stats")
            # Use Neo4j stats as fallback, which should be 0 if clean was successful
            node_count = neo4j_stats.get("node_count", 0)
            relationship_count = neo4j_stats.get("relationship_count", 0)
            node_counts = neo4j_stats.get("node_counts", {})
            relationship_counts = neo4j_stats.get("relationship_counts", {})
    else:
        # No clean job after load, use the load job counts
        # Debug information about the last load job
        if last_load_job:
            print(f"DEBUG: Found last_load_job with ID {last_load_job.id} for schema {schema_id}")
            print(f"DEBUG: Job attributes: status={last_load_job.status}, job_type={last_load_job.job_type}")
            
            # Check if node_count and relationship_count attributes exist
            has_node_count = hasattr(last_load_job, 'node_count')
            has_rel_count = hasattr(last_load_job, 'relationship_count')
            print(f"DEBUG: Has node_count attribute: {has_node_count}, Has relationship_count attribute: {has_rel_count}")
            
            if has_node_count and has_rel_count:
                print(f"DEBUG: Job count values: node_count={last_load_job.node_count}, relationship_count={last_load_job.relationship_count}")
        else:
            print(f"DEBUG: No last_load_job found for schema {schema_id}")
        
        # Debug Neo4j stats
        print(f"DEBUG: Neo4j stats: node_count={neo4j_stats.get('node_count', 0)}, relationship_count={neo4j_stats.get('relationship_count', 0)}")
        
        if last_load_job and hasattr(last_load_job, 'node_count') and hasattr(last_load_job, 'relationship_count'):
            # Use counts from the job record if available
            node_count = last_load_job.node_count or 0
            relationship_count = last_load_job.relationship_count or 0
            
            # Try to get detailed counts from job result
            if hasattr(last_load_job, 'result') and last_load_job.result:
                try:
                    job_result = json.loads(last_load_job.result)
                    node_counts = job_result.get("node_counts", {})
                    relationship_counts = job_result.get("relationship_counts", {})
                    print(f"DEBUG: Successfully parsed job result JSON with node_counts: {list(node_counts.keys())}")
                except (json.JSONDecodeError, TypeError) as e:
                    print(f"DEBUG: Error parsing job result JSON: {str(e)}")
                    # Fallback to Neo4j stats if result parsing fails
                    node_counts = neo4j_stats.get("node_counts", {})
                    relationship_counts = neo4j_stats.get("relationship_counts", {})
            else:
                print(f"DEBUG: Job has no result attribute or result is empty")
                node_counts = neo4j_stats.get("node_counts", {})
                relationship_counts = neo4j_stats.get("relationship_counts", {})
        else:
            # Fallback to Neo4j stats if job record doesn't have the counts
            print(f"DEBUG: Using Neo4j stats as fallback for counts")
            node_count = neo4j_stats.get("node_count", 0)
            relationship_count = neo4j_stats.get("relationship_count", 0)
            node_counts = neo4j_stats.get("node_counts", {})
            relationship_counts = neo4j_stats.get("relationship_counts", {})
    
    # Final debug output of what will be returned
    print(f"DEBUG: Final counts to be returned: node_count={node_count}, relationship_count={relationship_count}, has_data={has_data}, was_cleaned={was_cleaned}")
    
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
