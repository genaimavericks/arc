"""
JSON Processing Optimizations for generate_neo4j_files.py

This module contains optimized functions for JSON data processing that can be used to 
replace the corresponding functions in the generate_neo4j_files.py script.
"""

import json
import pandas as pd
import ast
import re
import logging

# Cache settings
MAX_CACHE_SIZE = 10000  # Maximum number of items to keep in caches
json_parse_cache = {}  # Cache for parsed JSON data

def clean_non_json_chars_optimized(value):
    """Clean and prepare a string for JSON parsing by removing problematic characters."""
    if pd.isna(value) or value == '':
        return None
    
    # Common replacements for JSON-like strings that don't parse correctly
    value_str = str(value)
    
    # Remove any leading/trailing whitespace or quotes
    value_str = value_str.strip()
    
    # Handle JSON array format with single quotes
    if value_str.startswith('[{') or value_str.startswith('{'):
        # Make sure single quotes are converted to double quotes for JSON
        value_str = value_str.replace("'", '"')
        
        # Fix common JSON formatting issues
        value_str = value_str.replace('None', 'null')
        
        # Make sure property names are in double quotes
        value_str = re.sub(r'([{,])\s*([a-zA-Z0-9_() %]+):', r'\1"\2":', value_str)
    
    # Remove leading/trailing quotes if they exist
    if value_str.startswith('"') and value_str.endswith('"'):
        value_str = value_str[1:-1]
    
    return value_str

