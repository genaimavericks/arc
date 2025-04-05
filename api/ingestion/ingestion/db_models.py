"""
Database models for DataPuur Ingestion API.
These models define the database schema for sources and datasets.
"""

from sqlalchemy import Column, String, ForeignKey, DateTime, Integer, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from ...models import Base

class Source(Base):
    """
    Source model representing raw data uploaded or connected to the system.
    This is a wrapper around the existing UploadedFile model.
    """
    __tablename__ = "sources"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # "csv", "json", "database"
    status = Column(String, nullable=False)  # "available", "processing", "error"
    created_at = Column(DateTime, default=datetime.now)
    created_by = Column(String, nullable=False)
    path = Column(String)  # For file sources
    connection_info = Column(JSON)  # For database sources
    schema = Column(JSON)
    
    # Relationship to datasets created from this source
    datasets = relationship("Dataset", back_populates="source")

class Dataset(Base):
    """
    Dataset model representing processed data after ingestion.
    This is a wrapper around the existing IngestionJob model.
    """
    __tablename__ = "datasets"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String)
    created_at = Column(DateTime, default=datetime.now)
    created_by = Column(String, nullable=False)
    status = Column(String, nullable=False)  # "processing", "available", "error"
    
    # Relationship to source
    source_id = Column(String, ForeignKey("sources.id"))
    source = relationship("Source", back_populates="datasets")
    
    # Dataset properties
    file_path = Column(String)  # Path to parquet file
    schema = Column(JSON)
    statistics = Column(JSON)
    row_count = Column(Integer)
