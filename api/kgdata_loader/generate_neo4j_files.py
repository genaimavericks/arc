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

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Helper Functions ---

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

def parse_json_data(value):
    """Attempts to parse a JSON string into a Python object."""
    if pd.isna(value) or value == '':
        return None
    
    # First clean the string
    cleaned_value = clean_non_json_chars(value)
    if not cleaned_value:
        return None
    
    try:
        # First try standard JSON parsing
        return json.loads(cleaned_value)
    except json.JSONDecodeError:
        try:
            # If that fails, try Python's literal_eval which can parse some non-standard JSON
            # This helps with cases where single quotes are used instead of double quotes
            return ast.literal_eval(cleaned_value)
        except (SyntaxError, ValueError) as e:
            # Last attempt with regex-based parsing for array-like string representation
            if cleaned_value.startswith('[{') and "}" in cleaned_value and "]" in cleaned_value:
                try:
                    # Extract individual objects from the array-like string
                    items = []
                    # Crude but effective approach: split by "},{" to get individual objects
                    parts = cleaned_value.strip('[]').split('},{')
                    for i, part in enumerate(parts):
                        if i > 0:
                            part = '{' + part
                        if i < len(parts) - 1:
                            part = part + '}'
                        try:
                            # Try to parse each part
                            item_dict = {}
                            # Extract key-value pairs using regex
                            for match in re.finditer(r'"([^"]+)"\s*:\s*([^,}]+)', part):
                                key = match.group(1)
                                value_str = match.group(2).strip()
                                
                                # Parse the value based on its format
                                if value_str.lower() == 'null':
                                    value = None
                                elif value_str.lower() == 'true':
                                    value = True
                                elif value_str.lower() == 'false':
                                    value = False
                                elif value_str.startswith('"') and value_str.endswith('"'):
                                    value = value_str[1:-1]
                                else:
                                    try:
                                        value = float(value_str)
                                        if value.is_integer():
                                            value = int(value)
                                    except:
                                        value = value_str
                                
                                item_dict[key] = value
                            
                            if item_dict:
                                items.append(item_dict)
                        except Exception as e3:
                            logging.debug(f"Error parsing object part: {e3}")
                    
                    if items:
                        return items
                except Exception as e2:
                    logging.debug(f"Error parsing array string: {e2}")
            
            logging.warning(f"Error parsing JSON value. Value: '{cleaned_value[:50]}...' Error: {e}")
            return None

