from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
import os
from datetime import datetime
import bcrypt
import pytz
import json
import logging

# Import from our new configurable database layer
from api.db_config import Base, get_db, engine, SessionLocal

# Configure logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# Models
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="admin")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @staticmethod
    def get_password_hash(password: str) -> str:
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def verify_password(self, password: str) -> bool:
        return bcrypt.checkpw(password.encode('utf-8'), self.hashed_password.encode('utf-8'))

class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String, nullable=True)
    permissions = Column(Text, nullable=True)  # Store permissions as JSON array
    is_system_role = Column(Boolean, default=False)  # Flag for system-defined roles
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def get_permissions(self):
        """Get the list of permissions for this role"""
        # First try to get permissions from the permissions field
        if self.permissions:
            try:
                return json.loads(self.permissions)
            except json.JSONDecodeError:
                pass  # Fall back to checking description
                
        # If no permissions in the permissions field or it couldn't be parsed,
        # try to get permissions from the description field (for backward compatibility)
        if self.description:
            try:
                # Try to parse as JSON
                if self.description.strip() and (self.description.strip()[0] == '{' or self.description.strip()[0] == '['):
                    description_data = json.loads(self.description)
                    if isinstance(description_data, dict) and "permissions" in description_data:
                        return description_data.get("permissions", [])
                    elif isinstance(description_data, list):
                        return description_data
            except (json.JSONDecodeError, TypeError):
                pass  # Ignore parsing errors
                
        # If we reach here, no permissions were found
        return []
    
    def has_permission(self, permission):
        """Check if this role has a specific permission"""
        # Admin role always has all permissions
        if self.name == "admin":
            return True
            
        permissions = self.get_permissions()
        return permission in permissions

class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, index=True)
    action = Column(String, index=True)
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, index=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    page_url = Column(String, nullable=True)  # Added page_url field

    # Add an index on the timestamp column for faster queries
    __table_args__ = (
        Index('idx_activity_logs_timestamp', 'timestamp'),
    )

class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id = Column(String, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    path = Column(String, nullable=False)
    type = Column(String, nullable=False)
    uploaded_by = Column(String, nullable=False)
    uploaded_at = Column(DateTime, nullable=False)
    chunk_size = Column(Integer, default=1000)
    schema = Column(Text, nullable=True)  # Store schema as JSON string

class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # 'file' or 'database'
    status = Column(String, nullable=False)  # 'queued', 'running', 'completed', 'failed'
    progress = Column(Integer, default=0)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    details = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    duration = Column(String, nullable=True)
    config = Column(Text, nullable=True)  # Store config as JSON string

class Schema(Base):
    __tablename__ = "schemas"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    source_id = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    schema = Column(Text, nullable=False)  # Store schema as JSON string
    csv_file_path = Column(Text, nullable=True)  # Path to the original CSV file
    schema_generated = Column(Text, nullable=True, default='no')
    db_loaded = Column(Text, nullable=True, default='no')
    db_id = Column(String, nullable=True, default='invalid')
    generation_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class GraphIngestionJob(Base):
    """
    Dedicated model for tracking KGInsights graph processing jobs.
    Separate from the DataPuur IngestionJob model to maintain component separation.
    """
    __tablename__ = "graph_ingestion_jobs"

    id = Column(String, primary_key=True, index=True)
    schema_id = Column(Integer, ForeignKey("schemas.id"), nullable=False, index=True)
    job_type = Column(String, nullable=False)  # e.g., 'load', 'unload', 'update'
    status = Column(String, nullable=False)  # 'pending', 'running', 'completed', 'failed'
    progress = Column(Integer, default=0)
    message = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    params = Column(Text, nullable=True)  # Store job parameters as JSON string
    node_count = Column(Integer, default=0)  # Count of nodes created during job execution
    relationship_count = Column(Integer, default=0)  # Count of relationships created during job execution
    result = Column(Text, nullable=True)  # Store detailed job results as JSON string

    # Relationship to Schema
    schema = relationship("Schema", backref="graph_jobs")


# Create tables
Base.metadata.create_all(bind=engine)
