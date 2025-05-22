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
    """Get entity names from schema
    
    Args:
        schema_id: ID of the schema
        
    Returns:
        Dictionary with node_labels, relationship_types, and property_names
    """
    try:
        # Import the Neo4j schema helper
        try:
            # When imported as a module
            from api.kgdatainsights.neo4j_schema_helper import (
                get_neo4j_node_labels,
                get_neo4j_relationship_types,
                get_neo4j_property_keys
            )
        except ImportError:
            # When run directly
            from .neo4j_schema_helper import (
                get_neo4j_node_labels,
                get_neo4j_relationship_types,
                get_neo4j_property_keys
            )
        
        # Get node labels from Neo4j
        node_labels = await get_neo4j_node_labels()
        logger.debug(f"Retrieved {len(node_labels)} node labels from Neo4j: {node_labels}")
        
        # Get relationship types from Neo4j
        relationship_types = await get_neo4j_relationship_types()
        logger.debug(f"Retrieved {len(relationship_types)} relationship types from Neo4j: {relationship_types}")
        
        # Get property names for each node label
        property_names = {}
        for label in node_labels:
            properties = await get_neo4j_property_keys(label)
            property_names[label] = properties
            logger.debug(f"Retrieved {len(properties)} properties for node label '{label}'")
        
        return {
            "node_labels": node_labels,
            "relationship_types": relationship_types,
            "property_names": property_names
        }
    except Exception as e:
        logger.error(f"Error getting entity names: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "node_labels": [],
            "relationship_types": [],
            "property_names": {}
        }

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
    
    # Analyze the query context to determine what kind of suggestions to provide
    is_typing_node_label = False
    is_typing_relationship = False
    is_typing_property = False
    
    # Check if we're in a context where node labels are expected
    # This includes after a colon, after MATCH/CREATE/MERGE keywords, etc.
    if ":" in text_before_cursor and ":" in text_before_cursor[-len(current_word)-1:]:
        is_typing_node_label = True
        # If the user has typed a colon, extract just the part after it
        if ":" in current_word:
            current_word = current_word.split(":", 1)[1]
            lower_current_word = current_word.lower()
            logger.debug(f"Detected node label context after colon, current word: '{current_word}'")
    
    # Also check for node label context after certain keywords or patterns
    node_context_keywords = ["match", "create", "merge", "where", "with", "return"]
    for keyword in node_context_keywords:
        if keyword in lower_text and lower_text.rfind(keyword) > lower_text.rfind(";"):
            is_typing_node_label = True
            logger.debug(f"Detected node label context after keyword: '{keyword}'")
    
    # If the user is typing a node label
    if lower_current_word:
        # Debug logging to help diagnose matching issues
        logger.debug(f"Current word: '{lower_current_word}', Available node labels: {node_labels}")
        
        # Always check for node label matches regardless of context
        matching_labels = []
        for label in node_labels:
            lower_label = label.lower()
            if lower_label.startswith(lower_current_word):
                logger.debug(f"Match found: '{label}' starts with '{lower_current_word}'")
                matching_labels.append({"text": label, "description": "Node type"})
        
        if matching_labels:
            logger.debug(f"Found {len(matching_labels)} matching node labels: {matching_labels}")
            return matching_labels[:10]  # Limit to 10 suggestions
    
    # Check if we're in a context where relationship types are expected
    # This includes inside square brackets, after a dash, etc.
    if ("[" in text_before_cursor and "]" not in text_before_cursor[text_before_cursor.rfind("["):]) or \
       "-[" in text_before_cursor or \
       "]-" in text_before_cursor:
        is_typing_relationship = True
        logger.debug("Detected relationship context")
        
        # If we're inside brackets, extract just that part
        if "[" in current_word:
            current_word = current_word.split("[", 1)[1]
            if ":" in current_word:
                current_word = current_word.split(":", 1)[1]
            lower_current_word = current_word.lower()
            logger.debug(f"Extracted relationship part: '{current_word}'")
    
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
    
    # Check if we're in a context where property names are expected
    # This includes after a dot, inside WHERE clauses, etc.
    if "." in text_before_cursor:
        is_typing_property = True
        logger.debug("Detected property context")
        
        # If we're after a dot, extract just that part
        if "." in current_word:
            node_alias, prop_part = current_word.split(".", 1)
            current_word = prop_part
            lower_current_word = current_word.lower()
            logger.debug(f"Extracted property part: '{current_word}' for node alias: '{node_alias}'")
            
            # Try to determine the node label for this alias
            node_pattern = rf'\({node_alias}:(\w+)'
            import re
            label_matches = re.findall(node_pattern, partial_text)
            if label_matches:
                specified_label = label_matches[0]
                logger.debug(f"Found node label '{specified_label}' for alias '{node_alias}'")
    
    # If we have a specified label (either from context or explicitly provided)
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
        # If query is empty, suggest common starting patterns
        return [
            {"text": "MATCH (n) RETURN n LIMIT 10", "description": "Get some nodes"}, 
            {"text": "MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 10", "description": "Get some relationships"}
        ]
    
    # Check if we're in a specific query context and provide relevant suggestions
    if "MATCH" in partial_text.upper() and not "WHERE" in partial_text.upper():
        # After MATCH but before WHERE, suggest node patterns or WHERE clause
        return [
            {"text": "WHERE", "description": "Filter results"},
            {"text": "RETURN", "description": "Return results"}
        ]
    
    if "WHERE" in partial_text.upper() and not "RETURN" in partial_text.upper():
        # After WHERE but before RETURN, suggest property conditions
        return [
            {"text": "RETURN", "description": "Return results"},
            {"text": "AND", "description": "Logical AND"},
            {"text": "OR", "description": "Logical OR"}
        ]
    
    # Default to keyword suggestions if nothing else matched
    return [
        {"text": "MATCH", "description": "Match pattern in graph"}, 
        {"text": "WHERE", "description": "Filter results"}, 
        {"text": "RETURN", "description": "Return results"}, 
        {"text": "ORDER BY", "description": "Sort results"}, 
        {"text": "LIMIT", "description": "Limit number of results"}
    ]

    # The code below is unreachable due to the return statement above
    # This section is no longer needed as we've improved the context detection logic
    
    # If no specific suggestions, return empty list
    return []
