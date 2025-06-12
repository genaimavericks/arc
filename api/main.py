print("*******Checking if main this is getting called!")
import json
import logging
import asyncio
import uvicorn
import os
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, Request, Query, WebSocket
from starlette.websockets import WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi
from sqlalchemy.orm import Session
import os
from pathlib import Path
import dotenv
import datetime
from typing import Optional

# Load environment variables from .env file
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    print(f"Loading environment variables from {dotenv_path}")
    dotenv.load_dotenv(dotenv_path)
    print(f"OPENAI_API_KEY is {'set' if os.getenv('OPENAI_API_KEY') else 'not set'}")

from api.models import User, Schema
from api.db_config import get_db, init_db
from api.auth import router as auth_router, has_any_permission
#from api.ingestion import router as ingestion_router
from api.auth import router as auth_router, has_any_permission
#from api.ingestion import router as ingestion_router
from api.datapuur import router as datapuur_router
#from api.datapuur_dramatiq_api import router as datapuur_router
from api.datapuur import get_all_jobs_admin, stop_job_admin, delete_job_admin
from api.kginsights import router as kginsights_router
from api.kgdatainsights.data_insights_api import router as kgdatainsights_router, get_query_history, get_predefined_queries
from api.kginsights.graphschemaapi import router as graphschema_router, build_schema_from_source, SourceIdInput, SchemaResult
from api.kginsights.websocket_api import router as websocket_router
from api.profiler import router as profiler_router
from api.datapuur_ai import router as datapuur_ai_router
from api.admin import router as admin_router
from api.gen_ai_layer.router import router as gen_ai_router
from api.export_router import router as export_router
from api.middleware import ActivityLoggerMiddleware
from api.log_filter_middleware import LogFilterMiddleware


# # Run database migrations
# try:
#     migrate_database()
#     print("Database migrations completed successfully")
# except Exception as e:
#     print(f"Error running database migrations: {str(e)}")

app = FastAPI(
    title="Knowledge Graph API",
    description="API for interacting with Knowledge Graphs",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add middlewares - order matters in FastAPI (first added = outermost in the chain)
#app.add_middleware(APIDebugMiddleware)  # Add debug middleware first so it logs all requests
app.add_middleware(LogFilterMiddleware)  # Add log filter middleware first to mark requests for log filtering
app.add_middleware(ActivityLoggerMiddleware)

# Direct datainsights API endpoint routes with authentication - must be defined before including the router

# All datainsights API routes are now handled by the kgdatainsights_router
# No direct routes needed here anymore

# Register routers after defining all direct routes
app.include_router(auth_router)
#app.include_router(ingestion_router)
app.include_router(datapuur_router)
print("DEBUG: Including kginsights_router in main app with prefix /api")
app.include_router(kginsights_router, prefix="/api")
print(f"DEBUG: kginsights_router routes: {[route.path for route in kginsights_router.routes]}")
print(f"DEBUG: Full application routes: {[route.path for route in app.routes]}")
# The graphschema router should be included with just /api prefix since it already has /graphschema in its routes
app.include_router(graphschema_router, prefix="/api")
app.include_router(kgdatainsights_router, prefix="/api")
app.include_router(profiler_router)
# The datapuur_ai_router already has a prefix of /api/datapuur-ai in its definition,
# so we should ensure it doesn't get an extra /api prefix
app.include_router(datapuur_ai_router, prefix="")

app.include_router(export_router)
app.include_router(admin_router)
# Include the Gen AI Layer router
app.include_router(gen_ai_router)

# Add additional admin routes that map to datapuur admin endpoints
app.add_api_route("/api/admin/jobs", get_all_jobs_admin, methods=["GET"])
app.add_api_route("/api/admin/jobs/{job_id}/stop", stop_job_admin, methods=["POST"])
app.add_api_route("/api/admin/jobs/{job_id}", delete_job_admin, methods=["DELETE"])

# Removed old compatibility routes for KGInsights
# These are now handled by the kgdatainsights_router

# Custom OpenAPI and Swagger UI endpoints
@app.get("/api/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url="/api/openapi.json",
        title="Research AI API",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
    )

@app.get("/api/redoc", include_in_schema=False)
async def redoc_html():
    return get_redoc_html(
        openapi_url="/api/openapi.json",
        title="Research AI API - ReDoc",
        redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js",
    )

@app.get("/api/openapi.json", include_in_schema=False)
async def get_open_api_endpoint():
    return get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

# Health check endpoint
@app.get("/api/health")
async def health_check():
    print("Health check endpoint called")
    return {"status": "healthy", "timestamp": datetime.datetime.now().isoformat()}

# Create initial admin user if it doesn't exist
@app.on_event("startup")
async def startup_event():
    # Initialize the database
    init_db()
    
    db = next(get_db())
    
    # Create default users if they don't exist
    admin_user = db.query(User).filter(User.username == "admin").first()
    if not admin_user:
        hashed_password = User.get_password_hash("admin123")
        admin = User(
            username="admin",
            email="admin@example.com",
            hashed_password=hashed_password,
            role="admin"
        )
        db.add(admin)
        db.commit()
        print("Created initial admin user")
    
    # Ensure roles have proper permissions
    try:
        from api.migrate_db import setup_default_role_permissions
        setup_default_role_permissions(db)
        print("Updated role permissions")
    except Exception as e:
        print(f"Error updating role permissions: {str(e)}")
    
    # Initialize query suggestion cache
    try:
        import asyncio
        from api.kgdatainsights.query_processor import refresh_cache_task
        
        # Get all schema IDs from the database
        schemas = db.query(Schema).all()
        schema_ids = [str(schema.id) for schema in schemas]
        
        if schema_ids:
            # Initialize cache for each schema
            for schema_id in schema_ids:
                asyncio.create_task(refresh_cache_task(schema_id))
                print(f"Initialized query suggestion cache for schema {schema_id}")
            
            # Set up background task to periodically refresh the cache
            async def periodic_cache_refresh():
                while True:
                    try:
                        # Refresh cache for all schemas every 5 minutes
                        await asyncio.sleep(300)  # 5 minutes
                        # Get fresh list of schemas in case they've changed
                        try:
                            db_refresh = next(get_db())
                            schemas_refresh = db_refresh.query(Schema).all()
                            schema_ids_refresh = [str(schema.id) for schema in schemas_refresh]
                            for schema_id in schema_ids_refresh:
                                asyncio.create_task(refresh_cache_task(schema_id))
                        except Exception as inner_e:
                            print(f"Error refreshing schema list: {str(inner_e)}")
                            # Fall back to original schema list
                            for schema_id in schema_ids:
                                asyncio.create_task(refresh_cache_task(schema_id))
                    except Exception as e:
                        print(f"Error in periodic cache refresh: {str(e)}")
            
            # Start the background task
            asyncio.create_task(periodic_cache_refresh())
            print("Started background task for periodic cache refresh")
        else:
            print("No schemas found for query suggestion cache initialization")
    except Exception as e:
        print(f"Error initializing query suggestion cache: {str(e)}")
        
    # Include WebSocket API router
    app.include_router(websocket_router, prefix="/api")
    print("Included WebSocket API router")

# Mount static files after all API routes are registered
# Mount static files directory if it exists
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    # Add a fallback route for API paths that aren't handled by other routers
    @app.get("/api/{path:path}", include_in_schema=False)
    async def api_not_found(path: str):
        raise HTTPException(status_code=404, detail=f"API endpoint not found: {path}")
    
    # Mount static files at the root path to ensure all assets are accessible
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
