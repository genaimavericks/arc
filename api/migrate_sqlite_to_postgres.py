"""
Script to migrate data from SQLite to PostgreSQL.
This script will:
1. Read all data from the SQLite database
2. Create tables in PostgreSQL if they don't exist
3. Insert the data into PostgreSQL

Usage:
python migrate_sqlite_to_postgres.py
"""

import os
import sys
import json
from sqlalchemy import create_engine, MetaData, Table, Column, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import pandas as pd
from datetime import datetime
import logging

# Add the parent directory to the Python path so we can import the api module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# SQLite database configuration
SQLITE_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.db')
SQLITE_URL = f"sqlite:///{SQLITE_DB_PATH}"

# PostgreSQL database configuration
PG_HOST = os.getenv("DB_HOST", "localhost")
PG_PORT = os.getenv("DB_PORT", "5432")
PG_USER = os.getenv("DB_USER", "dhani")
PG_PASSWORD = os.getenv("DB_PASSWORD", "")
PG_DB_NAME = os.getenv("DB_NAME", "rsw")
PG_URL = f"postgresql://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DB_NAME}"

def migrate_data():
    """Migrate data from SQLite to PostgreSQL"""
    logger.info("Starting migration from SQLite to PostgreSQL")
    
    # Check if SQLite database exists
    if not os.path.exists(SQLITE_DB_PATH):
        logger.error(f"SQLite database not found at {SQLITE_DB_PATH}")
        return False
    
    try:
        # Connect to SQLite database
        sqlite_engine = create_engine(SQLITE_URL)
        sqlite_metadata = MetaData()
        sqlite_metadata.reflect(bind=sqlite_engine)
        sqlite_tables = sqlite_metadata.tables
        sqlite_inspector = inspect(sqlite_engine)
        
        # Connect to PostgreSQL database
        pg_engine = create_engine(PG_URL)
        
        # Get list of tables from SQLite
        table_names = sqlite_inspector.get_table_names()
        logger.info(f"Found {len(table_names)} tables in SQLite database: {', '.join(table_names)}")
        
        # Import models to ensure tables are created with proper schema
        from api.models import Base, User, Role, ActivityLog, UploadedFile, IngestionJob
        
        # Drop all tables in PostgreSQL and recreate them
        with pg_engine.begin() as connection:
            # Drop all tables if they exist
            connection.execute(text("DROP SCHEMA public CASCADE"))
            connection.execute(text("CREATE SCHEMA public"))
            connection.execute(text("GRANT ALL ON SCHEMA public TO public"))
            logger.info("Dropped and recreated schema in PostgreSQL")
        
        # Create all tables in PostgreSQL with the correct schema
        Base.metadata.create_all(pg_engine)
        logger.info("Created tables in PostgreSQL database")
        
        # Create connections
        sqlite_conn = sqlite_engine.connect()
        pg_conn = pg_engine.connect()
        
        # Migrate each table
        for table_name in table_names:
            try:
                # Get SQLite table
                sqlite_table = sqlite_tables[table_name]
                
                # Read all data from SQLite table
                query = sqlite_table.select()
                result = sqlite_conn.execute(query)
                rows = result.fetchall()
                
                if not rows:
                    logger.info(f"Table {table_name} is empty, skipping")
                    continue
                
                logger.info(f"Migrating {len(rows)} rows from table {table_name}")
                
                # Get column names
                columns = [column.name for column in sqlite_table.columns]
                
                # Create DataFrame from SQLite data
                df = pd.DataFrame(rows, columns=columns)
                
                # Insert data into PostgreSQL
                df.to_sql(table_name, pg_engine, if_exists='append', index=False)
                
                # Reset sequence for the primary key if it exists
                try:
                    # Find the primary key column
                    pk_column = None
                    for column in sqlite_table.columns:
                        if column.primary_key:
                            pk_column = column.name
                            break
                    
                    if pk_column:
                        # Create a new connection for sequence reset to avoid transaction issues
                        with pg_engine.begin() as seq_conn:
                            # Get the maximum ID value
                            max_id_query = f"SELECT MAX({pk_column}) FROM {table_name}"
                            max_id_result = seq_conn.execute(text(max_id_query))
                            max_id = max_id_result.scalar() or 0
                            
                            # Reset the sequence to the max ID + 1
                            sequence_name = f"{table_name}_{pk_column}_seq"
                            reset_query = f"SELECT setval('{sequence_name}', {max_id}, true)"
                            seq_conn.execute(text(reset_query))
                            logger.info(f"Reset sequence for {table_name}.{pk_column} to {max_id}")
                except Exception as seq_error:
                    logger.warning(f"Could not reset sequence for table {table_name}: {str(seq_error)}")
                
                logger.info(f"Successfully migrated table {table_name}")
            except Exception as e:
                logger.error(f"Error migrating table {table_name}: {str(e)}")
        
        # Close connections
        sqlite_conn.close()
        pg_conn.close()
        
        logger.info("Migration completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error during migration: {str(e)}")
        return False

if __name__ == "__main__":
    # Set environment variable for PostgreSQL
    os.environ["DB_TYPE"] = "postgresql"
    
    # Run migration
    success = migrate_data()
    
    if success:
        print("Migration completed successfully!")
    else:
        print("Migration failed. Check the logs for details.")
        sys.exit(1)
