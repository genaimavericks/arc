from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from typing import Dict, List, Optional, Any, Set
import json
import logging
import asyncio
import time
import os
import re
from pathlib import Path
from datetime import datetime
from jose import jwt
from ..auth import SECRET_KEY, ALGORITHM
from ..models import User, SessionLocal
from ..kgdatainsights.data_insights_api import DEFAULT_PREDEFINED_QUERIES, QUERIES_DIR, HISTORY_DIR

# Import language checking libraries
try:
    import language_tool_python
    from spellchecker import SpellChecker
    LINGUISTIC_CHECKS_AVAILABLE = True
except ImportError:
    LINGUISTIC_CHECKS_AVAILABLE = False
    logging.warning("Language checking libraries not available. Install with: pip install language-tool-python pyspellchecker")

# Import Neo4j schema helper functions
try:
    # First try relative import (most reliable)
    from ..kgdatainsights.neo4j_schema_helper import (
        get_neo4j_node_labels,
        get_neo4j_relationship_types,
        get_neo4j_property_keys
    )
except ImportError as e:
    logger.error(f"Failed to import neo4j_schema_helper with relative import: {e}")
    try:
        # Try absolute import as fallback
        from api.kgdatainsights.neo4j_schema_helper import (
            get_neo4j_node_labels,
            get_neo4j_relationship_types,
            get_neo4j_property_keys
        )
    except ImportError as e:
        logger.error(f"Failed to import neo4j_schema_helper with absolute import: {e}")
        # Define stub functions for graceful degradation
        async def get_neo4j_node_labels():
            logger.warning("Using stub node labels due to import failure")
            return ["Person", "Customer", "InternetService", "PhoneService", "Product"]
            
        async def get_neo4j_relationship_types():
            logger.warning("Using stub relationship types due to import failure")
            return ["HAS_SERVICE", "SUBSCRIBES_TO", "PURCHASED"]
            
        async def get_neo4j_property_keys(label):
            logger.warning(f"Using stub property keys for {label} due to import failure")
            return ["name", "id", "type"]

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("kginsights.websocket")

router = APIRouter()

# Dictionary to store active WebSocket connections
active_connections: Dict[str, Dict[str, WebSocket]] = {}

# Maximum number of suggestions to return
MAX_SUGGESTIONS = 10

# Initialize language checking tools if available
if LINGUISTIC_CHECKS_AVAILABLE:
    try:
        language_tool = language_tool_python.LanguageTool('en-US')
        spell_checker = SpellChecker()
        logging.info("Linguistic checking tools initialized successfully")
    except Exception as e:
        logging.error(f"Failed to initialize linguistic checking tools: {e}")
        LINGUISTIC_CHECKS_AVAILABLE = False

# Common node labels and relationship types to suggest
COMMON_NODE_LABELS = [
    {"text": "Customer", "description": "Customer node"},
    {"text": "InternetService", "description": "Internet service node"},
    {"text": "PhoneService", "description": "Phone service node"},
    {"text": "Contract", "description": "Contract node"},
    {"text": "PaymentMethod", "description": "Payment method node"}
]

COMMON_RELATIONSHIP_TYPES = [
    {"text": "HAS_SERVICE", "description": "Customer to service relationship"},
    {"text": "HAS_CONTRACT", "description": "Customer to contract relationship"},
    {"text": "USES_PAYMENT", "description": "Customer to payment method relationship"}
]

# Ensure directories exist
os.makedirs(HISTORY_DIR, exist_ok=True)
os.makedirs(QUERIES_DIR, exist_ok=True)

