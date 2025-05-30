"""
Schema Service for Knowledge Graph Insights
Provides schema details for dynamic query generation and analysis
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional
import json
import os
from sqlalchemy.orm import Session
import traceback

# Setup logging
logger = logging.getLogger(__name__)

# Try importing models with both possible import paths
try:
    # When imported as a module
    from api.models import GraphSchema, SessionLocal
except ImportError:
    try:
        # When run directly
        from ..models import GraphSchema, SessionLocal
    except ImportError:
        logger.error("Could not import models, schema service will use fallback methods")
        GraphSchema = None
        SessionLocal = None

class SchemaService:
    """Service for loading and processing schema information"""
    
    def __init__(self):
        """Initialize the schema service"""
        self.schema_cache = {}  # Cache schema details by ID
        self.initialization_complete = False
        
        # Start asynchronous initialization
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're in an async context, start a background task
                asyncio.create_task(self.initialize_service())
            else:
                # If we're in a synchronous context, run immediately
                loop.run_until_complete(self.initialize_service())
        except Exception as e:
            logger.error(f"Error starting schema service initialization: {e}")
            # Mark as initialized to avoid blocking
            self.initialization_complete = True
    
    async def initialize_service(self):
        """Preload all available schemas to ensure fast response times"""
        try:
            logger.info("Starting schema service initialization")
            
            # Get list of available schemas
            schema_ids = await self.get_available_schemas()
            
            if schema_ids:
                logger.info(f"Preloading {len(schema_ids)} schemas")
                
                # Preload schemas in parallel
                await asyncio.gather(*[self.get_schema_details(schema_id) for schema_id in schema_ids])
                logger.info(f"Successfully preloaded {len(self.schema_cache)} schemas")
            else:
                logger.warning("No schemas available for preloading")
            
            self.initialization_complete = True
            logger.info("Schema service initialization complete")
        except Exception as e:
            logger.error(f"Error during schema service initialization: {e}")
            logger.error(traceback.format_exc())
            # Mark as initialized to avoid blocking
            self.initialization_complete = True
        
    async def get_schema_details(self, schema_id: str) -> Dict[str, Any]:
        """
        Get schema details by ID
        
        Args:
            schema_id: The schema ID
            
        Returns:
            Schema details as a dictionary
        """
        # Wait for initialization if still in progress and this is one of the first requests
        if not self.initialization_complete:
            # Wait up to 500ms for initialization to complete
            try:
                wait_start = asyncio.get_event_loop().time()
                while not self.initialization_complete and asyncio.get_event_loop().time() - wait_start < 0.5:
                    await asyncio.sleep(0.01)  # Short sleep to yield control
            except Exception as e:
                logger.error(f"Error waiting for initialization: {e}")
        
        # Check cache first for performance
        if schema_id in self.schema_cache:
            logger.debug(f"Using cached schema for {schema_id}")
            return self.schema_cache[schema_id]
        
        logger.info(f"Loading schema details for {schema_id}")
        
        try:
            # Try loading from database if models are available
            if GraphSchema and SessionLocal:
                async with asyncio.Lock():
                    with SessionLocal() as db:
                        schema = db.query(GraphSchema).filter(GraphSchema.id == schema_id).first()
                        
                        if schema:
                            # Process schema content
                            schema_content = json.loads(schema.content) if schema.content else {}
                            
                            # Cache the schema for future use
                            self.schema_cache[schema_id] = schema_content
                            logger.info(f"Loaded schema {schema_id} from database")
                            return schema_content
                        else:
                            logger.warning(f"Schema {schema_id} not found in database")
            else:
                logger.warning("GraphSchema model not available, trying to load from file system")
            
            # Fallback to loading from a file if available
            schema_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'schemas')
            schema_path = os.path.join(schema_dir, f"{schema_id}.json")
            
            if os.path.exists(schema_path):
                with open(schema_path, 'r') as f:
                    schema_content = json.load(f)
                    
                    # Cache the schema for future use
                    self.schema_cache[schema_id] = schema_content
                    logger.info(f"Loaded schema {schema_id} from file")
                    return schema_content
            
            logger.warning(f"Could not find schema {schema_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error loading schema {schema_id}: {e}")
            logger.error(traceback.format_exc())
            return None
    
    async def get_available_schemas(self) -> List[str]:
        """
        Get list of all available schema IDs
        
        Returns:
            List of schema IDs
        """
        schema_ids = []
        
        try:
            # Try to fetch from database if models are available
            if GraphSchema and SessionLocal:
                async with asyncio.Lock():
                    with SessionLocal() as db:
                        schemas = db.query(GraphSchema).all()
                        schema_ids = [schema.id for schema in schemas if schema.id]
                        logger.info(f"Found {len(schema_ids)} schemas in database")
            else:
                logger.warning("GraphSchema model not available, trying to load from file system")
                
            # Fallback to scanning schema directory if database query failed or returned empty
            if not schema_ids:
                schema_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'schemas')
                if os.path.exists(schema_dir):
                    for filename in os.listdir(schema_dir):
                        if filename.endswith('.json'):
                            schema_id = filename.replace('.json', '')
                            schema_ids.append(schema_id)
                    logger.info(f"Found {len(schema_ids)} schemas in file system")
            
            # If still no schemas found, use some defaults for testing
            if not schema_ids:
                schema_ids = ["default", "manufacturing", "supply_chain"]
                logger.warning(f"No schemas found, using default schema IDs: {schema_ids}")
            
            return schema_ids
        except Exception as e:
            logger.error(f"Error getting available schemas: {e}")
            return ["default"]
    
    def clear_cache(self, schema_id: Optional[str] = None):
        """
        Clear schema cache
        
        Args:
            schema_id: Optional specific schema ID to clear, or None to clear all
        """
        if schema_id:
            if schema_id in self.schema_cache:
                del self.schema_cache[schema_id]
                logger.info(f"Cleared cache for schema {schema_id}")
        else:
            self.schema_cache.clear()
            logger.info("Cleared entire schema cache")
            # Re-initialize if we're clearing the whole cache
            asyncio.create_task(self.initialize_service())

# Create a singleton instance
schema_service = SchemaService()

# Expose service functions for easy import
async def get_schema_details(schema_id: str) -> Dict[str, Any]:
    """
    Get schema details by ID
    
    Args:
        schema_id: The schema ID
        
    Returns:
        Schema details as a dictionary
    """
    return await schema_service.get_schema_details(schema_id)

async def get_available_schemas() -> List[str]:
    """
    Get list of all available schema IDs
    
    Returns:
        List of schema IDs
    """
    return await schema_service.get_available_schemas()
