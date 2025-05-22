import json
import csv
import pandas as pd
import os
import argparse
import logging
from pathlib import Path
import string
import re
import ast

# Import optimized JSON processing functions
try:
    # Try relative import first (when run as a module)
    from api.kgdata_loader.json_processing_optimizations import (
        clean_non_json_chars_optimized,
        parse_json_data_optimized,
        process_json_column_optimized,
        generate_node_id
    )
except ImportError:
    # Fall back to local import (when run directly)
    from json_processing_optimizations import (
        clean_non_json_chars_optimized,
        parse_json_data_optimized,
        process_json_column_optimized,
        generate_node_id
    )

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Performance optimization settings
BATCH_SIZE = 5000  # Process data in batches of this size

# Cache settings
MAX_CACHE_SIZE = 10000  # Maximum number of items to keep in caches
json_parse_cache = {}  # Cache for parsed JSON data
existing_relationships_set = set()  # For faster relationship lookups

# --- Helper Functions ---

def convert_to_neo4j_type(python_type):
    """Converts Python type to Neo4j compatible type for CSV headers."""
    if not python_type:
        return None
        
    # Mapping from Python type name to Neo4j type
    type_mapping = {
        'string': 'string',
        'str': 'string',
        'integer': 'int',
        'int': 'int',
        'float': 'float',
        'double': 'float',
        'boolean': 'boolean',
        'bool': 'boolean',
        'date': 'date',
        'datetime': 'datetime',
        # Add other mappings as needed
    }
    return type_mapping.get(str(python_type).lower(), None)

# Common date formats to check before using the expensive pd.to_datetime
DATE_FORMATS = [
    '%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d',
    '%d-%m-%Y', '%m-%d-%Y', '%Y.%m.%d', '%d.%m.%Y'
]

# Cache for previously inferred types
type_cache = {}

def infer_data_type(val):
    """Infers the data type based on the value.
    
    Args:
        val: Value to infer type from
        
    Returns:
        string: The inferred type (string, integer, float, boolean, date, datetime)
    """
    # Check cache first
    if val in type_cache:
        return type_cache[val]
        
    if val is None:
        return None
    
    # If it's already a typed value (not a string), use its Python type
    if isinstance(val, bool):
        result = 'boolean'
    elif isinstance(val, int):
        result = 'integer'
    elif isinstance(val, float):
        # All floats are treated as floats for consistency
        result = 'float'
    else:
        # For strings and other types, try to parse
        # Convert to string for parsing
        val_str = str(val).strip()
        if not val_str or val_str.lower() == 'nan' or val_str.lower() == 'null':
            result = None
        # Check if it's a boolean
        elif val_str.lower() in ('true', 'false', 't', 'f', 'yes', 'no', 'y', 'n'):
            result = 'boolean'
        else:
            # Check if it's a number
            try:
                # Try to convert to int first
                int(val_str)
                result = 'integer'
            except (ValueError, TypeError):
                try:
                    # Then try float
                    float(val_str)
                    result = 'float'
                except (ValueError, TypeError):
                    # Check if it's a date using common formats first (faster)
                    is_date = False
                    for fmt in DATE_FORMATS:
                        try:
                            import datetime
                            dt = datetime.datetime.strptime(val_str, fmt)
                            # If it parsed successfully, it's a date
                            if dt.hour == 0 and dt.minute == 0 and dt.second == 0:
                                result = 'date'
                            else:
                                result = 'datetime'
                            is_date = True
                            break
                        except (ValueError, TypeError):
                            continue
                    
                    if not is_date:
                        # Only use expensive pd.to_datetime as a last resort
                        try:
                            dt = pd.to_datetime(val_str)
                            # If it has time components with non-zero values
                            if dt.hour != 0 or dt.minute != 0 or dt.second != 0:
                                result = 'datetime'
                            else:
                                result = 'date'
                        except (ValueError, TypeError):
                            # Default to string if nothing else matches
                            result = 'string'
    
    # Cache the result for future use
    type_cache[val] = result
    return result

# Cache for column type detection results
column_type_cache = {}

def detect_type_mismatch(df, column_name, schema_type):
    """Detects if the schema type matches the actual data types in a column.
    
    Args:
        df: DataFrame containing the data
        column_name: The column to check
        schema_type: The type specified in the schema
        
    Returns:
        (boolean, string) - Whether there's a mismatch and the recommended type
    """
    # Check if we've already analyzed this column
    cache_key = f"{id(df)}_{column_name}_{schema_type}"
    if cache_key in column_type_cache:
        return column_type_cache[cache_key]
        
    if column_name not in df.columns:
        result = (False, schema_type)
        column_type_cache[cache_key] = result
        return result
    
    # Get non-null values for type checking
    values = df[column_name].dropna()
    if len(values) == 0:
        result = (False, schema_type)  # No data to infer from
        column_type_cache[cache_key] = result
        return result
    
    # Use a smaller sample size to improve performance
    sample_size = min(len(values), 20)  # Reduced from 100 to 20
    
    # Use a fixed random seed for reproducibility and to avoid resampling
    samples = values.sample(sample_size, random_state=42) if len(values) > 20 else values
    
    # Count types in sample
    type_counts = {}
    for val in samples:
        inferred_type = infer_data_type(val)
        if inferred_type:
            type_counts[inferred_type] = type_counts.get(inferred_type, 0) + 1
    
    if not type_counts:  # All null values
        result = (False, schema_type)
        column_type_cache[cache_key] = result
        return result
    
    # Find the most common type
    most_common_type = max(type_counts.items(), key=lambda x: x[1])[0]
    
    # Check type compatibility
    compatible = False
    
    # If schema doesn't specify a type, use the inferred type
    if not schema_type:
        result = (True, most_common_type)
        column_type_cache[cache_key] = result
        return result
    
    # Check compatibility between schema type and inferred type
    if schema_type == most_common_type:
        compatible = True
    # Integer can be stored as float
    elif schema_type == 'float' and most_common_type == 'integer':
        compatible = True
    # String can store anything
    elif schema_type == 'string':
        compatible = True
    # Date can be stored as datetime
    elif schema_type == 'datetime' and most_common_type == 'date':
        compatible = True
    
    # If compatible, use schema type, otherwise recommend the inferred type
    result = (not compatible, most_common_type if not compatible else schema_type)
    column_type_cache[cache_key] = result
    return result

