import os
import json
import time
import hashlib
import threading
import traceback
import re
import asyncio
from pathlib import Path
from uuid import uuid4
from typing import Dict, Any, Optional, Callable
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from dotenv import load_dotenv
from langchain.chains import GraphCypherQAChain
from langchain.prompts import ChatPromptTemplate, PromptTemplate
from langchain_neo4j import (
    Neo4jChatMessageHistory,
    Neo4jGraph
)

from .cache import Cache
from .cache import cacheable

from ...kginsights.database_api import get_database_config, parse_connection_params
from ...models import Schema
from ...db_config import SessionLocal  
from .csv_to_cypher_generator import CsvToCypherGenerator
from ...utils.llm_provider import LLMProvider, LLMConstants

# Load environment variables
load_dotenv()

# Output directories
OUTPUT_DIR = Path("runtime-data/output/kgdatainsights")
SCHEMA_DIR = OUTPUT_DIR / "schema"
PROMPT_DIR = OUTPUT_DIR / "prompts"
QUERY_DIR = OUTPUT_DIR / "queries"  # This matches QUERIES_DIR in data_insights_api.py

# Create directories if they don't exist
SCHEMA_DIR.mkdir(parents=True, exist_ok=True)
PROMPT_DIR.mkdir(parents=True, exist_ok=True)

