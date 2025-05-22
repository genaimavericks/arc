"""
Suggestion Service

Provides contextually relevant suggestions for queries based on:
1. Common phrases and SQL/Cypher keywords
2. Query history
3. Schema information
"""

import json
import os
import logging
import asyncio
from typing import List, Dict, Any, Optional, Set
import re

# Import other modules
from .neo4j_schema_helper import get_neo4j_node_labels, get_neo4j_relationship_types, get_neo4j_property_keys
from .query_history_tracker import get_query_suggestions, extract_common_patterns

logger = logging.getLogger(__name__)

# Path to common phrases file
COMMON_PHRASES_FILE = os.path.join(os.path.dirname(__file__), "common_phrases.json")

# Cache for common phrases
common_phrases_cache: Dict[str, Any] = {}

async def load_common_phrases():
    """Load common phrases from file"""
    global common_phrases_cache
    
    try:
        if os.path.exists(COMMON_PHRASES_FILE):
            with open(COMMON_PHRASES_FILE, "r") as f:
                common_phrases_cache = json.load(f)
                logger.info(f"Loaded common phrases: {len(common_phrases_cache.get('keywords', {}))} keywords, "
                           f"{len(common_phrases_cache.get('common_phrases', {}))} common phrases")
        else:
            logger.warning(f"Common phrases file not found: {COMMON_PHRASES_FILE}")
            common_phrases_cache = {"keywords": {}, "common_phrases": {}, "domain_specific": {}}
    except Exception as e:
        logger.error(f"Error loading common phrases: {str(e)}")
        common_phrases_cache = {"keywords": {}, "common_phrases": {}, "domain_specific": {}}

async def get_keyword_suggestions(partial_text: str) -> List[str]:
    """
    Get keyword suggestions based on partial text
    
    Args:
        partial_text: Partial text entered by user
        
    Returns:
        List of keyword suggestions
    """
    if not common_phrases_cache:
        await load_common_phrases()
    
    suggestions = []
    
    # If partial text is empty, return common keywords
    if not partial_text:
        # Return top 5 common keywords
        top_keywords = list(common_phrases_cache.get("keywords", {}).keys())[:5]
        return [kw.upper() for kw in top_keywords]
    
    # Convert to lowercase for case-insensitive matching
    partial_lower = partial_text.lower()
    
    # Check for keyword matches
    for keyword, data in common_phrases_cache.get("keywords", {}).items():
        if keyword.lower().startswith(partial_lower):
            suggestions.append(keyword.upper())
    
    return suggestions[:5]  # Limit to 5 suggestions

async def get_phrase_suggestions(schema_id: str, partial_text: str, node_labels: List[str]) -> List[str]:
    """
    Get phrase suggestions based on partial text and schema
    
    Args:
        schema_id: ID of the schema
        partial_text: Partial text entered by user
        node_labels: List of node labels from the schema
        
    Returns:
        List of phrase suggestions
    """
    if not common_phrases_cache:
        await load_common_phrases()
    
    suggestions = []
    
    # If we have node labels, try to generate domain-specific suggestions
    if node_labels:
        # Check for manufacturing domain if we have relevant node labels
        manufacturing_nodes = {"Machine", "Batch", "Product", "Defect", "Location"}
        if any(label in manufacturing_nodes for label in node_labels):
            # Add manufacturing-specific suggestions
            for phrase_key, phrase_data in common_phrases_cache.get("domain_specific", {}).get("manufacturing", {}).items():
                template = phrase_data.get("template", "")
                
                # Replace placeholders with actual values from schema
                for label in node_labels:
                    if "{node_label}" in template:
                        template = template.replace("{node_label}", label, 1)
                        suggestions.append(template)
    
    # Add common phrases
    for phrase_key, phrase_data in common_phrases_cache.get("common_phrases", {}).items():
        template = phrase_data.get("template", "")
        
        # Replace placeholders with actual values from schema
        if node_labels and "{node_label}" in template:
            for label in node_labels[:2]:  # Limit to first 2 labels to avoid too many suggestions
                suggestion = template.replace("{node_label}", label)
                suggestions.append(suggestion)
    
    # If partial text is provided, filter suggestions
    if partial_text:
        partial_lower = partial_text.lower()
        suggestions = [s for s in suggestions if s.lower().startswith(partial_lower)]
    
    return suggestions[:5]  # Limit to 5 suggestions

async def analyze_query_context(query_text: str) -> Dict[str, Any]:
    """
    Analyze query context to determine what the user is trying to do
    
    Args:
        query_text: Current query text
        
    Returns:
        Dictionary with context information
    """
    context = {
        "query_type": None,
        "node_labels": [],
        "relationship_types": [],
        "properties": [],
        "last_keyword": None,
        "last_token": None
    }
    
    if not query_text:
        return context
    
    # Convert to uppercase for keyword matching
    query_upper = query_text.upper()
    
    # Identify query type
    if "MATCH" in query_upper:
        context["query_type"] = "read"
    elif "CREATE" in query_upper:
        context["query_type"] = "write"
    elif "MERGE" in query_upper:
        context["query_type"] = "merge"
    elif "DELETE" in query_upper or "REMOVE" in query_upper:
        context["query_type"] = "delete"
    
    # Extract node labels
    node_labels = re.findall(r':\s*(\w+)', query_text)
    context["node_labels"] = node_labels
    
    # Extract relationship types
    rel_types = re.findall(r'\[\s*(?:\w+\s*:)?\s*(\w+)', query_text)
    context["relationship_types"] = rel_types
    
    # Extract properties
    properties = re.findall(r'\.(\w+)\s*[=<>]', query_text)
    context["properties"] = properties
    
    # Determine last keyword
    keywords = ["MATCH", "WHERE", "RETURN", "CREATE", "DELETE", "SET", "REMOVE", "WITH", "ORDER BY", "LIMIT", "SKIP"]
    for keyword in keywords:
        if keyword in query_upper:
            last_pos = query_upper.rfind(keyword)
            if last_pos > query_upper.rfind(context["last_keyword"] or "") if context["last_keyword"] else -1:
                context["last_keyword"] = keyword
    
    # Get last token
    tokens = query_text.split()
    context["last_token"] = tokens[-1] if tokens else ""
    
    return context