def generate_node_id(node_schema, row):
    """Generates a unique ID for a node based on schema rules or primary property."""
    # Handle old schema format with explicit ID specifications
    id_config = node_schema.get('id', {})
    if id_config and 'property' in id_config:
        id_prop = id_config['property']
        if id_prop in row.index:
            id_val = row[id_prop]
            if not pd.isna(id_val) and id_val != '':
                return f"{node_schema['label']}-{id_val}"
    
    # If no explicit ID is specified in the schema, use heuristics to determine the best ID property
    # This is a more robust way to determine the primary ID property for each node type
    
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
    
    # If no appropriate ID property was found, use a UUID-like approach with a combination of the first value and row index
    if not row.empty:
        first_val = row.iloc[0]
        if not pd.isna(first_val) and first_val != '':
            # Use row index as a unique identifier if available, otherwise use the first value
            if hasattr(row, 'name'):
                return f"{node_schema['label']}-{row.name}"
            else:
                hash_val = hash(str(first_val))
                return f"{node_schema['label']}-{hash_val}"
    
    # Last resort - use a random ID if everything else fails
    import uuid
    logging.info(f"Using random UUID for {node_schema['label']} node - no suitable ID property found")
    return f"{node_schema['label']}-{uuid.uuid4()}"

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
    
    logging.info(f"Loading data from: {data_path}")
    try:
        original_df = pd.read_csv(data_path)
    except FileNotFoundError:
        logging.error(f"Data file not found: {data_path}")
        return
    except Exception as e:
        logging.error(f"Error reading CSV data: {e}")
        return
    
    # Add indexes to the DataFrame to help with lookups later
    original_df = original_df.reset_index(drop=True)
    
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
            node_headers[label] = set()  # Initialize headers set
            
        # Get properties schema for this node type
        properties_schema = node_schema.get('properties', {})
        
        # Check if any property is a JSON array that should be processed into separate nodes
        for prop_name, prop_details in properties_schema.items():
            # If the property is of type "json" and maps to another node type,
            # record this mapping for later processing
            if isinstance(prop_details, dict) and prop_details.get('type') == 'json':
                source_col = prop_details.get('source_column', prop_name)
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
    
    # Process JSON arrays and create related nodes/relationships
    logging.info("Processing JSON arrays in CSV columns...")
    for json_col, mapping in json_array_mappings.items():
        source_label = mapping['source_node']
        target_label = mapping['target_node']
        relationship_type = mapping['relationship_type']
        
        # Make sure target node label has a data dictionary
        if target_label not in nodes_data:
            nodes_data[target_label] = {}
            node_headers[target_label] = set([':ID', ':LABEL'])
            node_headers[target_label].update(mapping['property_schema'].keys())
            
        logging.info(f"Processing column '{json_col}' to create {target_label} nodes")
        
        # Initialize counters for reporting
        json_nodes_created = 0
        json_relationships_created = 0
        
        # For each row that has data in this column
        for index, row in original_df.iterrows():
            if json_col not in row or pd.isna(row[json_col]):
                continue
                
            # Get the source node ID for this row
            source_node_schema = next((n for n in schema.get('nodes', []) if n.get('label') == source_label), None)
            if not source_node_schema:
                continue
                
            source_node_id = generate_node_id(source_node_schema, row)
            if not source_node_id or source_node_id not in nodes_data.get(source_label, {}):
                continue
                
            # Parse the JSON data
            json_str = clean_non_json_chars(row[json_col])
            json_data = parse_json_data(json_str)
            
            if not json_data:
                # If parsing failed, log a debug message with a sample
                if index < 5:  # Only log the first few failures to avoid log spam
                    logging.debug(f"Failed to parse JSON data in row {index}, column '{json_col}': {str(row[json_col])[:100]}")
                continue
                
            # If it's not a list, convert it to a list with one item
            if not isinstance(json_data, list):
                json_data = [json_data]
                
            # Process each item in the JSON data
            for i, item in enumerate(json_data):
                if not isinstance(item, dict):
                    logging.warning(f"JSON array item is not a dictionary: {item}")
                    continue
                    
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
                    
                # Skip if this node was already processed
                if target_node_id in nodes_data[target_label]:
                    # Still create the relationship if it doesn't already exist
                    existing_rel = False
                    for rel in relationships_output:
                        if (rel[':START_ID'] == source_node_id and 
                            rel[':END_ID'] == target_node_id and 
                            rel[':TYPE'] == relationship_type):
                            existing_rel = True
                            break
                            
                    if not existing_rel:
                        rel_data = {
                            ':START_ID': source_node_id,
                            ':END_ID': target_node_id,
                            ':TYPE': relationship_type
                        }
                        relationships_output.append(rel_data)
                        json_relationships_created += 1
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
                    
                    # Get the target type from the schema or default to string
                    target_type = None
                    if prop_name in mapping['property_schema']:
                        prop_details = mapping['property_schema'][prop_name]
                        if isinstance(prop_details, dict):
                            target_type = prop_details.get('type', 'string')
                        elif isinstance(prop_details, str):
                            target_type = prop_details
                            
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
                
                # Create the relationship
                rel_data = {
                    ':START_ID': source_node_id,
                    ':END_ID': target_node_id,
                    ':TYPE': relationship_type
                }
                relationships_output.append(rel_data)
                rel_headers.update(rel_data.keys())
                processed_relationship_types.add(relationship_type)
                json_relationships_created += 1
                
        logging.info(f"Generated {json_nodes_created} {target_label} nodes from '{json_col}' column")
        logging.info(f"Generated {json_relationships_created} {relationship_type} relationships from '{json_col}' column")
    
    # --- Write Node Files ---
    logging.info("Writing node files...")
    for label, data_list in nodes_data.items():
        if data_list:
            # Get the schema for this node label
            node_schema = next((n for n in schema['nodes'] if n['label'] == label), None)
            df = pd.DataFrame(list(data_list.values()))
            
            # Create a mapping from schema property names to original CSV column names
            column_rename_map = {':ID': ':ID', ':LABEL': ':LABEL'}  # Special columns always stay the same
            
            if node_schema and 'properties' in node_schema:
                for prop_name, prop_details in node_schema['properties'].items():
                    if isinstance(prop_details, dict) and 'source_column' in prop_details:
                        # Map from schema property name to the original CSV column name
                        column_rename_map[prop_name] = prop_details['source_column']
            
            # Apply the column renaming to the DataFrame
            df.rename(columns=column_rename_map, inplace=True)
            
            # Write the file with renamed columns
            output_path = os.path.join(output_dir, f"{label}_nodes.csv")
            df.to_csv(output_path, index=False, lineterminator='\n')
            logging.info(f"Successfully wrote node file: {output_path}")
        else:
            logging.warning(f"No data generated for node label: {label}")

    # --- Process Relationships ---
    logging.info("Processing relationships...")
    
    # Process each relationship defined in the schema
    for rel_schema in schema.get('relationships', []):
        rel_type = rel_schema.get('type')
        from_label = rel_schema.get('startNode')
        to_label = rel_schema.get('endNode')
        
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
                    
    # --- Write Relationships File ---
    logging.info("Writing relationships file...")
    if relationships_output:
        df = pd.DataFrame(relationships_output)
        
        # Create a mapping from schema property names to original CSV column names for relationships
        # Special relationship columns always stay the same
        rel_column_rename_map = {':START_ID': ':START_ID', ':END_ID': ':END_ID', ':TYPE': ':TYPE'}
        
        # Loop through all relationship schemas to build the property mapping
        for rel_schema in schema.get('relationships', []):
            if 'properties' in rel_schema:
                for prop_name, prop_details in rel_schema['properties'].items():
                    if isinstance(prop_details, dict) and 'source_column' in prop_details:
                        # Map from schema property name to the original CSV column name
                        rel_column_rename_map[prop_name] = prop_details['source_column']
        
        # Apply the column renaming to the DataFrame
        df.rename(columns=rel_column_rename_map, inplace=True)
        
        # Write the relationships CSV file
        output_path = os.path.join(output_dir, "relationships.csv")
        df.to_csv(output_path, index=False, lineterminator='\n')
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