def parse_json_data_optimized(value):
    """Attempts to parse a JSON string into a Python object with caching for performance."""
    if pd.isna(value) or value == '':
        return None
    
    # First clean the string
    cleaned_value = clean_non_json_chars_optimized(value)
    if not cleaned_value:
        return None
        
    # Check cache first
    if cleaned_value in json_parse_cache:
        return json_parse_cache[cleaned_value]
        
    # Limit cache size to prevent memory issues
    if len(json_parse_cache) > MAX_CACHE_SIZE:
        # Clear half the cache when it gets too large
        keys_to_remove = list(json_parse_cache.keys())[:MAX_CACHE_SIZE//2]
        for key in keys_to_remove:
            json_parse_cache.pop(key, None)
    
    result = None
    try:
        # First try standard JSON parsing (fastest method)
        result = json.loads(cleaned_value)
    except json.JSONDecodeError:
        try:
            # If that fails, try Python's literal_eval which can parse some non-standard JSON
            # This helps with cases where single quotes are used instead of double quotes
            result = ast.literal_eval(cleaned_value)
        except (ValueError, SyntaxError):
            # For more complex cases, try some additional parsing strategies
            
            # Check if it looks like a JSON array
            if cleaned_value.startswith('[') and cleaned_value.endswith(']'):
                try:
                    # Try to parse each item in the array separately
                    items = []
                    array_content = cleaned_value[1:-1].strip()
                    
                    # Use regex to split by commas outside of braces/brackets
                    # This is more efficient than character-by-character parsing
                    # This regex finds commas that are not inside {} or [] brackets
                    parts = re.split(r',(?=(?:[^{}\[\]]*(?:\{[^{}]*\}|\[[^\[\]]*\])?)*[^{}\[\]]*$)', array_content)
                    
                    # Process each part
                    for part in parts:
                        part = part.strip()
                        if not part:
                            continue
                            
                        try:
                            # Try to parse this part as JSON
                            item_dict = json.loads(part)
                            if item_dict:
                                items.append(item_dict)
                        except Exception:
                            # If JSON parsing fails, try literal_eval
                            try:
                                item_dict = ast.literal_eval(part)
                                if item_dict:
                                    items.append(item_dict)
                            except Exception:
                                pass
                    
                    if items:
                        result = items
                except Exception:
                    pass
    
    # Cache the result
    if result is not None:
        json_parse_cache[cleaned_value] = result
        
    return result

# Reference to the generate_node_id function from the main script
# This will be set by the main script when importing this module
generate_node_id = None

def process_json_column_optimized(original_df, json_col, source_label, target_label, relationship_type, schema, nodes_data, node_headers, relationships_output, batch_size=5000):
    # Initialize counters for reporting
    json_nodes_created = 0
    json_relationships_created = 0
    processed_relationship_types = set()
    
    # Get the schema for the source node
    source_node_schema = next((node for node in schema['nodes'] if node['label'] == source_label), None)
    if not source_node_schema:
        logging.warning(f"No schema found for source label {source_label}")
        return 0, 0, processed_relationship_types
        
    # Get the schema for the target node
    target_node_schema = next((node for node in schema['nodes'] if node['label'] == target_label), None)
    if not target_node_schema:
        logging.warning(f"No schema found for target label {target_label}")
        return 0, 0, processed_relationship_types
        
    # Get the schema for the relationship
    relationship_schema = next((rel for rel in schema['relationships'] if rel['type'] == relationship_type), None)
    if not relationship_schema:
        logging.warning(f"No schema found for relationship type {relationship_type}")
        return 0, 0, processed_relationship_types
        
    # Initialize data structures
    if target_label not in nodes_data:
        nodes_data[target_label] = {}
    if target_label not in node_headers:
        node_headers[target_label] = set()
    if source_label not in nodes_data:
        nodes_data[source_label] = {}
        
    # Track existing relationships to avoid duplicates
    existing_relationships = set()
    
    # Check if this column contains JSON array data
    is_json_array_column = json_col.endswith('_Members') or json_col.endswith('_Array') or json_col.endswith('_List')
    
    # Process the JSON column in batches
    logging.info(f"Processing {json_col} column in batches of {batch_size}")
    
    # Store all JSON items for batch processing
    all_json_items = {}
    source_node_ids = {}
    
    # Get the mapping from the schema
    mapping = next((m for m in schema.get('json_mappings', []) 
                   if m.get('source_column') == json_col 
                   and m.get('target_label') == target_label), None)
    
    if not mapping or 'property_schema' not in mapping:
        logging.warning(f"No property schema found for JSON mapping from {json_col} to {target_label}")
        return 0, 0, set()
    
    # Update node headers with property schema keys
    node_headers[target_label].update(mapping['property_schema'].keys())
    
    logging.info(f"Processing column '{json_col}' to create {target_label} nodes")
    
    # First, collect all valid rows with JSON data
    valid_rows = []
    source_node_ids = {}
    
    # Use a set to track existing relationships for faster lookups
    existing_relationships = set()
    
    # Pre-compute source node IDs and filter valid rows
    logging.info(f"Pre-processing JSON data in column '{json_col}'")
    
    # Get the source node schema once outside the loop
    source_node_schema = next((n for n in schema.get('nodes', []) if n.get('label') == source_label), None)
    if not source_node_schema:
        logging.warning(f"Source node schema not found for label: {source_label}")
        return 0, 0, set()
        
    # Process in batches for better memory management
    total_batches = (len(original_df) + batch_size - 1) // batch_size
    
    for batch_num in range(total_batches):
        start_idx = batch_num * batch_size
        end_idx = min(start_idx + batch_size, len(original_df))
        batch_df = original_df.iloc[start_idx:end_idx]
        
        for index, row in batch_df.iterrows():
            if json_col not in row or pd.isna(row[json_col]):
                continue
                
            # Generate source node ID
            source_node_id = generate_node_id(source_node_schema, row)
            if not source_node_id:
                continue
                
            # For relationships involving JSON array columns, we should process them even if source nodes don't exist yet
            # This allows for creating relationships between nodes that are defined in the JSON arrays
            if is_json_array_column:
                # Allow processing even if the source node doesn't exist yet
                pass
            elif source_node_id not in nodes_data.get(source_label, {}):
                continue
                
            # Store the row and source node ID for later processing
            valid_rows.append((index, row))
            source_node_ids[index] = source_node_id
    
    # Initialize a dictionary to store all JSON items by row index
    all_json_items = {}
    
    # Parse all JSON data in one pass
    logging.info(f"Parsing JSON data from {len(valid_rows)} rows")
    for index, row in valid_rows:
        json_str = clean_non_json_chars_optimized(row[json_col])
        json_data = parse_json_data_optimized(json_str)
        
        if not json_data:
            # If parsing failed, log a debug message with a sample
            if index < 5:  # Only log the first few failures to avoid log spam
                logging.debug(f"Failed to parse JSON data in row {index}, column '{json_col}': {str(row[json_col])[:100]}")
            continue
            
        # If it's not a list, convert it to a list with one item
        if not isinstance(json_data, list):
            json_data = [json_data]
            
        # Store valid JSON items
        all_json_items[index] = [item for item in json_data if isinstance(item, dict)]
    
    # Pre-compute property type mapping for better performance
    property_type_mapping = {}
    for prop_name, prop_details in mapping['property_schema'].items():
        if isinstance(prop_details, dict):
            property_type_mapping[prop_name] = prop_details.get('type', 'string')
        elif isinstance(prop_details, str):
            property_type_mapping[prop_name] = prop_details
    
    # Process all JSON items and create nodes and relationships
    logging.info(f"Processing JSON items and creating nodes and relationships")
    
    # Check if this column contains JSON array data
    is_json_array_column = json_col.endswith('_Members') or json_col.endswith('_Array') or json_col.endswith('_List')
    
    # Batch process the JSON items
    for index, json_items in all_json_items.items():
        source_node_id = source_node_ids[index]
        
        for i, item in enumerate(json_items):
            # Generate a unique ID for this node
            # Try to use a name-like field from the item first, if available
            name_field = None
            for key in item.keys():
                if 'name' in key.lower() or key.lower() == 'id':
                    name_field = item[key]
                    break
                    
            if name_field:
                # Use the name field to ensure consistent IDs across rows
                target_node_id = f"{target_label}-{name_field}"
            else:
                # Fallback to position-based ID
                target_node_id = f"{target_label}-{source_node_id}-{i}"
            
            # Check for existing relationship using the set for faster lookup
            rel_key = (source_node_id, target_node_id, relationship_type)
            
            # For JSON array columns, ensure the source node exists in the nodes_data dictionary
            if is_json_array_column:
                # Create or update the source node if needed
                if source_node_id not in nodes_data.get(source_label, {}):
                    logging.info(f"Creating {source_label} node {source_node_id} for {relationship_type} relationship")
                    nodes_data.setdefault(source_label, {})[source_node_id] = {
                        ':ID': source_node_id,
                        ':LABEL': source_label
                    }
                # Ensure the target node is created
                if target_node_id not in nodes_data.get(target_label, {}):
                    logging.info(f"Creating {target_label} node {target_node_id} for {relationship_type} relationship")
                    node_data = {
                        ':ID': target_node_id,
                        ':LABEL': target_label
                    }
                    # Add properties from the JSON item
                    for key, value in item.items():
                        prop_name = key
                        if prop_name in property_type_mapping:
                            node_data[prop_name] = value
                            node_headers[target_label].add(prop_name)
                    nodes_data[target_label][target_node_id] = node_data
            
            # Create the relationship if it doesn't exist
            if rel_key not in existing_relationships:
                rel_data = {
                    ':START_ID': source_node_id,
                    ':END_ID': target_node_id,
                    ':TYPE': relationship_type
                }
                relationships_output.append(rel_data)
                existing_relationships.add(rel_key)
                processed_relationship_types.add(relationship_type)
                json_relationships_created += 1
            
            # Skip node creation if this node was already processed
            if target_node_id in nodes_data[target_label]:
                continue
            
            # Create the node data
            node_data = {
                ":ID": target_node_id,
                ":LABEL": target_label
            }
            
            # Add all properties from the JSON item
            for key, value in item.items():
                # Map to a property that exists in the schema if possible
                prop_name = next((p for p in mapping['property_schema'].keys() if p.lower() == key.lower()), key)
                
                # Get the target type from pre-computed mapping or infer from value
                target_type = property_type_mapping.get(prop_name)
                if not target_type:
                    # Guess the type based on the value
                    if isinstance(value, bool):
                        target_type = 'boolean'
                    elif isinstance(value, int):
                        target_type = 'integer'
                    elif isinstance(value, float):
                        target_type = 'float'
                    else:
                        target_type = 'string'
                
                # Convert value to the right type
                if target_type in ['string', 'integer', 'float', 'boolean', 'date', 'datetime']:
                    node_data[prop_name] = cast_value(value, target_type)
                else:
                    node_data[prop_name] = value
                    
                # Track headers
                node_headers[target_label].add(prop_name)
            
            # Add node to the data
            nodes_data[target_label][target_node_id] = node_data
            json_nodes_created += 1
            
    logging.info(f"Generated {json_nodes_created} {target_label} nodes from '{json_col}' column")
    logging.info(f"Generated {json_relationships_created} {relationship_type} relationships from '{json_col}' column")
    
    return json_nodes_created, json_relationships_created, processed_relationship_types

# Reference to the cast_value function from the main script
# This will be set by the main script when importing this module
cast_value = None

# Note: This function is a placeholder and should be replaced with the actual implementation
# from the original script when integrating these optimizations
def generate_node_id(node_schema, row):
    """Placeholder for the generate_node_id function from the original script."""
    pass

# Note: This function is a placeholder and should be replaced with the actual implementation
# from the original script when integrating these optimizations
def cast_value(value, target_type):
    """Placeholder for the cast_value function from the original script."""
    pass

# Usage instructions:
"""
To use these optimized functions in the generate_neo4j_files.py script:

1. Replace the original clean_non_json_chars function with clean_non_json_chars_optimized
2. Replace the original parse_json_data function with parse_json_data_optimized
3. Replace the JSON column processing code in the create_neo4j_import_files function with 
   a call to process_json_column_optimized

Example integration:

# In the create_neo4j_import_files function, replace the JSON processing code with:

for mapping in schema.get('json_mappings', []):
    json_col = mapping.get('source_column')
    target_label = mapping.get('target_label')
    relationship_type = mapping.get('relationship_type')
    source_label = mapping.get('source_label')
    
    if not json_col or not target_label or not relationship_type or not source_label:
        continue
        
    if json_col not in original_df.columns:
        logging.warning(f"JSON column '{json_col}' not found in data")
        continue
        
    nodes_created, rels_created, new_rel_types = process_json_column_optimized(
        original_df, json_col, source_label, target_label, relationship_type,
        schema, nodes_data, node_headers, relationships_output, BATCH_SIZE
    )
    
    # Update processed relationship types
    processed_relationship_types.update(new_rel_types)
"""