async def get_context_aware_suggestions(schema_id: str, query_text: str, cursor_position: int) -> List[str]:
    """
    Get context-aware suggestions based on the current query and cursor position
    
    Args:
        schema_id: ID of the schema
        query_text: Current query text
        cursor_position: Current cursor position
        
    Returns:
        List of suggestions
    """
    # Ensure common phrases are loaded
    if not common_phrases_cache:
        await load_common_phrases()
    
    suggestions = []
    
    # Get text before cursor
    text_before_cursor = query_text[:cursor_position]
    
    # Get the current word being typed
    current_word = ""
    if text_before_cursor:
        # Find the last space before cursor to determine the current word
        last_space_pos = text_before_cursor.rfind(" ")
        if last_space_pos >= 0:
            current_word = text_before_cursor[last_space_pos + 1:]
        else:
            current_word = text_before_cursor
    
    # If query is empty or just starting, suggest keywords and common queries
    if not text_before_cursor or text_before_cursor.isspace():
        # Get keyword suggestions
        keyword_suggestions = await get_keyword_suggestions("")
        suggestions.extend(keyword_suggestions)
        
        # Get historical query suggestions
        history_suggestions = await get_query_suggestions(schema_id)
        suggestions.extend(history_suggestions)
        
        return suggestions[:10]  # Limit to 10 suggestions
    
    # Analyze query context
    context = await analyze_query_context(text_before_cursor)
    
    # If typing a keyword, suggest matching keywords
    if current_word and not current_word.isspace() and not ":" in current_word and not "." in current_word:
        keyword_suggestions = await get_keyword_suggestions(current_word)
        suggestions.extend(keyword_suggestions)
    
    # Get node labels from schema
    node_labels = await get_neo4j_node_labels()
    
    # If after a MATCH or CREATE keyword, suggest node patterns
    if context["last_keyword"] in ["MATCH", "CREATE", "MERGE"] and "(" in text_before_cursor:
        # If typing a node label (after a colon)
        if ":" in current_word:
            label_prefix = current_word.split(":")[-1]
            matching_labels = [
                f"{current_word.split(':')[0]}:{label}" 
                for label in node_labels 
                if label.lower().startswith(label_prefix.lower())
            ]
            suggestions.extend(matching_labels)
    
    # If after a WHERE keyword, suggest property conditions
    if context["last_keyword"] == "WHERE" and "." in current_word:
        node_alias, prop_prefix = current_word.split(".", 1)
        
        # If we have identified node labels in the query, get their properties
        if context["node_labels"]:
            for label in context["node_labels"]:
                properties = await get_neo4j_property_keys(label)
                matching_props = [
                    f"{node_alias}.{prop}" 
                    for prop in properties 
                    if prop.lower().startswith(prop_prefix.lower())
                ]
                suggestions.extend(matching_props)
    
    # If after a RETURN keyword, suggest node aliases and properties
    if context["last_keyword"] == "RETURN":
        # Extract node aliases from the query
        aliases = re.findall(r'\(\s*(\w+)\s*:', text_before_cursor)
        
        # Suggest node aliases
        for alias in aliases:
            if not current_word or alias.lower().startswith(current_word.lower()):
                suggestions.append(alias)
            
            # Suggest properties for this alias
            if current_word and current_word.startswith(f"{alias}."):
                prop_prefix = current_word[len(f"{alias}."):]
                
                # Find the node label for this alias
                alias_pattern = rf'\(\s*{alias}\s*:(\w+)'
                label_matches = re.findall(alias_pattern, text_before_cursor)
                
                if label_matches:
                    label = label_matches[0]
                    properties = await get_neo4j_property_keys(label)
                    matching_props = [
                        f"{alias}.{prop}" 
                        for prop in properties 
                        if prop.lower().startswith(prop_prefix.lower())
                    ]
                    suggestions.extend(matching_props)
    
    # Add phrase suggestions based on context
    phrase_suggestions = await get_phrase_suggestions(schema_id, current_word, node_labels)
    suggestions.extend(phrase_suggestions)
    
    # Add historical query suggestions
    history_suggestions = await get_query_suggestions(schema_id, current_word)
    suggestions.extend(history_suggestions)
    
    # Remove duplicates while preserving order
    unique_suggestions = []
    seen = set()
    for suggestion in suggestions:
        if suggestion.lower() not in seen:
            unique_suggestions.append(suggestion)
            seen.add(suggestion.lower())
    
    return unique_suggestions[:10]  # Limit to 10 suggestions

# Initialize on module load
asyncio.create_task(load_common_phrases())
