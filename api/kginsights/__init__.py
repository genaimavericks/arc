# This file makes the api directory a Python package

from fastapi import APIRouter
from .graphschemaapi import router as graphschema_router

# Export the GraphSchemaAPI router directly
router = graphschema_router
