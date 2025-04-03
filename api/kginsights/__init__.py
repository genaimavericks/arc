# This file makes the api directory a Python package

from fastapi import APIRouter
from .graphschemaapi import router as graphschema_router
from .database_api import router as database_router

# Create a new router for kginsights
router = APIRouter()

# Include the graphschema router
router.include_router(graphschema_router)

# Include the database router
router.include_router(database_router)