# Function to get predefined (canned) queries directly
async def get_canned_queries(schema_id: str = "-1") -> List[Dict[str, str]]:
    """Get predefined queries directly from the filesystem or default queries"""
    try:
        # Log the schema_id we're using
        logger.info(f"Getting canned queries for schema_id: {schema_id}")
        
        # Try different possible schema IDs to find canned queries
        possible_schema_ids = [schema_id, "1", "-1", "default"]
        predefined_queries = None
        used_schema_id = None
        
        for sid in possible_schema_ids:
            queries_file = os.path.join(QUERIES_DIR, f"{sid}_queries.json")
            logger.info(f"Checking for canned queries file: {queries_file}")
            
            if os.path.exists(queries_file):
                logger.info(f"Found canned queries file for schema_id: {sid}")
                with open(queries_file, 'r') as f:
                    predefined_queries = json.load(f)
                used_schema_id = sid
                break
        
        # If no file found, use default predefined queries
        if predefined_queries is None:
            logger.info("No canned queries file found, using default predefined queries")
            predefined_queries = DEFAULT_PREDEFINED_QUERIES
            used_schema_id = "default"
        
        # Flatten queries from all categories
        result_queries = []
        
        # Include all categories
        for cat, queries in predefined_queries.items():
            for query in queries:
                result_queries.append({
                    "text": query["query"],
                    "description": query.get("description", f"Canned query ({used_schema_id})")
                })
        
        logger.info(f"Returning {len(result_queries)} canned queries for schema_id: {used_schema_id}")
        return result_queries
    except Exception as e:
        logger.error(f"Error getting canned queries: {str(e)}")
        return []

# Function to get query history directly
async def get_query_history(schema_id: str) -> List[Dict[str, str]]:
    """Get query history directly from the filesystem"""
    try:
        # Log the schema_id we're using
        logger.info(f"Getting query history for schema_id: {schema_id}")
        
        # Try different possible schema IDs to find history
        possible_schema_ids = [schema_id, "1", "-1", "default"]
        history_items = []
        used_schema_id = None
        
        for sid in possible_schema_ids:
            history_file = os.path.join(HISTORY_DIR, f"{sid}_history.json")
            logger.info(f"Checking for history file: {history_file}")
            
            if os.path.exists(history_file):
                logger.info(f"Found history file for schema_id: {sid}")
                with open(history_file, 'r') as f:
                    history_items = json.load(f)
                used_schema_id = sid
                break
        
        if not history_items:
            logger.info(f"No history found for any schema ID")
            return []
            
        # Sort by timestamp (newest first) and limit
        sorted_history = sorted(history_items, key=lambda x: x.get("timestamp", ""), reverse=True)[:5]
        
        # Transform to expected format
        result = [{
            "text": item.get("query", ""),
            "description": f"History: {item.get('timestamp', '')}" 
        } for item in sorted_history]  # Limit to 5 items
        
        logger.info(f"Returning {len(result)} history items for schema_id: {used_schema_id}")
        return result
    except Exception as e:
        logger.error(f"Error getting query history: {str(e)}")
        return []

# Function to add a query to history
async def add_to_query_history(schema_id: str, query: str) -> None:
    """Add a query to the history file"""
    try:
        if not query or len(query.strip()) == 0:
            return
        
        # Log the schema_id we're using
        logger.info(f"Adding query to history for schema_id: {schema_id}")
        
        # Try to find an existing history file for any schema ID
        possible_schema_ids = [schema_id, "1", "-1", "default"]
        existing_history_file = None
        used_schema_id = schema_id  # Default to the provided schema_id
        
        for sid in possible_schema_ids:
            history_file = os.path.join(HISTORY_DIR, f"{sid}_history.json")
            if os.path.exists(history_file):
                existing_history_file = history_file
                used_schema_id = sid
                logger.info(f"Found existing history file for schema_id: {sid}")
                break
        
        # If no existing file found, create one with the provided schema_id
        if existing_history_file is None:
            used_schema_id = schema_id
            existing_history_file = os.path.join(HISTORY_DIR, f"{used_schema_id}_history.json")
            logger.info(f"No existing history file found, creating new one for schema_id: {used_schema_id}")
        
        history_items = []
        
        # Load existing history if file exists
        if os.path.exists(existing_history_file):
            with open(existing_history_file, 'r') as f:
                history_items = json.load(f)
        
        # Create history item with timestamp
        timestamp = datetime.now().isoformat()
        history_item = {
            "id": f"{used_schema_id}_{int(time.time())}",
            "schema_id": used_schema_id,
            "query": query,
            "result": "",  # We don't have actual results here
            "timestamp": timestamp
        }
        
        # Remove if already exists
        history_items = [item for item in history_items if item.get("query") != query]
        
        # Add to beginning
        history_items.insert(0, history_item)
        
        # Limit size
        if len(history_items) > 10:  # MAX_HISTORY_ITEMS
            history_items = history_items[:10]
        
        # Save back to file
        with open(existing_history_file, 'w') as f:
            json.dump(history_items, f)
            
        logger.info(f"Added query to history for schema {used_schema_id}: {query}")
    except Exception as e:
        logger.error(f"Error adding query to history: {str(e)}")

