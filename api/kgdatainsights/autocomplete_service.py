"""
Autocomplete service for Knowledge Graph Insights.
Provides schema-aware autocomplete suggestions for the chat interface.
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
import json
import re

# Fix import paths for both direct and module imports
try:
    # When imported as a module
    from api.models import User, Schema
    from api.db_config import get_db
    from api.kgdatainsights.query_processor import get_schema_data
except ImportError:
    # When run directly
    from ..models import User, Schema
    from ..db_config import get_db
    from .query_processor import get_schema_data

logger = logging.getLogger(__name__)

# Cache for entity names and properties
autocomplete_cache = {}

async def get_entity_names(schema_id: str) -> Dict[str, List[str]]:
    """
    Get entity names (node labels, relationship types, property names) from schema
    """
    # Check cache first
    cache_key = f"entity_names_{schema_id}"
    if cache_key in autocomplete_cache:
        return autocomplete_cache[cache_key]
    
    # Get schema data
    schema_data = await get_schema_data(schema_id)
    
    # Extract node labels
    node_labels = [node.get("label", "") for node in schema_data.get("nodes", [])]
    node_labels = list(set(filter(None, node_labels)))
    
    # Extract relationship types
    relationship_types = [rel.get("type", "") for rel in schema_data.get("relationships", [])]
    relationship_types = list(set(filter(None, relationship_types)))
    
    # Extract property names by node label
    property_names = {}
    for node in schema_data.get("nodes", []):
        label = node.get("label", "")
        if label:
            props = [prop.get("name", "") for prop in node.get("properties", [])]
            props = list(set(filter(None, props)))
            property_names[label] = props
    
    # Prepare result
    result = {
        "node_labels": node_labels,
        "relationship_types": relationship_types,
        "property_names": property_names
    }
    
    # Cache the result
    autocomplete_cache[cache_key] = result
    
    return result

async def get_common_phrases() -> List[str]:
    """
    Get common phrases for autocomplete
    """
    return [
        "Show me all",
        "Find nodes where",
        "Count nodes by",
        "Match relationships between",
        "What are the most connected",
        "How many",
        "Which nodes have the highest",
        "Show the relationship between",
        "List all properties of"
    ]

async def get_autocomplete_suggestions(
    schema_id: str, 
    partial_text: str, 
    cursor_position: int, 
    user: User
) -> List[Dict[str, Any]]:
    """
    Get autocomplete suggestions based on partial text and schema
    
    Args:
        schema_id: ID of the schema
        partial_text: Text entered by the user
        cursor_position: Position of the cursor in the text
        user: User object
        
    Returns:
        List of suggestion objects with text and optional description
    """
    # Get entity names from schema
    entity_data = await get_entity_names(schema_id)
    node_labels = entity_data["node_labels"]
    relationship_types = entity_data["relationship_types"]
    property_names = entity_data["property_names"]
    
    # Get common phrases
    common_phrases = await get_common_phrases()
    
    # Get the current word being typed
    if cursor_position > 0 and cursor_position <= len(partial_text):
        text_before_cursor = partial_text[:cursor_position]
        
        # Find the last space before cursor to determine the current word
        last_space_pos = text_before_cursor.rfind(" ")
        if last_space_pos >= 0:
            current_word = text_before_cursor[last_space_pos + 1:]
        else:
            current_word = text_before_cursor
    else:
        current_word = ""
    
    # Convert to lowercase for case-insensitive matching
    lower_text = partial_text.lower()
    lower_current_word = current_word.lower()
    
    suggestions = []
    
    # If the user is typing a node label
    if lower_current_word:
        # Debug logging to help diagnose matching issues
        logger.debug(f"Current word: '{lower_current_word}', Available node labels: {node_labels}")
        
        # Check for node label matches
        matching_labels = []
        for label in node_labels:
            lower_label = label.lower()
            if lower_label.startswith(lower_current_word):
                logger.debug(f"Match found: '{label}' starts with '{lower_current_word}'")
                matching_labels.append({"text": label, "description": "Node type"})
        
        if matching_labels:
            logger.debug(f"Found {len(matching_labels)} matching node labels: {matching_labels}")
            return matching_labels[:10]  # Limit to 10 suggestions
    
    # If the user is typing a relationship type
    if lower_current_word:
        # Check for relationship type matches
        matching_rel_types = []
        for rel_type in relationship_types:
            lower_rel_type = rel_type.lower()
            if lower_rel_type.startswith(lower_current_word):
                logger.debug(f"Match found: relationship '{rel_type}' starts with '{lower_current_word}'")
                matching_rel_types.append({"text": rel_type, "description": "Relationship type"})
        
        if matching_rel_types:
            logger.debug(f"Found {len(matching_rel_types)} matching relationship types")
            return matching_rel_types[:10]  # Limit to 10 suggestions
    
    # If the user is typing a property name
    # First, determine if we've specified a node label
    words = lower_text.split()
    specified_label = None
    for label in node_labels:
        if label.lower() in words:
            specified_label = label
            break
    
    if specified_label and specified_label in property_names:
        props = property_names[specified_label]
        if lower_current_word:
            # Check for property name matches
            matching_props = []
            for prop in props:
                lower_prop = prop.lower()
                if lower_prop.startswith(lower_current_word):
                    logger.debug(f"Match found: property '{prop}' of '{specified_label}' starts with '{lower_current_word}'")
                    matching_props.append({"text": prop, "description": f"Property of {specified_label}"})
            
            if matching_props:
                logger.debug(f"Found {len(matching_props)} matching properties for {specified_label}")
                return matching_props[:10]  # Limit to 10 suggestions
    
    # Context-aware suggestions based on query patterns
    if not partial_text.strip():
        # Empty input, suggest common phrases
        return [{"text": phrase, "description": "Common query pattern"} for phrase in common_phrases]
    
    # Suggest node labels after "Show me all" or similar phrases
    show_patterns = ["show me all", "find all", "list all", "get all"]
    if any(lower_text.startswith(pattern) for pattern in show_patterns):
        return [
            {"text": f"{partial_text} {label} nodes", "description": f"Show all {label} nodes"} 
            for label in node_labels[:10]
        ]
    
    # Suggest relationship patterns
    if "relationship" in lower_text or "connected to" in lower_text:
        suggestions = []
        for source in node_labels[:3]:  # Limit to first 3 node types
            for target in node_labels[:3]:
                if source != target:
                    for rel_type in relationship_types[:2]:  # Limit to first 2 relationship types
                        suggestion = f"Match {source}-[{rel_type}]->{target}"
                        suggestions.append({
                            "text": suggestion,
                            "description": f"Find {source} nodes connected to {target} nodes"
                        })
        return suggestions[:10]  # Limit to 10 suggestions
    
    # Suggest property-based filters
    if "where" in lower_text or "with" in lower_text:
        for label in node_labels:
            if label.lower() in lower_text and label in property_names:
                props = property_names[label]
                return [
                    {"text": f"{partial_text} {prop} =", "description": f"Filter by {prop}"} 
                    for prop in props[:10]
                ]
    
    # Default suggestions based on input length
    if len(partial_text) < 10:
        return [{"text": phrase, "description": "Common query pattern"} for phrase in common_phrases]
    
    # If no specific suggestions, return empty list
    return []
