#!/usr/bin/env python3

import sqlalchemy
from sqlalchemy import create_engine, inspect, text
import pandas as pd
import traceback
import json

# Function to create connection string identical to the API
def create_connection_string(db_type, config):
    """Create a database connection string exactly as done in the API"""
    if db_type == "mysql":
        return f"mysql+pymysql://{config['username']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
    elif db_type == "postgresql":
        return f"postgresql://{config['username']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
    elif db_type == "mssql":
        return f"mssql+pyodbc://{config['username']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}?driver=ODBC+Driver+17+for+SQL+Server"
    else:
        raise ValueError(f"Unsupported database type: {db_type}")

# Function to safely convert row to dict for different SQLAlchemy versions
def row_to_dict(row, column_names=None):
    """Safely convert SQLAlchemy row to dictionary, handling different SQLAlchemy versions"""
    if row is None:
        return {}
        
    # Method 1: Try to directly access .keys() and values (SQLAlchemy 2.0)
    try:
        keys = row.keys()
        values = row
        print(f"Method 1: Found keys: {keys}")
        return {k: values[i] for i, k in enumerate(keys)}
    except Exception as e:
        print(f"Method 1 failed: {str(e)}")
    
    # Method 2: Try dict comprehension with keys (SQLAlchemy 1.4+)
    try:
        keys = row.keys()
        result = {key: row[key] for key in keys}
        print(f"Method 2: Created dict with keys: {list(result.keys())}")
        return result
    except Exception as e:
        print(f"Method 2 failed: {str(e)}")
    
    # Method 3: Try direct dict conversion (older SQLAlchemy)
    try:
        result = dict(row)
        print(f"Method 3: Created dict with keys: {list(result.keys())}")
        return result
    except Exception as e:
        print(f"Method 3 failed: {str(e)}")

    # Method 4: Manual conversion with column names
    try:
        if column_names:
            print(f"Method 4: Using column names: {column_names}")
            result = {}
            for i, value in enumerate(row):
                if i < len(column_names):
                    result[column_names[i]] = value
                else:
                    result[f'column_{i}'] = value
            return result
        else:
            print("Method 4: No column names provided")
    except Exception as e:
        print(f"Method 4 failed: {str(e)}")
    
    # Method 5: Last resort - just return values as list
    try:
        print("Method 5: Fallback to list of values")
        return {f'column_{i}': value for i, value in enumerate(row)}
    except Exception as e:
        print(f"Method 5 failed: {str(e)}")
        return {}

# Debug version of get_db_schema function
def debug_get_db_schema(db_type, config, chunk_size=1000):
    """Debug version of get schema from a database table with verbose output"""
    print(f"\n{'-'*80}\nDEBUG: Starting schema detection for {db_type} database: {config['database']}.{config['table']}")
    print(f"Connection configuration: host={config['host']}, port={config['port']}, username={config['username']}")
    
    connection_string = create_connection_string(db_type, config)
    print(f"Connection string: {connection_string}")
    
    try:
        print("Creating engine...")
        engine = create_engine(connection_string)
        
        print("Creating inspector...")
        inspector = inspect(engine)
        
        # Check if table exists
        print("Getting table names...")
        table_names = inspector.get_table_names()
        print(f"Available tables: {table_names}")
        
        if config["table"] not in table_names:
            raise ValueError(f"Table '{config['table']}' not found in database")
        
        # Get table columns
        print(f"Getting columns for table '{config['table']}'...")
        columns = inspector.get_columns(config["table"])
        print(f"Found {len(columns)} columns")
        
        # Simple column info for reference
        column_names = [col["name"] for col in columns]
        print(f"Column names: {column_names}")
        
        # Get sample data
        print("Connecting to execute sample query...")
        with engine.connect() as connection:
            print("Building query...")
            query = sqlalchemy.text(f"SELECT * FROM {config['table']} LIMIT 1")
            print(f"Executing query: {query}")
            
            result = connection.execute(query).fetchone()
            print(f"Query executed, result type: {type(result)}")
            
            if result:
                print(f"Result has {len(result)} items")
                
                # Try to get column information
                try:
                    result_keys = result.keys()
                    print(f"Result keys: {result_keys}")
                except Exception as e:
                    print(f"Could not get result keys: {str(e)}")
                
                # Try to convert to dict
                sample_data = row_to_dict(result, column_names)
                print(f"Converted to dict with {len(sample_data)} entries")
            else:
                print("No results returned")
                sample_data = {}
        
        # Build schema
        schema = {
            "name": config["table"],
            "fields": []
        }
        
        print("Building schema object...")
        for column in columns:
            col_name = column["name"]
            col_type = str(column["type"]).lower()
            
            # Map SQL types to our schema types
            if "int" in col_type:
                field_type = "integer"
            elif "float" in col_type or "double" in col_type or "decimal" in col_type:
                field_type = "float"
            elif "bool" in col_type:
                field_type = "boolean"
            elif "date" in col_type and "time" in col_type:
                field_type = "datetime"
            elif "date" in col_type:
                field_type = "date"
            elif "json" in col_type:
                field_type = "object"
            else:
                field_type = "string"
            
            schema["fields"].append({
                "name": col_name,
                "type": field_type,
                "nullable": not column.get("nullable", True),
                "sample": sample_data.get(col_name) if col_name in sample_data else None
            })
        
        print(f"Schema built with {len(schema['fields'])} fields")
        return schema
    
    except Exception as e:
        print(f"ERROR in get_db_schema: {str(e)}")
        traceback.print_exc()
        raise ValueError(f"Error connecting to database: {str(e)}")

# Connection parameters
db_type = "postgresql"
config = {
    "host": "localhost",
    "port": "5432",
    "database": "rsw_test",
    "username": "dhani",
    "password": "",  # If using trust authentication, password can be empty
    "table": "customers" 
}

try:
    print(f"\nTesting schema extraction for {db_type} database: {config['database']}.{config['table']}")
    schema = debug_get_db_schema(db_type, config)
    
    # Print schema in a readable format
    print("\nExtracted Schema:")
    print(json.dumps(schema, indent=2))
    
    print("\nSchema extraction successful!")
    
except Exception as e:
    print(f"\nSchema extraction failed: {str(e)}")
    traceback.print_exc()