# Router
router = APIRouter(prefix="/kginsights", tags=["kginsights"])

# Store active connections
active_connections: Dict[str, Dict[str, WebSocket]] = {}

async def get_user_from_token(token: str) -> Optional[User]:
    """Get user from token for WebSocket authentication"""
    try:
        # Decode JWT token manually without using Depends
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            return None
            
        # Create a database session
        db = SessionLocal()
        try:
            # Get user from database
            user = db.query(User).filter(User.username == username).first()
            return user
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error authenticating WebSocket connection: {str(e)}")
        return None

# Function to get matching common items
async def get_matching_common_items(query_words: List[str], active_query: str) -> List[Dict[str, str]]:
    """Get common node labels and relationship types that match the query"""
    matching_items = []
    
    # Check if query is empty
    if not query_words or not active_query.strip():
        return []
    
    # Get last word in query for matching
    last_word = query_words[-1].lower() if query_words else ""
    
    # Match against common node labels
    for item in COMMON_NODE_LABELS:
        if last_word and item["text"].lower().startswith(last_word):
            matching_items.append(item)
    
    # Match against common relationship types
    for item in COMMON_RELATIONSHIP_TYPES:
        if last_word and item["text"].lower().startswith(last_word):
            matching_items.append(item)
    
    return matching_items

# Function to check for grammar and spelling errors
async def check_linguistic_errors(text: str) -> List[Dict[str, str]]:
    """Check for grammar and spelling errors in the text"""
    suggestions = []
    
    print(f"Checking linguistic errors for text: '{text}'")
    print(f"LINGUISTIC_CHECKS_AVAILABLE: {LINGUISTIC_CHECKS_AVAILABLE}")
    
    if not LINGUISTIC_CHECKS_AVAILABLE:
        print("Linguistic checks are not available. Required packages may not be installed.")
        return suggestions
    
    if not text or not text.strip():
        print("Empty text provided for linguistic check, returning empty suggestions.")
        return suggestions
    
    try:
        # Check spelling errors first (faster than grammar check)
        # Split text into words and check each one
        words = re.findall(r'\b\w+\b', text)
        print(f"Found {len(words)} words to check for spelling: {words}")
        
        misspelled = spell_checker.unknown(words)
        print(f"Found {len(misspelled)} misspelled words: {misspelled}")
        
        for word in misspelled:
            corrections = spell_checker.candidates(word)
            print(f"Spelling corrections for '{word}': {corrections}")
            
            if corrections:
                top_correction = list(corrections)[0] if corrections else word
                # Find position of the misspelled word
                word_pos = text.find(word)
                if word_pos >= 0:
                    suggestion = {
                        "text": top_correction,
                        "description": f"Spelling: '{word}' → '{top_correction}'",
                        "type": "spelling",
                        "offset": word_pos,
                        "errorLength": len(word)
                    }
                    print(f"Adding spelling suggestion: {suggestion}")
                    suggestions.append(suggestion)
        
        # Check grammar errors
        try:
            print("Starting grammar check...")
            grammar_matches = language_tool.check(text)
            print(f"Found {len(grammar_matches)} grammar matches")
            
            for match in grammar_matches[:5]:  # Limit to 5 grammar suggestions
                if match.replacements:
                    suggestion = {
                        "text": match.replacements[0],
                        "description": f"Grammar: '{match.context}' → '{match.replacements[0]}'",
                        "type": "grammar",
                        "offset": match.offset,
                        "errorLength": match.errorLength
                    }
                    print(f"Adding grammar suggestion: {suggestion}")
                    suggestions.append(suggestion)
        except Exception as grammar_error:
            print(f"Error in grammar checking: {grammar_error}")
            # Continue with spelling suggestions even if grammar check fails
        
        print(f"Returning {len(suggestions)} linguistic suggestions")
        return suggestions
    except Exception as e:
        print(f"Error checking linguistic errors: {e}")
        import traceback
        print(traceback.format_exc())
        return []

