"""
Database migration script to add duplicate detection columns to the profile_results table.
"""

import logging
import os
import sys
from sqlalchemy import create_engine, Column, Integer, JSON, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import inspect

# Updated imports for the new location
from ..db_config import engine, Base
from .models import ProfileResult

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def add_duplicate_columns():
    """
    Add the duplicate detection columns to the profile_results table using SQLAlchemy's
    approach of creating the tables if they don't exist.
    """
    try:
        # Check if the table exists and get its columns
        inspector = inspect(engine)
        if not inspector.has_table("profile_results"):
            logger.error("profile_results table does not exist. Database not initialized.")
            return
            
        columns = inspector.get_columns("profile_results")
        column_names = [col['name'] for col in columns]
        logger.info(f"Existing columns: {column_names}")
        
        # Check if columns exist and add them via direct SQL if needed
        with engine.begin() as conn:
            if "exact_duplicates_count" not in column_names:
                logger.info("Adding exact_duplicates_count column")
                conn.execute(text("ALTER TABLE profile_results ADD COLUMN exact_duplicates_count INTEGER DEFAULT 0"))
            
            if "fuzzy_duplicates_count" not in column_names:
                logger.info("Adding fuzzy_duplicates_count column") 
                conn.execute(text("ALTER TABLE profile_results ADD COLUMN fuzzy_duplicates_count INTEGER DEFAULT 0"))
            
            if "duplicate_groups" not in column_names:
                logger.info("Adding duplicate_groups column")
                conn.execute(text("ALTER TABLE profile_results ADD COLUMN duplicate_groups JSON"))
                
        logger.info("Columns added successfully")
        
    except Exception as e:
        logger.error(f"Error adding columns: {str(e)}")
        raise

if __name__ == "__main__":
    logger.info("Starting database migration for duplicate detection columns")
    add_duplicate_columns()
    logger.info("Migration complete")