class SchemaAwareGraphAssistant:
    """
    Enhanced Graph Assistant that automatically manages schemas and prompts.
    Extends the functionality of Neo4jGraphChatAssistant by adding schema and prompt management.
    """
    def __init__(self, db_id: str, schema_id: str, schema: str, session_id: str = None):
        """
        Initialize the Schema-Aware Graph Assistant.
        
        Args:
            db_id: The ID of the Neo4j database to query
            schema_id: The ID of the schema being used
            schema: The schema content as a string or dict
            session_id: Optional session ID for chat history, generated if not provided
        """
        print(f"TRACE: Before SchemaAwareGraphAssistant.__init__ for {db_id}")

        # Initialize basic properties regardless of gen_schema flag
        self.db_id = db_id
        self.schema_id = schema_id
        self.schema = json.loads(schema) if isinstance(schema, str) else schema
        self.session_id = session_id or f"session_{uuid4()}"
        self.formatted_schema = None
        
        # Get the schema CSV path first (unresolved)
        db = SessionLocal()
        try:
            schema_record = db.query(Schema).filter(Schema.id == self.schema_id).first()
            self.csv_file_path = schema_record.csv_file_path if schema_record else None
        finally:
            db.close()
        
        print(f"TRACE: Before _format_schema() for {self.db_id}")
        self._format_schema()
        print(f"TRACE: After _format_schema() for {self.db_id}")
        
        # After formatting schema, use our enhanced path resolution logic
        # We don't need _get_csv_path anymore as _resolve_data_path is more robust
        resolved_path = self._resolve_data_path()
        if resolved_path:
            self.csv_file_path = resolved_path
            print(f"TRACE: CSV file path resolved to: {self.csv_file_path}")
        else:
            print(f"WARNING: Could not resolve CSV file path for schema {self.schema_id}")
        
        # If gen_schema is True, skip expensive initializations
        print(f"TRACE: Initializing in schema generation mode for {self.db_id}")
        print(f"Initializing in schema generation mode - skipping LLM, graph connection, and chain setup")
        
        # Initialize minimal components needed for schema operations
        print(f"TRACE: Before _get_connection_params() for {self.db_id}")
        self.connection_params = self._get_connection_params()
        print(f"TRACE: After _get_connection_params() for {self.db_id}")
        
        print(f"TRACE: Before Cache initialization for {self.db_id}")
        self.cache = Cache()
        print(f"TRACE: After Cache initialization for {self.db_id}")
        
        print(f"TRACE: Before _ensure_prompt() for {self.db_id}")
        self._ensure_prompt()
        print(f"TRACE: After _ensure_prompt() for {self.db_id}")

        # Start async initialization in the background
        self.initialization_complete = False
        self.initialization_error = None
        self.llm = None
        self.graph = None
        self.history = None
        self.chain = None
        
        # Start the async initialization
        asyncio.create_task(self._initialize_async())

    async def _initialize_async(self):
        """
        Asynchronous initialization of LLM, graph connection, and chain.
        This runs in the background to avoid blocking object construction.
        """
        try:
            print(f"DEBUG: Starting async initialization for {self.db_id} with schema {self.schema_id}")
            
            # Initialize LLM
            self.llm = LLMProvider.get_llm(
                provider_name=LLMConstants.Providers.OPENAI, 
                model_name=LLMConstants.OpenAIModels.DEFAULT, 
                temperature=0.0
                # Note: request_timeout is handled separately in _invoke_llm_with_retry
            )
            
            # Load the custom prompts for this source
            self._load_prompts()
            
            # Initialize Neo4j Graph connection
            # Import the correct GraphStore implementation
            from langchain_community.graphs import Neo4jGraph as CommunityNeo4jGraph
            
            self.graph = CommunityNeo4jGraph(
                url=self.connection_params.get("uri"),
                username=self.connection_params.get("username"),
                password=self.connection_params.get("password"),
                database=self.connection_params.get("database", "neo4j"),
                enhanced_schema=True,
                refresh_schema=False  # Disable schema refresh to avoid APOC dependency
            )
            
            # Initialize Neo4j-backed chat history
            self.history = Neo4jChatMessageHistory(
                session_id=self.session_id,
                url=self.connection_params.get("uri"),
                username=self.connection_params.get("username"),
                password=self.connection_params.get("password"),
                database=self.connection_params.get("database", "neo4j")
            )
            
            # Initialize QA chain with Neo4j optimizations using modular LangChain pattern
            print(f"DEBUG: Initializing GraphCypherQAChain using langchain_community pattern")
            
            # Import the correct GraphCypherQAChain implementation
            from langchain_community.chains.graph_qa.cypher import GraphCypherQAChain as CommunityGraphCypherQAChain
            
            # Create a structured chain configuration dictionary
            chain_config = {
                "llm": self.llm,
                "graph": self.graph,
                "verbose": True,
                "return_intermediate_steps": True,
                "allow_dangerous_requests": True
            }
            
            # Ensure schema is properly parsed into a dict
            try:
                # self.schema can be a dict (already parsed) or a string (needs parsing)
                if isinstance(self.schema, str):
                    # json.loads converts a string to a Python object (dict)
                    db_schema = json.loads(self.schema)
                else:
                    # Already a dict, use as is
                    db_schema = self.schema
                    
                print(f"DEBUG: Schema information type: {type(db_schema).__name__}")
                # Only proceed with validation if we have a proper dict
                if db_schema and isinstance(db_schema, dict):
                    # Extract node and relationship schemas if available
                    node_props = {}
                    rel_props = {}
                
                    # Extract schema information based on the structure we have
                    if 'nodes' in db_schema:
                        for node in db_schema.get('nodes', []):
                            if 'label' in node and 'properties' in node:
                                # Extract property names from the properties object
                                # Properties are in format {"prop_name": "type"}
                                node_props[node['label']] = list(node['properties'].keys())
                    
                    if 'relationships' in db_schema:
                        for rel in db_schema.get('relationships', []):
                            if 'type' in rel:
                                # Extract property names from the properties object 
                                # Properties are in format {"prop_name": "value"}
                                rel_props[rel['type']] = list(rel.get('properties', {}).keys())
                    
                    # Only enable schema validation if we have actual schema data
                    if node_props or rel_props:
                        print("DEBUG: Enabling Cypher validation with schema information")
                        chain_config["validate_cypher"] = True
                        
                        # Prepare the schema for validation
                        formatted_schema = {
                            "node_props": node_props,
                            "rel_props": rel_props
                        }
                        
                        # The structured_schema needs to be directly available to the graph
                        # Create a structured schema with relationships in the format expected by CypherQueryCorrector
                        structured_schema = {
                            "nodes": [],
                            "relationships": []
                        }
                        
                        # Extract relationship info with the correct field names
                        # CypherQueryCorrector expects 'start', 'type', and 'end' fields
                        if 'relationships' in db_schema:
                            for rel in db_schema.get('relationships', []):
                                if all(k in rel for k in ['startNode', 'type', 'endNode']):
                                    # Map from our schema format to the expected format
                                    structured_schema['relationships'].append({
                                        "start": rel['startNode'],
                                        "type": rel['type'],
                                        "end": rel['endNode']
                                    })
                        
                        print(f"DEBUG: Structured schema: {structured_schema}")
                        
                        # For Cypher validation to work, the structured_schema needs to be 
                        # an attribute of the graph object itself
                        # This is because CommunityGraphCypherQAChain accesses it via:
                        # kwargs["graph"].structured_schema
                        
                        # Attach the structured schema to the graph object
                        self.graph.structured_schema = structured_schema
                        
                        # Add node/rel properties to the config
                        chain_config["schema"] = formatted_schema

                    else:
                        # Don't enable validation if we don't have schema data
                        print("DEBUG: Disabling Cypher validation due to missing schema information")
                        chain_config["validate_cypher"] = False
                else:
                    # Don't enable validation if schema is not available
                    print("DEBUG: Disabling Cypher validation due to missing schema information")
                    chain_config["validate_cypher"] = False
            except Exception as e:
                print(f"ERROR: Failed to process schema: {e}")
                print(f"DEBUG: Error details: {traceback.format_exc()}")
                print("DEBUG: Disabling Cypher validation due to schema processing error")
                chain_config["validate_cypher"] = False
            
            # Only add prompts if they are properly loaded
            if hasattr(self, 'cypher_prompt') and self.cypher_prompt:
                print('DEBUG: cypher prompt found')
                chain_config["cypher_prompt"] = self.cypher_prompt
            
            # QA prompt requires special handling because it relies on intermediate variables
            # that are generated by the chain itself (query and response)
            if hasattr(self, 'qa_prompt') and self.qa_prompt:
                print('DEBUG: qa prompt found - wrapping to handle intermediate variables')
                
                # We need to modify how the QA prompt is passed to work with GraphCypherQAChain
                # The chain internally generates 'query' and 'response' variables
                # Get the template string from our ChatPromptTemplate
                if hasattr(self.qa_prompt, 'template') and hasattr(self.qa_prompt.template, 'template'):
                    qa_template_str = self.qa_prompt.template.template
                    print(f"DEBUG: Using template string: {qa_template_str[:50]}...")
                    
                    # Create a proper PromptTemplate that GraphCypherQAChain can work with
                    # Based on the error, make sure we include 'query' as an input variable
                    # The langchain_neo4j GraphCypherQAChain specifically expects 'query' not 'question'
                    qa_prompt_template = PromptTemplate(
                        template=qa_template_str,
                        # Both 'query' and 'question' can refer to the same user input
                        # but the chain uses 'query' internally for the user question and for the Cypher query
                        input_variables=["query", "context"]
                    )
                    chain_config["qa_prompt"] = qa_prompt_template
                else:
                    print(f"DEBUG: Using original QA prompt - may cause errors")
                    chain_config["qa_prompt"] = self.qa_prompt
            
            # Initialize with the validated configuration using the community implementation
            self.chain = CommunityGraphCypherQAChain.from_llm(**chain_config)
            print(f"DEBUG: Successfully initialized GraphCypherQAChain")
            
            # Mark initialization as complete
            self.initialization_complete = True
            print(f"DEBUG: Async initialization completed successfully for {self.db_id}")
            
        except Exception as e:
            self.initialization_error = str(e)
            print(f"ERROR: Async initialization failed: {str(e)}")
            print(f"DEBUG: Error details: {traceback.format_exc()}")
    
    def _get_csv_path(self):
        """
        Read csv path from Schema table
        """
        db = SessionLocal()
        schema = db.query(Schema).filter(Schema.id == self.schema_id).first()
        return schema.csv_file_path

    def _get_connection_params(self) -> dict:
        """
        Get connection parameters for the specified database ID from the database API.
        
        Returns:
            dict: Connection parameters including uri, username, password, and database
        """
        try:
            # Get the full database configuration
            config = get_database_config()
            
            # Get the specific graph configuration
            graph_config = config.get(self.db_id, {})
            
            if not graph_config:
                print(f"WARNING: No configuration found for database '{self.db_id}' in neo4j.databases.yaml")
                # Try to use default configuration if available
                graph_config = config.get("default", {})
                if graph_config:
                    print(f"INFO: Using 'default' Neo4j configuration as fallback for '{self.db_id}'")
                else:
                    print(f"ERROR: No fallback configuration found for '{self.db_id}'")
            
            # Parse the connection parameters
            params = parse_connection_params(graph_config)
            
            # Validate and log the parameters
            if not params:
                print(f"ERROR: Failed to parse connection parameters for '{self.db_id}'")
                return {
                    "uri": None,
                    "username": None,
                    "password": None,
                    "database": None
                }
            
            # Log the connection parameters (hide password)
            conn_debug = {
                "uri": params.get("uri"),
                "username": params.get("username"),
                "database": params.get("database"),
                "password": "*****" if params.get("password") else None
            }
            print(f"DEBUG: Neo4j connection parameters for '{self.db_id}': {conn_debug}")
            
            # Validate the essential parameters
            if not params.get("uri"):
                print(f"ERROR: Missing Neo4j URI for database '{self.db_id}'")
            
            return params
            
        except Exception as e:
            print(f"ERROR: Failed to get connection params for {self.db_id}: {str(e)}")
            print(f"DEBUG: Stack trace: {traceback.format_exc()}")
            return {
                "uri": None,
                "username": None,
                "password": None,
                "database": None
            }
        
    def _ensure_prompt(self) -> None:
        """Check if prompts exist, validate generation_id, create and save if needed."""
        print(f"TRACE: _ensure_prompt started for db_id={self.db_id}, schema_id={self.schema_id}")
        prompt_file = PROMPT_DIR / f"prompt_{self.db_id}_{self.schema_id}.json"
        query_file = QUERY_DIR / f"{self.schema_id}_queries.json" 
        print(f"TRACE: Prompt file path: {prompt_file}")
        print(f"TRACE: Query file path: {query_file}")

        regenerate_prompts = False
        current_generation_id = None
        existing_prompts = None
        domain = None

        # 1. Fetch current generation_id and domain from DB
        print(f"TRACE: Starting DB fetch for generation_id, schema_id={self.schema_id}")
        db = None # Initialize db to None
        try:
            print(f"TRACE: Creating DB session")
            db = SessionLocal()
            print(f"TRACE: Querying Schema table for schema_id={self.schema_id}")
            schema_record = db.query(Schema).filter(Schema.id == self.schema_id).first()
            if schema_record:
                print(f"TRACE: Schema record found, checking generation_id")
                current_generation_id = schema_record.generation_id
                domain = schema_record.domain  # Get the domain from the schema record
                print(f"TRACE: Domain from schema record: {domain}")
                if not current_generation_id:
                    print(f"Warning: Schema record found for {self.schema_id}, but generation_id is missing. Will regenerate prompts.")
                    regenerate_prompts = True
                else:
                    print(f"DEBUG: Schema record found for {self.schema_id} with generation_id {current_generation_id}")    
            else:
                print(f"Warning: Schema record not found for schema_id {self.schema_id}. Cannot verify prompt generation ID. Will regenerate prompts.")
                regenerate_prompts = True # If schema record is missing, prompts might be invalid.
        except Exception as e:
            print(f"Error fetching schema generation_id: {e}. Proceeding, may regenerate prompts.")
            print(f"TRACE: Exception details: {traceback.format_exc()}")
            # If DB access fails, we should probably regenerate prompts
            regenerate_prompts = True
        finally:
            if db:
                print(f"TRACE: Closing DB session")
                db.close()

        # 2. Check prompt file and generation_id if regeneration not already decided
        if not regenerate_prompts and prompt_file.exists():
            try:
                with open(prompt_file, "r") as f:
                    existing_prompts = json.load(f)
                
                file_generation_id = existing_prompts.get("generation_id")

                if not current_generation_id: 
                     # This case should be handled above by setting regenerate_prompts=True
                     print(f"Error: Logic flaw - current_generation_id missing but regeneration wasn't triggered.")
                     regenerate_prompts = True 
                elif file_generation_id == current_generation_id:
                    print(f"Prompt file {prompt_file} found and generation_id matches. Loading prompts.")
                    # Load prompts later, set flag to false
                    regenerate_prompts = False 
                else:
                    print(f"Prompt file {prompt_file} found, but generation_id mismatch (File: {file_generation_id}, DB: {current_generation_id}). Regenerating prompts.")
                    regenerate_prompts = True
            except (json.JSONDecodeError, KeyError, Exception) as e:
                print(f"Error reading or parsing prompt file {prompt_file}: {e}. Regenerating prompts.")
                regenerate_prompts = True
        elif not prompt_file.exists():
             print(f"Prompt file for db '{self.db_id}' and schema '{self.schema_id}' not found. Creating prompts...")
             regenerate_prompts = True

        # 3. Regenerate and save if needed
        if regenerate_prompts:
            print("Generating new prompts...")
            print(f"TRACE: Starting _generate_prompts() for db_id={self.db_id}, schema_id={self.schema_id}")
            # Generate prompts based on schema
            try:
                # Check if we should use domain-specific sample queries
                use_domain_specific_queries = False
                domain_specific_queries = []
                domain_queries_file = None
                
                # Check if domain contains telecom_churn or foam_factory
                if domain:
                    domain_lower = domain.lower()
                    if 'telecom_churn' in domain_lower:
                        print(f"Using domain-specific sample queries for telecom_churn domain")
                        domain_queries_file = os.path.join(os.path.dirname(__file__), 'domain_queries', 'telecom_churn_queries.json')
                        use_domain_specific_queries = True
                    elif 'foam_factory' in domain_lower:
                        print(f"Using domain-specific sample queries for foam_factory domain")
                        domain_queries_file = os.path.join(os.path.dirname(__file__), 'domain_queries', 'foam_factory_queries.json')
                        use_domain_specific_queries = True
                
                # Generate prompts - pass a flag indicating if domain-specific queries will be used
                prompts = self._generate_prompts(skip_sample_queries_generation=use_domain_specific_queries) # Assumes this returns a dict
                
                # If we should use domain-specific queries, load them from the JSON file
                if use_domain_specific_queries and domain_queries_file and os.path.exists(domain_queries_file):
                    try:
                        with open(domain_queries_file, 'r') as f:
                            domain_data = json.load(f)
                            domain_specific_queries = domain_data.get('queries', [])
                        
                        if domain_specific_queries:
                            # Replace the LLM-generated sample queries with domain-specific ones
                            print(f"Replacing LLM-generated sample queries with domain-specific queries for {domain}")
                            prompts["sample_queries"] = domain_specific_queries
                    except Exception as e:
                        print(f"Error loading domain-specific queries from {domain_queries_file}: {e}")
                        print(f"TRACE: Exception details: {traceback.format_exc()}")
                        # Continue with LLM-generated queries if there's an error
                
                print(f"TRACE: Successfully completed _generate_prompts()")
            except Exception as e:
                print(f"TRACE: Error in _generate_prompts(): {str(e)}")
                print(f"TRACE: Exception details: {traceback.format_exc()}")
                raise
            
            # Add the current generation_id (if available and valid)
            if current_generation_id:
                prompts["generation_id"] = current_generation_id
            else:
                 print(f"Warning: Could not retrieve valid current generation_id for schema {self.schema_id}. Saving prompts without generation_id.")
                 prompts.pop("generation_id", None) # Ensure it's not stale

            # Save the prompts to file
            try:
                print(f"TRACE: Creating prompt directory: {PROMPT_DIR}")
                PROMPT_DIR.mkdir(parents=True, exist_ok=True) # Ensure directory exists
                print(f"TRACE: Saving prompts to file: {prompt_file}")
                with open(prompt_file, "w") as f:
                    json.dump(prompts, f, indent=2)
                print(f"Prompts saved to {prompt_file}")

                print(f"TRACE: Creating query directory: {QUERY_DIR}")
                QUERY_DIR.mkdir(parents=True, exist_ok=True) # Ensure directory exists
                print(f"TRACE: Saving queries to file: {query_file}")
                with open(query_file, "w") as f:
                    # Format the sample queries to match what the API expects
                    # The API expects a dictionary with categories as keys and lists of queries as values
                    formatted_queries = {
                        "general": [],
                        "relationships": [],
                        "domain": []
                    }
                    
                    # Add each sample query to an appropriate category based on content analysis
                    for i, query in enumerate(prompts["sample_queries"]):
                        query_lower = query.lower()
                        
                        # Determine the best category based on query content
                        if any(keyword in query_lower for keyword in ["relation", "connect", "link", "between", "path"]):
                            category = "relationships"
                        elif any(keyword in query_lower for keyword in ["domain", "specific", "industry", "field", "area"]):
                            category = "domain"
                        else:
                            category = "general"  # Default category
                        
                        formatted_queries[category].append({
                            "id": f"{category}_{len(formatted_queries[category])+1}",
                            "query": query,
                            "description": f"Sample query for {domain if domain else 'graph'} #{i+1}"
                        })
                    
                    json.dump(formatted_queries, f, indent=2)
                print(f"Queries saved to {query_file}")

            except Exception as e:
                print(f"Error saving prompts to {prompt_file}: {e}")
                print("Warning: Prompts generated but failed to save to file. Using in-memory prompts for this session.")
        
    def _generate_prompts(self, skip_sample_queries_generation=False) -> Dict[str, Any]:
        """Generate custom prompts using LLM based on the schema
        
        Args:
            skip_sample_queries_generation: If True, don't generate sample queries with LLM
                                          as they will be replaced with domain-specific ones
        """
        
        # Define a system prompt for prompt generation
        cypher_system_prompt = """
        You are a Knowledge Graph expert tasked with creating optimal prompts for Neo4j graph database interactions. 
        You're being given a Neo4j graph schema in JSON format.
        
        Your job is to analyze the schema and generate a Cypher query generation prompt that will help an LLM convert natural language questions to Cypher queries
        1. Do not include any additional text other than the prompt template in required output format
        2. Do not include duplicate output sections
        3. The prompts should be tailored to the specific domain and structure of the knowledge graph as defined in the schema.
        """

        # Define a system prompt for prompt generation
        qa_system_prompt = """
        You are a Knowledge Graph expert tasked with creating optimal prompts for Neo4j graph database interactions. 
        You're being given a Neo4j graph schema in JSON format.
        
        Your job is to analyze the schema and generate a QA prompt that will help an LLM interpret Cypher query results and answer user questions
        1. Do not include any additional text other than the prompt template in required output format
        2. Do not include duplicate output sections
        3. The prompts should be tailored to the specific domain and structure of the knowledge graph as defined in the schema.
        """
        
        sample_queries_system_prompt = """
        You are a Knowledge Graph expert tasked with creating optimal prompts for Neo4j graph database interactions. 
        You're being given a Neo4j graph schema in JSON format.
        
        Your job is to analyze the schema, given data and generate a sample queries generation prompt that will help an LLM generate sample queries based on the graph schema
        1. Do not include any additional text other than the prompt template in required output format
        2. Do not include duplicate output sections
        3. The prompts should be tailored to the specific domain and structure of the knowledge graph as defined in the schema.
        """

        # Define the prompt for generating the Cypher generation prompt
        # IMPORTANT: Updated to use 'query' instead of 'question' for compatibility with GraphCypherQAChain
        cypher_prompt_instruction = """
        Create a prompt template for generating Neo4j Cypher queries.
        
        The template should:
        1. Be tailored to the specific domain and structure of this knowledge graph
        2. Include specific node labels, relationship types, and properties from the schema
        3. Provide guidance on Neo4j Cypher best practices
        4. Include examples of good question patterns based on this schema
        6. The output must ONLY contain the executable Cypher query string without quotes or backticks around it
        7. VERY IMPORTANT: While generating Cypher queries, embed values directly. DO NOT use parameters like $name.
           - For string values, use single quotes: `{{name: 'Example Name'}}` (Note the double braces for the example itself!)
           - For numeric values, use them directly: `{{born: 1234}}` (Note the double braces!)
           - Ensure example Cypher queries you provide in the prompt follow this pattern, e.g.: `MATCH (p:Person {{name: 'Example Name'}})-[:ACTED_IN]->(m:Movie) RETURN m.title`
        
        8. Include example queries **Examples** section as per output format, use the following format to make it clear what is the natural language and what is the Cypher code:
           DO NOT put {question} in the example queries
            Example 1: <example_natural_language_query>
            cypher: MATCH (n) RETURN n LIMIT 5
            
            Example 2: <example_natural_language_query>
            cypher: MATCH (p)-[r]->(m) RETURN p, r, m LIMIT 5
        
        9. Include placeholders for {question} where the user question will be inserted
        
        10. Do not use generic examples - use the actual node labels, relationship types and properties from the provided schema.
        Keep the prompt concise but comprehensive enough to guide accurate Cypher query generation.
        
        11. IMPORTANT: Use {question} (not {{question}} or query) as the placeholder for the user's question, as this is required for compatibility with the GraphCypherQAChain.
        12. CRITICAL: When accessing relationship properties, ALWAYS first assign the relationship to a variable and then access its properties. For example:
            - INCORRECT: MATCH (a)-[:RELATIONSHIP {property: value}]->(b)
            - CORRECT: MATCH (a)-[r:RELATIONSHIP]->(b) WHERE r.property = value
            - CORRECT: MATCH (a)-[r:RELATIONSHIP]->(b) RETURN r.property
        13. Append following critical instructions to **Instructions for Cypher Query Generation:** section:
            - Cypher query should only include names of node, relationship or properties as per given schema
            - Return ONLY a single raw Cypher query with NO explanations, NO headers, NO numbering, NO query repetition, NO backticks, and NO additional text of any kind
            - The response should be ONLY the executable Cypher query with no additional text. The LLM must not include any of the following in its response:
                - NO "Simple Query:" or "Medium Query:" or "Complex Query:" headers
                - NO numbered lists like "1." or "2."
                - NO explanations before or after the query
                - NO backticks around the query
                - NO examples of multiple queries - just one single executable query
                - NO "Here's a Cypher query that..." text
                - NO "This query will..." explanatory text
            - For Date properties, in where clause or in filter queries, cast 'Date' attribute to datetime type and value to datetime type e.g. WHERE datetime(d.Date) = datetime('2020-01-03')
            - IMPORTANT: When accessing relationship properties, ALWAYS first assign the relationship to a variable and then access its properties. NEVER try to filter on relationship properties inside the relationship pattern.
            - If no cypher query could be generated for given query then return None or empty. DO NOT RETURN text with explaination.
        14. Do not alter **Sample Cyphers used for node/relationship creation** section
        15. Output Format:
        **Your Role:**
        **Your Task:**
        **Schema:**
          **Nodes:**
          **Relationships:**
        **Sample Cyphers used for node/relationship creation:**
        {sample_cyphers}
        **Cypher Best Practices:**
        **Value Embedding:**
        **Examples:**
        **Instructions for Cypher Query Generation:**
        **Question:**
        """
        
        # Define the prompt for generating the QA prompt
        # IMPORTANT: Updated to use simple {question} and {response} for compatibility with GraphCypherQAChain
        qa_prompt_instruction = """
        Create a prompt template for answering questions based on Neo4j query results.
        
        The template should:
        1. Guide the response generation for questions about this specific knowledge graph
        2. Include domain-specific guidance based on the node types and relationships in the schema
        3. Provide instructions on how to interpret and present the query results
        4. IMPORTANT: Include placeholders for {question} and {context} 
        5. Suggest how to handle common scenarios like empty results or large result sets
        6. Make the prompt specific to this graph's domain and structure, not generic.
        7. Include specific examples based on schema only, examples should similar in format to following -
            **Example 1:**
                *   `question`: "How many senior citizens have churned?"
                *   `context`: `[{{"count": 150}}]`
                *   *Answer:* "There are 150 senior citizens who have churned."

            **Example 2:**
                *   `question`: "What are the details for customer '1234-ABCD'?"
                *   `context`: `[{{"customerID": "1234-ABCD", "tenure": 24, "Contract": "Month-to-month", "MonthlyCharges": 75.50, "Churn": "No"}}]`
                *   *Answer:* "Customer '1234-ABCD' has been with us for 24 months, is on a Month-to-month contract, has monthly charges of $75.50, and has not churned."

            **Example 3:**
                *   `question`: "Are there any customers with Fiber optic who pay by Electronic check?"
                *   `context`: `[]`
                *   *Answer:* "No, I could not find any customers who have Fiber optic internet service and pay by Electronic check."

        8. Append following critical instructions to **Instructions for Interpretation and Response:** section. Do not include {question} or {context} directly in **Instructions for Interpretation and Response:** section instead if needed just use words 'question', 'context'
            - Return ONLY the answer string with data from context or question
            - Return "It seems like there is no data to support this query" string if no answer can be generated
            - Use data only from context or question to prepare answer
        9. Output Format:
        **Your Role:**
        **Your Task:**
        **Schema:**
          **Nodes:**
          **Relationships:**
        **Cypher Results Context:**
        **User Question:**
        **Example Scenario:**
        **Instructions for Interpretation and Response:**
        """
        
        # Define the prompt for generating sample queries
        sample_queries_instruction = """
        Generate 15 sample natural language questions based on provided knowledge graph schema and data from original dataset
        
        The questions should:
        1. Reflect the actual structure and domain of this knowledge graph
        2. Use the real node labels, relationship types and properties from the schema
        3. Include a mix of simple and complex queries
        4. Focus on questions that would provide meaningful insights
        5. Be organized as a JSON array of strings
        6. Generate questions using sample data values only
        
        Return ONLY the JSON array of sample questions, nothing else.
        """
        
        try:
            # Generate Cypher prompt template with retry
            print(f"Generating Cypher prompt template for {self.db_id}...")
            cypher_messages = [
                {"role": "system", "content": cypher_system_prompt},
                {"role": "user", "content": f"Use this Neo4j schema: {self.formatted_schema} for generating Cypher prompt as per following instructions:\n\n{cypher_prompt_instruction}"}
            ]
            llm_local = LLMProvider.get_llm(provider_name=LLMConstants.Providers.GOOGLE, model_name=LLMConstants.GoogleModels.DEFAULT, temperature=0.0)
            
            # Use retry mechanism for Cypher prompt generation
            cypher_prompt_template = self._generate_prompt_with_retry(llm_local, cypher_messages, "Cypher prompt")
            
            cypher_queries = ''
            
            '''import pandas as pd
            import tempfile
            import os
            
            # Get resolved data file path to ensure proper handling of transformed datasets
            data_file_path = self._resolve_data_path()
            if not data_file_path or not os.path.exists(data_file_path):
                print(f"Warning: Data file not found at {data_file_path}, falling back to original path")
                data_file_path = self.csv_file_path  # Fallback to original path
            
            # Check file type to handle differently based on extension
            is_parquet = data_file_path and data_file_path.lower().endswith('.parquet')
            
            print(f"Using data file for cypher generation: {data_file_path} (is_parquet={is_parquet})")
            
            # Use the proper generator based on file type
            if is_parquet:
                # For parquet files, we need to convert to a temporary CSV first
                
                temp_csv_path = None
                try:
                    # Create a temporary CSV file
                    with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as temp_file:
                        temp_csv_path = temp_file.name
                    
                    # Read parquet and write to CSV
                    print(f"Converting parquet to temporary CSV for processing")
                    df = pd.read_parquet(data_file_path, engine='pyarrow')
                    df.head(100).to_csv(temp_csv_path, index=False)
                    
                    # Use the temporary CSV file for CsvToCypherGenerator
                    cypher_generator = CsvToCypherGenerator(self.schema, temp_csv_path, 
                                                         LLMConstants.Providers.GOOGLE, 
                                                         LLMConstants.GoogleModels.DEFAULT)
                    cypher_queries = cypher_generator.generate_cypher_for_rows()
                    
                finally:
                    # Clean up the temporary file
                    if temp_csv_path and os.path.exists(temp_csv_path):
                        try:
                            os.unlink(temp_csv_path)
                        except Exception as e:
                            print(f"Warning: Could not delete temp file {temp_csv_path}: {str(e)}")
            else:
                # For CSV files, use the standard approach
                cypher_generator = CsvToCypherGenerator(self.schema, data_file_path, 
                                                     LLMConstants.Providers.GOOGLE, 
                                                     LLMConstants.GoogleModels.DEFAULT)
                cypher_queries = cypher_generator.generate_cypher_for_rows()
            '''
            # Apply Neo4j property syntax escaping to prevent template variable confusion
            cypher_prompt_template = self._escape_neo4j_properties(cypher_prompt_template)
            cypher_prompt_template = cypher_prompt_template.replace("{context}", "")

            
            # Generate QA prompt template with retry
            print(f"Generating QA prompt template for {self.db_id}...")
            qa_messages = [
                {"role": "system", "content": qa_system_prompt},
                {"role": "user", "content": f"Use this Neo4j schema: {self.formatted_schema} for generating QA prompt as per following instructions:\n\n{qa_prompt_instruction}"}
            ]
            # Use retry mechanism for QA prompt generation
            qa_prompt_template = self._generate_prompt_with_retry(llm_local, qa_messages, "QA prompt")
            
            # Apply Neo4j property syntax escaping to prevent template variable confusion
            qa_prompt_template = self._escape_neo4j_properties(qa_prompt_template)
            
            # Generate sample queries only if we're not using domain-specific ones
            if skip_sample_queries_generation:
                print(f"Skipping sample queries generation as domain-specific queries will be used")
                sample_queries = []  # Empty list as placeholder, will be replaced by domain-specific queries
            else:
                # Generate sample data JSON
                sample_data = self._generate_sample_data_json()
                print(f"Sample data JSON for Queries!!!: {sample_data}")
                # Generate sample queries with retry
                sample_queries_messages = [
                    {"role": "system", "content": sample_queries_system_prompt},
                    {"role": "user", "content": f"Use this Neo4j schema: {self.formatted_schema} and the data to use: {sample_data} for generating sample questions prompt as per following instruction: \n\n{sample_queries_instruction}"}
                ]
                
                # Use retry mechanism for sample queries generation and parsing
                sample_queries = self._generate_sample_queries_with_retry(llm_local, sample_queries_messages, sample_data)
                            
            # Create prompts dictionary
            prompts = {
                "db_id": self.db_id,
                "cypher_prompt": cypher_prompt_template,
                "qa_prompt": qa_prompt_template,
                "sample_queries": sample_queries,
                "sample_cyphers": cypher_queries
            }
            print(f"DEBUG: Created prompts with properly escaped Neo4j property syntax")
            
            return prompts
            
        except Exception as e:
            print(f"Error generating prompts with LLM: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            
            # Instead of using fallback prompts, raise the exception to fail explicitly
            # This makes debugging easier by exposing the actual error
            raise RuntimeError(f"Failed to generate prompts for schema: {str(e)}")
        
    def _generate_sample_data_json(self):
        """Generate a JSON with column names as keys and lists of unique values for each column."""
        import pandas as pd
        import json
        import os
        
        try:
            # Resolve the file path for the data file
            file_path = self._resolve_data_path()
            
            if not file_path or not os.path.exists(file_path):
                print(f"Error: Data file not found at {file_path}")
                return "{}"
                
            print(f"Reading data from resolved path: {file_path}")
            
            # Determine file type and read accordingly
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path, nrows=100)
            elif file_path.endswith('.parquet'):
                df = pd.read_parquet(file_path, engine='pyarrow')
                # Limit to first 100 rows after loading
                df = df.head(100)
            elif file_path.endswith('.json'):
                df = pd.read_json(file_path)
                df = df.head(100)
            else:
                print(f"Unsupported file format for {file_path}")
                return "{}"
            
            # Create a dictionary to store column names and unique values
            sample_data = {}
            
            # For each column, get up to 10 unique values
            for column in df.columns:
                unique_values = df[column].dropna().unique()
                # Take only up to 10 unique values
                sample_values = unique_values[:10].tolist()
                
                # Convert numpy types to native Python types for JSON serialization
                sample_values = [
                    v.item() if hasattr(v, 'item') else v 
                    for v in sample_values
                ]
                
                sample_data[column] = sample_values
            
            return json.dumps(sample_data, indent=2)
        except Exception as e:
            print(f"Error generating sample data JSON: {str(e)}")
            return "{}"
            
    def _resolve_data_path(self):
        """Resolve the data file path, handling both source and transformed datasets."""
        import os
        from sqlalchemy.orm import Session
        from ...models import Schema
        from ...db_config import SessionLocal
        
        # Get the schema record from the database
        db = SessionLocal()
        try:
            schema = db.query(Schema).filter(Schema.id == self.schema_id).first()
            if not schema:
                print(f"Schema with ID {self.schema_id} not found")
                return None
                
            # Get the file path from the schema
            data_path = schema.csv_file_path
            if not data_path:
                print(f"No file path found in schema {self.schema_id}")
                return None
                
            # Check if this is a transformed dataset based on dataset_type flag
            is_transformed_dataset = schema.dataset_type == 'transformed'
            
            # Only apply path resolution for transformed datasets with just a filename
            if is_transformed_dataset:
                print(f"Resolving path for transformed dataset: {data_path}")
                # If just a filename without path, check in data directories
                data_dirs = [
                    os.path.join(os.path.dirname(__file__), '..', '..', 'data'),
                    os.path.join(os.path.dirname(__file__), '..', '..', 'datapuur_ai', 'data'),
                    os.path.join(os.path.dirname(__file__), '..', '..', 'uploads')
                ]
                
                for dir_path in data_dirs:
                    full_path = os.path.join(dir_path, data_path)
                    if os.path.exists(full_path):
                        print(f"Found transformed dataset at {full_path}")
                        return full_path
                        
                print(f"Warning: Could not find transformed dataset in any of the data directories")
            
            # If not a transformed dataset or if it already has a full path, use as-is
            if os.path.exists(data_path):
                return data_path
            else:
                print(f"Warning: File does not exist at path: {data_path}")
                return None
                
        finally:
            db.close()

    def _escape_neo4j_properties(self, prompt_text: str) -> str:
        """
        Escapes Neo4j property maps (e.g., {key: value}) within node/relationship patterns (...) or [...]
        by wrapping them in double curly braces {{ {key: value} }} for LangChain compatibility.
        It avoids wrapping already escaped maps {{...}} and template variables like {question} or {context}.
        """
        if not prompt_text:
            return prompt_text

        # First, temporarily replace {question} and {context} with placeholders
        # to prevent them from being double-escaped
        placeholder_map = {
            "{question}": "__QUESTION_PLACEHOLDER__",
            "{context}": "__CONTEXT_PLACEHOLDER__",
            "{query}": "__QUERY_PLACEHOLDER__"
        }
        
        # Replace template variables with placeholders
        for template_var, placeholder in placeholder_map.items():
            prompt_text = prompt_text.replace(template_var, placeholder)
        
        # Now escape all remaining curly braces
        prompt_text = prompt_text.replace("{", "{{").replace("}", "}}")
        
        # Restore the template variables from placeholders
        for template_var, placeholder in placeholder_map.items():
            prompt_text = prompt_text.replace(placeholder, template_var)
            
        return prompt_text

    def _load_prompts(self) -> None:
        """Load custom prompts for this source"""
        # Use both db_id and schema_id in the prompt filename for better specificity
        prompt_file = PROMPT_DIR / f"prompt_{self.db_id}_{self.schema_id}.json"
        
        try:
            # Default to None initially to detect loading issues
            self.cypher_prompt = None
            self.qa_prompt = None
            
            print(f"DEBUG: Attempting to load prompts")
            prompts = {}
            
            # Try to load the specific prompt file first
            if prompt_file.exists():
                with open(prompt_file, "r") as f:
                    prompts = json.load(f)
                print(f"DEBUG: Loaded prompt file for db '{self.db_id}' and schema '{self.schema_id}'")
            else:
                print(f"DEBUG: No prompt files found, will use default prompts")
                
            # Convert string prompts to ChatPromptTemplate objects if needed
            if "cypher_prompt" in prompts:
                cypher_prompt_text = prompts.get("cypher_prompt")
                # Check if it's already a structured object or a string
                if isinstance(cypher_prompt_text, str):
                    print(f"DEBUG: Converting cypher_prompt string to ChatPromptTemplate")
                    # Check if the prompt starts with "Prompt:" or "Prompt Template:" and clean it
                    if cypher_prompt_text.startswith("Prompt:") or cypher_prompt_text.startswith("Prompt Template:"):
                        lines = cypher_prompt_text.split('\n')
                        # Skip the first line if it's just the "Prompt:" header
                        template_text = '\n'.join(lines[1:]).strip()
                        print(f"DEBUG: Cleaned prompt template from header")
                    else:
                        template_text = cypher_prompt_text
                        
                    # Fix all placeholder formats for compatibility with GraphCypherQAChain
                    # The key parameter expected by the chain is 'query', not 'question'
                    # if "{{query}}" in template_text:
                    #     template_text = template_text.replace("{{query}}", "{query}")
                    #     print(f"DEBUG: Fixed {{query}} placeholder format")
                    
                    # if "{{question}}" in template_text:
                    #     # Replace 'question' with 'query' for compatibility
                    #     template_text = template_text.replace("{{question}}", "{query}")
                    #     print(f"DEBUG: Replaced {{question}} with {{query}} for compatibility")
                    
                    self.cypher_prompt = ChatPromptTemplate.from_template(template_text)
                else:
                    self.cypher_prompt = cypher_prompt_text
            
            if "qa_prompt" in prompts:
                qa_prompt_text = prompts.get("qa_prompt")
                # Check if it's already a structured object or a string
                if isinstance(qa_prompt_text, str):
                    print(f"DEBUG: Converting qa_prompt string to ChatPromptTemplate")
                    # Check if the prompt starts with "Prompt:" or "Prompt Template:" and clean it
                    if qa_prompt_text.startswith("Prompt:") or qa_prompt_text.startswith("Prompt Template:"):
                        lines = qa_prompt_text.split('\n')
                        # Skip the first line if it's just the "Prompt:" header
                        template_text = '\n'.join(lines[1:]).strip()
                        print(f"DEBUG: Cleaned prompt template from header")
                    else:
                        template_text = qa_prompt_text
                        
                    # Fix all placeholder formats for compatibility with GraphCypherQAChain
                    # QA prompt should use 'query' and 'context' parameters
                    # LangChain specifically expects 'query' not 'question'
                    # if "{{question}}" in template_text:
                    #     # Always replace 'question' with 'query' - this is critical
                    #     template_text = template_text.replace("{{question}}", "{query}")
                    #     print(f"DEBUG: Replaced {{question}} with {{query}} in QA prompt")
                        
                    # if "{{query}}" in template_text:
                    #     template_text = template_text.replace("{{query}}", "{query}")
                    #     print(f"DEBUG: Fixed {{query}} format in QA prompt")
                        
                    # if "{{context}}" in template_text:
                    #     template_text = template_text.replace("{{context}}", "{context}")
                    #     print(f"DEBUG: Fixed {{context}} format in QA prompt")
                        
                    # if "{{response}}" in template_text:
                    #     # Also replace 'response' with 'context' as needed
                    #     template_text = template_text.replace("{{response}}", "{context}")
                    #     print(f"DEBUG: Replaced {{response}} with {{context}} in QA prompt")
                            
                    print(f"DEBUG: Fixed placeholders in QA prompt")
                    self.qa_prompt = ChatPromptTemplate.from_template(template_text)
                else:
                    self.qa_prompt = qa_prompt_text
                
            # Load sample queries 
            self.sample_queries = prompts.get("sample_queries", [])
            
        except Exception as e:
            # Handle any errors in loading prompts
            print(f"ERROR: Failed to load prompts: {str(e)}")
            print(f"DEBUG: {traceback.format_exc()}")
            
            # Instead of using fallback prompts, raise the exception to fail explicitly
            # This makes debugging easier by exposing the actual error
            raise RuntimeError(f"Failed to load prompts for schema: {str(e)}") from e
            
    def _debug_print_prompts(self):
        """Print debug information about the loaded prompts"""
        print("\n=== DEBUG: PROMPT INFORMATION ===")
        print(f"Cypher prompt type: {type(self.cypher_prompt)}")
        print(f"QA prompt type: {type(self.qa_prompt)}")
        
        # Check prompt template variable names
        if hasattr(self.cypher_prompt, 'template') and hasattr(self.cypher_prompt.template, 'variable_names'):
            print(f"Cypher prompt variables: {self.cypher_prompt.template.variable_names}")
        elif hasattr(self.cypher_prompt, 'input_variables'):
            print(f"Cypher prompt variables: {self.cypher_prompt.input_variables}")
        else:
            print("Cannot determine Cypher prompt variables")
            
        if hasattr(self.qa_prompt, 'template') and hasattr(self.qa_prompt.template, 'variable_names'):
            print(f"QA prompt variables: {self.qa_prompt.template.variable_names}")
        elif hasattr(self.qa_prompt, 'input_variables'):
            print(f"QA prompt variables: {self.qa_prompt.input_variables}")
        else:
            print("Cannot determine QA prompt variables")
        print("===================================\n")

    def _get_cypher_from_table(self, model_class) -> str:
        """Reads loading cypher from the specified table based on schema_id."""
        db = None
        try:
            db = SessionLocal()
            record = db.query(model_class).filter(model_class.schema_id == self.schema_id).first()
            if record and record.cypher:
                print(f"Found loading cypher in {model_class.__tablename__} for schema {self.schema_id}")
                return record.cypher
            else:
                print(f"No loading cypher found in {model_class.__tablename__} for schema {self.schema_id}")
                return "" # Return empty string if not found
        except Exception as e:
            print(f"Error reading from {model_class.__tablename__} for schema {self.schema_id}: {e}")
            if db:
                db.rollback() # Rollback on error, though it's just a read
            return "" # Return empty string on error
        finally:
            if db:
                db.close()

    def _format_schema(self):
        """
        Convert the class's schema property to a formatted text representation
        suitable for LLM prompts.
        
        Returns:
            str: A formatted text representation of the schema listing nodes and relationships
        """
        try:
            # Use the class's schema property
            schema = self.schema

            # Start building the schema text
            schema_text = "The graph contains the following nodes and relationships:\n\nNodes:\n"
            
            # Process nodes
            if 'nodes' in schema:
                for node in schema['nodes']:
                    node_label = node.get('label', 'UnknownNode')
                    schema_text += f"\n  {node_label}:\n"
                    
                    if 'properties' in node and node['properties']:
                        # Handle properties as a dictionary of key:type pairs
                        for prop_name, prop_type in node['properties'].items():
                            # Format property with type
                            schema_text += f"    {prop_name} ({prop_type})\n"
                    else:
                        schema_text += "    (no properties)\n"

            # Process relationships
            schema_text += "\nRelationships:\n"
            
            if 'relationships' in schema:
                for relationship in schema['relationships']:
                    rel_type = relationship.get('type', 'UNKNOWN_RELATIONSHIP')
                    # Handle different formats of relationship node references
                    start_node = None
                    end_node = None
                    
                    # Try different ways the schema might represent source/target nodes
                    if 'startNode' in relationship:
                        start_node = relationship['startNode']
                    elif 'source' in relationship:
                        start_node = relationship['source']
                    
                    if 'endNode' in relationship:
                        end_node = relationship['endNode']
                    elif 'target' in relationship:
                        end_node = relationship['target']
                    
                    schema_text += f"\n  [{start_node}]-[{rel_type}]->({end_node}):\n"
                    
                    if 'properties' in relationship and relationship['properties']:
                        # Handle properties as a dictionary of key:type pairs
                        for prop_name, prop_type in relationship['properties'].items():
                            # Format property with type
                            schema_text += f"    {prop_name} ({prop_type})\n"
                    else:
                        schema_text += "    (no properties)\n"
            
            self.formatted_schema = schema_text
            print(f"DEBUG: Successfully formatted schema")
        
        except Exception as e:
            print(f"ERROR: Failed to convert schema to text: {str(e)}")
            traceback.print_exc()
            # Set a fallback formatted schema
            self.formatted_schema = "Schema information not available in expected format."

    def _format_history(self) -> str:
        """Format last exchanges for context"""
        return "\n".join(
            f"{msg.content}" 
            for msg in self.history.messages[-5:] if msg.type == "ai"
        )

    @retry(stop=stop_after_attempt(3),
           wait=wait_exponential(multiplier=1, min=2, max=10),
           retry=retry_if_exception_type((TimeoutError, ConnectionError, Exception)))
    def _invoke_llm_with_retry(self, llm, prompt_formatted, timeout=30) -> str:
        """Invoke LLM with retry logic for timeouts and connection errors"""
        try:
            # Safely get attempt number with a default value of 1
            attempt = 1
            if hasattr(self._invoke_llm_with_retry, 'retry') and hasattr(self._invoke_llm_with_retry.retry, 'statistics'):
                attempt = self._invoke_llm_with_retry.retry.statistics.get('attempt_number', 1)
            print(f"Invoking LLM (attempt {attempt})")
            
            # Use asyncio to implement timeout
            async def invoke_with_timeout():
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, lambda: llm.invoke(prompt_formatted))
            
            # Run with timeout
            result = asyncio.run(asyncio.wait_for(invoke_with_timeout(), timeout))
            return result
        except Exception as e:
            print(f"Error invoking LLM: {str(e)}")
            # If this is the final retry attempt, return None
            attempt = 1
            if hasattr(self._invoke_llm_with_retry, 'retry') and hasattr(self._invoke_llm_with_retry.retry, 'statistics'):
                attempt = self._invoke_llm_with_retry.retry.statistics.get('attempt_number', 1)
            if attempt >= 3:
                return None
            raise

    @retry(stop=stop_after_attempt(3),
           wait=wait_exponential(multiplier=1, min=2, max=10),
           retry=retry_if_exception_type((TimeoutError, ConnectionError, Exception)))
    def _extract_valid_cypher_with_retry(self, llm_output: str):
        """Extract a valid Cypher query with retry logic for parsing failures"""
        try:
            # Safely get attempt number with a default value of 1
            attempt = 1
            if hasattr(self._extract_valid_cypher_with_retry, 'retry') and hasattr(self._extract_valid_cypher_with_retry.retry, 'statistics'):
                attempt = self._extract_valid_cypher_with_retry.retry.statistics.get('attempt_number', 1)
            print(f"Extracting Cypher query (attempt {attempt})")
            
            result = self._extract_valid_cypher_query(llm_output)
            if result is None:
                raise ValueError("Failed to extract valid Cypher query")
            return result
        except Exception as e:
            print(f"Error extracting Cypher query: {str(e)}")
            # If this is the final retry attempt, return None
            attempt = 1
            if hasattr(self._extract_valid_cypher_with_retry, 'retry') and hasattr(self._extract_valid_cypher_with_retry.retry, 'statistics'):
                attempt = self._extract_valid_cypher_with_retry.retry.statistics.get('attempt_number', 1)
            if attempt >= 3:
                return None
            raise
            
    @retry(stop=stop_after_attempt(3),
           wait=wait_exponential(multiplier=1, min=2, max=10),
           retry=retry_if_exception_type((TimeoutError, ConnectionError, Exception)))
    def _generate_prompt_with_retry(self, llm, messages, prompt_type="prompt"):
        """Generate a prompt template with retry logic for LLM failures"""
        try:
            # Safely get attempt number with a default value of 1
            attempt = 1
            if hasattr(self._generate_prompt_with_retry, 'retry') and hasattr(self._generate_prompt_with_retry.retry, 'statistics'):
                attempt = self._generate_prompt_with_retry.retry.statistics.get('attempt_number', 1)
            print(f"Generating {prompt_type} (attempt {attempt})")
            
            # Convert messages to the format expected by the LLM
            from langchain_core.messages import SystemMessage, HumanMessage
            lc_messages = []
            for msg in messages:
                if msg.get('role') == 'system':
                    lc_messages.append(SystemMessage(content=msg['content']))
                elif msg.get('role') == 'user':
                    lc_messages.append(HumanMessage(content=msg['content']))
            
            # Use the correct API for the LLM
            result = llm.invoke(lc_messages).content.strip()
            
            # Validate the response - ensure it's not empty and has reasonable length
            if not result or len(result) < 20:
                raise ValueError(f"Generated {prompt_type} is too short or empty")
                
            return result
        except Exception as e:
            print(f"Error generating {prompt_type}: {str(e)}")
            # If this is the final retry attempt, raise the exception to fail explicitly
            attempt = 1
            if hasattr(self._generate_prompt_with_retry, 'retry') and hasattr(self._generate_prompt_with_retry.retry, 'statistics'):
                attempt = self._generate_prompt_with_retry.retry.statistics.get('attempt_number', 1)
            if attempt >= 3:
                raise RuntimeError(f"Failed to generate {prompt_type} after multiple retries: {str(e)}")
            raise
    
    @retry(stop=stop_after_attempt(3),
           wait=wait_exponential(multiplier=1, min=2, max=10),
           retry=retry_if_exception_type((TimeoutError, ConnectionError, Exception)))
    def _generate_sample_queries_with_retry(self, llm, messages, sample_data):
        """Generate sample queries with retry logic for LLM failures and JSON parsing"""
        try:
            # Safely get attempt number with a default value of 1
            attempt = 1
            if hasattr(self._generate_sample_queries_with_retry, 'retry') and hasattr(self._generate_sample_queries_with_retry.retry, 'statistics'):
                attempt = self._generate_sample_queries_with_retry.retry.statistics.get('attempt_number', 1)
            print(f"Generating sample queries (attempt {attempt})")
            
            # Convert messages to the format expected by the LLM
            from langchain_core.messages import SystemMessage, HumanMessage
            lc_messages = []
            for msg in messages:
                if msg.get('role') == 'system':
                    lc_messages.append(SystemMessage(content=msg['content']))
                elif msg.get('role') == 'user':
                    lc_messages.append(HumanMessage(content=msg['content']))
            
            # Use the correct API for the LLM
            result = llm.invoke(lc_messages).content.strip()
            
            # Validate the response - ensure it's not empty
            if not result:
                raise ValueError("Generated sample queries response is empty")
            
            # Try to parse as JSON
            try:
                import json
                import re
                
                # First, try to extract JSON array if embedded in other text
                json_match = re.search(r'\[\s*".*"\s*\]', result, re.DOTALL)
                if json_match:
                    result = json_match.group(0)
                
                # Parse the JSON
                queries = json.loads(result)
                
                # Validate the parsed result is a list with at least a few items
                if not isinstance(queries, list) or len(queries) < 3:
                    raise ValueError(f"Invalid sample queries format or too few queries: {result}")
                    
                return queries
            except json.JSONDecodeError as json_err:
                print(f"JSON parsing error for sample queries: {str(json_err)}")
                raise ValueError(f"Failed to parse sample queries as JSON: {str(json_err)}")
                
        except Exception as e:
            print(f"Error generating sample queries: {str(e)}")
            # If this is the final retry attempt, return a minimal set of generic queries
            attempt = 1
            if hasattr(self._generate_sample_queries_with_retry, 'retry') and hasattr(self._generate_sample_queries_with_retry.retry, 'statistics'):
                attempt = self._generate_sample_queries_with_retry.retry.statistics.get('attempt_number', 1)
            if attempt >= 3:
                print("Falling back to generic sample queries after multiple retry failures")
                return ["What data is available in the graph?", "Show me the schema of this graph", "What are the main node types?"]
            raise
            
    @retry(stop=stop_after_attempt(3),
           wait=wait_exponential(multiplier=1, min=2, max=10),
           retry=retry_if_exception_type((TimeoutError, ConnectionError, Exception)))
    def _generate_qa_response_with_retry(self, llm, prompt_formatted, timeout=30):
        """Generate QA response with retry logic for parsing failures"""
        try:
            # Safely get attempt number with a default value of 1
            attempt = 1
            if hasattr(self._generate_qa_response_with_retry, 'retry') and hasattr(self._generate_qa_response_with_retry.retry, 'statistics'):
                attempt = self._generate_qa_response_with_retry.retry.statistics.get('attempt_number', 1)
            print(f"Generating QA response (attempt {attempt})")
            
            result = self._invoke_llm_with_retry(llm, prompt_formatted, timeout=timeout)
            
            # Validate the response - ensure it's not empty and has reasonable length
            if not result or len(result.strip()) < 10:
                raise ValueError("Generated QA response is too short or empty")
                
            return result
        except Exception as e:
            print(f"Error generating QA response: {str(e)}")
            # If this is the final retry attempt, return a user-friendly message
            attempt = 1
            if hasattr(self._generate_qa_response_with_retry, 'retry') and hasattr(self._generate_qa_response_with_retry.retry, 'statistics'):
                attempt = self._generate_qa_response_with_retry.retry.statistics.get('attempt_number', 1)
            if attempt >= 3:
                return "I found some information but couldn't generate a complete response. Please try rephrasing your question."
            raise

    def _extract_valid_cypher_query(self, llm_output: str):
        """
        Extract a valid Cypher query from the LLM's output.
        
        Args:
            llm_output: The raw output from the LLM containing Cypher query
            
        Returns:
            str: A clean, executable Cypher query
        """
        if not llm_output:
            return None
            
        # First, try to extract code blocks with ```cypher ... ``` format
        if "```cypher" in llm_output and "```" in llm_output:
            # Extract content between ```cypher and ```
            parts = llm_output.split("```cypher")
            if len(parts) > 1:
                code_part = parts[1].split("```")[0].strip()
                if code_part:
                    return code_part
        
        # Next, try to extract code blocks with just ``` ... ``` format
        if "```" in llm_output:
            # Extract content between ``` and ```
            parts = llm_output.split("```")
            if len(parts) > 1:
                code_part = parts[1].strip()
                if code_part.lower().startswith("cypher"):
                    code_part = code_part[len("cypher"):].strip()
                if code_part:
                    return code_part
        
        # Try to extract based on keywords like "MATCH", "RETURN", etc.
        cypher_keywords = ["MATCH", "RETURN", "WHERE", "WITH", "CALL"]
        for keyword in cypher_keywords:
            if keyword in llm_output.upper():
                # Find the position of the keyword
                pos = llm_output.upper().find(keyword)
                # Extract from the keyword to the end of the text
                query = llm_output[pos:].strip()
                # Clean up any trailing text
                for line in query.split("\n"):
                    if line.strip() and not any(k in line.upper() for k in cypher_keywords + ["LIMIT", "ORDER BY", "SKIP", "CREATE", "MERGE"]):
                        query = query.split(line)[0].strip()
                        break
                if query:
                    return query
        
        # If all else fails, return None instead of a hardcoded query
        print(f"WARNING: Could not extract a valid Cypher query from LLM output.")
        return None
        
    def query(self, question: str) -> Dict[str, Any]:
        """Process a natural language question and return an answer based on the graph data.
        
        Args:
            question: The natural language question to answer
            
        Returns:
            Dict with the result key containing the answer
        """
        start_time = time.time()
        print(f"Processing query: {question}")
        
        # Check if initialization is complete
        if not self.initialization_complete:
            # Wait for initialization to complete (with timeout)
            max_wait_time = 10  # seconds
            wait_start = time.time()
            while not self.initialization_complete and time.time() - wait_start < max_wait_time:
                print(f"Waiting for initialization to complete...")
                time.sleep(0.5)  # Wait a bit and check again
            
            # Check if initialization completed or timed out
            if not self.initialization_complete:
                if self.initialization_error:
                    return {"result": f"Error initializing the assistant: {self.initialization_error}"}
                else:
                    return {"result": "The assistant is still initializing. Please try again in a few moments."}
        
        try:
            # Special handling for schema-related questions
            if any(keyword in question.lower() for keyword in ["schema", "structure", "model", "nodes", "relationships", "node types", "relationship types"]):
                print("DEBUG: Schema-related question detected, using direct schema information")
                return {"result": f"Here's the schema of the graph:\n\n{self.formatted_schema}"}
                    
            # Try the direct approach with our custom prompts
            try:
                # Step 1: Generate Cypher query using the cypher_prompt
                print("DEBUG: Generating Cypher query")
                cypher_inputs = {"query": question}
                if hasattr(self.chain, "llm") and hasattr(self.chain, "cypher_prompt"):
                    # Use the retry-enabled LLM invocation
                    generated_cypher = self._invoke_llm_with_retry(
                        self.chain.llm,
                        self.chain.cypher_prompt.format(**cypher_inputs),
                        timeout=30  # Standard timeout for Cypher generation
                    )
                    print(f"DEBUG: Generated Cypher: {generated_cypher}")
                    
                    # Step 2: Extract valid Cypher query with retry
                    clean_cypher = self._extract_valid_cypher_with_retry(generated_cypher)
                    
                    if clean_cypher is None:
                        print("DEBUG: Failed to extract a valid Cypher query after multiple retries")
                        return {"result": "I couldn't generate a valid query for your question. Could you please rephrase or provide more specific details?"}
                    
                    print(f"DEBUG: Clean Cypher: {clean_cypher}")
                    
                    # Step 3: Execute the Cypher query
                    print("DEBUG: Executing Cypher query")
                    context = self.graph.query(clean_cypher)
                    print(f"DEBUG: Query result: {context}")
                    
                    # Step 4: Generate the final answer using the qa_prompt
                    qa_inputs = {"query": question, "context": context}
                    if hasattr(self.chain, "qa_llm") and hasattr(self.chain, "qa_prompt"):
                        print("DEBUG: Generating answer using QA prompt")
                        # Use the retry-enabled QA response generation with validation
                        try:
                            answer = self._generate_qa_response_with_retry(
                                self.chain.qa_llm,
                                self.chain.qa_prompt.format(**qa_inputs),
                                timeout=30  # Standard timeout for QA generation
                            )
                            result = {"result": answer}
                        except (TimeoutError, ConnectionError, Exception) as e:
                            print(f"Failed to generate answer after retries: {str(e)}")
                            return {"result": f"I retrieved data from the database but had trouble generating a response. Here's the raw data: {str(context)}"}
                    else:
                        result = {"result": f"Query results: {context}"}
                else:
                    # Fallback to standard chain invocation
                    print("DEBUG: Falling back to standard chain invocation")
                    try:
                        result = self.chain.invoke({'question': question, 'query': question})
                    except Exception as chain_error:
                        print(f"DEBUG: Standard chain invocation failed: {str(chain_error)}")
                        # Check if error is related to None Cypher query
                        if "Invalid input 'None'" in str(chain_error):
                            return {"result": "Not able to prepare valid queries. Please update your question with specific data attributes or relationships."}
                        # Otherwise, raise the error to be caught by the outer try-except
                        raise
            except Exception as e:
                print(f"ERROR: Direct approach failed: {str(e)}")
                print(f"DEBUG: {traceback.format_exc()}")
                # Return an informative error message instead of using hardcoded fallback queries
                result = {
                    "result": "I encountered an error processing your query. The database might be unavailable or your question might be too complex. Could you please try a simpler question or check if the database is accessible?"
                }
            
            query_time = time.time() - start_time
            print(f"Query completed in {query_time:.2f} seconds")
            
            # Persist conversation
            print(f"Persisting conversation: {result}")
            self.history.add_user_message(question)
            self.history.add_ai_message(result["result"])
            
            return result
        
        except Exception as e:
            print(f"Research error: {str(e)}")
            print(f"Full error traceback: {traceback.format_exc()}")
            return {"result": f"An error occurred while processing your query: {str(e)}. Please try again or contact support."}

    def __del__(self):
        # Close the cache connection when the object is garbage collected
        if hasattr(self, 'cache'):
            self.cache.close()

