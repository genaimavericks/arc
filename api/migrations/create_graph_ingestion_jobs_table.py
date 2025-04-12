"""
Migration script to create the graph_ingestion_jobs table for KGInsights.
This separates KGInsights job tracking from DataPuur's ingestion tracking.

Run this script directly: python -m api.migrations.create_graph_ingestion_jobs_table
"""

import sys
import os
import logging
from sqlalchemy import text
from datetime import datetime

# Add the parent directory to sys.path to allow importing from api
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from api.db_config import engine, SessionLocal

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_graph_ingestion_jobs_table():
    """Create the graph_ingestion_jobs table if it doesn't exist."""
    
    # SQL statements for creating the graph_ingestion_jobs table and indexes
    sql_statements = [
        """
        CREATE TABLE IF NOT EXISTS graph_ingestion_jobs (
            id VARCHAR(255) PRIMARY KEY,
            schema_id INTEGER NOT NULL,
            job_type VARCHAR(255) NOT NULL,
            status VARCHAR(50) NOT NULL,
            progress INTEGER DEFAULT 0,
            message TEXT,
            error TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            params TEXT,
            FOREIGN KEY (schema_id) REFERENCES schemas(id)
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_graph_ingestion_jobs_schema_id ON graph_ingestion_jobs(schema_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_graph_ingestion_jobs_status ON graph_ingestion_jobs(status)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_graph_ingestion_jobs_created_at ON graph_ingestion_jobs(created_at)
        """
    ]
    
    try:
        # Create a connection and execute each SQL statement separately
        with engine.connect() as connection:
            for sql in sql_statements:
                connection.execute(text(sql))
                connection.commit()
            
        logger.info("Successfully created graph_ingestion_jobs table and indexes")
        return True
    except Exception as e:
        logger.error(f"Error creating graph_ingestion_jobs table: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Starting migration to create graph_ingestion_jobs table...")
    
    success = create_graph_ingestion_jobs_table()
    
    if success:
        logger.info("Migration completed successfully")
    else:
        logger.error("Migration failed")
        sys.exit(1)
