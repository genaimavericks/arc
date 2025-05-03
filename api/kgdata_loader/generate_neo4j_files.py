import json
import csv
import pandas as pd
import os
import argparse
import logging
from pathlib import Path
import string
import re

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

def generate_node_id(node_schema, row):
    """Generates a unique ID for a node based on schema rules or primary property."""
    # Handle old schema format with explicit ID specifications
    if 'id_column' in node_schema:
        source_col = node_schema['id_column']
        if source_col in row.index:  # Check if column exists in row
            id_val = row[source_col]
            if pd.isna(id_val) or id_val == '':
                logging.warning(f"Missing value in ID column '{source_col}'. Cannot generate node ID.")
                return None
            return str(id_val)
        else:
            logging.warning(f"ID column '{source_col}' not found in data. Cannot generate node ID.")
            return None
    elif 'id_template' in node_schema:
        template = node_schema['id_template']
        try:
            # Find all placeholders like {Column Name}
            placeholders = re.findall(r'\{([^{}]+)\}', template)
            format_values = {}
            for ph in placeholders:
                # Check if placeholder column exists in row
                if ph not in row.index:
                    logging.warning(f"Template placeholder '{ph}' not found in data. Cannot generate node ID.")
                    return None
                    
                val = row[ph]  # Direct Series indexing
                if pd.isna(val) or val == '':
                     logging.warning(f"Missing value for placeholder '{{{ph}}}' in ID template '{template}'. Cannot generate node ID.")
                     return None
                format_values[ph] = str(val) # Ensure values are strings for formatting
            return template.format(**format_values)
        except Exception as e:
             logging.warning(f"Error formatting ID template: {e}. Cannot generate node ID.")
             return None
    else:
        # Handle new schema format that doesn't specify ID columns/templates
        # Use the first property as ID (which is usually the label name as a property)
        label = node_schema.get('label', 'Unknown')
        
        # Try to use the same property name as the label
        if label in row.index:
            id_val = row[label]
            if not pd.isna(id_val) and id_val != '':
                return str(id_val)
                
        # Look at the indexes section if available
        # This is a simplified approach - in a real scenario, we would have a more
        # robust way to determine the primary ID property for each node type
        
        # Try to find a property with the same name as the label
        for prop_name in node_schema.get('properties', {}):
            if prop_name in row.index:
                id_val = row[prop_name]
                if not pd.isna(id_val) and id_val != '':
                    return str(id_val)
                    
        logging.warning(f"No suitable ID property found for node label '{label}'. Cannot generate node ID.")
        return None

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
        logging.error(f"Error decoding JSON schema file: {e}")
        return

    logging.info(f"Loading data from: {data_path}")
    try:
        # Store original data in a DataFrame that won't be modified
        original_df = pd.read_csv(data_path)
        # Debug check
        logging.info(f"Loaded CSV has {len(original_df)} rows and {len(original_df.columns)} columns")
        logging.info(f"First few columns: {list(original_df.columns)[:5]}")
    except FileNotFoundError:
        logging.error(f"Data file not found: {data_path}")
        return
    except Exception as e:
        logging.error(f"Error reading data file: {e}")
        return
        
    logging.info(f"Output directory: {output_dir}")
    os.makedirs(output_dir, exist_ok=True)
    
    # Data storage
    nodes_data = {}  # Dictionary by label of node data
    node_headers = {}  # Track headers by label
    relationships_output = []  # List of relationship data
    rel_headers = set([':START_ID', ':END_ID', ':TYPE'])  # Standard rel headers

    # --- Process Nodes ---
    logging.info("Processing nodes...")
    nodes_data = {}  # Track all node data for relationship creation later
    
    # First pass: Process all nodes except TeamMember (which needs special handling)
    for node_schema in schema.get('nodes', []):
        label = node_schema.get('label')
        
        # Skip TeamMember nodes in the initial processing - they'll be handled specially later
        if label == 'TeamMember':
            logging.info(f"Skipping initial processing of {label} nodes (will be handled specially)")
            continue
            
        logging.info(f"Processing label: {label}")
        
        if not label:
            logging.warning("Node schema missing 'label' key. Skipping.")
            continue
            
        nodes_data[label] = {}  # Initialize dict for this label
        node_headers[label] = set([':ID', ':LABEL']) # Track headers for output
        prop_definitions = node_schema.get('properties', {})
        node_headers[label].update(prop_definitions.keys()) # Add property names to headers
        
        for index, row in original_df.iterrows():
            node_id = generate_node_id(node_schema, row)
            
            if node_id is None or node_id in nodes_data[label]:
                continue # Skip if ID generation failed or node already added
                
            node_data = {
                ':ID': node_id,
                ':LABEL': label
            }
            
            for prop_name, prop_details in prop_definitions.items():
                if isinstance(prop_details, dict):
                    source_col = prop_details.get('source_column')
                    target_type = prop_details.get('type')
                    use_generated_id = prop_details.get('use_generated_id', False)
                else:
                    source_col = prop_name
                    target_type = prop_details
                    use_generated_id = False
                    
                prop_value = None
                if use_generated_id:
                    prop_value = node_id
                elif source_col and source_col in original_df.columns:
                    prop_value = cast_value(row[source_col], target_type)
                elif source_col:
                    logging.warning(f"Source column '{source_col}' not found in CSV. Setting property '{prop_name}' to null.")
                    
                node_data[prop_name] = prop_value
                
            nodes_data[label][node_id] = node_data

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
    relationships_output = []
    rel_headers = set([':START_ID', ':END_ID', ':TYPE']) # Standard relationship headers
    
    # Debug: Print the original CSV data columns to confirm availability
    logging.info(f"Original CSV columns available: {list(original_df.columns)}")

    # Track which relationship types have been processed
    processed_relationship_types = set()
    
    # Special handling for TeamMember nodes since they don't have direct columns in the CSV
    # We'll create TeamMember nodes based on the Shift nodes
    logging.info("Adding special handling for TeamMember nodes and HAS_TEAM_MEMBER relationship")
    if "Shift" in nodes_data:
        if "TeamMember" not in nodes_data:
            nodes_data["TeamMember"] = {}
        
        # For each Shift node, create a corresponding TeamMember
        for shift_id, shift_data in nodes_data.get("Shift", {}).items():
            # Generate a TeamMember ID based on the shift
            team_member_id = f"TeamMember-{shift_id}"
            
            # Create the TeamMember node
            if team_member_id not in nodes_data["TeamMember"]:
                nodes_data["TeamMember"][team_member_id] = {
                    ":ID": team_member_id,
                    ":LABEL": "TeamMember",
                    "Name": f"Operator-{shift_id}"
                }
                
                # Create the HAS_TEAM_MEMBER relationship
                rel_data = {
                    ':START_ID': shift_id,
                    ':END_ID': team_member_id,
                    ':TYPE': "HAS_TEAM_MEMBER"
                }
                relationships_output.append(rel_data)
                rel_headers.update(rel_data.keys())
                processed_relationship_types.add("HAS_TEAM_MEMBER")
                
        # Write TeamMember nodes file
        if nodes_data["TeamMember"]:
            df = pd.DataFrame(list(nodes_data["TeamMember"].values()))
            output_path = os.path.join(output_dir, "TeamMember_nodes.csv")
            df.to_csv(output_path, index=False, lineterminator='\n')
            logging.info(f"Successfully wrote node file: {output_path}")
            logging.info(f"Generated {len(nodes_data['TeamMember'])} TeamMember nodes")
            logging.info(f"Generated {len(nodes_data['TeamMember'])} HAS_TEAM_MEMBER relationships")
    
    # Process each relationship defined in the schema
    for rel_schema in schema.get('relationships', []):
        rel_type = rel_schema.get('type')
        from_label = rel_schema.get('from_node')
        to_label = rel_schema.get('to_node')
        
        # Skip HAS_TEAM_MEMBER as we've already handled it specially
        if rel_type == "HAS_TEAM_MEMBER":
            continue
            
        if from_label not in nodes_data or to_label not in nodes_data:
            logging.warning(f"Skipping relationship type {rel_type} due to missing node data for {from_label} or {to_label}")
            continue
            
        logging.info(f"Processing relationship type: {rel_type} ({from_label} -> {to_label})")
        
        # Get node schemas for ID generation
        from_node_schema = next((n for n in schema['nodes'] if n['label'] == from_label), None)
        to_node_schema = next((n for n in schema['nodes'] if n['label'] == to_label), None)
        
        if not from_node_schema or not to_node_schema:
            logging.warning(f"Could not find node schemas for {from_label} or {to_label}. Skipping relationship.")
            continue
        
        # For each row in the ORIGINAL CSV data, try to create a relationship
        relationship_count = 0
        for index, row in original_df.iterrows():
            # Generate node IDs using the exact same method as node creation
            from_node_id = generate_node_id(from_node_schema, row)
            to_node_id = generate_node_id(to_node_schema, row)
            
            # Debug info to track down the issue
            logging.debug(f"Row {index}: Generated from_node_id={from_node_id}, to_node_id={to_node_id}")
            
            # Check if both nodes exist in our nodes_data dictionaries
            from_node_exists = from_node_id is not None and from_node_id in nodes_data[from_label]
            to_node_exists = to_node_id is not None and to_node_id in nodes_data[to_label]
            
            if from_node_exists and to_node_exists:
                # We found a valid relationship! Add it.
                rel_props = rel_schema.get('properties', {})
                rel_data = {
                    ':START_ID': from_node_id,
                    ':END_ID': to_node_id,
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
                if from_node_id is None or to_node_id is None:
                    logging.debug(f"Row {index}: Unable to generate node IDs for relationship ({from_label} -> {to_label})")
                elif not from_node_exists:
                    logging.debug(f"Row {index}: From node ID {from_node_id} does not exist in {from_label} nodes")
                elif not to_node_exists:
                    logging.debug(f"Row {index}: To node ID {to_node_id} does not exist in {to_label} nodes")
        
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
