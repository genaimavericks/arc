from typing import Dict, List, Optional, Any
import json
import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.requests import Request

# Fix import paths for both direct and module imports
try:
    # When imported as a module
    from api.kgdatainsights.websocket_manager import ConnectionManager, get_connection_manager
    from api.auth import get_current_user
    from api.models import User
    from api.kgdatainsights.query_processor import (
        process_query, 
        get_autocomplete_suggestions, 
        validate_query, 
        get_query_suggestions
    )
except ImportError:
    # When run directly
    from .websocket_manager import ConnectionManager, get_connection_manager
    from ..auth import get_current_user
    from ..models import User
    from .query_processor import (
        process_query, 
        get_autocomplete_suggestions, 
        validate_query, 
        get_query_suggestions
    )

# Setup logging
logger = logging.getLogger(__name__)

# Create router with proper tags and prefix
# Note: We're NOT including the prefix here, as it will be added when the router is included in the main app
router = APIRouter(tags=["websocket"])

# Security scheme
security = HTTPBearer()

async def check_ws_permission(websocket: WebSocket, required_permissions: List[str]):
    """Check if the user has the required permissions for WebSocket access"""
    try:
        # Get token from query parameters or headers
        token = websocket.query_params.get("token")
        if not token:
            # Try to get from headers
            auth_header = websocket.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header[7:]  # Remove "Bearer " prefix
        
        if not token:
            logger.warning("WebSocket connection attempt without token")
            # For development, allow connections without authentication
            # In production, this should be removed
            dummy_user = User(id=999, username="anonymous", email="anonymous@example.com", role="user")
            dummy_user.permissions = ["kginsights:read"]
            return dummy_user
            # Uncomment in production:
            # await websocket.close(code=1008, reason="Missing authentication token")
            # return None
        
        try:
            # Get user from token
            user = await get_current_user(token)
            
            # Check permissions
            user_permissions = user.permissions or []
            if not all(perm in user_permissions for perm in required_permissions):
                logger.warning(f"User {user.username} has insufficient permissions for WebSocket")
                await websocket.close(code=1008, reason="Insufficient permissions")
                return None
            
            logger.info(f"WebSocket authenticated for user {user.username}")
            return user
        except Exception as e:
            logger.error(f"Error validating token: {str(e)}")
            # For development, allow connections with invalid tokens
            dummy_user = User(id=999, username="anonymous", email="anonymous@example.com", role="user")
            dummy_user.permissions = ["kginsights:read"]
            return dummy_user
    except Exception as e:
        logger.error(f"WebSocket authentication error: {str(e)}")
        # For development, don't close the connection
        dummy_user = User(id=999, username="anonymous", email="anonymous@example.com", role="user")
        dummy_user.permissions = ["kginsights:read"]
        return dummy_user
        # Uncomment in production:
        # await websocket.close(code=1008, reason="Authentication failed")
        # return None

