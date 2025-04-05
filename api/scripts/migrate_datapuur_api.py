"""
Database migration script for the new DataPuur API structure.
This script creates the new tables required for the DataPuur Ingestion API.
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime
import uuid

# Add the parent directory to the path so we can import from api
sys.path.append(str(Path(__file__).parent.parent.parent))

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker, Session

from api.models import Base, UploadedFile, IngestionJob
from api.ingestion.ingestion.db_models import Source, Dataset
from api.db_config import SQLALCHEMY_DATABASE_URL, connect_args

def run_migration():
    """Run the migration to create and populate the new tables."""
    print("Starting DataPuur API structure migration...")
    
    # Create database engine and session
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Check if tables already exist
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    # Create tables if they don't exist
    if "sources" not in existing_tables or "datasets" not in existing_tables:
        print("Creating new tables: sources, datasets")
        Base.metadata.create_all(bind=engine, tables=[Source.__table__, Dataset.__table__])
    else:
        print("Tables already exist, skipping creation")
    
    # Migrate data from existing tables to new tables
    migrate_data(SessionLocal())
    
    print("Migration completed successfully")

def migrate_data(db: Session):
    """Migrate data from the existing tables to the new ones."""
    print("Migrating data from existing tables...")
    
    # Count existing data
    source_count = db.query(Source).count()
    dataset_count = db.query(Dataset).count()
    
    if source_count > 0 or dataset_count > 0:
        print(f"Found existing data: {source_count} sources, {dataset_count} datasets")
        print("Skipping data migration to avoid duplicates")
        return
    
    # Migrate uploaded files to sources
    uploaded_files = db.query(UploadedFile).all()
    print(f"Migrating {len(uploaded_files)} uploaded files to sources...")
    
    for file in uploaded_files:
        try:
            # Extract schema if available
            schema_data = None
            if file.schema:
                try:
                    schema_data = json.loads(file.schema)
                except:
                    pass
            
            # Determine the status
            status = "available"
            
            # Create source record
            source = Source(
                id=file.id,
                name=file.filename,
                type=file.type,
                status=status,
                created_at=file.uploaded_at,
                created_by=file.uploaded_by,
                path=file.path,
                connection_info=json.loads(file.connection_info) if hasattr(file, "connection_info") and file.connection_info else None,
                schema=schema_data
            )
            
            db.add(source)
        except Exception as e:
            print(f"Error migrating file {file.id}: {str(e)}")
    
    # Commit source records
    db.commit()
    print(f"Migrated {len(uploaded_files)} sources")
    
    # Migrate ingestion jobs to datasets
    ingestion_jobs = db.query(IngestionJob).all()
    print(f"Migrating {len(ingestion_jobs)} ingestion jobs to datasets...")
    
    for job in ingestion_jobs:
        try:
            # Determine status
            if job.status == "completed":
                status = "available"
            elif job.status in ["error", "failed"]:
                status = "error"
            else:
                status = "processing"
            
            # Extract config if available
            config = None
            source_id = None
            if job.config:
                try:
                    config = json.loads(job.config) if isinstance(job.config, str) else job.config
                    source_id = config.get("file_id")
                except:
                    pass
            
            # Skip if no source ID (required for foreign key)
            if not source_id:
                print(f"Skipping job {job.id}: No source ID found")
                continue
            
            # Create dataset record
            dataset = Dataset(
                id=job.id,
                name=job.name,
                description=None,
                created_at=job.start_time,
                created_by=job.created_by if hasattr(job, "created_by") else "system",
                status=status,
                source_id=source_id,
                file_path=config.get("output_path") if config else None,
                schema=None,
                statistics=None,
                row_count=None
            )
            
            db.add(dataset)
        except Exception as e:
            print(f"Error migrating job {job.id}: {str(e)}")
    
    # Commit dataset records
    db.commit()
    print(f"Migrated {len(ingestion_jobs)} datasets")

if __name__ == "__main__":
    run_migration()