def cast_value(value, target_type):
    """Attempts to cast a value to the specified Neo4j type."""
    if pd.isna(value) or value == '':
        return None  # Represent missing values as None

    try:
        if target_type == 'string':
            return str(value)
        elif target_type == 'integer':
            # Handle potential floats in CSV representation of integers
            return int(float(value))
        elif target_type == 'float':
            return float(value)
        elif target_type == 'boolean':
             # Handle common string representations of boolean
            if isinstance(value, bool):
                return value
            
            # Handle string representations
            val_str = str(value).strip().lower()
            if val_str in ('true', 't', '1', 'yes', 'y'):
                return True
            elif val_str in ('false', 'f', '0', 'no', 'n'):
                return False
            else:
                return bool(value)
        elif target_type == 'date':
            if pd.isna(value):
                return None
            dt = pd.to_datetime(value)
            if pd.isna(dt): # Check again after conversion
                return None
            return dt.strftime('%Y-%m-%d')
        elif target_type == 'datetime':
            if pd.isna(value):
                return None
            dt = pd.to_datetime(value)
            if pd.isna(dt): # Check again after conversion
                return None
            # Format for Neo4j datetime: yyyy-MM-ddTHH:mm:ss.sssZ
            return dt.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        # Add other type conversions as needed (e.g., point)
        else:
            logging.warning(f"Unsupported target type '{target_type}' for value '{value}'. Returning as string.")
            return str(value)
    except (ValueError, TypeError) as e:
        logging.error(f"Error casting value '{value}' to type '{target_type}': {e}. Returning None.")
        return None

def clean_non_json_chars(value):
    """Clean and prepare a string for JSON parsing by removing problematic characters."""
    # Directly use the optimized version
    return clean_non_json_chars_optimized(value)

def parse_json_data(value):
    """Attempts to parse a JSON string into a Python object with caching for performance."""
    # Directly use the optimized version
    return parse_json_data_optimized(value)

def generate_node_id(node_schema, row):
    """Generates a unique ID for a node based on schema rules or primary property."""
    # Check if the node schema defines a specific ID generation rule
    id_rule = node_schema.get('id_rule')
    if id_rule:
        # Use the specified rule to generate the ID
        if id_rule.get('type') == 'property':
            # Use a specific property as the ID
            prop_name = id_rule.get('property')
            if prop_name and prop_name in row and not pd.isna(row[prop_name]):
                return f"{node_schema.get('label')}-{row[prop_name]}"
        elif id_rule.get('type') == 'composite':
            # Use multiple properties to form a composite ID
            properties = id_rule.get('properties', [])
            if properties:
                parts = []
                for prop in properties:
                    if prop in row and not pd.isna(row[prop]):
                        parts.append(str(row[prop]))
                    else:
                        # If any part is missing, we can't form a complete ID
                        return None
                if parts:
                    return f"{node_schema.get('label')}-{'_'.join(parts)}"
    
    # Handle old schema format with explicit ID specifications
    id_config = node_schema.get('id', {})
    if id_config and 'property' in id_config:
        id_prop = id_config['property']
        if id_prop in row.index:
            id_val = row[id_prop]
            if not pd.isna(id_val) and id_val != '':
                return f"{node_schema['label']}-{id_val}"
    
    # If no specific rule or rule application failed, use the primary property
    primary_prop = node_schema.get('primary_property')
    if primary_prop and primary_prop in row and not pd.isna(row[primary_prop]):
        return f"{node_schema.get('label')}-{row[primary_prop]}"
    
    # Try to find a property with the same name as the label
    for prop_name in node_schema.get('properties', {}).keys():
        if prop_name in row.index:
            id_val = row[prop_name]
            if not pd.isna(id_val) and id_val != '':
                return f"{node_schema['label']}-{id_val}"
    
    # Try to find common ID properties
    for id_name in ['id', 'ID', 'Id', 'name', 'Name', 'identifier', 'Identifier', 'key', 'Key']:
        if id_name in row.index:
            id_val = row[id_name]
            if not pd.isna(id_val) and id_val != '':
                return f"{node_schema['label']}-{id_val}"
    
    # If no explicit ID is specified in the schema, use heuristics to determine the best ID property
    # Try to find a property that looks like an ID
    for col in row.index:
        if 'id' in col.lower() and not pd.isna(row[col]):
            return f"{node_schema.get('label')}-{row[col]}"
    
    # If we still don't have an ID, use a hash of the row values
    row_hash = hash(tuple(str(v) for v in row.values if not pd.isna(v)))
    return f"{node_schema.get('label')}-{abs(row_hash)}"


# Set the reference to this function in the optimized module
try:
    # Try to set it in the imported module
    import sys
    if 'api.kgdata_loader.json_processing_optimizations' in sys.modules:
        sys.modules['api.kgdata_loader.json_processing_optimizations'].generate_node_id = generate_node_id
        sys.modules['api.kgdata_loader.json_processing_optimizations'].cast_value = cast_value
    elif 'json_processing_optimizations' in sys.modules:
        sys.modules['json_processing_optimizations'].generate_node_id = generate_node_id
        sys.modules['json_processing_optimizations'].cast_value = cast_value