@router.websocket("/ws/{schema_id}", name="websocket_endpoint")
async def websocket_endpoint(
    websocket: WebSocket, 
    schema_id: str,
    manager: ConnectionManager = Depends(get_connection_manager)
):
    """WebSocket endpoint for real-time knowledge graph insights"""
    # Check if user has required permissions
    user = await check_ws_permission(websocket, ["kginsights:read"])
    if not user:
        return
    
    try:
        # Accept connection
        await manager.connect(websocket, str(user.id), schema_id)
        
        # Process messages
        while True:
            # Wait for a message from the client
            data = await websocket.receive_text()
            
            try:
                # Parse the message
                message = json.loads(data)
                message_type = message.get("type", "")
                content = message.get("content", {})
                
                # Log message receipt
                logger.info(f"Received {message_type} message from user_id={user.id}, schema_id={schema_id}")
                
                # Process different message types
                if message_type == "query":
                    # Process the query
                    query_text = content.get("query", "")
                    if not query_text:
                        await manager.send_message(
                            websocket=websocket,
                            message_type="error",
                            content={"error": "Empty query", "query_id": content.get("query_id")}
                        )
                        continue
                    
                    # Process the query asynchronously
                    asyncio.create_task(
                        handle_query(
                            manager=manager,
                            websocket=websocket,
                            user=user,
                            schema_id=schema_id,
                            query_text=query_text,
                            query_id=content.get("query_id")
                        )
                    )
                
                elif message_type == "autocomplete":
                    # Handle autocomplete request
                    partial_text = content.get("text", "")
                    cursor_position = content.get("cursor_position", len(partial_text))
                    
                    # Process autocomplete asynchronously
                    asyncio.create_task(
                        handle_autocomplete(
                            manager=manager,
                            websocket=websocket,
                            schema_id=schema_id,
                            partial_text=partial_text,
                            cursor_position=cursor_position,
                            request_id=content.get("request_id"),
                            user=user
                        )
                    )
                
                elif message_type == "validate":
                    # Handle validation request
                    query_text = content.get("query", "")
                    
                    # Process validation asynchronously
                    asyncio.create_task(
                        handle_validation(
                            manager=manager,
                            websocket=websocket,
                            schema_id=schema_id,
                            query_text=query_text,
                            request_id=content.get("request_id"),
                            user=user
                        )
                    )
                
                elif message_type == "suggest":
                    # Handle suggestion request
                    query_text = content.get("query", "")
                    
                    # Process suggestions asynchronously
                    asyncio.create_task(
                        handle_suggestions(
                            manager=manager,
                            websocket=websocket,
                            schema_id=schema_id,
                            query_text=query_text,
                            request_id=content.get("request_id"),
                            user=user
                        )
                    )
                
                elif message_type == "ping":
                    # Respond to ping with pong
                    await manager.send_message(
                        websocket=websocket,
                        message_type="pong",
                        content={"received_at": content.get("sent_at")}
                    )
                
                else:
                    # Unknown message type
                    await manager.send_message(
                        websocket=websocket,
                        message_type="error",
                        content={"error": f"Unknown message type: {message_type}"}
                    )
            
            except json.JSONDecodeError:
                # Invalid JSON
                await manager.send_message(
                    websocket=websocket,
                    message_type="error",
                    content={"error": "Invalid JSON message"}
                )
            
            except Exception as e:
                # General error
                logger.error(f"Error processing WebSocket message: {str(e)}")
                await manager.send_message(
                    websocket=websocket,
                    message_type="error",
                    content={"error": "Internal server error"}
                )
    
    except WebSocketDisconnect:
        # Client disconnected
        manager.disconnect(str(user.id), schema_id)
    
    except Exception as e:
        # Unexpected error
        logger.error(f"WebSocket error: {str(e)}")
        manager.disconnect(str(user.id), schema_id)

async def handle_query(
    manager: ConnectionManager,
    websocket: WebSocket,
    user: User,
    schema_id: str,
    query_text: str,
    query_id: Optional[str] = None
):
    """Handle a query request asynchronously"""
    try:
        # Send acknowledgment
        await manager.send_message(
            websocket=websocket,
            message_type="query_received",
            content={"query_id": query_id, "query": query_text}
        )
        
        # Process the query using the existing query processor
        result = await process_query(schema_id, query_text, user)
        
        # Send the result
        await manager.send_message(
            websocket=websocket,
            message_type="query_result",
            content={
                "query_id": query_id,
                "query": query_text,
                "result": result.get("result", ""),
                "intermediate_steps": result.get("intermediate_steps", []),
                "visualization": result.get("visualization", None)
            }
        )
        
        # Broadcast that a new query was processed (without the full result)
        await manager.broadcast(
            schema_id=schema_id,
            message_type="query_processed",
            content={
                "user_id": str(user.id),
                "query": query_text,
                "timestamp": result.get("timestamp")
            },
            exclude_user_id=str(user.id)  # Don't send to the original requester
        )
    
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        await manager.send_message(
            websocket=websocket,
            message_type="query_error",
            content={"query_id": query_id, "error": str(e)}
        )

