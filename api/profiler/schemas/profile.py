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
    count: int
    null_count: int
    unique_count: int
    min_value: Optional[str] = None
    max_value: Optional[str] = None
    mean_value: Optional[float] = None
    median_value: Optional[float] = None
    mode_value: Optional[str] = None
    std_dev: Optional[float] = None
    frequent_values: Dict[str, Any]
    invalid_values: Optional[Dict[str, Any]] = {}
    outliers: Optional[Dict[str, Dict[str, Any]]] = {"z_score": {}, "iqr": {}}
    patterns: Dict[str, Any]
    quality_score: Optional[float] = None
    completeness: Optional[float] = None
    uniqueness: Optional[float] = None
    validity: Optional[float] = None

class ProfileSummaryResponse(BaseModel):
    id: str
    file_id: Optional[str] = None
    file_name: str
    total_rows: int
    total_columns: int
    data_quality_score: float
    exact_duplicates_count: Optional[int] = 0
    fuzzy_duplicates_count: Optional[int] = 0
    created_at: datetime

    class Config:
        from_attributes = True

class ProfileResponse(ProfileSummaryResponse):
    columns: Dict[str, Any]  # Changed back to more flexible type
    original_headers: Optional[List[str]] = None
    duplicate_groups: Optional[Dict[str, List[Dict[str, Any]]]] = None  # Keep duplicate groups info

    class Config:
        from_attributes = True

class ProfileListItem(BaseModel):
    id: str
    file_id: Optional[str] = None
    file_name: str
    total_rows: int
    total_columns: int
    data_quality_score: float
    exact_duplicates_count: Optional[int] = 0
    fuzzy_duplicates_count: Optional[int] = 0
    created_at: datetime

    class Config:
        from_attributes = True

class ProfileListResponse(BaseModel):
    items: List[ProfileListItem]
    total: int
    page: int
    limit: int
    pages: int