except Exception as e:
    logging.warning(f"Could not set function references in optimized module: {e}")

# --- Main Processing Function ---

def create_neo4j_import_files(schema_path, data_path, output_dir):
    """
    Generates nodes.csv and relationships.csv files for Neo4j import.

    Args:
        schema_path (str): Path to the JSON schema file.
        data_path (str): Path to the input CSV data file.
        output_dir (str): Directory to save the output CSV files.
    """
    logging.info(f"Loading schema from: {schema_path}")
    try:
        with open(schema_path, 'r') as f:
            schema = json.load(f)
    except FileNotFoundError:
        logging.error(f"Schema file not found: {schema_path}")
        return
    except json.JSONDecodeError as e:
        logging.error(f"Error parsing schema JSON: {e}")
        return
    
    logging.info(f"Loading data from {data_path}")
    try:
        # Use optimized CSV reading parameters
        df = pd.read_csv(
            data_path, 
            low_memory=False,
            # Only parse dates when needed later, not during initial load
            parse_dates=False,
            # Use a more efficient engine
            engine='c' if 'c' in pd.read_csv.__doc__ else 'python'
        )
        logging.info(f"Loaded {len(df)} rows of data")
    except Exception as e:
        logging.error(f"Error loading data: {e}")
        raise
    
    # Add indexes to the DataFrame to help with lookups later
    original_df = df.reset_index(drop=True)
    
    logging.info(f"Loaded CSV has {len(original_df)} rows and {len(original_df.columns)} columns")
    logging.info(f"First few columns: {list(original_df.columns[:5])}")
    logging.info(f"Output directory: {output_dir}")
        
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Data storage structures
    nodes_data = {}  # Dictionary by label of node data
    node_headers = {}  # Track headers by label
    relationships_output = []  # List of relationship data
    rel_headers = set([':START_ID', ':END_ID', ':TYPE'])  # Standard rel headers
    processed_relationship_types = set()  # Track which relationship types have been processed
    json_array_mappings = {}  # Track columns that contain JSON arrays
    
    # Process JSON array columns in schema first to identify which node types will be processed from JSON
    json_handled_node_types = set()
    for rel_schema in schema.get('relationships', []):
        # Get relationship details
        source_label = rel_schema.get('startNode')
        target_label = rel_schema.get('endNode')
        rel_type = rel_schema.get('type')
        
        logging.info(f"Checking relationship: {rel_type} ({source_label} -> {target_label})")
        
        # Find the target node schema to get its properties
        target_node_schema = next((n for n in schema.get('nodes', []) if n.get('label') == target_label), None)
        if not target_node_schema:
            continue
            
        # Find columns in the CSV that might contain related entity data for this relationship type
        # First, look for direct matches where column name contains the target label or relationship type
        potential_columns = []
        
        # Create naming patterns to look for based on relationship and target node type
        rel_parts = re.split(r'[^a-zA-Z0-9]', rel_type.lower())
        target_parts = re.split(r'[^a-zA-Z0-9]', target_label.lower())
        
        for col in original_df.columns:
            col_lower = col.lower()
            col_parts = re.split(r'[^a-zA-Z0-9]', col_lower)
            
            # High priority match if column name directly contains target node label
            direct_match = any(part in col_lower for part in target_parts) or target_label.lower() in col_lower
            
            # Medium priority match if column contains relationship type words
            rel_match = any(part in col_lower for part in rel_parts)
            
            # Also check if column name looks like it might contain nested data for this relationship
            # For example: "team_members" for a "HAS_TEAM_MEMBER" relationship
            related_match = False
            for rel_part in rel_parts:
                if len(rel_part) > 3:  # Only consider meaningful parts, not small words
                    if rel_part in col_lower:
                        related_match = True
                        break
            
            if direct_match or rel_match or related_match:
                # Look at a sample to see if it might contain JSON-like data
                sample_values = original_df[col].dropna().head(3)
                if not sample_values.empty:
                    for sample_value in sample_values:
                        value_str = str(sample_value)
                        
                        # Prioritize columns that look like they contain structured data
                        has_json_syntax = ((value_str.startswith('[') and value_str.endswith(']')) or 
                            (value_str.startswith('{') and value_str.endswith('}')) or
                            ("{'" in value_str and "':" in value_str) or
                            ('{"' in value_str and '":' in value_str))
                            
                        # Check for patterns that suggest this contains related entity data
                        has_related_data = (
                            ("name" in value_str.lower() and ":" in value_str) or
                            (target_label.lower() in value_str.lower() and ":" in value_str) or
                            ("id" in value_str.lower() and ":" in value_str))
                            
                        # If the column looks like it contains JSON or related entity data
                        if has_json_syntax or has_related_data:
                            # Try to parse a sample to verify it's valid JSON or can be converted
                            clean_sample = clean_non_json_chars(sample_value)
                            test_parse = parse_json_data(clean_sample)
                            
                            if test_parse is not None:
                                logging.info(f"Found structured data in '{col}' column - mapping to {target_label} nodes via {rel_type}")
                                json_array_mappings[col] = {
                                    'source_node': source_label,
                                    'target_node': target_label,
                                    'relationship_type': rel_type,
                                    'property_schema': target_node_schema.get('properties', {})
                                }
                                json_handled_node_types.add(target_label)
                                break
                        
                    # Only process one sample per column
                    if col in json_array_mappings:
                        break

    # --- Process Nodes ---
    logging.info("Processing nodes...")
    
    # Process standard nodes 
    for node_schema in schema.get('nodes', []):
        label = node_schema.get('label')
        
        # Skip nodes that will be processed from JSON arrays
        if label in json_handled_node_types:
            logging.info(f"Skipping {label} nodes in initial processing - will handle through JSON arrays")
            continue
            
        logging.info(f"Processing label: {label}")
        
        if not label:
            logging.warning("Node schema missing 'label' field. Skipping.")
            continue
            
        # Initialize dictionary for this node type if it doesn't exist
        if label not in nodes_data:
            nodes_data[label] = {}
            node_headers[label] = set([':ID', ':LABEL'])
            
        # Get property schema for this node type
        properties_schema = node_schema.get('properties', {})
        
        # Check data types against schema and update if necessary
        for prop_name, prop_details in properties_schema.items():
            source_col = None
            schema_type = None
            
            if isinstance(prop_details, dict):
                source_col = prop_details.get('source_column', prop_name)
                schema_type = prop_details.get('type', 'string')
            elif isinstance(prop_details, dict) and prop_details.get('type') == 'json':
                source_col = prop_details.get('source_column', prop_name)
                schema_type = 'json'
                target_node_type = prop_details.get('target_node')
                relationship_type = prop_details.get('relationship_type')
                
                if target_node_type and relationship_type and source_col in original_df.columns:
                    logging.info(f"Found JSON array mapping: {source_col} -> {target_node_type} via {relationship_type}")
                    json_array_mappings[source_col] = {
                        'source_node': label,
                        'target_node': target_node_type,
                        'relationship_type': relationship_type,
                        'property_schema': prop_details.get('properties', {})
                    }
            elif isinstance(prop_details, str):
                source_col = prop_name
                schema_type = prop_details
            
            # If it's a simple string type, it might indicate the column name directly
            elif isinstance(prop_details, str) and prop_details == 'json':
                # Look for potential JSON array columns
                if prop_name in original_df.columns:
                    # Assume this is a JSON array
                    logging.info(f"Found potential JSON array in column: {prop_name}")
                    # We'll detect the relationship type from the schema later
                    for rel_schema in schema.get('relationships', []):
                        if rel_schema.get('endNode') == label:
                            target_node_type = rel_schema.get('endNode')
                            relationship_type = rel_schema.get('type')
                            if target_node_type and relationship_type:
                                logging.info(f"Identified JSON array mapping: {prop_name} -> {target_node_type} via {relationship_type}")
                                json_array_mappings[prop_name] = {
                                    'source_node': rel_schema.get('startNode'),
                                    'target_node': target_node_type,
                                    'relationship_type': relationship_type,
                                    'property_schema': {}  # Will be detected from the data
                                }
        
        # Process each row in the CSV data
        for index, row in original_df.iterrows():
            # Generate unique ID for this node
            node_id = generate_node_id(node_schema, row)
            
            if not node_id:
                # Skip this row if no valid ID could be generated
                continue
                
            # Skip if node already processed (avoid duplicates)
            if node_id in nodes_data[label]:
                continue
                
            # Create node data
            node_data = {
                ":ID": node_id,
                ":LABEL": label
            }
            
            # Process properties according to schema
            for prop_name, prop_details in properties_schema.items():
                # Determine source column name and target data type
                source_col = None
                target_type = None
                use_generated_id = False
                
                if isinstance(prop_details, dict):
                    source_col = prop_details.get('source_column', prop_name)
                    target_type = prop_details.get('type', 'string')
                    use_generated_id = prop_details.get('use_id', False)
                elif isinstance(prop_details, str):
                    source_col = prop_name
                    target_type = prop_details
                
                # Check data types against schema and update if necessary
                if source_col and source_col in original_df.columns and not use_generated_id:
                    has_mismatch, inferred_type = detect_type_mismatch(original_df, source_col, target_type)
                    if has_mismatch:
                        logging.warning(f"Type mismatch for {label}.{prop_name}: schema says '{target_type}' but data indicates '{inferred_type}'")
                        # Update the schema type to match the data
                        if isinstance(prop_details, dict):
                            properties_schema[prop_name]['type'] = inferred_type
                            target_type = inferred_type
                        else:
                            properties_schema[prop_name] = inferred_type
                            target_type = inferred_type
                        logging.info(f"Updated type for {label}.{prop_name} from '{target_type}' to '{inferred_type}'")
                
                # Get property value
                prop_value = None
                if use_generated_id:
                    prop_value = node_id
                elif source_col and source_col in original_df.columns:
                    if target_type == 'json':
                        prop_value = parse_json_data(clean_non_json_chars(row[source_col]))
                    else:
                        prop_value = cast_value(row[source_col], target_type)
                elif source_col:
                    logging.warning(f"Source column '{source_col}' not found in CSV. Setting property '{prop_name}' to null.")
                    
                # Add property to node data
                node_data[prop_name] = prop_value
                node_headers[label].add(prop_name)  # Track header
                
            # Store node data for later writing to file
            nodes_data[label][node_id] = node_data
            
            # Check if this node is a target of any relationship in the schema
            processed_node_relationships = set()
            for rel_schema in schema.get('relationships', []):
                # Check if this relationship involves the current node as source or target
                if rel_schema.get('startNode') == label:
                    # This node is the source of the relationship
                    target_label = rel_schema.get('endNode')
                    relationship_type = rel_schema.get('type')
                    
                    # Skip if we have already processed this relationship type for this node
                    relationship_key = f"{node_id}_{relationship_type}"
                    if relationship_key in processed_node_relationships:
                        continue
                    processed_node_relationships.add(relationship_key)
                    
                    # Find the target node ID column
                    target_node_schema = next((n for n in schema.get('nodes', []) if n.get('label') == target_label), None)
                    if not target_node_schema:
                        continue
                    
                    # Only create the relationship if target nodes exist in our data
                    if target_label in nodes_data and len(nodes_data[target_label]) > 0:
                        # Find the column that determines the relationship
                        rel_col = None
                        for col in row.index:
                            if target_label in col or any(p.lower() in col.lower() for p in target_node_schema.get('properties', {}).keys()):
                                rel_col = col
                                break
                        
                        if rel_col and rel_col in row and not pd.isna(row[rel_col]):
                            # Get target node ID
                            target_id_value = row[rel_col]
                            
                            # Try to find the target node ID format
                            if target_label in nodes_data:
                                target_node_ids = list(nodes_data[target_label].keys())
                                if target_node_ids:
                                    # Match format from existing target nodes
                                    sample_id = target_node_ids[0]
                                    if sample_id.startswith(f"{target_label}-"):
                                        target_id = f"{target_label}-{target_id_value}"
                                    else:
                                        target_id = str(target_id_value)
                                    
                                    # Only create relationship if target node exists
                                    if target_id in nodes_data[target_label]:
                                        rel_data = {
                                            ':START_ID': node_id,
                                            ':END_ID': target_id,
                                            ':TYPE': relationship_type
                                        }
                                        relationships_output.append(rel_data)
                                        rel_headers.update(rel_data.keys())
                                        processed_relationship_types.add(relationship_type)
    
    # Process JSON arrays in CSV columns
    logging.info("Processing JSON arrays in CSV columns...")
    
    # Directly use the optimized function for all JSON mappings
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
        
        # Use the optimized function to process the JSON column
        nodes_created, rels_created, new_rel_types = process_json_column_optimized(
            original_df, json_col, source_label, target_label, relationship_type,
            schema, nodes_data, node_headers, relationships_output, BATCH_SIZE
        )
        
        # Update processed relationship types
        processed_relationship_types.update(new_rel_types)
    
        # Create a new DataFrame with the typed headers
        typed_df = df.copy()
        typed_df.columns = [neo4j_headers.get(col, col) for col in df.columns]
        
        # Write the file with type information in the headers
        output_path = os.path.join(output_dir, f"{label}_nodes.csv")
        typed_df.to_csv(output_path, index=False, lineterminator='\n')
        logging.info(f"Successfully wrote node file: {output_path}")
    else:
        logging.warning(f"No data generated for node label: {label}")

    # --- Process Relationships ---
    logging.info("Processing relationships...")
    
    # Process relationships defined in the schema
    for rel_schema in schema['relationships']:
        rel_type = rel_schema['type']
        from_label = rel_schema['source']
        to_label = rel_schema['target']
        
        logging.info(f"Processing relationship type: {rel_type} ({from_label} -> {to_label})")
        
        # Generic handling for relationships with JSON array columns
        # Check if this relationship involves a JSON array column
        json_array_column = None
        for column in original_df.columns:
            if column.endswith('_Members') or column.endswith('_Array') or column.endswith('_List'):
                # Check if this column contains JSON arrays
                sample_value = original_df[column].dropna().iloc[0] if not original_df[column].dropna().empty else None
                if sample_value and isinstance(sample_value, str) and (sample_value.startswith('[') or sample_value.startswith('{')):
                    # Find if this column is related to the current relationship
                    if (column.replace('_Members', '').replace('_Array', '').replace('_List', '') == to_label or 
                        to_label.lower() in column.lower()):
                        json_array_column = column
                        logging.info(f"Found JSON array column {json_array_column} for relationship {rel_type}")
                        break
        
        if json_array_column:
            # Process JSON array column to create target nodes and relationships
            logging.info(f"Special handling for {rel_type} relationship using {json_array_column}")
            relationship_count = 0
            
            for index, row in original_df.iterrows():
                if json_array_column in row and not pd.isna(row[json_array_column]):
                    # Get the source node ID
                    source_schema = next((n for n in schema['nodes'] if n['label'] == from_label), None)
                    source_id = generate_node_id(source_schema, row)
                    
                    if not source_id:
                        continue
                        
                    # Ensure source node exists
                    if source_id not in nodes_data.get(from_label, {}):
                        logging.info(f"Creating {from_label} node {source_id} for {rel_type} relationship")
                        nodes_data.setdefault(from_label, {})[source_id] = {
                            ':ID': source_id,
                            ':LABEL': from_label
                        }
                    
                    # Process JSON array data
                    json_data = parse_json_data_optimized(clean_non_json_chars_optimized(row[json_array_column]))
                    
                    if json_data and isinstance(json_data, list):
                        for item in json_data:
                            if isinstance(item, dict):
                                # Determine a unique ID for the target node
                                # Try to use a name-like field from the item first, if available
                                name_field = None
                                for key in item.keys():
                                    if 'name' in key.lower() or key.lower() == 'id':
                                        name_field = item[key]
                                        break
                                        
                                if name_field:
                                    target_id = f"{to_label}-{name_field}"
                                else:
                                    # Fallback to a position-based ID
                                    target_id = f"{to_label}-{source_id}-{hash(str(item))}"
                                
                                # Create target node if it doesn't exist
                                if target_id not in nodes_data.get(to_label, {}):
                                    node_data = {
                                        ':ID': target_id,
                                        ':LABEL': to_label
                                    }
                                    # Add properties from the JSON item
                                    for key, value in item.items():
                                        node_data[key] = value
                                        node_headers.setdefault(to_label, set()).add(key)
                                    
                                    # Add to nodes_data
                                    nodes_data.setdefault(to_label, {})[target_id] = node_data
                                
                                # Create relationship
                                rel_data = {
                                    ':START_ID': source_id,
                                    ':END_ID': target_id,
                                    ':TYPE': rel_type
                                }
                                
                                # Add relationship properties if defined in schema
                                rel_props = rel_schema.get('properties', {})
                                for prop_name, prop_details in rel_props.items():
                                    if isinstance(prop_details, dict):
                                        target_type = prop_details.get('type')
                                    else:
                                        target_type = prop_details
                                        
                                    # Get property value from JSON item
                                    if prop_name in item:
                                        rel_data[prop_name] = cast_value(item[prop_name], target_type)
                                
                                relationships_output.append(rel_data)
                                rel_headers.update(rel_data.keys())
                                relationship_count += 1
                                processed_relationship_types.add(rel_type)
            
            if relationship_count > 0:
                logging.info(f"Generated {relationship_count} relationships of type {rel_type}")
            continue
            
        # Skip if either node type doesn't exist in our data
        if from_label not in nodes_data or to_label not in nodes_data:
            logging.warning(f"Skipping relationship type {rel_type} due to missing node data for {from_label} or {to_label}")
            continue
            
        logging.info(f"Processing relationship type: {rel_type} ({from_label} -> {to_label})")
        
        # Get node schemas for ID generation
        startNode_schema = next((n for n in schema['nodes'] if n['label'] == from_label), None)
        endNode_schema = next((n for n in schema['nodes'] if n['label'] == to_label), None)
        
        if not startNode_schema or not endNode_schema:
            logging.warning(f"Could not find node schemas for {from_label} or {to_label}. Skipping relationship.")
            continue
        
        # For each row in the ORIGINAL CSV data, try to create a relationship
        relationship_count = 0
        for index, row in original_df.iterrows():
            # Generate node IDs using the exact same method as node creation
            startNode_id = generate_node_id(startNode_schema, row)
            endNode_id = generate_node_id(endNode_schema, row)
            
            # Debug info to track down the issue
            logging.debug(f"Row {index}: Generated startNode_id={startNode_id}, endNode_id={endNode_id}")
            
            # Check if both nodes exist in our nodes_data dictionaries
            startNode_exists = startNode_id is not None and startNode_id in nodes_data[from_label]
            endNode_exists = endNode_id is not None and endNode_id in nodes_data[to_label]
            
            if startNode_exists and endNode_exists:
                # We found a valid relationship! Add it.
                rel_props = rel_schema.get('properties', {})
                rel_data = {
                    ':START_ID': startNode_id,
                    ':END_ID': endNode_id,
                    ':TYPE': rel_type
                }
                
                # Process relationship properties
                for prop_name, prop_details in rel_props.items():
                    if isinstance(prop_details, dict):
                        source_col = prop_details.get('source_column')
                        target_type = prop_details.get('type')
                    else:
                        source_col = prop_name
                        target_type = prop_details
                        
                    # Check data types against schema and update if necessary
                    if source_col and source_col in original_df.columns:
                        has_mismatch, inferred_type = detect_type_mismatch(original_df, source_col, target_type)
                        if has_mismatch:
                            logging.warning(f"Type mismatch for relationship property {prop_name}: schema says '{target_type}' but data indicates '{inferred_type}'")
                            # Update the schema type to match the data
                            if isinstance(prop_details, dict):
                                rel_props[prop_name]['type'] = inferred_type
                                target_type = inferred_type
                            else:
                                rel_props[prop_name] = inferred_type
                                target_type = inferred_type
                            logging.info(f"Updated type for relationship property {prop_name} from '{target_type}' to '{inferred_type}'")
                    
                    prop_value = None
                    if source_col and source_col in original_df.columns:  # Check against original CSV columns
                        if target_type == 'json':
                            prop_value = parse_json_data(clean_non_json_chars(row[source_col]))
                        else:
                            prop_value = cast_value(row[source_col], target_type)
                    elif source_col:
                        logging.warning(f"Source column '{source_col}' not found in CSV data. Setting property to null.")
                        
                    rel_data[prop_name] = prop_value
                    
                relationships_output.append(rel_data)
                # Add to rel_headers set for consistent output
                rel_headers.update(rel_data.keys())
                relationship_count += 1
                processed_relationship_types.add(rel_type)
            else:
                if startNode_id is None or endNode_id is None:
                    logging.debug(f"Row {index}: Unable to generate node IDs for relationship ({from_label} -> {to_label})")
                elif not startNode_exists:
                    logging.debug(f"Row {index}: From node ID {startNode_id} does not exist in {from_label} nodes")
                elif not endNode_exists:
                    logging.debug(f"Row {index}: To node ID {endNode_id} does not exist in {to_label} nodes")
        
        if relationship_count > 0:
            logging.info(f"Generated {relationship_count} relationships of type {rel_type}")
                    
    # --- Write Node Files ---
    logging.info("Writing node files...")
    for label, nodes in nodes_data.items():
        if not nodes:
            logging.warning(f"No data generated for node label: {label}")
            continue
            
        # Convert the nodes dictionary to a DataFrame
        node_df = pd.DataFrame(list(nodes.values()))
        
        # Ensure all headers are included
        for header in node_headers.get(label, set()):
            if header not in node_df.columns:
                node_df[header] = None
        
        # Add Neo4j type information to headers
        neo4j_headers = {}
        for header in node_df.columns:
            if header in [':ID', ':LABEL']:
                neo4j_headers[header] = header
                continue
                
            # Find the property type in the schema
            prop_type = None
            for node_schema in schema.get('nodes', []):
                if node_schema.get('label') == label and header in node_schema.get('properties', {}):
                    prop_details = node_schema['properties'][header]
                    if isinstance(prop_details, dict):
                        prop_type = prop_details.get('type')
                    else:
                        prop_type = prop_details
                    break
            
            # If no type found in schema, infer from data
            if not prop_type and header in node_df.columns:
                non_null_values = node_df[header].dropna()
                if not non_null_values.empty:
                    sample_values = non_null_values.head(5)
                    sample_types = [type(val).__name__ for val in sample_values]
                    
                    if all(t == 'float' for t in sample_types):
                        prop_type = 'float'
                    elif all(t == 'int' for t in sample_types):
                        prop_type = 'integer'
                    elif all(t == 'bool' for t in sample_types):
                        prop_type = 'boolean'
                    else:
                        prop_type = 'string'
            
            # Convert to Neo4j type
            neo4j_type = convert_to_neo4j_type(prop_type) if prop_type else None
            if neo4j_type:
                neo4j_headers[header] = f"{header}:{neo4j_type}"
            else:
                neo4j_headers[header] = header
        
        # Write the node file with Neo4j type information in headers
        output_path = os.path.join(output_dir, f"{label}_nodes.csv")
        
        # Rename columns to include type information
        node_df_with_types = node_df.copy()
        node_df_with_types.columns = [neo4j_headers[col] for col in node_df.columns]
        
        node_df_with_types.to_csv(output_path, index=False, lineterminator='\n')
        logging.info(f"Successfully wrote {len(node_df_with_types)} {label} nodes to {output_path}")
    
    # --- Write Relationships File ---
    logging.info("Writing relationships file...")
    if relationships_output:
        df = pd.DataFrame(relationships_output)
        
        # Create a mapping from schema property names to original CSV column names for relationships
        # Special relationship columns always stay the same
        rel_column_rename_map = {':START_ID': ':START_ID', ':END_ID': ':END_ID', ':TYPE': ':TYPE'}
        
        # Create a header with Neo4j type information
        neo4j_rel_headers = {':START_ID': ':START_ID', ':END_ID': ':END_ID', ':TYPE': ':TYPE'}
        
        # First, scan the actual data for ALL properties to determine their types
        # This ensures we're not constrained by what's in the schema and can process any property
        rel_property_samples = {}
        for rel_data in relationships_output:
            for prop_name, prop_value in rel_data.items():
                if prop_name not in [':START_ID', ':END_ID', ':TYPE'] and prop_value is not None:
                    if prop_name not in rel_property_samples:
                        rel_property_samples[prop_name] = []
                    rel_property_samples[prop_name].append(prop_value)
        
        # Infer types from actual data
        rel_property_types = {}
        for prop_name, samples in rel_property_samples.items():
            # Get a representative sample for type inference
            sample_values = [s for s in samples if s is not None][:10]  # Use up to 10 non-null values
            if sample_values:
                # Print the raw sample values for debugging
                logging.info(f"Raw sample values for {prop_name}: {sample_values[:5]} of types {[type(v).__name__ for v in sample_values[:5]]}")
                
                # Special handling for numeric values with decimal points
                has_decimal_points = False
                for val in sample_values:
                    # Check if it's a string representation with a decimal point
                    if isinstance(val, str) and '.' in val:
                        logging.info(f"Found decimal point in string value: {val}")
                        has_decimal_points = True
                        break
                    # Check if it's actually a float value (even if it's 0.0 or 1.0)
                    elif isinstance(val, float):
                        logging.info(f"Found float value: {val} (is_integer: {val.is_integer()})")
                        # Even for integers stored as floats (e.g., 0.0, 1.0), treat as float for Neo4j compatibility
                        has_decimal_points = True
                        break
                    # Additional check for values that might be parsed incorrectly
                    elif isinstance(val, (int, bool)):
                        try:
                            # Try parsing as float to catch cases where values like 0.0 are converted to 0
                            str_val = str(val)
                            parsed_val = float(str_val)
                            if '.' in str_val or isinstance(parsed_val, float):
                                logging.info(f"Found numeric value that should be float: {val}")
                                has_decimal_points = True
                                break
                        except (ValueError, TypeError):
                            pass
                
                # If any value has a decimal point, force float type
                if has_decimal_points:
                    inferred_type = 'float'
                    logging.info(f"Detected decimal values in {prop_name}, forcing 'float' type")
                    # Ensure we override the relationship property type in the schema
                    for rel_schema in schema.get('relationships', []):
                        if 'properties' in rel_schema and prop_name in rel_schema['properties']:
                            logging.info(f"Explicitly setting schema type for {prop_name} to float")
                            if isinstance(rel_schema['properties'][prop_name], dict):
                                rel_schema['properties'][prop_name]['type'] = 'float'
                            else:
                                rel_schema['properties'][prop_name] = 'float'
                else:
                    # Normal type inference for each sample
                    sample_types = [infer_data_type(val) for val in sample_values]
                    # Filter out None values
                    sample_types = [t for t in sample_types if t is not None]
                    
                    if sample_types:
                        # Find the most flexible type that can accommodate all values
                        if 'string' in sample_types:
                            # String can hold any value
                            inferred_type = 'string'
                        elif 'float' in sample_types:
                            # Float can hold integers too
                            inferred_type = 'float'
                        elif 'integer' in sample_types:
                            inferred_type = 'integer'
                        elif 'boolean' in sample_types:
                            inferred_type = 'boolean'
                        elif 'datetime' in sample_types:
                            inferred_type = 'datetime'
                        elif 'date' in sample_types:
                            inferred_type = 'date'
                        else:
                            # Default to string if mixed/unknown types
                            inferred_type = 'string'
                    
                    rel_property_types[prop_name] = inferred_type
                    logging.info(f"Inferred type '{inferred_type}' for relationship property '{prop_name}' from samples {sample_values[:3]}...")
        
        # Now apply inferred types to the headers and update schema if needed
        for prop_name, inferred_type in rel_property_types.items():
            # Check against schema to report mismatches
            schema_type = None
            for rel_schema in schema.get('relationships', []):
                if 'properties' in rel_schema and prop_name in rel_schema['properties']:
                    prop_details = rel_schema['properties'][prop_name]
                    if isinstance(prop_details, dict):
                        schema_type = prop_details.get('type', 'string')
                    else:
                        schema_type = prop_details
                    
                    # Report mismatch and update schema
                    if schema_type != inferred_type:
                        logging.warning(f"Type mismatch for relationship property {prop_name}: schema says '{schema_type}' but data indicates '{inferred_type}'")
                        logging.info(f"Using '{inferred_type}' for property {prop_name} in relationship header")
                        
                        # Update schema to match actual data
                        if isinstance(prop_details, dict):
                            rel_schema['properties'][prop_name]['type'] = inferred_type
                        else:
                            rel_schema['properties'][prop_name] = inferred_type
            
            # Create the Neo4j type header
            neo4j_type = convert_to_neo4j_type(inferred_type)
            if neo4j_type:
                neo4j_rel_headers[prop_name] = f"{prop_name}:{neo4j_type}"
            else:
                neo4j_rel_headers[prop_name] = prop_name
        
        # Add any schema-defined properties that weren't in the data
        for rel_schema in schema.get('relationships', []):
            if 'properties' in rel_schema:
                for prop_name, prop_details in rel_schema['properties'].items():
                    # Skip properties we've already processed
                    if prop_name in neo4j_rel_headers:
                        continue
                        
                    if isinstance(prop_details, dict):
                        source_col = prop_details.get('source_column', prop_name)
                        data_type = prop_details.get('type', 'string')
                        neo4j_type = convert_to_neo4j_type(data_type)
                        if neo4j_type:
                            neo4j_rel_headers[prop_name] = f"{prop_name}:{neo4j_type}"
                        else:
                            neo4j_rel_headers[prop_name] = prop_name
                            
                        # Store the original mapping for renaming
                        rel_column_rename_map[prop_name] = source_col
                    else:
                        # For string props with no detailed config, just add them directly
                        neo4j_rel_headers[prop_name] = f"{prop_name}:string"
                        rel_column_rename_map[prop_name] = prop_name
        
        # Apply the column renaming to the DataFrame
        df.rename(columns=rel_column_rename_map, inplace=True)
        
        # Generic solution for handling numeric fields with potential decimal values
        # Scan through all columns to find numeric columns that might need to be handled as float
        for col in df.columns:
            # Skip special columns
            if col in [':START_ID', ':END_ID', ':TYPE']:
                continue
                
            # If already defined as float, no need to check further
            if col in neo4j_rel_headers and ':float' in neo4j_rel_headers[col]:
                continue
                
            # Check if this is a numeric column
            if col in df.columns and not df[col].empty:
                # Sample some non-null values
                sample = df[col].dropna().head(10).tolist()
                
                if sample:
                    # Check if values are numeric and if any might be floats
                    might_be_float = False
                    all_numeric = True
                    
                    for val in sample:
                        if isinstance(val, (int, float)):
                            # For direct numeric types
                            if isinstance(val, float) or (isinstance(val, str) and '.' in val):
                                might_be_float = True
                                break
                        elif isinstance(val, str):
                            # Try to convert string to number
                            try:
                                num_val = float(val)
                                if '.' in val or not float(val).is_integer():
                                    might_be_float = True
                                    break
                            except (ValueError, TypeError):
                                all_numeric = False
                        else:
                            all_numeric = False
                    
                    # If it's numeric and might contain float values, ensure it's treated as float
                    if all_numeric and might_be_float and col in neo4j_rel_headers:
                        logging.info(f"Generic handling: Setting {col} to float type based on value analysis")
                        neo4j_rel_headers[col] = f"{col}:float"
        
        # Create a new DataFrame with the typed headers
        typed_df = df.copy()
        typed_df.columns = [neo4j_rel_headers.get(col, col) for col in df.columns]
        
        # Write the relationships CSV file with type information in the headers
        output_path = os.path.join(output_dir, "relationships.csv")
        typed_df.to_csv(output_path, index=False, lineterminator='\n')
        logging.info(f"Successfully wrote relationships file: {output_path}")
    else:
        logging.warning("No relationship data generated.")

    # Validate that all relationship types in the schema are present in the output
    schema_relationship_types = {rel.get('type') for rel in schema.get('relationships', [])}
    missing_relationship_types = schema_relationship_types - processed_relationship_types
    
    if missing_relationship_types:
        logging.warning(f"WARNING: The following relationship types were defined in the schema but not generated: {missing_relationship_types}")
    else:
        logging.info("SUCCESS: All relationship types defined in the schema were successfully generated.")
    
    logging.info("Processing complete.")

# --- Command Line Interface ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Neo4j import CSV files from a schema and data CSV.")
    parser.add_argument("schema_file", help="Path to the JSON schema definition file.")
    parser.add_argument("data_file", help="Path to the input data CSV file.")
    parser.add_argument("output_dir", help="Directory to save the generated node and relationship CSV files.")

    args = parser.parse_args()

    create_neo4j_import_files(args.schema_file, args.data_file, args.output_dir)
