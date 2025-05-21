import asyncio
import logging
import random
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

# Fix import paths for both direct and module imports
try:
    # When imported as a module
    from api.models import User, Schema
    from api.db_config import get_db
except ImportError:
    # When run directly
    from ..models import User, Schema
    from ..db_config import get_db

logger = logging.getLogger(__name__)

# Cache for schema data to avoid repeated database lookups
schema_cache = {}

async def get_schema_data(schema_id: str) -> Dict[str, Any]:
    """Get schema data from database or cache"""
    if schema_id in schema_cache:
        return schema_cache[schema_id]
    
    # For testing, use the sample schema data
    try:
        # First try to load from the sample schema file
        sample_schema_path = os.path.join(os.path.dirname(__file__), "sample_schema.json")
        if os.path.exists(sample_schema_path):
            with open(sample_schema_path, "r") as f:
                schema_data = json.load(f)
                # Cache the schema data
                schema_cache[schema_id] = schema_data
                return schema_data
        
        # If sample schema not found, try database
        try:
            db = next(get_db())
            schema = db.query(Schema).filter(Schema.id == schema_id).first()
            if schema:
                # Parse schema data from the schema field
                schema_data = json.loads(schema.schema)
                # Cache the schema data
                schema_cache[schema_id] = schema_data
                return schema_data
        except Exception as db_error:
            logger.error(f"Error getting schema from database: {str(db_error)}")
        
        # If all else fails, return empty schema
        return {"nodes": [], "relationships": []}
    except Exception as e:
        logger.error(f"Error getting schema data: {str(e)}")
        return {"nodes": [], "relationships": []}

async def get_entity_suggestions(schema_id: str) -> Dict[str, List[str]]:
    """Get entity suggestions based on schema"""
    schema_data = await get_schema_data(schema_id)
    
    # Extract node labels and relationship types
    node_labels = [node.get("label", "") for node in schema_data.get("nodes", [])]
    relationship_types = [rel.get("type", "") for rel in schema_data.get("relationships", [])]
    
    # Remove empty strings and duplicates
    node_labels = list(set(filter(None, node_labels)))
    relationship_types = list(set(filter(None, relationship_types)))
    
    return {
        "node_labels": node_labels,
        "relationship_types": relationship_types
    }

async def process_query(schema_id: str, query_text: str, user: User) -> Dict[str, Any]:
    """
    Process a knowledge graph query and return the results
    
    This is a simplified version for testing the WebSocket API
    In a real implementation, this would query the knowledge graph
    """
    logger.info(f"Processing query for schema_id={schema_id}, user_id={user.id}: {query_text}")
    
    # Simulate processing time
    await asyncio.sleep(1)
    
    # Generate a dummy response
    result = {
        "result": f"Response to: {query_text}",
        "timestamp": datetime.now().isoformat(),
        "intermediate_steps": [
            {"step": 1, "description": "Parsed query", "details": f"Parsed '{query_text}' into query object"},
            {"step": 2, "description": "Executed query", "details": "Executed query against knowledge graph"},
            {"step": 3, "description": "Generated response", "details": "Formatted results into response"}
        ]
    }
    
    # Randomly add visualization data
    if random.random() > 0.5:
        result["visualization"] = generate_dummy_visualization(query_text)
    
    return result

async def get_autocomplete_suggestions(schema_id: str, partial_text: str, cursor_position: int, user: User) -> List[str]:
    """Get autocomplete suggestions based on partial text and schema"""
    # Get entity suggestions from schema
    entities = await get_entity_suggestions(schema_id)
    node_labels = entities["node_labels"]
    relationship_types = entities["relationship_types"]
    
    # Convert partial text to lowercase for case-insensitive matching
    lower_text = partial_text.lower()
    
    # Simple autocomplete logic based on schema entities
    if lower_text.startswith("show") or lower_text.startswith("find"):
        # Suggest node labels
        return [f"Show me all {label} nodes" for label in node_labels] + \
               [f"Find {label} nodes with property" for label in node_labels]
    elif lower_text.startswith("count"):
        # Suggest counting by node label or relationship type
        return [f"Count {label} nodes" for label in node_labels] + \
               [f"Count {rel_type} relationships" for rel_type in relationship_types]
    elif lower_text.startswith("match"):
        # Suggest relationship patterns
        suggestions = []
        for source in node_labels:
            for target in node_labels:
                if source != target:
                    for rel_type in relationship_types:
                        suggestions.append(f"Match {source}-[{rel_type}]->{target}")
        return suggestions[:10]  # Limit to 10 suggestions to avoid overwhelming the user
    else:
        # Default suggestions
        return ["Show", "Find", "Count", "Match"]

