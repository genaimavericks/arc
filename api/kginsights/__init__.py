# This file makes the api directory a Python package

from fastapi import APIRouter
from .graphschemaapi import router as graphschema_router
from .database_api import router as database_router
from .kginsights import router as kginsights_router

from .graph_visualization_api import router as graph_visualization_router
from .processing_jobs_api import router as processing_jobs_router
from .schema_status_api import router as schema_status_router

# Create a new router for kginsights
router = APIRouter()

# Include the graphschema router
router.include_router(graphschema_router)

# Include the database router
router.include_router(database_router)

# Include the kginsights router
router.include_router(kginsights_router)

# Include the graph visualization router
router.include_router(graph_visualization_router)

# Include the processing jobs router
print("DEBUG: Including processing_jobs_router in kginsights router")
router.include_router(processing_jobs_router)
print(f"DEBUG: processing_jobs_router routes: {[{route.path: route.methods} for route in processing_jobs_router.routes]}")

# Include the schema status router
router.include_router(schema_status_router)