# Singleton-like behavior with dict of assistants by db_id
_assistants = {}
_lock = threading.Lock()

def initialize_all_agents(db_session=None):
    """
    Initialize all schema-aware agents at application startup.
    This helps avoid cold-start delays when users first interact with the system.
    
    Args:
        db_session: Optional database session. If not provided, a new session will be created.
    
    Returns:
        dict: A dictionary mapping schema IDs to initialization status (True for success, False for failure)
    """
    from ...db_config import SessionLocal
    from ...models import Schema
    import time
    
    print("Starting initialization of all schema-aware agents...")
    start_time = time.time()
    
    # Use provided session or create a new one
    close_session = False
    if db_session is None:
        db_session = SessionLocal()
        close_session = True
    
    results = {}
    try:
        # Get only schemas with db_loaded='yes' from the database
        schemas = db_session.query(Schema).filter(Schema.db_loaded == 'yes').all()
        print(f"Found {len(schemas)} schemas with db_loaded='yes' to initialize")
        
        for schema in schemas:
            if not schema.schema or not schema.db_id:
                print(f"Skipping schema {schema.id}: Missing schema data or DB ID")
                results[schema.id] = False
                continue
            
            try:
                print(f"Pre-initializing agent for schema {schema.id}...")
                # Initialize the agent
                assistant = get_schema_aware_assistant(schema.db_id, schema.id, schema.schema)
                # Force initialization of prompt templates
                assistant._ensure_prompt()
                results[schema.id] = True
                print(f"Successfully initialized agent for schema {schema.id}")
            except Exception as e:
                print(f"Failed to initialize agent for schema {schema.id}: {str(e)}")
                results[schema.id] = False
    
    except Exception as e:
        print(f"Error during agent initialization: {str(e)}")
    
    finally:
        if close_session:
            db_session.close()
    
    elapsed_time = time.time() - start_time
    success_count = sum(1 for v in results.values() if v)
    print(f"Completed initialization of {success_count}/{len(results)} agents in {elapsed_time:.2f} seconds")
    
    return results

