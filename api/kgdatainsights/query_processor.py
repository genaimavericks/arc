import asyncio
import logging
import random
import json
import os
import re
from pathlib import Path
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

async def get_autocomplete_suggestions(schema_id: str, partial_text: str, cursor_position: int, user: User) -> List[Dict[str, Any]]:
    """Get autocomplete suggestions based on partial text and schema
    
    This function now delegates to the autocomplete_service module for more advanced suggestions.
    
    Args:
        schema_id: ID of the schema
        partial_text: Text entered by the user
        cursor_position: Position of the cursor in the text
        user: User object
        
    Returns:
        List of suggestion objects with text and optional description
    """
    try:
        # Import the autocomplete service
        try:
            # When imported as a module
            from api.kgdatainsights.autocomplete_service import get_autocomplete_suggestions as get_suggestions
        except ImportError:
            # When run directly
            from .autocomplete_service import get_autocomplete_suggestions as get_suggestions
        
        # Get suggestions from the autocomplete service
        suggestions = await get_suggestions(schema_id, partial_text, cursor_position, user)
        return suggestions
    except Exception as e:
        # Log the error
        logger.error(f"Error getting autocomplete suggestions: {str(e)}")
        
        # Fall back to basic suggestions if there's an error
        entities = await get_entity_suggestions(schema_id)
        node_labels = entities["node_labels"]
        
        # Return basic suggestions
        if not partial_text.strip():
            return [
                {"text": "Show me all nodes", "description": "List all nodes in the graph"},
                {"text": "Find nodes where", "description": "Search for specific nodes"},
                {"text": "Count nodes by type", "description": "Count nodes by label"},
                {"text": "Match relationships between", "description": "Find connections"}
            ]
        
        # Suggest node labels
        if partial_text.lower().startswith("show") or partial_text.lower().startswith("find"):
            return [{"text": f"Show me all {label} nodes", "description": f"List all {label} nodes"} for label in node_labels[:5]]
        
        # Default suggestions
        return [{"text": suggestion, "description": None} for suggestion in ["Show", "Find", "Count", "Match", "Where"]]

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