async def handle_autocomplete(
    manager: ConnectionManager,
    websocket: WebSocket,
    schema_id: str,
    partial_text: str,
    cursor_position: int,
    request_id: Optional[str] = None,
    user: Optional[User] = None
):
    """Handle an autocomplete request asynchronously"""
    try:
        # Get the current user from the connection
        user_id = None
        for uid, connections in manager.active_connections.get(schema_id, {}).items():
            if websocket in connections.values():
                user_id = uid
                break
        
        if not user_id:
            # If user not found, use a dummy user
            user = User(id=999, username="anonymous", email="anonymous@example.com", role="user")
            user.permissions = ["kginsights:read"]
        else:
            # Create a user object with the ID
            user = User(id=int(user_id), username="user", email="user@example.com", role="user")
            user.permissions = ["kginsights:read"]
        
        # Get the current word being typed
        if not partial_text or cursor_position == 0:
            current_word = ""
        else:
            # Extract the word at the cursor position
            text_before_cursor = partial_text[:cursor_position]
            last_space_pos = text_before_cursor.rfind(" ")
            current_word = text_before_cursor[last_space_pos + 1:] if last_space_pos >= 0 else text_before_cursor
        
        # Get schema-based autocomplete suggestions
        suggestions = await get_autocomplete_suggestions(schema_id, partial_text, cursor_position, user)
        
        # Send suggestions
        await manager.send_message(
            websocket=websocket,
            message_type="autocomplete_suggestions",
            content={
                "request_id": request_id,
                "suggestions": suggestions,
                "current_word": current_word,
                "cursor_position": cursor_position
            }
        )
    
    except Exception as e:
        logger.error(f"Error processing autocomplete: {str(e)}")
        await manager.send_message(
            websocket=websocket,
            message_type="autocomplete_error",
            content={"request_id": request_id, "error": str(e)}
        )

async def handle_validation(
    manager: ConnectionManager,
    websocket: WebSocket,
    schema_id: str,
    query_text: str,
    request_id: Optional[str] = None,
    user: Optional[User] = None
):
    """Handle a validation request asynchronously"""
    try:
        # Get the current user from the connection
        user_id = None
        for uid, connections in manager.active_connections.get(schema_id, {}).items():
            if websocket in connections.values():
                user_id = uid
                break
        
        if not user_id:
            # If user not found, use a dummy user
            user = User(id=999, username="anonymous", email="anonymous@example.com", role="user")
            user.permissions = ["kginsights:read"]
        else:
            # Create a user object with the ID
            user = User(id=int(user_id), username="user", email="user@example.com", role="user")
            user.permissions = ["kginsights:read"]
        
        # Validate query against schema
        errors = await validate_query(schema_id, query_text, user)
        
        # Send validation results
        await manager.send_message(
            websocket=websocket,
            message_type="validation_results",
            content={
                "request_id": request_id,
                "query": query_text,
                "errors": errors
            }
        )
    
    except Exception as e:
        logger.error(f"Error processing validation: {str(e)}")
        await manager.send_message(
            websocket=websocket,
            message_type="validation_error",
            content={"request_id": request_id, "error": str(e)}
        )

async def handle_suggestions(
    manager: ConnectionManager,
    websocket: WebSocket,
    schema_id: str,
    query_text: str,
    request_id: Optional[str] = None,
    user: Optional[User] = None
):
    """Handle a suggestions request asynchronously"""
    try:
        # If user not provided, get the current user from the connection
        if not user:
            user_id = None
            for uid, connections in manager.active_connections.get(schema_id, {}).items():
                if websocket in connections.values():
                    user_id = uid
                    break
            
            if not user_id:
                # If user not found, use a dummy user
                user = User(id=999, username="anonymous", email="anonymous@example.com", role="user")
                user.permissions = ["kginsights:read"]
            else:
                # Create a user object with the ID
                user = User(id=int(user_id), username="user", email="user@example.com", role="user")
                user.permissions = ["kginsights:read"]
        
        # Get schema-based query suggestions
        suggestions = await get_query_suggestions(schema_id, user)
        
        # Send suggestions
        await manager.send_message(
            websocket=websocket,
            message_type="suggestions",
            content={
                "request_id": request_id,
                "query": query_text,
                "suggestions": suggestions
            }
        )
    
    except Exception as e:
        logger.error(f"Error processing suggestions: {str(e)}")
        await manager.send_message(
            websocket=websocket,
            message_type="suggestions_error",
            content={"request_id": request_id, "error": str(e)}
        )

# Function to register the WebSocket router with the main app
def register_websocket_api(app):
    """Register the WebSocket API with the main FastAPI app"""
    logger.info("WebSocket API registered")
    return router
