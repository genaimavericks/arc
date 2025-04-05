"""
DataPuur API package.
This package contains all DataPuur-related API endpoints.
"""

from fastapi import APIRouter
from .. import datapuur as legacy_datapuur
from .ingestion.router import router as ingestion_router

# Create a main router without a prefix - this will be included directly in main.py
router = APIRouter()

# Create a router specifically for new APIs with the correct prefix
new_api_router = APIRouter(prefix="/api/ingestion")

# Include new API routers in the new_api_router
new_api_router.include_router(ingestion_router)

# Include the new API router in the main router
router.include_router(new_api_router)
