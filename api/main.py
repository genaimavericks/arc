print("*******Checking if main this is getting called!")
from fastapi import FastAPI, HTTPException, Depends, Request, Query
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

from api.models import User
from api.db_config import get_db, init_db
from api.auth import router as auth_router, has_any_permission
#from api.ingestion import router as ingestion_router
from api.datapuur import router as datapuur_router
#from api.datapuur_dramatiq_api import router as datapuur_router
from api.datapuur_dramatiq_api import get_all_jobs_admin, stop_job_admin, delete_job_admin
from api.kginsights import router as kginsights_router
from api.kgdatainsights.data_insights_api import router as kgdatainsights_router, get_query_history, get_predefined_queries
from api.kginsights.graphschemaapi import router as graphschema_router, build_schema_from_source, SourceIdInput, SchemaResult
from api.profiler import router as profiler_router
from api.admin import router as admin_router
from api.gen_ai_layer.router import router as gen_ai_router
from api.middleware import ActivityLoggerMiddleware


# # Run database migrations
# try:
#     migrate_database()
#     print("Database migrations completed successfully")
# except Exception as e:
#     print(f"Error running database migrations: {str(e)}")

app = FastAPI(
    title="RSW API",
    description="API for RSW platform",
    version="1.0.0",
    docs_url=None,  # Disable default docs URL
    redoc_url=None  # Disable default redoc URL
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

# Mount static files directory if it exists
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

    # Serve index.html for all non-API routes to support client-side routing
    @app.get("/{full_path:path}")
    async def serve_frontend(request: Request, full_path: str):
        # Skip API routes
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
            
        # Check if the path exists as a file
        file_path = static_dir / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
            
        # Otherwise serve index.html for client-side routing
        return FileResponse(str(static_dir / "index.html"))