async def validate_query(schema_id: str, query_text: str, user: User) -> List[Dict[str, Any]]:
    """Validate a query against the schema and return any errors or warnings"""
    # Get entity suggestions from schema
    entities = await get_entity_suggestions(schema_id)
    node_labels = entities["node_labels"]
    relationship_types = entities["relationship_types"]
    
    # Convert query to lowercase for case-insensitive matching
    lower_query = query_text.lower()
    
    # Simple validation logic
    errors = []
    
    # Check for query length
    if len(query_text) < 5:
        errors.append({"type": "error", "message": "Query is too short", "position": 0})
        return errors
    
    # Check for unknown node labels
    for word in lower_query.split():
        # Remove punctuation
        word = word.strip(",.;:()[]{}'\"").lower()
        
        # Skip common words and short words
        if word in ["show", "find", "count", "match", "me", "all", "the", "with", "by", "and", "or"] or len(word) < 3:
            continue
        
        # Check if word might be a node label but isn't in our schema
        if word.endswith("s"):  # Might be plural
            singular = word[:-1]  # Remove trailing 's'
            if singular not in [label.lower() for label in node_labels] and word not in [label.lower() for label in node_labels]:
                # Check if it looks like a potential entity name (capitalized in original query)
                original_word = query_text.split()[lower_query.split().index(word)]
                if original_word[0].isupper():
                    errors.append({
                        "type": "warning", 
                        "message": f"Unknown entity type: {original_word}", 
                        "position": query_text.find(original_word)
                    })
    
    return errors

async def get_query_suggestions(schema_id: str, user: User) -> List[str]:
    """Get query suggestions based on schema"""
    # Get entity suggestions from schema
    entities = await get_entity_suggestions(schema_id)
    node_labels = entities["node_labels"]
    relationship_types = entities["relationship_types"]
    
    # Generate suggestions based on schema entities
    suggestions = []
    
    # Add node-based suggestions
    for label in node_labels[:3]:  # Limit to first 3 node types to avoid too many suggestions
        suggestions.append(f"Show me all {label} nodes")
        suggestions.append(f"Count {label} nodes")
    
    # Add relationship-based suggestions
    if len(node_labels) >= 2 and len(relationship_types) > 0:
        suggestions.append(f"Find relationships between {node_labels[0]} and {node_labels[1]}")
    
    # Add general suggestions if we don't have enough
    if len(suggestions) < 5:
        general_suggestions = [
            "Show the most connected nodes",
            "Find the shortest path between two nodes",
            "Count nodes by type"
        ]
        suggestions.extend(general_suggestions)
    
    return suggestions[:5]  # Return at most 5 suggestions

def generate_dummy_visualization(query_text: str) -> Dict[str, Any]:
    """Generate dummy visualization data for testing"""
    viz_types = ["bar", "pie", "line", "histogram", "heatmap"]
    viz_type = random.choice(viz_types)
    
    # Generate random data based on visualization type
    if viz_type in ["bar", "line"]:
        return {
            "type": viz_type,
            "title": f"{viz_type.capitalize()} Chart for {query_text[:20]}...",
            "description": f"Visualization of data related to '{query_text}'",
            "x_axis": {
                "label": "Categories",
                "values": ["Category A", "Category B", "Category C", "Category D", "Category E"]
            },
            "y_axis": {
                "label": "Values",
                "values": [random.randint(10, 100) for _ in range(5)]
            }
        }
    elif viz_type == "pie":
        return {
            "type": viz_type,
            "title": f"Pie Chart for {query_text[:20]}...",
            "description": f"Distribution of data related to '{query_text}'",
            "labels": ["Segment A", "Segment B", "Segment C", "Segment D"],
            "values": [random.randint(10, 100) for _ in range(4)]
        }
    else:
        # Histogram or heatmap
        return {
            "type": viz_type,
            "title": f"{viz_type.capitalize()} for {query_text[:20]}...",
            "description": f"Analysis of data related to '{query_text}'",
            "raw_data": {
                "x": [random.randint(1, 100) for _ in range(20)],
                "y": [random.randint(1, 100) for _ in range(20)]
            }
        }