def remove_schema_aware_assistant(schema_id: str):
    """
    Remove schema-aware assistant for the specified schema ID.
    This should be called when a schema's db_loaded status is changed to 'no'.
    
    Args:
        schema_id: ID of the schema whose assistant should be removed
        
    Returns:
        bool: True if an assistant was removed, False otherwise
    """
    removed = False
    try:
        with _lock:
            # Find and remove all assistants for this schema_id
            keys_to_remove = []
            for key in list(_assistants.keys()):
                # Each key is formatted as "db_id:schema_id" or "db_id:schema_id:session_id"
                parts = key.split(':')
                if len(parts) >= 2 and parts[1] == str(schema_id):
                    keys_to_remove.append(key)
            
            # Remove all found assistants
            for key in keys_to_remove:
                if key in _assistants:
                    print(f"DEBUG: Removing schema-aware assistant for schema {schema_id} with key {key}")
                    del _assistants[key]
                    removed = True
            
            if removed:
                print(f"DEBUG: Successfully removed assistant(s) for schema {schema_id}")
            else:
                print(f"DEBUG: No assistants found for schema {schema_id}")
            
            return removed
    except Exception as e:
        print(f"ERROR: Failed to remove schema-aware assistant for schema {schema_id}: {str(e)}")
        return False


