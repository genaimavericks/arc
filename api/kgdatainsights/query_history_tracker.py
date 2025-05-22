"""
Query History Tracker

Tracks and manages query history for providing intelligent suggestions.
"""

import json
import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio
from collections import Counter

logger = logging.getLogger(__name__)

# Maximum number of queries to store per schema
MAX_QUERIES_PER_SCHEMA = 100

# In-memory storage for query history
# Structure: {schema_id: [{"query": "...", "timestamp": "...", "count": 1}]}
query_history: Dict[str, List[Dict[str, Any]]] = {}

# Path to the query history file
HISTORY_FILE = os.path.join(os.path.dirname(__file__), "query_history.json")

async def load_query_history():
    """Load query history from file"""
    global query_history
    
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r") as f:
                query_history = json.load(f)
                logger.info(f"Loaded query history for {len(query_history)} schemas")
        else:
            query_history = {}
            logger.info("No query history file found, starting with empty history")
    except Exception as e:
        logger.error(f"Error loading query history: {str(e)}")
        query_history = {}

async def save_query_history():
    """Save query history to file"""
    try:
        with open(HISTORY_FILE, "w") as f:
            json.dump(query_history, f, indent=2)
            logger.info(f"Saved query history for {len(query_history)} schemas")
    except Exception as e:
        logger.error(f"Error saving query history: {str(e)}")

async def add_query_to_history(schema_id: str, query_text: str, successful: bool = True):
    """
    Add a query to the history
    
    Args:
        schema_id: ID of the schema
        query_text: The query text
        successful: Whether the query was successful
    """
    if not successful:
        # Only track successful queries
        return
    
    # Normalize query text (remove extra whitespace)
    query_text = " ".join(query_text.split())
    
    # Initialize history for this schema if it doesn't exist
    if schema_id not in query_history:
        query_history[schema_id] = []
    
    # Check if this query already exists in history
    existing_query = next((q for q in query_history[schema_id] if q["query"].lower() == query_text.lower()), None)
    
    if existing_query:
        # Update existing query
        existing_query["count"] += 1
        existing_query["timestamp"] = datetime.now().isoformat()
    else:
        # Add new query
        query_history[schema_id].append({
            "query": query_text,
            "timestamp": datetime.now().isoformat(),
            "count": 1
        })
    
    # Sort by count (descending) and timestamp (descending)
    query_history[schema_id].sort(key=lambda x: (-x["count"], x["timestamp"]), reverse=True)
    
    # Limit to maximum number of queries
    if len(query_history[schema_id]) > MAX_QUERIES_PER_SCHEMA:
        query_history[schema_id] = query_history[schema_id][:MAX_QUERIES_PER_SCHEMA]
    
    # Save history to file (async)
    asyncio.create_task(save_query_history())

async def get_query_suggestions(schema_id: str, current_input: str = "", max_suggestions: int = 5) -> List[str]:
    """
    Get query suggestions based on history
    
    Args:
        schema_id: ID of the schema
        current_input: Current user input (for context-aware suggestions)
        max_suggestions: Maximum number of suggestions to return
        
    Returns:
        List of suggested queries
    """
    suggestions = []
    
    if schema_id not in query_history:
        return suggestions
    
    # If current input is provided, filter suggestions that start with it
    if current_input:
        current_input_lower = current_input.lower()
        filtered_history = [
            q for q in query_history[schema_id] 
            if q["query"].lower().startswith(current_input_lower)
        ]
        
        # Add matching historical queries
        suggestions.extend([q["query"] for q in filtered_history[:max_suggestions]])
    else:
        # Add most frequent queries
        suggestions.extend([q["query"] for q in query_history[schema_id][:max_suggestions]])
    
    return suggestions[:max_suggestions]

async def extract_common_patterns(schema_id: str) -> List[str]:
    """
    Extract common patterns from query history
    
    Args:
        schema_id: ID of the schema
        
    Returns:
        List of common query patterns
    """
    if schema_id not in query_history or not query_history[schema_id]:
        return []
    
    # Extract node labels and relationship types from queries
    node_labels = []
    rel_types = []
    
    for query_item in query_history[schema_id]:
        query = query_item["query"].upper()
        
        # Extract node labels (e.g., :Person, :Product)
        import re
        labels = re.findall(r':\w+', query)
        node_labels.extend([label[1:] for label in labels])  # Remove the colon
        
        # Extract relationship types (e.g., :KNOWS, :PURCHASED)
        rel_matches = re.findall(r'\[(?:[\w]*:)([\w]+)', query)
        rel_types.extend(rel_matches)
    
    # Count occurrences
    common_labels = Counter(node_labels).most_common(5)
    common_rels = Counter(rel_types).most_common(5)
    
    # Generate pattern suggestions
    patterns = []
    
    # Add common node query patterns
    for label, _ in common_labels:
        patterns.append(f"MATCH (n:{label}) RETURN n LIMIT 10")
    
    # Add common relationship query patterns
    for rel, _ in common_rels:
        if common_labels:
            patterns.append(f"MATCH (n:{common_labels[0][0]})-[r:{rel}]->(m) RETURN n, r, m LIMIT 10")
    
    return patterns

# Initialize history on module load
asyncio.create_task(load_query_history())
