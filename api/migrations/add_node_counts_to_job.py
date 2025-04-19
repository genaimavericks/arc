"""
Migration script to add node_count, relationship_count, and result columns to graph_ingestion_jobs table.
"""
import os
import sys
import logging

# Add the parent directory to the path so we can import from api
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import Column, Integer, Text
from sqlalchemy.exc import SQLAlchemyError
from db_config import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    """
    Add node_count, relationship_count, and result columns to graph_ingestion_jobs table.
    """
    try:
        logger.info("Starting migration to add node count columns to graph_ingestion_jobs table")
        
        # Check if the columns already exist
        with engine.connect() as conn:
            # Check if node_count column exists
            result = conn.execute("SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'graph_ingestion_jobs' AND column_name = 'node_count'")
            node_count_exists = result.scalar() > 0
            
            # Check if relationship_count column exists
            result = conn.execute("SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'graph_ingestion_jobs' AND column_name = 'relationship_count'")
            relationship_count_exists = result.scalar() > 0
            
            # Check if result column exists
            result = conn.execute("SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'graph_ingestion_jobs' AND column_name = 'result'")
            result_exists = result.scalar() > 0
            
            # Add the columns if they don't exist
            if not node_count_exists:
                logger.info("Adding node_count column to graph_ingestion_jobs table")
                conn.execute("ALTER TABLE graph_ingestion_jobs ADD COLUMN node_count INTEGER DEFAULT 0")
            else:
                logger.info("node_count column already exists")
                
            if not relationship_count_exists:
                logger.info("Adding relationship_count column to graph_ingestion_jobs table")
                conn.execute("ALTER TABLE graph_ingestion_jobs ADD COLUMN relationship_count INTEGER DEFAULT 0")
            else:
                logger.info("relationship_count column already exists")
                
            if not result_exists:
                logger.info("Adding result column to graph_ingestion_jobs table")
                conn.execute("ALTER TABLE graph_ingestion_jobs ADD COLUMN result TEXT")
            else:
                logger.info("result column already exists")
                
        logger.info("Migration completed successfully")
        return True
    except SQLAlchemyError as e:
        logger.error(f"Error during migration: {str(e)}")
        return False

if __name__ == "__main__":
    run_migration()
