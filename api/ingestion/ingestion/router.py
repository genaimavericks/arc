"""
Main router for DataPuur Ingestion API.
This module combines all DataPuur ingestion-related routers.
"""

from fastapi import APIRouter
from .source_router import router as source_router
from .dataset_router import router as dataset_router

# Create main router
router = APIRouter()

# Include all sub-routers
router.include_router(source_router)
router.include_router(dataset_router)
