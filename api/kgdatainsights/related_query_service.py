"""
Related Query Service for Knowledge Graph Insights
Generates suggestions to broaden or narrow analysis based on current query
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple
import re
from collections import defaultdict

# Try importing the schema service for dynamic schema loading
try:
    # When imported as a module
    from api.kgdatainsights.schema_service import get_schema_details
except ImportError:
    # When run directly
    try:
        from .schema_service import get_schema_details
    except ImportError:
        # If schema_service is not available, we'll use a fallback method
        logger = logging.getLogger(__name__)
        logger.warning("schema_service module not found, using fallback schema loading")
        get_schema_details = None

# Setup logging
logger = logging.getLogger(__name__)

class RelatedQueryService:
    """
    Service for generating related queries to help users explore the knowledge graph
    Provides both broader and narrower query suggestions
    """
    
    def __init__(self):
        """Initialize the related query service"""
        self.query_history = defaultdict(int)  # Track query frequency
        self.entity_patterns = {}  # Cache entity patterns by schema
        self.schema_cache = {}  # Cache schema details
        self.initialization_complete = False
        self._initialization_lock = asyncio.Lock()
        self._preloaded_default_patterns = False
        
        # Preload some basic patterns to avoid completely empty results
        self.entity_patterns["default"] = {
            "node_labels": ["Machine", "Part", "Worker", "Process", "Defect", "Batch", "Order", "Material"],
            "relationships": ["contains", "operates", "produces", "uses", "requires", "reports", "processes"],
            "properties": ["name", "status", "quantity", "date", "location", "category", "type", "id", "code"]
        }
        self._preloaded_default_patterns = True
    
    async def initialize_service(self):
        """Initialize the service by preloading schemas and preparing patterns"""
        # Use a lock to prevent multiple initializations
        async with self._initialization_lock:
            if self.initialization_complete:
                logger.info("Service already initialized, skipping")
                return
                
            try:
                logger.info("Starting related query service initialization")
                
                # Get list of available schemas
                available_schemas = await self._get_available_schemas()
                
                if available_schemas:
                    logger.info(f"Preloading {len(available_schemas)} schemas")
                    
                    # Preload schemas one by one to avoid overwhelming the system
                    for schema_id in available_schemas:
                        if schema_id not in self.entity_patterns:
                            await self._load_schema_patterns(schema_id)
                    
                    logger.info(f"Successfully preloaded {len(self.entity_patterns)} schemas")
                else:
                    logger.warning("No schemas available for preloading")
                    # Make sure we have at least the default schema
                    if "default" not in self.entity_patterns:
                        await self._load_schema_patterns("default")
                
                self.initialization_complete = True
                logger.info("Related query service initialization complete")
            except Exception as e:
                logger.error(f"Error during service initialization: {e}")
                # Still mark as initialized to avoid repeated attempts
                self.initialization_complete = True
    
    async def _get_available_schemas(self) -> List[str]:
        """Get list of available schema IDs"""
        try:
            if get_schema_details and hasattr(get_schema_details, 'get_available_schemas'):
                # Use schema service if it has the method
                return await get_schema_details.get_available_schemas()
            
            # Fallback to a default list if schema service doesn't support listing
            return ["default", "manufacturing", "supply_chain"]
        except Exception as e:
            logger.error(f"Error getting available schemas: {e}")
            return ["default"]
        
    async def get_related_queries(
        self, 
        schema_id: str, 
        query_text: str,
        user_id: Optional[str] = None,
        max_suggestions: int = 5
    ) -> Dict[str, List[str]]:
        """
        Generate related queries for a given query
        
        Args:
            schema_id: The schema ID
            query_text: The current query text
            user_id: Optional user ID for personalization
            max_suggestions: Maximum number of suggestions per category
            
        Returns:
            Dictionary with 'broader' and 'narrower' query suggestions
        """
        logger.info(f"Generating related queries for: '{query_text}' (schema: {schema_id})")
        
        # Initialize results
        results = {
            "broader": [],
            "narrower": []
        }
        
        if not query_text or len(query_text.strip()) < 3:
            logger.info("Query too short, returning empty suggestions")
            return results
            
        # Start lazy initialization if needed
        if not self.initialization_complete and not self._initialization_lock.locked():
            # Start the initialization in the background if not already running
            asyncio.create_task(self.initialize_service())
            
        try:
            # Make sure we have schema patterns for this schema
            if schema_id not in self.entity_patterns and self._preloaded_default_patterns:
                # Use default patterns first to ensure immediate response
                self.entity_patterns[schema_id] = self.entity_patterns["default"]
                # Load actual schema patterns in the background
                asyncio.create_task(self._load_schema_patterns(schema_id))
            elif schema_id not in self.entity_patterns:
                # If we don't have default patterns, load synchronously
                await self._load_schema_patterns(schema_id)
            
            # Extract key entities from the query
            entities = await self._extract_entities(schema_id, query_text)
            logger.info(f"Extracted entities: {entities}")
            
            # Generate broader queries (more general)
            broader_queries = await self._generate_broader_queries(schema_id, query_text, entities)
            results["broader"] = broader_queries[:max_suggestions]
            
            # Generate narrower queries (more specific)
            narrower_queries = await self._generate_narrower_queries(schema_id, query_text, entities)
            results["narrower"] = narrower_queries[:max_suggestions]
            
            # Add to query history for future reference
            if query_text.strip():
                self.query_history[query_text.strip()] += 1
                
            logger.info(f"Generated {len(results['broader'])} broader and {len(results['narrower'])} narrower queries")
            return results
            
        except Exception as e:
            logger.error(f"Error generating related queries: {e}")
            return results
    
    async def _extract_entities(self, schema_id: str, query_text: str) -> List[Dict[str, Any]]:
        """
        Extract entities from the query text
        
        Args:
            schema_id: The schema ID
            query_text: The query text
            
        Returns:
            List of entity dictionaries with type and value
        """
        # Cache entity patterns by schema to avoid recomputation
        if schema_id not in self.entity_patterns:
            # Load entity patterns from schema dynamically
            await self._load_schema_patterns(schema_id)
            
        entities = []
        
        # Extract node labels using patterns from the schema
        if 'node_labels' in self.entity_patterns.get(schema_id, {}):
            node_labels = self.entity_patterns[schema_id]['node_labels']
            if node_labels:
                node_pattern = r'\b(' + '|'.join(node_labels) + r')s?\b'
                node_matches = re.finditer(node_pattern, query_text, re.IGNORECASE)
                for match in node_matches:
                    entities.append({
                        "type": "node_label",
                        "value": match.group(1),
                        "position": match.start()
                    })
                logger.info(f"Extracted {len([e for e in entities if e['type'] == 'node_label'])} node labels")
            
        # Extract relationship types using patterns from the schema
        if 'relationships' in self.entity_patterns.get(schema_id, {}):
            relationships = self.entity_patterns[schema_id]['relationships']
            if relationships:
                rel_pattern = r'\b(' + '|'.join(relationships) + r')\b'
                rel_matches = re.finditer(rel_pattern, query_text, re.IGNORECASE)
                for match in rel_matches:
                    entities.append({
                        "type": "relationship",
                        "value": match.group(1),
                        "position": match.start()
                    })
                logger.info(f"Extracted {len([e for e in entities if e['type'] == 'relationship'])} relationships")
            
        # Extract property names using patterns from the schema
        if 'properties' in self.entity_patterns.get(schema_id, {}):
            properties = self.entity_patterns[schema_id]['properties']
            if properties:
                prop_pattern = r'\b(' + '|'.join(properties) + r')\b'
                prop_matches = re.finditer(prop_pattern, query_text, re.IGNORECASE)
                for match in prop_matches:
                    entities.append({
                        "type": "property",
                        "value": match.group(1),
                        "position": match.start()
                    })
                logger.info(f"Extracted {len([e for e in entities if e['type'] == 'property'])} properties")
            
        # Extract numerical constraints
        num_matches = re.finditer(r'\b(more than|less than|greater than|equal to|at least|at most)\s+(\d+)\b', query_text, re.IGNORECASE)
        for match in num_matches:
            entities.append({
                "type": "numerical_constraint",
                "value": match.group(0),
                "operator": match.group(1),
                "number": match.group(2),
                "position": match.start()
            })
            
        # Extract temporal references
        time_matches = re.finditer(r'\b(this month|last month|this year|last year|today|yesterday|last week|this week)\b', query_text, re.IGNORECASE)
        for match in time_matches:
            entities.append({
                "type": "temporal",
                "value": match.group(1),
                "position": match.start()
            })
            
        return entities
    
    async def _load_schema_patterns(self, schema_id: str) -> None:
        """
        Load entity patterns from schema dynamically
        
        Args:
            schema_id: The schema ID
        """
        # Try to load schema from database using schema service
        schema_loaded = False
        
        try:
            if get_schema_details:
                # Check schema cache first
                if schema_id in self.schema_cache:
                    schema_details = self.schema_cache[schema_id]
                    logger.info(f"Using cached schema for {schema_id}")
                else:
                    # Get schema details from the service
                    schema_details = await get_schema_details(schema_id)
                    if schema_details:
                        self.schema_cache[schema_id] = schema_details
                        logger.info(f"Loaded schema from database for {schema_id}")
                
                if schema_details:
                    # Extract node labels, relationships, and properties
                    node_labels = []
                    relationships = []
                    properties = []
                    
                    # Process nodes
                    for node in schema_details.get('nodes', []):
                        if 'label' in node:
                            node_labels.append(node['label'])
                        
                        # Add node properties
                        for prop in node.get('properties', []):
                            if 'name' in prop and prop['name'] not in properties:
                                properties.append(prop['name'])
                    
                    # Process relationships
                    for rel in schema_details.get('relationships', []):
                        if 'type' in rel:
                            relationships.append(rel['type'])
                        
                        # Add relationship properties
                        for prop in rel.get('properties', []):
                            if 'name' in prop and prop['name'] not in properties:
                                properties.append(prop['name'])
                    
                    # Save the extracted patterns
                    self.entity_patterns[schema_id] = {
                        "node_labels": node_labels,
                        "relationships": relationships,
                        "properties": properties
                    }
                    
                    schema_loaded = True
                    logger.info(f"Extracted {len(node_labels)} node labels, {len(relationships)} relationships, and {len(properties)} properties from schema {schema_id}")
        except Exception as e:
            logger.error(f"Error loading schema details for {schema_id}: {e}")
            logger.error(f"Using fallback schema patterns")
        
        # Fallback to default patterns if schema could not be loaded
        if not schema_loaded:
            self.entity_patterns[schema_id] = {
                "node_labels": ["Machine", "Part", "Worker", "Process", "Defect", "Batch", "Order", "Material"],
                "relationships": ["contains", "operates", "produces", "uses", "requires", "reports", "processes"],
                "properties": ["name", "status", "quantity", "date", "location", "category", "type", "id", "code"]
            }
            logger.warning(f"Using fallback schema patterns for {schema_id}")
    
    async def _generate_broader_queries(
        self, 
        schema_id: str, 
        query_text: str, 
        entities: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Generate broader (more general) queries
        
        Args:
            schema_id: The schema ID
            query_text: The current query text
            entities: Extracted entities
            
        Returns:
            List of broader query suggestions
        """
        broader_queries = []
        
        # Strategy 1: Remove specific constraints
        if any(e["type"] == "numerical_constraint" for e in entities):
            # Remove numerical constraints to make query broader
            for entity in entities:
                if entity["type"] == "numerical_constraint":
                    broader_query = query_text.replace(entity["value"], "")
                    broader_query = re.sub(r'\s+', ' ', broader_query).strip()
                    broader_queries.append(f"All {broader_query}")
        
        # Strategy 2: Remove temporal constraints
        if any(e["type"] == "temporal" for e in entities):
            # Remove time constraints to make query broader
            for entity in entities:
                if entity["type"] == "temporal":
                    broader_query = query_text.replace(entity["value"], "")
                    broader_query = re.sub(r'\s+', ' ', broader_query).strip()
                    broader_queries.append(f"All time periods: {broader_query}")
        
        # Strategy 3: Focus on higher-level entities
        node_entities = [e for e in entities if e["type"] == "node_label"]
        if node_entities:
            for node in node_entities:
                # Create query focusing on this entity type
                broader_query = f"Show all {node['value']}s"
                broader_queries.append(broader_query)
                
                # Add additional context if available
                if "status" in query_text.lower():
                    broader_queries.append(f"Distribution of {node['value']}s by status")
                if "location" in query_text.lower():
                    broader_queries.append(f"Distribution of {node['value']}s by location")
        
        # Strategy 4: Suggest related analysis
        if "defect" in query_text.lower() or "issue" in query_text.lower():
            broader_queries.append("Show all types of defects across production")
            broader_queries.append("Compare defect rates across different machines")
        
        if "performance" in query_text.lower() or "efficiency" in query_text.lower():
            broader_queries.append("Overall factory performance metrics")
            broader_queries.append("Compare performance across all production lines")
        
        return list(set(broader_queries))  # Remove duplicates
    
    async def _generate_narrower_queries(
        self, 
        schema_id: str, 
        query_text: str, 
        entities: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Generate narrower (more specific) queries
        
        Args:
            schema_id: The schema ID
            query_text: The current query text
            entities: Extracted entities
            
        Returns:
            List of narrower query suggestions
        """
        narrower_queries = []
        
        # Strategy 1: Add time constraints
        if not any(e["type"] == "temporal" for e in entities):
            narrower_queries.append(f"{query_text} from this month")
            narrower_queries.append(f"{query_text} from last week")
        
        # Strategy 2: Add specific node types
        node_entities = [e for e in entities if e["type"] == "node_label"]
        if node_entities:
            for node in node_entities:
                # Add property filters
                narrower_queries.append(f"{query_text} with high priority")
                narrower_queries.append(f"{query_text} in critical status")
                
                # Add relationship to other nodes
                if node["value"] == "Machine":
                    narrower_queries.append(f"{query_text} that produced defects")
                    narrower_queries.append(f"{query_text} with efficiency below 90%")
                elif node["value"] == "Worker":
                    narrower_queries.append(f"{query_text} who operated Machine-01")
                    narrower_queries.append(f"{query_text} with certification level A")
                elif node["value"] == "Process":
                    narrower_queries.append(f"{query_text} with more than 5 steps")
                    narrower_queries.append(f"{query_text} requiring special materials")
        else:
            # If no specific node type, suggest adding one
            narrower_queries.append(f"{query_text} for Machine-01")
            narrower_queries.append(f"{query_text} in Assembly department")
        
        # Strategy 3: Add numerical constraints
        if not any(e["type"] == "numerical_constraint" for e in entities):
            if "quantity" in query_text.lower() or "count" in query_text.lower():
                narrower_queries.append(f"{query_text} greater than 100")
                narrower_queries.append(f"{query_text} less than 50")
            elif "efficiency" in query_text.lower() or "rate" in query_text.lower():
                narrower_queries.append(f"{query_text} above 95%")
                narrower_queries.append(f"{query_text} below 80%")
        
        # Strategy 4: Suggest comparative analysis
        if node_entities:
            narrower_queries.append(f"Compare {query_text} between departments")
            narrower_queries.append(f"Show {query_text} trend over time")
        
        return list(set(narrower_queries))  # Remove duplicates

# Create schema service stub if not available
if 'get_schema_details' not in globals() or get_schema_details is None:
    async def get_schema_details(schema_id: str) -> Dict[str, Any]:
        logger.warning(f"Using stub schema service for {schema_id}")
        return None
    
    # Add the get_available_schemas method to the stub
    get_schema_details.get_available_schemas = lambda: asyncio.Future().set_result(["default"])

# Create a singleton instance
related_query_service = RelatedQueryService()
