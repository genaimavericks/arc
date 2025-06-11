"""
Database models for DataPuur AI profiling and transformation
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Boolean, Float
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from api.db_config import Base


class ProfileSession(Base):
    """Stores AI-powered profiling sessions"""
    __tablename__ = "profile_sessions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    file_id = Column(String, nullable=False, index=True)
    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    username = Column(String, nullable=False, index=True)
    profile_id = Column(String, nullable=True, index=True)  # Link to profile result
    status = Column(String, default="active")  # active, completed, error
    
    # Session metadata
    session_type = Column(String, default="profiling")  # profiling, transformation
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # AI-generated insights
    profile_summary = Column(JSON, nullable=True)
    data_quality_issues = Column(JSON, nullable=True)
    improvement_suggestions = Column(JSON, nullable=True)
    
    # Generated scripts
    profile_script = Column(Text, nullable=True)
    profile_script_output = Column(JSON, nullable=True)
    
    # Relationships
    messages = relationship("ProfileMessage", back_populates="session", cascade="all, delete-orphan")
    transformation_plans = relationship("TransformationPlan", back_populates="profile_session", cascade="all, delete-orphan")


class ProfileMessage(Base):
    """Stores chat messages for profiling sessions"""
    __tablename__ = "profile_messages"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("profile_sessions.id"), nullable=False)
    role = Column(String, nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Metadata for AI responses
    message_metadata = Column(JSON, nullable=True)  # Can store script, suggestions, etc.
    
    # Relationship
    session = relationship("ProfileSession", back_populates="messages")


class TransformationPlan(Base):
    """Stores transformation plans generated from profiling"""
    __tablename__ = "transformation_plans"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    profile_session_id = Column(String, ForeignKey("profile_sessions.id"), nullable=True)
    source_id = Column(String, nullable=True)  # Optional reference to source file ID
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, default="draft")  # draft, approved, executing, completed, error
    
    # Plan details
    transformation_steps = Column(JSON, nullable=False)  # List of transformation steps
    expected_improvements = Column(JSON, nullable=True)
    
    # Generated code
    transformation_script = Column(Text, nullable=True)
    
    # Execution details
    job_id = Column(String, nullable=True)  # Link to background job
    execution_started_at = Column(DateTime, nullable=True)
    execution_completed_at = Column(DateTime, nullable=True)
    execution_output = Column(JSON, nullable=True)
    execution_error = Column(Text, nullable=True)
    
    # Output file details
    output_file_path = Column(String, nullable=True)
    output_file_id = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    profile_session = relationship("ProfileSession", back_populates="transformation_plans")
    messages = relationship("TransformationMessage", back_populates="plan", cascade="all, delete-orphan")


class TransformationMessage(Base):
    """Stores chat messages for transformation refinement"""
    __tablename__ = "transformation_messages"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    plan_id = Column(String, ForeignKey("transformation_plans.id"), nullable=False)
    role = Column(String, nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Metadata for AI responses
    message_metadata = Column(JSON, nullable=True)  # Can store refined script, changes, etc.
    
    # Relationship
    plan = relationship("TransformationPlan", back_populates="messages")


class ProfileJob(Base):
    """Background jobs for profiling and transformation execution"""
    __tablename__ = "profile_jobs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_type = Column(String, nullable=False)  # profile_script, transformation
    session_id = Column(String, nullable=True)
    plan_id = Column(String, nullable=True)
    
    # Job details
    status = Column(String, default="pending")  # pending, running, completed, failed
    progress = Column(Float, default=0.0)
    message = Column(String, nullable=True)
    
    # Script execution
    script = Column(Text, nullable=False)
    input_file_path = Column(String, nullable=False)
    output_file_path = Column(String, nullable=True)
    
    # Results
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    
    # Timing
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # User info
    created_by = Column(String, nullable=False)


class TransformedDataset(Base):
    """Stores information about transformed datasets including lineage"""
    __tablename__ = "transformed_datasets"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)  # Dataset name from source
    description = Column(Text, nullable=True)
    source_file_path = Column(String, nullable=False)
    source_file_id = Column(String, nullable=True)
    transformed_file_path = Column(String, nullable=False)
    
    # Lineage information
    transformation_plan_id = Column(String, ForeignKey("transformation_plans.id"))
    job_id = Column(String, ForeignKey("profile_jobs.id"), nullable=True)
    
    # Metadata
    dataset_metadata = Column(JSON, default={})  # Renamed from 'metadata' to avoid SQLAlchemy reserved name conflict
    column_metadata = Column(JSON, default={})
    
    # Statistics
    row_count = Column(Integer, nullable=True)
    column_count = Column(Integer, nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    data_summary = Column(JSON, nullable=True)
    
    # Tracking
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    transformation_plan = relationship("TransformationPlan", backref="transformed_datasets")
    job = relationship("ProfileJob")
