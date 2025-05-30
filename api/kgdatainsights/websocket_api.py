from typing import Dict, List, Optional, Any
import json
import asyncio
import logging
import traceback
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.requests import Request
from jose import jwt
from sqlalchemy.orm import Session

# Fix import paths for both direct and module imports
try:
    # When imported as a module
    from api.kgdatainsights.websocket_manager import ConnectionManager, get_connection_manager
    from api.auth import get_current_user, SECRET_KEY, ALGORITHM
    from api.models import User, Role, SessionLocal
    from api.kgdatainsights.query_processor import (
        process_query, 
        get_autocomplete_suggestions, 
        validate_query, 
        get_query_suggestions
    )
    from api.kgdatainsights.linguistic_checker import linguistic_checker
    from api.kgdatainsights.related_query_service import related_query_service
except ImportError:
    # When run directly
    from .websocket_manager import ConnectionManager, get_connection_manager
    from ..auth import get_current_user, SECRET_KEY, ALGORITHM
    from ..models import User, Role, SessionLocal
    from .query_processor import (
        process_query, 
        get_autocomplete_suggestions, 
        validate_query, 
        get_query_suggestions
    )
    from .linguistic_checker import linguistic_checker
    from .related_query_service import related_query_service

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
            # Note: permissions will be retrieved from the 'user' role
            return dummy_user
            # Uncomment in production:
            # await websocket.close(code=1008, reason="Missing authentication token")
            # return None
        
        try:
            # Get user from token - manually decode JWT instead of using Depends
            # Decode the JWT token manually
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username = payload.get("sub")
            if not username:
                raise ValueError("Invalid token: missing username")
            
            # Get the user from the database
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.username == username).first()
                if not user:
                    raise ValueError(f"User not found: {username}")
            finally:
                db.close()
            
            # Get permissions from the user's role
            # Check permissions
            user_permissions = []
            
            # Query the role for this user
            if user.role:
                with SessionLocal() as db:
                    role = db.query(Role).filter(Role.name == user.role).first()
                    if role:
                        # Get permissions from the role
                        user_permissions = role.get_permissions()
                    else:
                        logger.warning(f"Role '{user.role}' not found for user {user.username}")
            
            # Admin role always has all permissions
            if user.role == "admin":
                logger.info(f"User {user.username} has admin role, granting all permissions")
                return user
                
            # Check if user has the required permissions
            if not all(perm in user_permissions for perm in required_permissions):
                logger.warning(f"User {user.username} has insufficient permissions for WebSocket. Required: {required_permissions}, Has: {user_permissions}")
                await websocket.close(code=1008, reason="Insufficient permissions")
                return None
            
            logger.info(f"WebSocket authenticated for user {user.username}")
            return user
        except Exception as e:
            logger.error(f"Error validating token: {str(e)}")
            # For development, allow connections with invalid tokens
            dummy_user = User(id=999, username="anonymous", email="anonymous@example.com", role="user")
            # Note: permissions will be retrieved from the 'user' role
            return dummy_user
    except Exception as e:
        logger.error(f"WebSocket authentication error: {str(e)}")
        # For development, don't close the connection
        dummy_user = User(id=999, username="anonymous", email="anonymous@example.com", role="user")
        # Note: permissions will be retrieved from the 'user' role
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
                
                # Log detailed message info for debugging
                logger.info(f"Received message: {message}")
                
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
                
                elif message_type == "related_queries":
                    # Handle related queries request
                    query_text = content.get("query", "")
                    if not query_text:
                        await manager.send_message(
                            websocket=websocket,
                            message_type="error",
                            content={"error": "Empty query", "request_id": content.get("request_id")}
                        )
                        continue
                    
                    # Process related queries request asynchronously
                    asyncio.create_task(
                        handle_related_queries(
                            manager=manager,
                            websocket=websocket,
                            user=user,
                            schema_id=schema_id,
                            query_text=query_text,
                            request_id=content.get("request_id")
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
                
                elif message_type == "suggestions":
                    # Handle suggestions request
                    query_text = content.get("query", "")
                    cursor_position = content.get("cursor_position", 0)
                    request_id = content.get("request_id")
                    
                    # Process suggestions asynchronously
                    asyncio.create_task(
                        handle_suggestions(
                            manager=manager,
                            websocket=websocket,
                            schema_id=schema_id,
                            query_text=query_text,
                            cursor_position=cursor_position,
                            request_id=request_id,
                            user=user
                        )
                    )
                    
                elif message_type == "linguistic_check":
                    # Handle linguistic check request
                    logger.info(f"Received linguistic_check request: {content}")
                    query_text = content.get("query", "")
                    cursor_position = content.get("cursor_position", 0)
                    request_id = content.get("request_id")
                    
                    # Process linguistic check asynchronously
                    asyncio.create_task(
                        handle_linguistic_check(
                            manager=manager,
                            websocket=websocket,
                            schema_id=schema_id,
                            query_text=query_text,
                            cursor_position=cursor_position,
                            request_id=request_id,
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
                    # The frontend sends 'query' instead of 'text'
                    query_text = content.get("query", "")
                    cursor_position = content.get("cursor_position", len(query_text))
                    
                    # Log the received suggestion request
                    logger.info(f"Received suggestion request with query: '{query_text}', cursor_position: {cursor_position}")
                    
                    # Process suggestions asynchronously
                    asyncio.create_task(
                        handle_suggestions(
                            manager=manager,
                            websocket=websocket,
                            schema_id=schema_id,
                            query_text=query_text,
                            request_id=content.get("request_id"),
                            user=user,
                            cursor_position=cursor_position
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
        logger.error(traceback.format_exc())
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
        # Get the current user from the connection if not provided
        if not user:
            user_id = None
            for uid, ws in manager.active_connections.get(schema_id, {}).items():
                if websocket == ws:
                    user_id = uid
                    break
            
            if not user_id:
                # If user not found, use a dummy user
                user = User(id=999, username="anonymous", email="anonymous@example.com", role="user")
                # Note: permissions will be retrieved from the 'user' role
            else:
                # Get the user from the database
                with SessionLocal() as db:
                    db_user = db.query(User).filter(User.id == int(user_id)).first()
                    if db_user:
                        user = db_user
                    else:
                        # Create a user object with the ID if not found in DB
                        user = User(id=int(user_id), username="user", email="user@example.com", role="user")
        
        # Get the current word being typed
        if not partial_text or cursor_position == 0:
            current_word = ""
        else:
            # Extract the word at the cursor position
            text_before_cursor = partial_text[:cursor_position]
            
            # Find the last space before cursor to determine the current word
            last_space_pos = text_before_cursor.rfind(" ")
            if last_space_pos >= 0:
                current_word = text_before_cursor[last_space_pos + 1:]
            else:
                current_word = text_before_cursor
        
        logger.info(f"Autocomplete request: text='{partial_text}', cursor={cursor_position}, current_word='{current_word}'")
        
        # Get schema-based autocomplete suggestions
        suggestions = await get_autocomplete_suggestions(schema_id, partial_text, cursor_position, user)
        
        # Ensure all suggestions are in the correct format
        formatted_suggestions = []
        for suggestion in suggestions:
            if isinstance(suggestion, str):
                # Convert string suggestions to objects
                formatted_suggestions.append({
                    "text": suggestion,
                    "description": None
                })
            elif isinstance(suggestion, dict) and "text" in suggestion:
                # Use dictionary suggestions as-is
                formatted_suggestions.append({
                    "text": suggestion["text"],
                    "description": suggestion.get("description")
                })
            else:
                # Skip invalid suggestions
                logger.warning(f"Skipping invalid suggestion format: {suggestion}")
        
        # Send suggestions
        await manager.send_message(
            websocket=websocket,
            message_type="autocomplete_suggestions",
            content={
                "request_id": request_id,
                "suggestions": formatted_suggestions,
                "current_word": current_word,
                "cursor_position": cursor_position
            }
        )
        
        logger.info(f"Sent {len(formatted_suggestions)} autocomplete suggestions")
    
    except Exception as e:
        logger.error(f"Error processing autocomplete: {str(e)}")
        # Include traceback for better debugging
        logger.error(traceback.format_exc())
        
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
        # Get the current user from the connection if not provided
        if not user:
            user_id = None
            for uid, connections in manager.active_connections.get(schema_id, {}).items():
                if websocket in connections.values():
                    user_id = uid
                    break
            
            if not user_id:
                # If user not found, use a dummy user
                user = User(id=999, username="anonymous", email="anonymous@example.com", role="user")
                # Note: permissions will be retrieved from the 'user' role
            else:
                # Get the user from the database
                with SessionLocal() as db:
                    db_user = db.query(User).filter(User.id == int(user_id)).first()
                    if db_user:
                        user = db_user
                    else:
                        # Create a user object with the ID if not found in DB
                        user = User(id=int(user_id), username="user", email="user@example.com", role="user")
        
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
        logger.error(traceback.format_exc())
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
    user: Optional[User] = None,
    cursor_position: Optional[int] = None,
    suggestion_type: str = "query"
):
    """Handle a suggestions request asynchronously
    
    Args:
        manager: The connection manager
        websocket: The WebSocket connection
        schema_id: The schema ID
        query_text: The query text to get suggestions for
        request_id: Optional request ID for tracking
        user: Optional user object
        cursor_position: Optional cursor position in the query text
        suggestion_type: Type of suggestions ("query" or "linguistic")
    """
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
                # Note: permissions will be retrieved from the 'user' role
            else:
                # Get the user from the database
                with SessionLocal() as db:
                    db_user = db.query(User).filter(User.id == int(user_id)).first()
                    if db_user:
                        user = db_user
                    else:
                        # Create a user object with the ID if not found in DB
                        user = User(id=int(user_id), username="user", email="user@example.com", role="user")
        
        # Get schema-based query suggestions with current text for filtering
        if cursor_position is None:
            cursor_position = len(query_text) if query_text else 0  # Default to end of text if not specified
        
        # Log the input parameters for debugging
        logger.info(f"Generating suggestions for schema_id: {schema_id}, text: '{query_text}', cursor_position: {cursor_position}")
        
        # Call the query suggestions function with the text and cursor position
        suggestions = await get_query_suggestions(schema_id, user, query_text, cursor_position)
        
        # Log the results
        logger.info(f"Generated {len(suggestions)} suggestions for schema_id: {schema_id}")
        for i, suggestion in enumerate(suggestions[:5]):
            logger.info(f"  Suggestion {i+1}: '{suggestion}'")
        if len(suggestions) > 5:
            logger.info(f"  ... and {len(suggestions) - 5} more suggestions")
        
        # Send suggestions with type information to prevent overriding linguistic suggestions
        await manager.send_message(
            websocket=websocket,
            message_type="suggestions",
            content={
                "request_id": request_id,
                "query": query_text,
                "suggestions": suggestions,
                "schema_id": schema_id,  # Include schema_id in response for verification
                "suggestion_type": suggestion_type  # Add type to differentiate query vs linguistic suggestions
            }
        )
    
    except Exception as e:
        logger.error(f"Error processing suggestions: {str(e)}")
        logger.error(traceback.format_exc())
        await manager.send_message(
            websocket=websocket,
            message_type="suggestions_error",
            content={"request_id": request_id, "error": str(e)}
        )

async def handle_related_queries(
    manager: ConnectionManager,
    websocket: WebSocket,
    schema_id: str,
    query_text: str,
    request_id: Optional[str] = None,
    user: Optional[User] = None
):
    """Handle a related queries request asynchronously
    
    Args:
        manager: The connection manager
        websocket: The WebSocket connection
        schema_id: The schema ID
        query_text: The query text to get related queries for
        request_id: Optional request ID for tracking
        user: Optional user object
    """
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
            else:
                # Get the user from the database
                with SessionLocal() as db:
                    db_user = db.query(User).filter(User.id == int(user_id)).first()
                    if db_user:
                        user = db_user
                    else:
                        # Create a user object with the ID if not found in DB
                        user = User(id=int(user_id), username="user", email="user@example.com", role="user")
        
        # Log the input parameters for debugging
        logger.info(f"Generating related queries for schema_id: {schema_id}, text: '{query_text}'")
        
        # Get related queries from the service
        related_queries = await related_query_service.get_related_queries(
            schema_id=schema_id,
            query_text=query_text,
            user_id=str(user.id) if user else None
        )
        
        # Log the results
        logger.info(f"Generated {len(related_queries['broader'])} broader and {len(related_queries['narrower'])} narrower queries")
        
        # Send related queries
        await manager.send_message(
            websocket=websocket,
            message_type="related_queries",
            content={
                "request_id": request_id,
                "query": query_text,
                "broader": related_queries["broader"],
                "narrower": related_queries["narrower"],
                "schema_id": schema_id  # Include schema_id in response for verification
            }
        )
    
    except Exception as e:
        logger.error(f"Error processing related queries: {str(e)}")
        logger.error(traceback.format_exc())
        await manager.send_message(
            websocket=websocket,
            message_type="related_queries_error",
            content={"request_id": request_id, "error": str(e)}
        )

async def handle_linguistic_check(
    manager: ConnectionManager,
    websocket: WebSocket,
    schema_id: str,
    query_text: str,
    cursor_position: int,
    request_id: Optional[str] = None,
    user: Optional[User] = None
):
    """Handle a linguistic check request asynchronously
    
    Args:
        manager: The connection manager
        websocket: The WebSocket connection
        schema_id: The schema ID
        query_text: The query text to check
        cursor_position: The cursor position in the query text
        request_id: Optional request ID for tracking
        user: Optional user object
    """
    logger.info(f"[LINGUISTIC] Handling linguistic check: schema={schema_id}, query='{query_text}', pos={cursor_position}, req_id={request_id}")
    
    try:
        # Check linguistic issues using LanguageTool
        logger.info(f"[LINGUISTIC] Calling linguistic_checker.check_text")
        errors, analysis = linguistic_checker.check_text(query_text, cursor_position)
        logger.info(f"[LINGUISTIC] Got results: errors={errors}, analysis={analysis}")
        
        # Generate suggestions from linguistic errors
        linguistic_suggestions = []
        for error in errors:
            if "suggestion" in error and error["suggestion"]:
                # Create a formatted suggestion string for the frontend
                linguistic_suggestions.append(f"💡 {error['suggestion']} ({error['message']})")
        
        # Send linguistic suggestions through the suggestion system if we have any
        if linguistic_suggestions:
            # Send linguistic suggestions through the suggestion system
            await manager.send_message(
                websocket=websocket,
                message_type="suggestions",
                content={
                    "request_id": request_id,
                    "query": query_text,
                    "suggestions": linguistic_suggestions,
                    "schema_id": schema_id,
                    "suggestion_type": "linguistic"  # Mark these as linguistic suggestions
                }
            )
            logger.info(f"[LINGUISTIC] Sent {len(linguistic_suggestions)} linguistic suggestions")
        
        # Send the detailed check results back
        response = {
            "type": "linguistic_check_results",
            "status": "success",
            "errors": errors,
            "quality_analysis": analysis,
            "has_suggestions": len(linguistic_suggestions) > 0
        }
        
        # Add request ID if provided
        if request_id:
            response["request_id"] = request_id
        
        logger.info(f"[LINGUISTIC] Sending response: {response}")
        await manager.send_message(websocket, "linguistic_check_results", response)
        logger.info(f"[LINGUISTIC] Response sent successfully")
        
    except Exception as e:
        logger.error(f"[LINGUISTIC] Error in linguistic check: {str(e)}\n{traceback.format_exc()}")
        
        # Send error response
        error_response = {
            "type": "linguistic_check_error",
            "error": str(e)
        }
        
        # Add request ID if provided
        if request_id:
            error_response["request_id"] = request_id
        
        logger.info(f"[LINGUISTIC] Sending error response: {error_response}")
        await manager.send_message(websocket, "linguistic_check_error", {"error": str(e), "request_id": request_id})
        logger.info(f"[LINGUISTIC] Error response sent successfully")

# Function to register the WebSocket router with the main app
def register_websocket_api(app):
    """Register the WebSocket API with the main FastAPI app"""
    logger.info("WebSocket API registered")
    return router
