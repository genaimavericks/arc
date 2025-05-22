print("*******Checking if main this is getting called!")
from fastapi import FastAPI, HTTPException, Depends, Request, Query, WebSocket
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

from api.models import User
from api.db_config import get_db, init_db
from api.auth import router as auth_router, has_any_permission
#from api.ingestion import router as ingestion_router
from api.datapuur import router as datapuur_router
from api.kginsights import router as kginsights_router
from api.kgdatainsights.data_insights_api import router as kgdatainsights_router, get_query_history, get_predefined_queries
from api.kginsights.graphschemaapi import router as graphschema_router, build_schema_from_source, SourceIdInput, SchemaResult
from api.kgdatainsights.register_websocket import setup_websocket_api
from api.profiler import router as profiler_router
from api.admin import router as admin_router
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
app.include_router(export_router)

app.include_router(admin_router)

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
        
    # Register WebSocket API
    try:
        from api.kgdatainsights.websocket_api import router as websocket_router
        app.include_router(websocket_router, prefix="/api/kgdatainsights")
        print("Registered WebSocket API for KG Insights directly in startup_event")
    except Exception as e:
        print(f"Error registering WebSocket API in startup_event: {str(e)}")

# Register WebSocket API again outside of startup event to ensure it's registered
try:
    from api.kgdatainsights.register_websocket import setup_websocket_api
    setup_websocket_api(app)
    print("Registered WebSocket API for KG Insights")
except Exception as e:
    print(f"Error registering WebSocket API: {str(e)}")

# Add a direct WebSocket endpoint in the main app
@app.websocket("/api/kgdatainsights/ws/direct/{schema_id}")
async def direct_websocket_endpoint(websocket: WebSocket, schema_id: str):
    # Import the necessary modules with proper error handling
    try:
        # When imported as a module
        from api.kgdatainsights.query_processor import get_query_suggestions, get_autocomplete_suggestions, validate_query
        from api.models import User
    except ImportError:
        # When run directly
        from api.kgdatainsights.query_processor import get_query_suggestions, get_autocomplete_suggestions, validate_query
        from api.models import User
    import json
    
    await websocket.accept()
    try:
        # Create a dummy user for testing
        dummy_user = User(id=999, username="anonymous", email="anonymous@example.com", role="user")
        dummy_user.permissions = ["kginsights:read"]
        
        # Send a welcome message with schema-based suggestions
        suggestions = await get_query_suggestions(schema_id, dummy_user)
        await websocket.send_json({
            "type": "connection_established", 
            "message": "Connected to direct WebSocket API",
            "suggestions": suggestions
        })
        
        # Keep the connection open and handle messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                message_type = message.get("type", "")
                content = message.get("content", {})
                
                # Process different message types
                if message_type == "query":
                    query_text = content.get("query", "")
                    if not query_text:
                        await websocket.send_json({"type": "error", "content": {"error": "Empty query"}})
                        continue
                    
                    # Send a dummy response for now
                    await websocket.send_json({
                        "type": "query_result",
                        "content": {
                            "query": query_text,
                            "result": f"Response to: {query_text}",
                            "timestamp": datetime.datetime.now().isoformat()
                        }
                    })
                
                elif message_type == "autocomplete":
                    partial_text = content.get("text", "")
                    cursor_position = content.get("cursor_position", len(partial_text))
                    
                    # Get schema-based autocomplete suggestions
                    suggestions = await get_autocomplete_suggestions(schema_id, partial_text, cursor_position, dummy_user)
                    
                    # Extract the current word being typed
                    if not partial_text or cursor_position == 0:
                        current_word = ""
                    else:
                        text_before_cursor = partial_text[:cursor_position]
                        last_space_pos = text_before_cursor.rfind(" ")
                        current_word = text_before_cursor[last_space_pos + 1:] if last_space_pos >= 0 else text_before_cursor
                    
                    await websocket.send_json({
                        "type": "autocomplete_suggestions",
                        "content": {
                            "suggestions": suggestions,
                            "current_word": current_word,
                            "cursor_position": cursor_position
                        }
                    })
                
                elif message_type == "validate":
                    query_text = content.get("query", "")
                    
                    # Validate query against schema
                    errors = await validate_query(schema_id, query_text, dummy_user)
                    
                    await websocket.send_json({
                        "type": "validation_results",
                        "content": {
                            "query": query_text,
                            "errors": errors
                        }
                    })
                
                elif message_type == "suggest":
                    # Get context-aware query suggestions
                    current_text = content.get("text", "")
                    cursor_position = content.get("cursor_position", len(current_text))
                    
                    # Get enhanced query suggestions with context awareness
                    suggestions = await get_query_suggestions(schema_id, dummy_user, current_text, cursor_position)
                    
                    await websocket.send_json({
                        "type": "suggestions",
                        "content": {
                            "suggestions": suggestions,
                            "current_text": current_text,
                            "cursor_position": cursor_position
                        }
                    })
                
                elif message_type == "ping":
                    # Respond to ping with pong
                    await websocket.send_json({
                        "type": "pong",
                        "content": {"received_at": content.get("sent_at")}
                    })
                
                else:
                    # Unknown message type
                    await websocket.send_json({
                        "type": "error",
                        "content": {"error": f"Unknown message type: {message_type}"}
                    })
            
            except json.JSONDecodeError:
                # Invalid JSON
                await websocket.send_json({
                    "type": "error",
                    "content": {"error": "Invalid JSON message"}
                })
            
            except Exception as e:
                # General error
                print(f"Error processing WebSocket message: {str(e)}")
                await websocket.send_json({
                    "type": "error",
                    "content": {"error": "Internal server error"}
                })
    except WebSocketDisconnect:
        print(f"WebSocket client disconnected")
    except Exception as e:
        print(f"WebSocket error: {str(e)}")

# Add a health check endpoint for WebSockets
@app.get("/api/kgdatainsights/ws/health")
async def websocket_health():
    return {"status": "ok", "websocket": "available"}

# Mount static files directory if it exists
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    # Add a fallback route for API paths that aren't handled by other routers
    @app.get("/api/{path:path}", include_in_schema=False)
    async def api_not_found(path: str):
        raise HTTPException(status_code=404, detail=f"API endpoint not found: {path}")
    
    # Mount static files at the root path to ensure all assets are accessible
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
