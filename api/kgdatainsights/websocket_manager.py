from typing import Dict, List, Optional, Any
import json
import asyncio
from fastapi import WebSocket
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manages WebSocket connections for real-time knowledge graph insights"""
    
    def __init__(self):
        # Store active connections by schema_id and user_id
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}
        # Store message history for each schema
        self.message_history: Dict[str, List[Dict[str, Any]]] = {}
        
    async def connect(self, websocket: WebSocket, user_id: str, schema_id: str):
        """Accept a new WebSocket connection and store it"""
        await websocket.accept()
        
        # Initialize schema_id dict if it doesn't exist
        if schema_id not in self.active_connections:
            self.active_connections[schema_id] = {}
            self.message_history[schema_id] = []
        
        # Store the connection
        self.active_connections[schema_id][user_id] = websocket
        logger.info(f"New WebSocket connection: user_id={user_id}, schema_id={schema_id}")
        
        # Send connection confirmation
        await self.send_message(
            websocket=websocket,
            message_type="connection_status",
            content={"status": "connected", "timestamp": datetime.now().isoformat()}
        )
    
    def disconnect(self, user_id: str, schema_id: str):
        """Remove a WebSocket connection"""
        if schema_id in self.active_connections and user_id in self.active_connections[schema_id]:
            del self.active_connections[schema_id][user_id]
            logger.info(f"WebSocket disconnected: user_id={user_id}, schema_id={schema_id}")
            
            # Clean up empty schema entries
            if not self.active_connections[schema_id]:
                del self.active_connections[schema_id]
                if schema_id in self.message_history:
                    del self.message_history[schema_id]
    
    async def send_message(self, websocket: WebSocket, message_type: str, content: Any):
        """Send a message to a specific WebSocket"""
        message = {
            "type": message_type,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        await websocket.send_json(message)
    
    async def broadcast(self, schema_id: str, message_type: str, content: Any, exclude_user_id: Optional[str] = None):
        """Broadcast a message to all connections for a schema, optionally excluding one user"""
        if schema_id not in self.active_connections:
            return
            
        message = {
            "type": message_type,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        
        # Store message in history
        self.message_history[schema_id].append(message)
        
        # Limit history size
        if len(self.message_history[schema_id]) > 100:
            self.message_history[schema_id] = self.message_history[schema_id][-100:]
        
        # Send to all connected clients for this schema
        for user_id, websocket in self.active_connections[schema_id].items():
            if exclude_user_id and user_id == exclude_user_id:
                continue
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to user_id={user_id}: {str(e)}")
                # Don't disconnect here, let the connection error handler do it
    
    def get_connection(self, user_id: str, schema_id: str) -> Optional[WebSocket]:
        """Get a specific WebSocket connection if it exists"""
        if schema_id in self.active_connections and user_id in self.active_connections[schema_id]:
            return self.active_connections[schema_id][user_id]
        return None
    
    def get_connection_count(self, schema_id: Optional[str] = None) -> int:
        """Get count of active connections, optionally filtered by schema_id"""
        if schema_id:
            return len(self.active_connections.get(schema_id, {}))
        
        # Count all connections across all schemas
        return sum(len(connections) for connections in self.active_connections.values())
    
    def get_active_schemas(self) -> List[str]:
        """Get list of schemas with active connections"""
        return list(self.active_connections.keys())
    
    def get_active_users(self, schema_id: Optional[str] = None) -> List[str]:
        """Get list of users with active connections, optionally filtered by schema_id"""
        if schema_id:
            return list(self.active_connections.get(schema_id, {}).keys())
        
        # Get all users across all schemas
        users = set()
        for schema_connections in self.active_connections.values():
            users.update(schema_connections.keys())
        return list(users)

# Singleton instance
_connection_manager = None

def get_connection_manager() -> ConnectionManager:
    """Get or create the singleton ConnectionManager instance"""
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
    return _connection_manager
