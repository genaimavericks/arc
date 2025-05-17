#!/usr/bin/env python3

import sqlalchemy
from sqlalchemy import create_engine, text
import pandas as pd
import time
import traceback
import os
import shutil
from pathlib import Path
import uuid

# Create test output directory
DATA_DIR = Path(__file__).parent / "test_data"
DATA_DIR.mkdir(exist_ok=True)

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
chunk_size = 5  # Small chunk size for testing

# Create a test job ID
job_id = str(uuid.uuid4())
print(f"Test job ID: {job_id}")

# Create output file path
output_file = DATA_DIR / f"{job_id}.parquet"

# Create temporary directory for parquet chunks
temp_dir = DATA_DIR / f"temp_{job_id}"
temp_dir.mkdir(exist_ok=True)

try:
    print(f"\n{'='*80}\nTesting database ingestion from {db_type} database: {config['database']}.{config['table']}")
    print(f"Connection configuration: host={config['host']}, port={config['port']}, username={config['username']}")
    
    start_time = time.time()
    
    # Step 1: Create connection string and engine
    print("\n--- STEP 1: Connecting to database ---")
    connection_string = create_connection_string(db_type, config)
    print(f"Connection string: {connection_string}")
    
    engine = create_engine(connection_string)
    print("Engine created successfully")
    
    # Step 2: Get total row count
    print("\n--- STEP 2: Getting row count ---")
    total_rows = 0
    try:
        row_count_query = f"SELECT COUNT(*) FROM {config['table']}"
        print(f"Row count query: {row_count_query}")
        
        with engine.connect() as conn:
            result = conn.execute(text(row_count_query))
            total_rows = result.scalar()
            
        print(f"Total rows to extract: {total_rows}")
    except Exception as e:
        print(f"WARN: Could not get exact row count: {str(e)}")
        total_rows = 0
    
    # Step 3: Read data in chunks and save to parquet
    print("\n--- STEP 3: Reading data in chunks ---")
    offset = 0
    processed_rows = 0
    chunk_files = []
    chunk_number = 0
    schema = None
    
    while True:
        print(f"\nProcessing chunk {chunk_number}, offset {offset}")
        
        try:
            # Construct query with proper handling for PostgreSQL
            query = f"SELECT * FROM {config['table']} LIMIT {chunk_size} OFFSET {offset}"
            print(f"Query: {query}")
            
            # Try executing the query with sqlalchemy.text()
            print("Executing query...")
            chunk = pd.read_sql(text(query), engine)
            print(f"Query executed, got {len(chunk)} rows")
            
            # Output sample data from the chunk
            if len(chunk) > 0:
                print(f"Column names: {list(chunk.columns)}")
                print("\nSample data (first row):")
                print(chunk.iloc[0])
            
            # If no rows returned, we've reached the end
            if len(chunk) == 0:
                print("No more data, stopping extraction")
                break
            
            # Save first chunk schema for consistency
            if chunk_number == 0:
                print("Saving schema from first chunk")
                try:
                    schema = pd.io.parquet.api.types.cast_pandas_dtype(str(chunk.dtypes[0]))
                    print(f"Schema sample: {schema}")
                except Exception as schema_error:
                    print(f"NOTE: Error capturing schema (non-critical): {schema_error}")
            
            # Save chunk to a temporary parquet file
            print("Saving chunk to parquet file...")
            chunk_file = temp_dir / f"chunk_{chunk_number}.parquet"
            
            try:
                # Attempt to convert datetime columns to string if needed
                for col in chunk.select_dtypes(include=['datetime64']).columns:
                    print(f"Converting datetime column '{col}' to string")
                    chunk[col] = chunk[col].astype(str)
                    
                chunk.to_parquet(chunk_file, index=False)
                print(f"Saved chunk to {chunk_file}")
                chunk_files.append(chunk_file)
            except Exception as parquet_error:
                print(f"\nERROR saving parquet: {str(parquet_error)}")
                print("Column types:")
                for col, dtype in chunk.dtypes.items():
                    print(f"  {col}: {dtype}")
                raise
            
            # Update counters
            processed_rows += len(chunk)
            offset += chunk_size
            chunk_number += 1
            
        except Exception as e:
            print(f"\nERROR processing chunk: {str(e)}")
            traceback.print_exc()
            break
    
    # Step 4: Combine chunks into a single parquet file
    print(f"\n--- STEP 4: Combining {len(chunk_files)} chunks ---")
    if not chunk_files:
        raise ValueError("No data was extracted from the database. The table might be empty.")
    
    # If only one chunk, just rename it
    if len(chunk_files) == 1:
        print("Only one chunk, moving directly to output file")
        shutil.move(str(chunk_files[0]), str(output_file))
    else:
        # Read and combine all chunks
        print("Reading and combining multiple chunks")
        dfs = []
        for i, chunk_file in enumerate(chunk_files):
            print(f"Reading chunk {i}: {chunk_file}")
            df = pd.read_parquet(chunk_file)
            dfs.append(df)
        
        combined_df = pd.concat(dfs, ignore_index=True)
        print(f"Combined dataframe has {len(combined_df)} rows")
        
        print(f"Saving to output file: {output_file}")
        combined_df.to_parquet(output_file, index=False)
        
        # Clean up temporary files
        print("Cleaning up temporary chunk files")
        for chunk_file in chunk_files:
            if os.path.exists(chunk_file):
                os.unlink(chunk_file)
    
    # Clean up temporary directory
    print("Cleaning up temporary directory")
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    
    # Calculate processing time
    processing_time = time.time() - start_time
    print(f"\nCompleted! Extracted {processed_rows} rows in {processing_time:.2f} seconds")
    print(f"Output saved to: {output_file}")
    
    # Verify the output file
    print("\nVerifying output parquet file...")
    verification_df = pd.read_parquet(output_file)
    print(f"Successfully read parquet file with {len(verification_df)} rows")
    print("First row of data:")
    print(verification_df.head(1))
    
except Exception as e:
    print(f"\nERROR: {str(e)}")
    traceback.print_exc()
    
    # Clean up temporary directory if it exists
    if temp_dir.exists():
        try:
            shutil.rmtree(temp_dir)
        except Exception as cleanup_error:
            print(f"Error cleaning up temporary directory: {str(cleanup_error)}")
finally:
    # Final cleanup
    if 'engine' in locals():
        engine.dispose()
    print("\nTest completed.")
