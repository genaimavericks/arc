from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
from uuid import uuid4

class ProfileRequest(BaseModel):
    file_name: str
    file_path: str
    file_id: Optional[str] = None

class ColumnProfileResponse(BaseModel):
    column_name: str
    data_type: str
    null_count: int
    unique_count: int
    min_value: Optional[str] = None
    max_value: Optional[str] = None
    mean_value: Optional[float] = None
    median_value: Optional[float] = None
    std_dev: Optional[float] = None
    frequent_values: Dict[str, Any]
    patterns: Dict[str, Any]

class ProfileSummaryResponse(BaseModel):
    id: str
    file_id: Optional[str] = None
    file_name: str
    total_rows: int
    total_columns: int
    data_quality_score: float
    created_at: datetime

    class Config:
        from_attributes = True

class ProfileResponse(ProfileSummaryResponse):
    columns: List[ColumnProfileResponse]

    class Config:
        from_attributes = True

class ProfileListItem(BaseModel):
    id: str
    file_id: Optional[str] = None
    file_name: str
    total_rows: int
    total_columns: int
    data_quality_score: float
    created_at: datetime

    class Config:
        from_attributes = True

class ProfileListResponse(BaseModel):
    items: List[ProfileListItem]
    total: int
    page: int
    limit: int
    pages: int