@router.websocket("/{schema_id}/ws")
@router.websocket("/ws/direct/{schema_id}")
async def websocket_endpoint(
    websocket: WebSocket, 
    schema_id: str,
    token: Optional[str] = Query(None)
):
    """WebSocket endpoint for KG Insights autocomplete and query functionality"""
    # Accept the connection
    await websocket.accept()
    
    # Generate a unique connection ID
    connection_id = f"conn_{id(websocket)}"
    
    try:
        # Authenticate user if token is provided
        user = None
        if token:
            user = await get_user_from_token(token)
            if not user:
                await websocket.send_json({
                    "type": "error",
                    "content": "Authentication failed"
                })
                await websocket.close()
                return
        
        # Initialize schema connections if needed
        if schema_id not in active_connections:
            active_connections[schema_id] = {}
        
        # Store the connection
        active_connections[schema_id][connection_id] = websocket
        logger.info(f"New WebSocket connection: schema_id={schema_id}, connection_id={connection_id}")
        
        # Send connection status message
        await websocket.send_json({
            "type": "connection_status",
            "content": "connected"
        })
        
        # Handle incoming messages
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                message_type = message.get("type", "")
                
                if message_type == "get_autocomplete_suggestions":
                    # Handle autocomplete request
                    query = message.get("query", "")
                    cursor_position = message.get("cursorPosition", len(query))
                    max_suggestions = message.get("maxSuggestions", MAX_SUGGESTIONS)
                    include_linguistic = message.get("includeLinguistic", True)
                    
                    # Get the active query (text up to cursor)
                    active_query = query[:cursor_position]
                    
                    # Split the active query into words
                    query_words = active_query.split()
                    
                    # Initialize suggestions list
                    suggestions = []
                    
                    # Get node labels from Neo4j schema
                    try:
                        node_labels = await get_neo4j_node_labels()
                        relationship_types = await get_neo4j_relationship_types()
                        
                        # Add node labels and relationship types to suggestions if they match
                        if query_words:
                            last_word = query_words[-1].lower()
                            
                            # Match node labels
                            for label in node_labels:
                                if label.lower().startswith(last_word):
                                    suggestions.append({
                                        "text": label,
                                        "description": f"Node label: {label}"
                                    })
                            
                            # Match relationship types
                            for rel_type in relationship_types:
                                if rel_type.lower().startswith(last_word):
                                    suggestions.append({
                                        "text": rel_type,
                                        "description": f"Relationship type: {rel_type}"
                                    })
                    except Exception as e:
                        logger.error(f"Error getting Neo4j schema: {e}")
                    
                    # Add common items that match
                    common_items = await get_matching_common_items(query_words, active_query)
                    suggestions.extend(common_items)
                    
                    # Add canned queries if appropriate
                    if len(query_words) <= 3:  # Only suggest canned queries for short inputs
                        try:
                            canned_queries = await get_canned_queries(schema_id)
                            for item in canned_queries:
                                if active_query.lower() in item["text"].lower():
                                    suggestions.append(item)
                        except Exception as e:
                            logger.error(f"Error getting canned queries: {e}")
                    
                    # Add query history if appropriate
                    if len(query_words) <= 3:  # Only suggest history for short inputs
                        try:
                            history_items = await get_query_history(schema_id)
                            for item in history_items:
                                if active_query.lower() in item["text"].lower():
                                    suggestions.append(item)
                        except Exception as e:
                            logger.error(f"Error getting query history: {e}")
                    
                    # Add linguistic suggestions if enabled
                    if include_linguistic and query:
                        try:
                            logger.info(f"Requesting linguistic checks for query: '{query}'")
                            linguistic_suggestions = await check_linguistic_errors(query)
                            logger.info(f"Received {len(linguistic_suggestions)} linguistic suggestions")
                            
                            # If we have linguistic suggestions, prioritize them by adding them first
                            if linguistic_suggestions:
                                logger.info(f"Adding linguistic suggestions to response: {linguistic_suggestions}")
                                # Add linguistic suggestions at the beginning for higher visibility
                                suggestions = linguistic_suggestions + suggestions
                            else:
                                logger.info("No linguistic suggestions found")
                        except Exception as e:
                            logger.error(f"Error checking linguistic errors: {e}")
                            import traceback
                            logger.error(traceback.format_exc())
                    
                    # Limit suggestions to max_suggestions
                    suggestions = suggestions[:max_suggestions]
                    
                    # Send suggestions back to client
                    await websocket.send_json({
                        "type": "autocomplete_suggestions",
                        "suggestions": suggestions
                    })
                
                elif message_type == "validate_query":
                    # Handle query validation
                    query = message.get("query", "")
                    
                    # Basic validation - query must not be empty
                    if not query or len(query.strip()) == 0:
                        await websocket.send_json({
                            "type": "validation_result",
                            "isValid": False,
                            "errors": ["Query cannot be empty"]
                        })
                        continue
                    
                    # TODO: Add more sophisticated validation by trying to parse the Cypher query
                    # For now, just check for basic MATCH syntax
                    is_valid = query.strip().upper().startswith("MATCH")
                    errors = [] if is_valid else ["Query should start with MATCH"]
                    
                    await websocket.send_json({
                        "type": "validation_result",
                        "isValid": is_valid,
                        "errors": errors
                    })
                
                elif message_type == "query":
                    # Handle actual query execution
                    query = message.get("query", "")
                    
                    if not query or len(query.strip()) == 0:
                        await websocket.send_json({
                            "type": "error",
                            "content": "Empty query"
                        })
                        continue
                    
                    logger.info(f"Executing query: {query}")
                    
                    # Add query to history
                    try:
                        await add_to_query_history(schema_id, query)
                        
                        # For now, just echo the query back as we don't have direct Neo4j execution
                        # In a real implementation, this would execute the query against Neo4j
                        await websocket.send_json({
                            "type": "query_result",
                            "query": query,
                            "results": ["Result 1", "Result 2"]
                        })
                        logger.info(f"Query executed successfully: {query}")
                    except Exception as e:
                        logger.error(f"Error executing query: {str(e)}")
                        await websocket.send_json({
                            "type": "error",
                            "content": f"Error executing query: {str(e)}"
                        })
                
                elif message_type == "ping":
                    # Respond to ping with pong
                    await websocket.send_json({
                        "type": "pong"
                    })
                
                elif message_type == "check_linguistic":
                    text = message.get("text", "")
                    
                    # Check for linguistic errors
                    try:
                        linguistic_suggestions = await check_linguistic_errors(text)
                        
                        # Send linguistic suggestions back to client
                        await websocket.send_json({
                            "type": "linguistic_suggestions",
                            "suggestions": linguistic_suggestions
                        })
                    except Exception as e:
                        logger.error(f"Error checking linguistic errors: {e}")
                        await websocket.send_json({
                            "type": "error",
                            "content": f"Error checking linguistic errors: {str(e)}"
                        })
                
                else:
                    logger.warning(f"Unknown message type: {message_type}")
                    await websocket.send_json({
                        "type": "error",
                        "content": f"Unknown message type: {message_type}"
                    })
            
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON received: {data}")
                await websocket.send_json({
                    "type": "error",
                    "content": "Invalid JSON format"
                })
            
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {str(e)}")
                await websocket.send_json({
                    "type": "error",
                    "content": f"Error processing message: {str(e)}"
                })
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: schema_id={schema_id}, connection_id={connection_id}")
    
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
    
    finally:
        # Clean up the connection
        if schema_id in active_connections and connection_id in active_connections[schema_id]:
            del active_connections[schema_id][connection_id]
            if not active_connections[schema_id]:
                del active_connections[schema_id]
