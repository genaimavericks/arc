import logging
from fastapi import FastAPI

# Fix import paths for both direct and module imports
try:
    # When imported as a module
    from api.kgdatainsights.websocket_api import router as websocket_router
except ImportError:
    # When run directly
    from .websocket_api import router as websocket_router

logger = logging.getLogger(__name__)

def setup_websocket_api(app: FastAPI):
    """Setup WebSocket API for the main FastAPI application"""
    try:
        # Register WebSocket API before any static file handlers
        # This ensures WebSocket routes are properly handled
        app.include_router(router=websocket_router, prefix="/api/kgdatainsights")
        
        # Log success
        logger.info("WebSocket API for KG Insights registered successfully")
        
        # Add a health check endpoint for WebSockets
        @app.get("/api/kgdatainsights/ws/health", tags=["websocket"])
        async def websocket_health():
            return {"status": "ok", "websocket": "available"}
            
    except Exception as e:
        logger.error(f"Failed to register WebSocket API: {str(e)}")
        # Don't raise the exception - we want the app to start even if WebSocket registration fails
        # This ensures backward compatibility