async def get_query_suggestions(schema_id: str, user: User, current_text: str = "", cursor_position: int = 0) -> List[str]:
    """Get query suggestions based on schema, canned queries, and query history"""
    # Get entity suggestions from schema
    entities = await get_entity_suggestions(schema_id)
    node_labels = entities["node_labels"]
    relationship_types = entities["relationship_types"]
    
    # Generate suggestions based on schema entities
    schema_suggestions = []
    
    # Add node-based suggestions
    for label in node_labels[:3]:  # Limit to first 3 node types to avoid too many suggestions
        schema_suggestions.append(f"Show me all {label} nodes")
        schema_suggestions.append(f"Count {label} nodes")
    
    # Add relationship-based suggestions
    if len(node_labels) >= 2 and len(relationship_types) > 0:
        schema_suggestions.append(f"Find relationships between {node_labels[0]} and {node_labels[1]}")
    
    # Add general suggestions if we don't have enough
    if len(schema_suggestions) < 5:
        general_suggestions = [
            "Show the most connected nodes",
            "Find the shortest path between two nodes",
            "What are the main entities in this graph?"
        ]
        schema_suggestions.extend(general_suggestions)
    
    # Get canned queries from file
    canned_queries = []
    try:
        # Directory to store query history and predefined queries as JSON files
        OUTPUT_DIR = Path("runtime-data/output/kgdatainsights")
        QUERIES_DIR = OUTPUT_DIR / "queries"
        
        # Try different possible filenames for the schema
        possible_filenames = [
            f"{schema_id}_queries.json",  # Original format with spaces
            f"{schema_id.replace(' ', '_')}_queries.json",  # Replace spaces with underscores
            f"{schema_id.split()[0]}_queries.json" if ' ' in schema_id else None,  # First word only
            "3_queries.json"  # Hardcoded ID that we know exists
        ]
        
        # Filter out None values
        possible_filenames = [f for f in possible_filenames if f]
        
        # Try each filename
        for filename in possible_filenames:
            canned_queries_file = QUERIES_DIR / filename
            logger.info(f"Trying to load canned queries from: {canned_queries_file}")
            
            if os.path.exists(canned_queries_file):
                with open(canned_queries_file, "r") as f:
                    queries_data = json.load(f)
                    # Extract queries from the general category
                    if "general" in queries_data:
                        canned_queries = [item.get("query", "") for item in queries_data["general"] if "query" in item]
                        logger.info(f"Loaded {len(canned_queries)} canned queries from file: {filename}")
                        break  # Stop after finding a valid file
    except Exception as e:
        logger.error(f"Error loading canned queries from file: {str(e)}")
    
    # Get query history from file
    history_queries = []
    try:
        # Directory for history
        HISTORY_DIR = OUTPUT_DIR / "history"
        
        # Try different possible filenames for the schema
        possible_filenames = [
            f"{schema_id}_history.json",  # Original format with spaces
            f"{schema_id.replace(' ', '_')}_history.json",  # Replace spaces with underscores
            f"{schema_id.split()[0]}_history.json" if ' ' in schema_id else None,  # First word only
            "3_history.json"  # Hardcoded ID that we know exists
        ]
        
        # Filter out None values
        possible_filenames = [f for f in possible_filenames if f]
        
        # Try each filename
        for filename in possible_filenames:
            history_file = HISTORY_DIR / filename
            logger.info(f"Trying to load query history from: {history_file}")
            
            if os.path.exists(history_file):
                with open(history_file, "r") as f:
                    history_data = json.load(f)
                    # Extract queries from history
                    history_queries = [item.get("query", "") for item in history_data if "query" in item]
                    logger.info(f"Loaded {len(history_queries)} history queries from file: {filename}")
                    break  # Stop after finding a valid file
    except Exception as e:
        logger.error(f"Error loading query history from file: {str(e)}")
    
    # Log detailed information about the sources
    logger.info(f"Schema-based suggestions for {schema_id}: {len(schema_suggestions)} items")
    logger.info(f"Canned queries for {schema_id}: {len(canned_queries)} items")
    logger.info(f"History queries for {schema_id}: {len(history_queries)} items")
    
    # Prioritize canned queries and history over schema-based suggestions
    # First add canned queries and history
    prioritized_suggestions = []
    
    # Add canned queries first (they're curated for quality)
    prioritized_suggestions.extend(canned_queries)
    
    # Then add history queries (they represent user's actual usage)
    for query in history_queries:
        if query not in prioritized_suggestions:  # Avoid duplicates
            prioritized_suggestions.append(query)
    
    # Finally, add schema-based suggestions to fill any remaining slots
    for suggestion in schema_suggestions:
        if suggestion not in prioritized_suggestions:  # Avoid duplicates
            prioritized_suggestions.append(suggestion)
    
    # Filter suggestions based on user input if provided
    filtered_suggestions = prioritized_suggestions
    logger.info(f"Current text for filtering: '{current_text}'")
    
    if current_text and current_text.strip():
        # Extract all words from user input, including partial words
        current_text_lower = current_text.lower().strip()
        
        # Log the exact text being used for filtering
        logger.info(f"Filtering suggestions based on text: '{current_text_lower}'")
        
        # Score each suggestion based on whether it contains the user's input
        scored_suggestions = []
        for suggestion in prioritized_suggestions:
            suggestion_lower = suggestion.lower()
            
            # Direct match gets highest score
            if current_text_lower in suggestion_lower:
                # Calculate how early in the suggestion the match occurs (earlier = better)
                position_score = 1.0 - (suggestion_lower.find(current_text_lower) / len(suggestion_lower))
                # Higher score for matches at the beginning
                score = 10 + (position_score * 5)
                scored_suggestions.append((suggestion, score))
                logger.info(f"  Direct match: '{suggestion}' (score: {score:.2f})")
            # Word-by-word partial matching as fallback
            else:
                # Extract words from user input (ignore very short words)
                user_words = [word for word in re.findall(r'\b\w+\b', current_text_lower) if len(word) > 2]
                
                if user_words:
                    # Count how many user words are in this suggestion
                    matches = [word for word in user_words if word in suggestion_lower]
                    if matches:
                        # Score based on number of matching words and their coverage of input
                        word_score = len(matches) / len(user_words)
                        score = word_score * 5  # Scale to be lower than direct matches
                        scored_suggestions.append((suggestion, score))
                        logger.info(f"  Word match: '{suggestion}' matches words {matches} (score: {score:.2f})")
        
        # Sort by score (highest first)
        scored_suggestions.sort(key=lambda x: x[1], reverse=True)
        
        # If we have filtered suggestions, use them
        if scored_suggestions:
            filtered_suggestions = [item[0] for item in scored_suggestions]
            logger.info(f"Found {len(filtered_suggestions)} suggestions matching user input '{current_text_lower}'")
        else:
            logger.info(f"No suggestions match user input '{current_text_lower}', using unfiltered list")
    
    # Log the final list of suggestions with their sources
    logger.info(f"Final suggestions for {schema_id}: {len(filtered_suggestions)} items")
    for i, suggestion in enumerate(filtered_suggestions[:10]):
        source = "unknown"
        if suggestion in schema_suggestions:
            source = "schema"
        elif suggestion in canned_queries:
            source = "canned"
        elif suggestion in history_queries:
            source = "history"
        logger.info(f"  Suggestion {i+1}: '{suggestion}' (source: {source})")
    
    return filtered_suggestions[:10]  # Return at most 10 suggestions

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

async def refresh_cache_task(schema_id: str) -> None:
    """
    Background task to refresh the query suggestion cache for a given schema.
    
    This function loads and caches:
    1. Schema data
    2. Query suggestions (from history, canned queries, and schema-based patterns)
    3. Common phrases and linguistic patterns
    
    Args:
        schema_id: ID of the schema to refresh cache for
    """
    try:
        logger.info(f"Refreshing query suggestion cache for schema {schema_id}")
        
        # Refresh schema data cache
        await get_schema_data(schema_id)
        
        # Create a dummy user for cache initialization
        dummy_user = User(id=0, username="system", email="system@example.com")
        
        # Pre-load entity suggestions
        await get_entity_suggestions(schema_id)
        
        # Pre-load query suggestions (without filtering)
        suggestions = await get_query_suggestions(schema_id, dummy_user)
        logger.info(f"Cached {len(suggestions)} query suggestions for schema {schema_id}")
        
        # Ensure directories exist for query history and suggestions
        output_dir = Path("runtime-data/output/kgdatainsights")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        queries_dir = output_dir / "queries"
        queries_dir.mkdir(exist_ok=True)
        
        history_dir = output_dir / "history"
        history_dir.mkdir(exist_ok=True)
        
        logger.info(f"Successfully refreshed cache for schema {schema_id}")
    except Exception as e:
        logger.error(f"Error refreshing cache for schema {schema_id}: {str(e)}")
