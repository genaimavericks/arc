"""
Database models for data profiling.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from ..models import Base

class ProfileResult(Base):
    """
    Profile result for a data source.
    Stores overall metrics about the profiled data.
    """
    __tablename__ = "profile_results"

    id = Column(String, primary_key=True)
    file_id = Column(String, index=True)
    file_name = Column(String)
    parquet_file_path = Column(String, nullable=True)  # Store the path to the parquet file
    total_rows = Column(Integer)
    total_columns = Column(Integer)
    data_quality_score = Column(Float)
    column_profiles = Column(JSON, nullable=True)  # Store column profiles as JSON
    exact_duplicates_count = Column(Integer, default=0)  # Number of exact duplicate rows
    fuzzy_duplicates_count = Column(Integer, default=0)  # Number of fuzzy/similar rows
    duplicate_groups = Column(JSON, nullable=True)  # Store groups of duplicates as JSON
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ColumnProfile(Base):
    """
    Profile for an individual column in a data source.
    Stores detailed statistics and metrics about the column.
    """
    __tablename__ = "column_profiles"

    id = Column(String, primary_key=True)
    profile_id = Column(String, ForeignKey("profile_results.id"))
    column_name = Column(String)
    data_type = Column(String)
    count = Column(Integer)  # Add count field for total values in the column
    null_count = Column(Integer)
    unique_count = Column(Integer)
    min_value = Column(String)
    max_value = Column(String)
    mean_value = Column(Float)
    median_value = Column(Float)
    mode_value = Column(String)
    std_dev = Column(Float)
    frequent_values = Column(JSON)
    invalid_values = Column(JSON)
    outliers = Column(JSON)
    patterns = Column(JSON)
    # Quality metrics
    quality_score = Column(Float, default=0.0)
    completeness = Column(Float, default=0.0)
    uniqueness = Column(Float, default=0.0)
    validity = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Remove the back_populates reference since ProfileResult.column_profiles is now a JSON column
    # profile_result = relationship("ProfileResult", back_populates="column_profiles")
