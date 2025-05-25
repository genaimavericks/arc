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
    """Get entity names for autocomplete suggestions
    
    Args:
        schema_id: ID of the schema
        
    Returns:
        Dictionary with node_labels, relationship_types, and property_names
    """
    # Use hardcoded sample entities for demonstration
    # In a real implementation, these would come from the database
    sample_entities = {
        "node_labels": ["Person", "Product", "Order", "Customer", "Factory", "Batch", "Machine", "Supplier"],
        "relationship_types": ["ORDERED", "CONTAINS", "WORKS_AT", "PRODUCED", "SUPPLIED_BY", "OPERATES"],
        "property_names": {
            "Person": ["name", "age", "email", "role"],
            "Product": ["name", "price", "sku", "description"],
            "Order": ["id", "date", "total", "status"],
            "Customer": ["name", "email", "address", "phone"],
            "Factory": ["name", "location", "capacity", "manager"],
            "Batch": ["id", "date", "quantity", "status"]
        }
    }
    
    logger.debug(f"Using sample entities for autocomplete suggestions")
    return sample_entities

async def get_common_phrases() -> List[str]:
    """
    Get common phrases for autocomplete
    """
    # Return an empty list as we're removing common phrases
    return []

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
    
    # Get the current word being typed and analyze the query context
    if cursor_position > 0 and cursor_position <= len(partial_text):
        text_before_cursor = partial_text[:cursor_position]
        text_after_cursor = partial_text[cursor_position:]
        
        # Find the last delimiter before cursor to determine the current word
        # Consider spaces, commas, parentheses, and other Cypher delimiters
        delimiters = " ,()[]{}:;\n\t"
        last_delimiter_pos = -1
        for delimiter in delimiters:
            pos = text_before_cursor.rfind(delimiter)
            if pos > last_delimiter_pos:
                last_delimiter_pos = pos
        
        if last_delimiter_pos >= 0:
            current_word = text_before_cursor[last_delimiter_pos + 1:]
        else:
            current_word = text_before_cursor
        
        # Log the extracted current word for debugging
        logger.debug(f"Extracted current word: '{current_word}' from text before cursor: '{text_before_cursor}'")
    else:
        current_word = ""
        text_before_cursor = ""
        text_after_cursor = partial_text
    
    # Convert to lowercase for case-insensitive matching
    lower_text = partial_text.lower()
    lower_current_word = current_word.lower()
    
    suggestions = []
    
    # Always provide entity-based suggestions regardless of context
    # This simplifies the logic and ensures we always show entity suggestions
    
    # If the user is typing something, check for matching node labels or relationship types
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
        
        # Check for relationship type matches
        matching_relationships = []
        for rel_type in relationship_types:
            lower_rel_type = rel_type.lower()
            if lower_rel_type.startswith(lower_current_word):
                matching_relationships.append({"text": rel_type, "description": "Relationship type"})
        
        # Combine matches, prioritizing node labels
        combined_matches = matching_labels + matching_relationships
        
        if combined_matches:
            logger.debug(f"Found {len(combined_matches)} matching entities")
            return combined_matches[:10]  # Limit to 10 suggestions
    
    # Check if any node label is mentioned in the text
    words = lower_text.split()
    specified_label = None
    for label in node_labels:
        if label.lower() in words:
            specified_label = label
            break
            
    # If the user is typing a property name and we have property information
    if specified_label and specified_label in property_names and lower_current_word:
        props = property_names[specified_label]
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
    
    # If no matches found, return an empty list

    # The code below is unreachable due to the return statement above
    # This section is no longer needed as we've improved the context detection logic
    
    # If no specific suggestions, return empty list
    return []