def get_schema_aware_assistant(db_id: str, schema_id: str, schema: str, session_id: str = None) -> SchemaAwareGraphAssistant:
    """
    Get a schema-aware assistant for the specified database ID.
    Creates a new assistant if one doesn't exist, otherwise returns the existing one.
    
    Args:
        db_id: ID of the Neo4j database to query
        schema_id: ID of the schema being used
        schema: JSON string containing the schema
        session_id: Optional session ID for chat history
    Returns:
        SchemaAwareGraphAssistant: The assistant for the database
    """
    # Create a unique key combining db_id, schema_id and session_id
    key = f"{db_id}:{schema_id}:{session_id}" if session_id else f"{db_id}:{schema_id}"
    
    try:
        with _lock:
            if key not in _assistants:
                # Log connection attempt for debugging
                print(f"DEBUG: Creating new schema-aware assistant for {db_id} with schema {schema_id}")
                print(f"DEBUG: Schema: {schema}")
                _assistants[key] = SchemaAwareGraphAssistant(db_id, schema_id, schema, session_id)
                print(f"DEBUG: Successfully created assistant for {db_id}")
            return _assistants[key]
    except Exception as e:
        # Log the error with detailed information
        error_message = f"Error creating schema-aware assistant for {db_id}: {str(e)}"
        print(f"ERROR: {error_message}")
        
        # Check for specific error types to provide better feedback
        if "Could not use APOC procedures" in str(e):
            print("DEBUG: APOC plugin issue detected. Ensure APOC is installed and configured.")
        elif "authentication failed" in str(e).lower() or "unauthorized" in str(e).lower():
            print("DEBUG: Authentication failed. Check Neo4j credentials.")
        elif "connection refused" in str(e).lower() or "unreachable" in str(e).lower():
            print("DEBUG: Connection failed. Check Neo4j server availability and network settings.")
            
        # Re-raise with a more informative message
        raise RuntimeError(f"Failed to initialize schema-aware assistant: {error_message}") from e
