"""
Pydantic schemas for DataPuur AI API
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime


# Profile Session Schemas
class ProfileSessionCreate(BaseModel):
    file_id: str
    file_name: str
    file_path: str
    recreate: bool = False  # Optional field to indicate profile recreation


class ProfileMessageSchema(BaseModel):
    id: str
    role: str
    content: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


class ProfileSessionResponse(BaseModel):
    id: str
    file_id: str
    file_name: str
    profile_id: Optional[str] = None
    status: str
    session_type: str
    created_at: datetime
    updated_at: datetime
    profile_summary: Optional[Dict[str, Any]] = None
    data_quality_issues: Optional[List[Dict[str, Any]]] = None
    improvement_suggestions: Optional[List[Dict[str, Any]]] = None
    messages: List[ProfileMessageSchema] = []


class ProfileSessionListResponse(BaseModel):
    sessions: List[ProfileSessionResponse]
    total: int
    page: int
    limit: int


# Chat Schemas
class ChatMessage(BaseModel):
    role: str = "user"
    content: str


class ProfileChatRequest(BaseModel):
    message: str
    include_code_execution: bool = False


class ProfileChatResponse(BaseModel):
    message: ProfileMessageSchema
    session_status: str
    profile_summary: Optional[Dict[str, Any]] = None
    suggestions: Optional[List[Dict[str, Any]]] = None
    generated_script: Optional[str] = None


# Transformation Schemas
class TransformationStep(BaseModel):
    description: str
    code: Optional[str] = None
    type: str
    id: str


class TransformationPlanCreate(BaseModel):
    name: str
    description: Optional[str] = None
    profile_session_id: Optional[str] = None
    source_id: Optional[str] = None  # Reference to source file ID
    plan_id: Optional[str] = None  # Optional existing plan ID
    input_instructions: Optional[str] = None
    is_draft: bool = True


class TransformationPlanUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class TransformationMessageCreate(BaseModel):
    plan_id: Optional[str] = None
    profile_session_id: Optional[str] = None  # For initial messages before plan creation
    content: str
    role: str = "user"  # user, assistant, system


class TransformationStep(BaseModel):
    order: int
    operation: str
    description: str
    parameters: Dict[str, Any]


class TransformationPlanResponse(BaseModel):
    id: str
    profile_session_id: Optional[str] = None
    name: str
    description: Optional[str]
    status: str
    transformation_steps: List[TransformationStep]
    expected_improvements: Optional[Dict[str, Any]]
    transformation_script: Optional[str]
    created_at: datetime
    updated_at: datetime


class TransformationChatRequest(BaseModel):
    plan_id: str
    message: str


class TransformationChatResponse(BaseModel):
    message: ProfileMessageSchema
    plan_status: str
    transformation_steps: Optional[List[TransformationStep]] = None
    generated_script: Optional[str] = None


class ProfileSessionWithPlansResponse(BaseModel):
    """Response model for profile session with its transformation plans"""
    id: Optional[str] = None
    file_id: str
    transformation_plans: List[TransformationPlanResponse] = []


# Job Schemas
class JobStatus(BaseModel):
    id: str
    job_type: str
    status: str
    progress: float
    message: Optional[str]
    result: Optional[Dict[str, Any]]
    error: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]


class ExecuteScriptRequest(BaseModel):
    session_id: Optional[str] = None
    plan_id: Optional[str] = None
    script: str
    job_type: str = "profile_script"  # profile_script or transformation


class ExecuteScriptResponse(BaseModel):
    job_id: str
    status: str
    message: str


# Data Source Schemas
class DataSourceResponse(BaseModel):
    id: str
    name: str
    file_path: str
    file_size: int
    row_count: Optional[int] = None
    column_count: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    data_type: str = "parquet"  # default to parquet, could be csv, etc.
    has_profile: bool = False


# Transformed Dataset Schemas
class TransformedDatasetCreate(BaseModel):
    name: str
    source_file_path: str
    source_file_id: Optional[str] = None
    transformed_file_path: str
    transformation_plan_id: Optional[str] = None
    job_id: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class TransformedDatasetResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    source_file_path: str
    source_file_id: Optional[str] = None
    transformed_file_path: str
    transformation_plan_id: Optional[str] = None
    job_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    column_metadata: Dict[str, Any] = Field(default_factory=dict)
    row_count: Optional[int] = None
    column_count: Optional[int] = None
    file_size_bytes: Optional[int] = None
    data_summary: Optional[Dict[str, Any]] = None
    created_at: datetime
    created_by: str
    updated_at: datetime


class DatasetMetadataUpdate(BaseModel):
    metadata: Dict[str, Any] = Field(default_factory=dict)
    column_metadata: Dict[str, Any] = Field(default_factory=dict)
    description: Optional[str] = None
