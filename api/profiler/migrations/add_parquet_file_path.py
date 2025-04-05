"""
Migration script to add parquet_file_path and column_profiles columns to profile_results table.
Run this script manually to update the database schema.
"""
import os
import sys
import logging
from sqlalchemy import create_engine, Column, String, text, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Add parent directory to path to import from api modules
current_dir = os.path.dirname(os.path.abspath(__file__))
api_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
sys.path.append(api_dir)

# Import database configuration
from api.db_config import SQLALCHEMY_DATABASE_URL, connect_args

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_migration():
    """
    Add parquet_file_path and column_profiles columns to profile_results table
    """
    logger.info("Starting migration to add new columns to profile_results table")
    
    # Create engine and session
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Check if columns already exist
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('profile_results')]
        
        # Add parquet_file_path column if it doesn't exist
        if 'parquet_file_path' not in columns:
            logger.info("Adding parquet_file_path column to profile_results table")
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE profile_results ADD COLUMN parquet_file_path VARCHAR;"))
        else:
            logger.info("Column parquet_file_path already exists in profile_results table")
        
        # Add column_profiles column if it doesn't exist
        if 'column_profiles' not in columns:
            logger.info("Adding column_profiles column to profile_results table")
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE profile_results ADD COLUMN column_profiles JSON;"))
        else:
            logger.info("Column column_profiles already exists in profile_results table")
        
        logger.info("Migration completed successfully")
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    run_migration()
