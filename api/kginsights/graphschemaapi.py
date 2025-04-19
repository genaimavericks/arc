from fastapi import APIRouter, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from .agent.graph_schema_agent import GraphSchemaAgent
# Using only Google Generative AI
import os
import json
import uuid
import time
import traceback
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session
from ..models import get_db, IngestionJob, UploadedFile, Schema
from ..auth import has_any_permission
from ..models import User
from ..db_config import SessionLocal
from neo4j import GraphDatabase
from .database_api import get_database_config, parse_connection_params
from .loaders.data_loader import DataLoader
from .loaders.neo4j_loader import Neo4jLoader
import traceback
import re
from langchain_google_genai import ChatGoogleGenerativeAI
from unittest.mock import MagicMock

# Utility function to update schema status
def update_schema_status(db=None, schema=None, db_id=None, schema_id=None, schema_generated=None, db_loaded=None):
    """
    Update schema status fields in the database.
    
    Args:
        db: Database session. If None, a new session will be created
        schema: Schema object to update. If None, will look up by schema_id or db_id
        db_id: Database ID to set on schema
        schema_id: Schema ID to look up if schema is None
        schema_generated: Set schema_generated status ('yes' or 'no')
        db_loaded: Set db_loaded status ('yes' or 'no')
        
    Returns:
        Updated schema object or None if update failed
    """
    # Create a database session if none is provided
    session_created = False
    try:
        if db is None:
            db = SessionLocal()
            session_created = True
            print("DEBUG: Created new database session for schema status update")
            
        # If schema object is not provided, try to find it
        if schema is None:
            if schema_id is not None:
                schema = db.query(Schema).filter(Schema.id == schema_id).first()
            elif db_id is not None:
                schema = db.query(Schema).filter(Schema.db_id == db_id).first()
                
            if schema is None:
                print(f"WARNING: Cannot update schema status - schema not found with id={schema_id} or db_id={db_id}")
                return None
        
        # Update status fields if provided
        if db_id is not None:
            schema.db_id = db_id
            
        if schema_generated is not None:
            schema.schema_generated = schema_generated
            
        if db_loaded is not None:
            schema.db_loaded = db_loaded
            
        # Always update the timestamp
        schema.updated_at = datetime.now()

        # Generate a new generation ID
        schema.generation_id = str(uuid.uuid4())
        # Commit changes
        db.commit()
        
        print(f"DEBUG: Schema record updated: schema_id={schema.id}, db_id={schema.db_id}, schema_generated={schema.schema_generated}, db_loaded={schema.db_loaded}, generation_id={schema.generation_id}")
        return schema
        
    except Exception as update_error:
        print(f"WARNING: Failed to update schema record: {update_error}")
        return None
    finally:
        # Close the session if we created it
        if session_created and db is not None:
            db.close()
            print("DEBUG: Closed database session created for schema status update")

# Utility function to reset all schemas with a specific db_id to default values
def reset_schemas_for_db_id(target_db_id, db=None):
    """
    Reset all schemas associated with a specific db_id to default values.
    
    Args:
        target_db_id: The database ID to search for and reset
        db: Database session. If None, a new session will be created
        
    Returns:
        dict: Result summary with count of schemas updated and any errors
    """
    # Create a database session if none is provided
    session_created = False
    updated_count = 0
    errors = []
    
    try:
        if db is None:
            db = SessionLocal()
            session_created = True
            print(f"DEBUG: Created new database session for batch schema reset of db_id={target_db_id}")
        
        # Find all schemas with the target db_id
        schemas = db.query(Schema).filter(Schema.db_id == target_db_id).all()
        
        if not schemas:
            print(f"WARNING: No schemas found with db_id={target_db_id}")
            return {"updated": 0, "errors": [f"No schemas found with db_id={target_db_id}"]}
        
        print(f"DEBUG: Found {len(schemas)} schemas with db_id={target_db_id}")
        
        # Update each schema with default values
        for schema in schemas:
            try:
                schema.db_id = "na"
                schema.schema_generated = "no"
                schema.db_loaded = "no"
                schema.updated_at = datetime.now()
                updated_count += 1
                print(f"DEBUG: Reset schema: id={schema.id}, name={schema.name} to default values")
            except Exception as schema_error:
                error_msg = f"Failed to reset schema id={schema.id}: {str(schema_error)}"
                print(f"WARNING: {error_msg}")
                errors.append(error_msg)
        
        # Commit all changes at once
        db.commit()
        print(f"DEBUG: Successfully reset {updated_count} schemas with db_id={target_db_id} to default values")
        
    except Exception as batch_error:
        error_msg = f"Batch schema reset failed: {str(batch_error)}"
        print(f"ERROR: {error_msg}")
        errors.append(error_msg)
        # Try to rollback if possible
        if 'db' in locals() and db is not None:
            try:
                db.rollback()
                print("DEBUG: Transaction rolled back")
            except:
                pass
    finally:
        # Close the session if we created it
        if session_created and db is not None:
            db.close()
            print(f"DEBUG: Closed database session for batch schema reset of db_id={target_db_id}")
    
    return {
        "updated": updated_count,
        "errors": errors
    }

# Models
class SchemaResult(BaseModel):
    schema: dict
    cypher: str

class FilePathInput(BaseModel):
    file_path: str

class SourceIdInput(BaseModel):
    source_id: str
    metadata: str = None  # Optional metadata about the data
    file_path: str = None  # Add file_path field to accept path from frontend
    domain: str = None  # Data domain (e.g., 'telecom_churn', 'foam_factory')

class SaveSchemaInput(BaseModel):
    schema: dict
    output_path: str = None  # Optional output path, if not provided will use default location
    csv_file_path: str = None  # Path to the original CSV file used to generate the schema

class SaveSchemaResponse(BaseModel):
    message: str
    file_path: str

class RefineSchemaInput(BaseModel):
    source_id: str
    current_schema: dict
    feedback: str
    file_path: str = None  # Optional file path, similar to SourceIdInput
    domain: str = None  # Data domain (e.g., 'telecom_churn', 'foam_factory')

class ApplySchemaInput(BaseModel):
    schema_id: int
    graph_name: str = "default"  # Default graph name to apply schema to
    drop_existing: bool = False  # Whether to drop existing constraints and indexes

class LoadDataInput(BaseModel):
    schema_id: int
    data_path: str = ''  # Optional path to data source - empty string instead of None
    use_source_data: bool = True  # Whether to use the original source data
    graph_name: str = "default"  # Default graph name to load data into
    batch_size: int = 1000  # Number of records to process in each batch
    drop_existing: bool = False  # Whether to drop existing data before loading

# Router
router = APIRouter(prefix="/graphschema", tags=["graphschema"])

# Initialize LLM
# Initialize the LLM variable
llm = None

# Try to initialize Google Gemini LLM
try:
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        print("Warning: GOOGLE_API_KEY environment variable is not set")
    else:
        llm = ChatGoogleGenerativeAI(
            model='gemini-1.5-pro',
            google_api_key=api_key,
            temperature=0
        )
        print("Successfully initialized Google Gemini LLM")
except Exception as e:
    print(f"Warning: Could not initialize Google Gemini LLM: {e}")

# Helper Functions
def read_domain_data(domain_name):
    """Read domain-specific data from text files"""
    if not domain_name:
        return ""
        
    # Map domain names to file paths
    domain_files = {
        "telecom_churn": "TelecomChurnDomain.txt",
        "foam_factory": "FoamFactoryDomain.txt"
    }
    
    # Get the file path for the domain
    file_name = domain_files.get(domain_name.lower())
    if not file_name:
        print(f"WARNING: Unknown domain: {domain_name}")
        return ""
    
    # Construct the full file path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, file_name)
    
    # Check if the file exists
    if not os.path.exists(file_path):
        print(f"WARNING: Domain file not found: {file_path}")
        return ""
    
    # Read the domain data from the file
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            domain_data = f.read().strip()
        print(f"DEBUG: Successfully read domain data from {file_path}")
        return domain_data
    except Exception as e:
        print(f"ERROR: Failed to read domain file {file_path}: {str(e)}")
        return ""

def format_schema_response(schema, cypher):
    """Format schema and cypher data for frontend consumption"""
    # Ensure schema has necessary structure
    formatted_schema = schema
    # If schema is a string (JSON), try to parse it
    if isinstance(schema, str):
        try:
            formatted_schema = json.loads(schema)
        except json.JSONDecodeError:
            print(f"Warning: Could not decode schema as JSON: {schema}")
            formatted_schema = {
                'nodes': [],
                'relationships': [],
                'indexes': []
            }
    
    # Ensure essential schema properties are present
    if not isinstance(formatted_schema, dict):
        formatted_schema = {
            'nodes': [],
            'relationships': [],
            'indexes': []
        }
    
    if 'nodes' not in formatted_schema:
        formatted_schema['nodes'] = []
    if 'relationships' not in formatted_schema:
        formatted_schema['relationships'] = []
    if 'indexes' not in formatted_schema:
        formatted_schema['indexes'] = []
    
    # Convert node properties from array format to object format expected by frontend
    for node in formatted_schema['nodes']:
        if 'properties' in node and isinstance(node['properties'], list):
            # Convert from [{"name": "prop1", "type": "string"}] to {"prop1": "string"}
            properties_obj = {}
            for prop in node['properties']:
                if isinstance(prop, dict) and 'name' in prop and 'type' in prop:
                    properties_obj[prop['name']] = prop['type']
            node['properties'] = properties_obj
    
    # Convert source/target to startNode/endNode in relationships
    for rel in formatted_schema['relationships']:
        if 'source' in rel and 'startNode' not in rel:
            rel['startNode'] = rel['source']
            # Keep source for backward compatibility
        if 'target' in rel and 'endNode' not in rel:
            rel['endNode'] = rel['target']
            # Keep target for backward compatibility
        
        # Convert relationship properties from array format to object format if needed
        if 'properties' in rel and isinstance(rel['properties'], list):
            properties_obj = {}
            for prop in rel['properties']:
                if isinstance(prop, dict) and 'name' in prop and 'type' in prop:
                    properties_obj[prop['name']] = prop['type']
            rel['properties'] = properties_obj
    
    # Convert indexes from complex objects to simple strings as expected by frontend
    # Frontend expects: indexes?: string[]
    if 'indexes' in formatted_schema and isinstance(formatted_schema['indexes'], list):
        # Check if indexes are in complex format (objects with label and properties)
        if formatted_schema['indexes'] and isinstance(formatted_schema['indexes'][0], dict):
            simplified_indexes = []
            for idx in formatted_schema['indexes']:
                if 'label' in idx and 'properties' in idx:
                    # Create a string representation like "Label(prop1, prop2)"
                    props_str = ", ".join(idx['properties']) if isinstance(idx['properties'], list) else str(idx['properties'])
                    simplified_indexes.append(f"{idx['label']}({props_str})")
            formatted_schema['indexes'] = simplified_indexes
    
    # Format cypher script if needed
    formatted_cypher = cypher
    if isinstance(cypher, dict) and 'cypher' in cypher:
        formatted_cypher = cypher['cypher']
        
    return formatted_schema, formatted_cypher

# API Routes
@router.get('/status')
async def get_status():
    """Return API status."""
    return {"status": "OK"}

@router.post('/build-schema', response_model=SchemaResult)
async def build_schema_from_path(file_input: FilePathInput):
    """Generate Neo4j schema from a file at the specified absolute path and return the results."""
    try:
        file_path = file_input.file_path
        
        # Validate file exists
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"File not found at path: {file_path}")
            
        # Validate file is a CSV
        if not file_path.lower().endswith('.csv'):
            raise HTTPException(status_code=400, detail="Only CSV files are supported")
        
        # Initialize agent with the provided file path
        agent_instance = GraphSchemaAgent(
            model=llm,
            csv_path=file_path,
            log=True,
            log_path='logs'
        )
        
        # Generate the schema
        response = agent_instance.invoke_agent()
        
        # Get the generated schema and cypher
        schema = agent_instance.get_schema()
        cypher = agent_instance.get_cypher() or ""
        
        # Format data to match what frontend expects
        formatted_schema, formatted_cypher = format_schema_response(schema, cypher)
        
        return {
            'schema': formatted_schema,
            'cypher': formatted_cypher,
            'csv_file_path': file_path  # Include the CSV file path in the response
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in build_schema_from_path: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Schema generation failed: {str(e)}")

@router.post('/build-schema-from-source', response_model=SchemaResult)
async def build_schema_from_source(
    source_input: SourceIdInput,
    current_user: User = Depends(has_any_permission(["kginsights:read", "datapuur:read"])),
    db: SessionLocal = Depends(get_db)
):
    """Generate Neo4j schema from a source ID and return the results."""
    print(f"DEBUG: build_schema_from_source called with source_id: {source_input.source_id}")
    try:
        source_id = source_input.source_id
        
        # Check if file_path is provided directly in the request
        if source_input.file_path:
            print(f"DEBUG: Using provided file path: {source_input.file_path}")
            file_path = source_input.file_path
            
            # Validate file exists
            if not os.path.exists(file_path):
                raise HTTPException(
                    status_code=404, 
                    detail=f"File not found at path: {file_path}. Current OS: {os.name}"
                )
                
            # Validate file is a CSV
            if not file_path.lower().endswith('.csv'):
                raise HTTPException(status_code=400, detail="Only CSV files are supported")
        else:
            # If file_path is not provided, try to get it from the source_id
            print(f"DEBUG: No file path provided, retrieving from source_id: {source_id}")
            
            # Query the database to get the file path from the source_id
            from models import UploadedFile, IngestionJob
            
            # Try to find the file in UploadedFile table
            uploaded_file = db.query(UploadedFile).filter(UploadedFile.id == source_id).first()
            
            if uploaded_file and uploaded_file.file_path:
                file_path = uploaded_file.file_path
                print(f"DEBUG: Found file path in UploadedFile: {file_path}")
            else:
                # Try to find the file in IngestionJob table
                ingestion_job = db.query(IngestionJob).filter(IngestionJob.id == source_id).first()
                
                if ingestion_job and ingestion_job.file_path:
                    file_path = ingestion_job.file_path
                    print(f"DEBUG: Found file path in IngestionJob: {file_path}")
                else:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Could not find file path for source_id: {source_id}"
                    )
            
            # Validate file exists
            if not os.path.exists(file_path):
                raise HTTPException(
                    status_code=404,
                    detail=f"File not found at path: {file_path}. Current OS: {os.name}"
                )

        # Additional debugging for file path
        print(f"DEBUG: File exists check passed for: {file_path}")
        print(f"DEBUG: File size: {os.path.getsize(file_path)} bytes")
        print(f"DEBUG: File is readable: {os.access(file_path, os.R_OK)}")
        
        # Try to read a few lines from the file to verify it's accessible
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                first_few_lines = ''.join([f.readline() for _ in range(3)])
                print(f"DEBUG: First few lines of file: {first_few_lines}")
        except Exception as e:
            print(f"WARNING: Could not read from file: {e}")

        # Process enhanced metadata if available
        metadata = source_input.metadata
        enhanced_metadata = {}
        
        try:
            # Check if metadata is a JSON string containing enhanced information
            if metadata and isinstance(metadata, str) and (metadata.startswith('{') or metadata.startswith('[')):
                enhanced_metadata = json.loads(metadata)
                print(f"DEBUG: Enhanced metadata parsed: {enhanced_metadata.keys()}")
                
                # Extract user prompt from enhanced metadata if available
                if isinstance(enhanced_metadata, dict) and "userPrompt" in enhanced_metadata:
                    metadata = enhanced_metadata["userPrompt"]
                    print(f"DEBUG: Extracted user prompt from metadata: {metadata}")
        except json.JSONDecodeError:
            # If not valid JSON, use as is (simple string)
            print(f"DEBUG: Using metadata as plain text: {metadata}")
            pass
        
        # Initialize agent with the provided file path and metadata
        print(f"DEBUG: Initializing GraphSchemaAgent with file_path: {file_path}")
        print(f"DEBUG: LLM type: {type(llm)}")
        print(f"DEBUG: Using domain: {source_input.domain}")
        
        # Read domain-specific data from text files
        domain_data = ""
        if source_input.domain:
            domain_data = read_domain_data(source_input.domain)
            print(f"DEBUG: Domain data length: {len(domain_data)} characters")
        
        try:
            # Set up initial state with domain information
            initial_state = {
                "csv_path": file_path,
                "messages": [],
                "data_info": None,
                "schema": None,
                "cypher": None,
                "error": None,
                "domain": source_input.domain  # Include domain information
            }
            
            agent_instance = GraphSchemaAgent(
                model=llm,
                csv_path=file_path,
                metadata=metadata,
                log=True,
                log_path='logs',
                domain=domain_data  # Pass domain data to the agent
            )
            print(f"DEBUG: GraphSchemaAgent initialized successfully")
            
            # Generate the schema
            print(f"DEBUG: Invoking GraphSchemaAgent with domain: {source_input.domain}")
            response = agent_instance.invoke_agent(initial_state)
            print(f"DEBUG: GraphSchemaAgent invoked successfully")
            
            # Get the generated schema and cypher
            schema = agent_instance.get_schema()
            cypher = agent_instance.get_cypher()
            
            print(f"DEBUG: Schema retrieved: {schema is not None}")
            print(f"DEBUG: Cypher retrieved: {cypher is not None}")
            
            if not schema:
                raise HTTPException(status_code=404, detail='Schema generation failed')
        except Exception as agent_error:
            print(f"ERROR: GraphSchemaAgent error: {str(agent_error)}")
            print(f"ERROR: Exception type: {type(agent_error).__name__}")
            print(f"ERROR: Exception traceback: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"Schema generation failed: {str(agent_error)}")
            
        # Ensure cypher is a string
        if cypher is None:
            cypher = ""
            
        # Format data to match what frontend expects
        formatted_schema, formatted_cypher = format_schema_response(schema, cypher)
        
        return {
            'schema': formatted_schema,
            'cypher': formatted_cypher,
            'csv_file_path': file_path  # Include the CSV file path in the response
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in build_schema_from_source: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Schema generation failed: {str(e)}")

@router.post('/refine-schema', response_model=SchemaResult)
async def refine_schema(
    refine_input: RefineSchemaInput,
    current_user: User = Depends(has_any_permission(["kginsights:read", "datapuur:read"])),
    db: SessionLocal = Depends(get_db)
):
    """Refine an existing Neo4j schema based on user feedback."""
    print(f"DEBUG: refine_schema called with source_id: {refine_input.source_id}")
    try:
        source_id = refine_input.source_id
        
        # Check if file_path is provided directly in the request
        if refine_input.file_path:
            print(f"DEBUG: Using provided file path: {refine_input.file_path}")
            file_path = refine_input.file_path
            
            # Validate file exists
            if not os.path.exists(file_path):
                raise HTTPException(
                    status_code=404, 
                    detail=f"File not found at path: {file_path}. Current OS: {os.name}"
                )
                
            # Validate file is a CSV
            if not file_path.lower().endswith('.csv'):
                raise HTTPException(status_code=400, detail="Only CSV files are supported")
        else:
            # If file_path not provided, get it from the database (legacy approach)
            print(f"DEBUG: No file path provided, retrieving from database")
            
            # Get the ingestion job
            job = db.query(IngestionJob).filter(IngestionJob.id == source_id).first()
            print(f"DEBUG: Found job: {job is not None}")
            if not job:
                raise HTTPException(status_code=404, detail=f"Source not found with ID: {source_id}")
                
            # Get the file path from the job config
            config = json.loads(job.config) if job.config else {}
            print(f"DEBUG: Job config: {config}")
            
            # Currently only supporting file sources
            if job.type == "file":
                # Get the file path
                file_id = config.get("file_id")
                if not file_id:
                    raise HTTPException(status_code=400, detail="No file ID found in job config")
                    
                # Get the file record
                file_record = db.query(UploadedFile).filter(UploadedFile.id == file_id).first()
                if not file_record:
                    raise HTTPException(status_code=404, detail=f"File not found with ID: {file_id}")
                    
                # Build the file path
                file_path = file_record.path
                print(f"DEBUG: File path from database: {file_path}")
            else:
                raise HTTPException(status_code=400, detail="Only file sources are supported")
        
        # Handle different OS path formats (for both direct and database paths)
        try:
            if os.name == 'nt' and file_path.startswith('/'):
                # This is a Unix path but we're on Windows
                # Extract the filename and use the local uploads directory
                filename = os.path.basename(file_path)
                file_path = os.path.join(os.path.abspath("api/uploads"), filename)
                print(f"DEBUG: Converted path for Windows: {file_path}")
            elif os.name != 'nt' and '\\' in file_path:
                # Convert Windows path to Unix path if needed
                file_path = file_path.replace('\\', '/')
                print(f"DEBUG: Converted path for Unix: {file_path}")
        except Exception as e:
            raise HTTPException(
                status_code=400, 
                detail=f"File path error: {str(e)}. The file appears to be from a different operating system."
            )
        
        # Validate file exists
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=404, 
                detail=f"File not found at path: {file_path}. Current OS: {os.name}"
            )
        
        # Validate file is a CSV
        if not file_path.lower().endswith('.csv'):
            raise HTTPException(status_code=400, detail="Only CSV files are supported")
        
        # Additional debugging for file path
        print(f"DEBUG: File exists check passed for: {file_path}")
        print(f"DEBUG: File size: {os.path.getsize(file_path)} bytes")
        print(f"DEBUG: File is readable: {os.access(file_path, os.R_OK)}")
        
        # Try to read a few lines from the file to verify it's accessible
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                first_few_lines = ''.join([f.readline() for _ in range(3)])
                print(f"DEBUG: First few lines of file: {first_few_lines}")
        except Exception as e:
            print(f"WARNING: Could not read from file: {e}")
        
        # Use the already initialized Google Gemini model
        # This uses the global 'llm' variable initialized at the module level
        # Try to initialize a fresh instance for refinement
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            raise HTTPException(status_code=500, detail="GOOGLE_API_KEY environment variable is not set")
            
        try:
            model_instance = ChatGoogleGenerativeAI(
                model='gemini-1.5-pro',
                google_api_key=api_key,
                temperature=0.2  # Slightly higher temperature for refinement
            )
            print("Successfully initialized Google Gemini LLM for schema refinement")
        except Exception as e:
            print(f"Error initializing Google Gemini LLM: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to initialize LLM: {str(e)}")
        
        # Read domain-specific data from text files
        domain_data = ""
        if refine_input.domain:
            domain_data = read_domain_data(refine_input.domain)
            print(f"DEBUG: Domain data length: {len(domain_data)} characters")
        
        # Initialize agent with the provided file path and current schema
        agent_instance = GraphSchemaAgent(
            model=model_instance,
            csv_path=file_path,
            metadata=refine_input.feedback,  # User feedback for schema refinement
            current_schema=refine_input.current_schema,  # Current schema to be refined
            log=True,
            log_path='logs',
            domain=domain_data  # Pass domain data to the agent
        )
        
        print(f"DEBUG: Refining schema with feedback: {refine_input.feedback}")
        print(f"DEBUG: Current schema structure: {json.dumps(refine_input.current_schema, indent=2)[:200]}...")
        
        # Explicitly set up the initial state to ensure current_schema is included
        initial_state = {
            "csv_path": file_path,
            "messages": [],
            "data_info": None,
            "schema": None,
            "cypher": None,
            "error": None,
            "current_schema": refine_input.current_schema,  # Explicitly include current schema in initial state
            "domain": refine_input.domain  # Include domain information
        }
        
        print(f"DEBUG: Using domain: {refine_input.domain}")
        
        # Run the agent to refine the schema with the explicit initial state
        agent_instance.invoke_agent(initial_state)
        
        # Get the refined schema and Cypher
        schema = agent_instance.get_schema()
        cypher = agent_instance.get_cypher()
        
        if not schema:
            raise HTTPException(status_code=500, detail="Failed to refine schema")
            
        # Ensure cypher is a string
        if cypher is None:
            cypher = ""
            
        # Format data to match what frontend expects
        formatted_schema, formatted_cypher = format_schema_response(schema, cypher)
            
        return {
            "schema": formatted_schema,
            "cypher": formatted_cypher,
            "csv_file_path": file_path  # Include the CSV file path in the response
        }
    except HTTPException as e:
        raise
    except Exception as e:
        print(f"Error in refine_schema: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Schema refinement failed: {str(e)}")

@router.post('/apply-schema', response_model=dict)
async def apply_schema_to_neo4j(
    apply_input: ApplySchemaInput,
    current_user: User = Depends(has_any_permission(["kginsights:write"])),
    db: SessionLocal = Depends(get_db)
):
    """Apply a saved schema to Neo4j."""
    try:
        print(f"DEBUG: Starting apply_schema_to_neo4j with input: {apply_input}")
        schema_id = apply_input.schema_id
        graph_name = 'default_graph'
        drop_existing = apply_input.drop_existing
        
        # Get the schema from the database
        print(f"DEBUG: Fetching schema with ID: {schema_id}")
        schema = db.query(Schema).filter(Schema.id == schema_id).first()
        if not schema:
            print(f"DEBUG: Schema not found with ID: {schema_id}")
            raise HTTPException(status_code=404, detail=f"Schema not found with ID: {schema_id}")
        
        # Get the schema content
        print(f"DEBUG: Schema found: {schema.name}")
        try:
            # Check if schema.schema is already a dictionary or a JSON string
            if isinstance(schema.schema, dict):
                schema_content = schema.schema
            else:
                schema_content = json.loads(schema.schema) if schema.schema else {}
            
            print(f"DEBUG: Schema content loaded successfully. Keys: {list(schema_content.keys())}")
            print(f"DEBUG: Full schema content: {json.dumps(schema_content, indent=2)[:1000]}...")
            
            # Check if the schema contains the expected structure
            if 'nodes' in schema_content:
                print(f"DEBUG: Schema contains {len(schema_content.get('nodes', []))} nodes")
            if 'relationships' in schema_content:
                print(f"DEBUG: Schema contains {len(schema_content.get('relationships', []))} relationships")
            if 'cypher' in schema_content:
                print(f"DEBUG: Schema contains cypher statements of length: {len(schema_content.get('cypher', ''))}")
            else:
                print(f"DEBUG: Schema does not contain 'cypher' key. Attempting to generate cypher from nodes and relationships.")
                # If cypher is not present but nodes and relationships are, we can generate the cypher
                if 'nodes' in schema_content and 'relationships' in schema_content:
                    # Generate Cypher statements from nodes and relationships
                    cypher_statements = []
                    created_indexes = set()  # Initialize the set to track created indexes
                    
                    # Create node labels and constraints
                    nodes = schema_content.get('nodes', [])
                    if isinstance(nodes, list):
                        node_labels_created = set()  # Track which node labels we've already created
                        for node in nodes:
                            if isinstance(node, dict):
                                node_label = node.get('label')
                                if node_label and node_label not in node_labels_created:
                                    node_labels_created.add(node_label)
                                    properties = node.get('properties', {})
                                    
                                    # Handle properties as dictionary or list
                                    if isinstance(properties, dict):
                                        id_properties = [p for p in ['id', 'ID', 'Id', 'CustomerID', 'customer_id'] if p in properties]
                                        # Comment out constraint creation
                                        # if id_properties:
                                        #     id_property = id_properties[0]
                                        #     # Use IF NOT EXISTS to avoid errors if constraint already exists
                                        #     cypher_statements.append(
                                        #         f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{node_label}) REQUIRE n.{id_property} IS UNIQUE"
                                        #     )
                                            
                                        # Comment out index creation
                                        # if node_label not in created_indexes:
                                        #     cypher_statements.append(
                                        #         f"CREATE INDEX IF NOT EXISTS FOR (n:{node_label}) ON (n.id)"
                                        #     )
                                        #     created_indexes.add(node_label)
                                            
                                        # Add a node creation example with properties
                                        prop_list = []
                                        for i, (k, v) in enumerate(properties.items()):
                                            if i >= 3:  # Limit to 3 properties for brevity
                                                break
                                            if isinstance(v, str):
                                                prop_list.append(f"{k}: 'example-{k.lower()}'")
                                            elif v in ["integer", "float", "number"]:
                                                prop_list.append(f"{k}: 0")
                                            elif v == "boolean":
                                                prop_list.append(f"{k}: false")
                                            else:
                                                prop_list.append(f"{k}: 'example'")
                                        
                                        # Always include id property
                                        props = f"id: 'example-{node_label.lower()}-id'"
                                        if prop_list:
                                            props += ", " + ", ".join(prop_list)
                                        
                                        # Use the node label as part of the variable name to make it unique
                                        var_name = node_label.lower()
                                        cypher_statements.append(
                                            f"CREATE ({var_name}:{node_label} {{{props}}})"
                                        )
                                
                                    elif isinstance(properties, list):
                                        # If properties is a list, look for property with name 'id'
                                        id_property = next((p.get('name') for p in properties if p.get('name') in ['id', 'ID', 'Id', 'CustomerID', 'customer_id']), None)
                                        if id_property:
                                            # Comment out constraint creation
                                            # if id_properties:
                                            #     id_property = id_properties[0]
                                            #     # Use IF NOT EXISTS to avoid errors if constraint already exists
                                            #     cypher_statements.append(
                                            #         f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{node_label}) REQUIRE n.{id_property} IS UNIQUE"
                                            #     )
                                                    
                                            # Comment out index creation
                                            # if node_label not in created_indexes:
                                            #     cypher_statements.append(
                                            #         f"CREATE INDEX IF NOT EXISTS FOR (n:{node_label}) ON (n.id)"
                                            #     )
                                            #     created_indexes.add(node_label)
                                            
                                            # Add a node creation example
                                            cypher_statements.append(
                                                f"CREATE ({node_label.lower()}:{node_label} {{id: 'example-{node_label.lower()}-id'}})"
                                            )
                    
                    # Create relationship types
                    for rel in schema_content.get('relationships', []):
                        rel_type = rel.get('type')
                        source_label = rel.get('source')
                        target_label = rel.get('target')
                        if rel_type and source_label and target_label:
                            # Comment out index creation
                            # if source_label not in created_indexes:
                            #     cypher_statements.append(
                            #         f"CREATE INDEX IF NOT EXISTS FOR (n:{source_label}) ON (n.id)"
                            #     )
                            #     created_indexes.add(source_label)
                            
                            # if target_label not in created_indexes:
                            #     cypher_statements.append(
                            #         f"CREATE INDEX IF NOT EXISTS FOR (n:{target_label}) ON (n.id)"
                            #     )
                            #     created_indexes.add(target_label)
                            
                            # Add example of creating a relationship
                            cypher_statements.append(
                                f"MATCH ({source_label.lower()}:{source_label} {{id: 'example-{source_label.lower()}-id'}}), "
                                f"({target_label.lower()}:{target_label} {{id: 'example-{target_label.lower()}-id'}}) "
                                f"CREATE ({source_label.lower()})-[r:{rel_type}]->({target_label.lower()})"
                            )
                    
                    # Join Cypher statements
                    cypher = "\n".join(cypher_statements)
                    print(f"DEBUG: Generated cypher statements: {cypher}")
        except Exception as e:
            print(f"ERROR: Failed to parse schema JSON: {e}")
            print(f"ERROR: Schema content type: {type(schema.schema)}")
            print(f"ERROR: Schema content preview: {str(schema.schema)[:200]}")
            print(f"ERROR: Exception traceback: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"Failed to parse schema JSON: {e}")
        
        # Load Neo4j configuration
        print("DEBUG: Loading Neo4j configuration")
        config = get_database_config()
        print(f"DEBUG: Neo4j configuration loaded. Available graphs: {list(config.keys())}")
        
        # Get connection parameters for the specified graph
        graph_name = 'default_graph'
        print(f"DEBUG: Parsing connection parameters for graph: {graph_name}")
        
        connection_params = parse_connection_params(config.get(graph_name, {}))
        print(f"DEBUG: Connection params type: {type(connection_params)}")
        print(f"DEBUG: Connection params: {connection_params}")
        
        # Extract connection parameters
        uri = connection_params.get('uri')
        username = connection_params.get('username')
        password = connection_params.get('password')
        database = connection_params.get('database', 'neo4j')
        
        print("DEBUG: Parsed connection parameters:")
        print(f"DEBUG: URI: {uri}")
        print(f"DEBUG: Username: {username}")
        print(f"DEBUG: Password: {'*' * 8}")
        print(f"DEBUG: Database: {database}")
        
        # Connect to Neo4j
        print(f"DEBUG: Connecting to Neo4j at {uri} with database {database}")
        
        # Create Neo4j driver
        print("DEBUG: Creating Neo4j driver")
        driver = GraphDatabase.driver(uri, auth=(username, password))
        print("DEBUG: Neo4j driver created successfully")
        
        try:
            # Create session
            print(f"DEBUG: Creating Neo4j session with database: {database}")
            session = driver.session(database=database)
            print("DEBUG: Neo4j session created successfully")
            
            # Clean up existing schema elements if drop_existing is True
            if apply_input.drop_existing:
                print("DEBUG: Dropping existing schema elements (constraints, indexes, nodes, relationships)")
                try:
                    # Try to use APOC if available for schema cleanup
                    try:
                        print("DEBUG: Attempting to use APOC to drop constraints and indexes")
                        session.run("CALL apoc.schema.assert({},{},true)")
                        print("DEBUG: Successfully used APOC to drop constraints and indexes")
                    except Exception as e:
                        print(f"WARNING: APOC library not available, using standard Cypher to drop constraints: {e}")
                        # Get all constraints
                        print("DEBUG: Fetching all constraints")
                        constraints = session.run("SHOW CONSTRAINTS").data()
                        print(f"DEBUG: Found {len(constraints)} constraints")
                        for constraint in constraints:
                            constraint_name = constraint.get('name')
                            if constraint_name:
                                print(f"DEBUG: Dropping constraint {constraint_name}")
                                session.run(f"DROP CONSTRAINT {constraint_name} IF EXISTS")
                        
                        # Get all indexes
                        print("DEBUG: Fetching all indexes")
                        indexes = session.run("SHOW INDEXES").data()
                        print(f"DEBUG: Found {len(indexes)} indexes")
                        for index in indexes:
                            index_name = index.get('name')
                            if index_name:
                                print(f"DEBUG: Dropping index {index_name}")
                                # Commenting out index dropping as requested
                                # session.run(f"DROP INDEX {index_name} IF EXISTS")
                    
                    # Delete all nodes and relationships
                    print("DEBUG: Deleting all nodes and relationships")
                    session.run("MATCH (n) DETACH DELETE n")
                    print("DEBUG: Successfully deleted all nodes and relationships")
                    
                except Exception as e:
                    print(f"WARNING: Error cleaning up existing schema elements: {e}")
            
            # Extract Cypher statements from schema
            print("DEBUG: Extracting Cypher statements from schema")
            
            # Process and split Cypher statements
            cypher = schema_content.get('cypher', '')
            if not cypher:
                # If no cypher is provided, use the generated statements
                cypher = "\n".join(cypher_statements)
            
            print(f"DEBUG: Cypher statements length: {len(cypher)}")
            print(f"DEBUG: First 200 characters of Cypher: {cypher[:200]}")
            
            # Split Cypher statements by semicolon or newline
            cypher_statements = []
            if cypher:
                # Split by semicolon or newline
                statements = re.split(r';\s*|\n+', cypher)
                cypher_statements = [stmt.strip() for stmt in statements if stmt.strip()]
            
            print(f"DEBUG: Found {len(cypher_statements)} Cypher statements to execute")
            
            # Execute Cypher statements
            statements_executed = 0
            statements_succeeded = 0
            statements_failed = 0
            
            for i, stmt in enumerate(cypher_statements):
                if not stmt:
                    continue
                    
                statements_executed += 1
                print(f"DEBUG: Executing Cypher [{i+1}/{len(cypher_statements)}]: {stmt[:100]}...")
                
                try:
                    session.run(stmt)
                    statements_succeeded += 1
                except Exception as e:
                    statements_failed += 1
                    print(f"ERROR: Error executing Cypher statement {i+1}: {str(e)}")
                    
            
            # Log the activity
            activity_log = {
                "schema_id": apply_input.schema_id,
                "graph_name": apply_input.graph_name,
                "statements_executed": len(cypher_statements),
                "statements_succeeded": statements_succeeded,
                "statements_failed": statements_failed,
                "timestamp": datetime.now().isoformat()
            }
            
            if statements_failed:
                print(f"WARNING: Schema applied with {statements_failed} errors. Activity log: {json.dumps(activity_log)}")
                return {
                    "success": True,
                    "message": f"Schema applied to Neo4j graph '{graph_name}' with {statements_failed} errors",
                    "details": {
                        "statements_executed": len(cypher_statements),
                        "statements_succeeded": statements_succeeded,
                        "statements_failed": statements_failed,
                        "errors": [],
                        "schema_id": apply_input.schema_id
                    }
                }
            else:
                # Update schema record to mark as generated and store the graph_name as db_id
                update_schema_status(
                    db=db,
                    schema=schema,
                    db_id=graph_name,
                    schema_generated='yes',
                    db_loaded='no'
                )
                    
                print(f"DEBUG: Schema applied successfully. Activity log: {json.dumps(activity_log)}")
                return {
                    "success": True,
                    "message": f"Schema applied to Neo4j graph '{graph_name}' successfully",
                    "details": {
                        "statements_executed": len(cypher_statements),
                        "schema_id": apply_input.schema_id
                    }
                }
        finally:
            # Close the session and driver
            if 'session' in locals():
                session.close()
            driver.close()
            print("DEBUG: Neo4j driver closed")
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR: Unhandled exception in apply_schema_to_neo4j: {e}")
        print(f"ERROR: Exception type: {type(e).__name__}")
        print(f"ERROR: Exception traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to apply schema to Neo4j: {e}")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in apply_schema_to_neo4j: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to apply schema: {e}")

@router.post('/save-schema', response_model=SaveSchemaResponse)
async def save_schema(
    save_input: SaveSchemaInput,
    current_user: User = Depends(has_any_permission(["kginsights:write"])),
    db: SessionLocal = Depends(get_db)
):
    """Save the generated schema to the database and as a JSON file."""
    try:
        print(f"DEBUG: save_schema called with schema data :  {save_input} ")
        
        schema_data = save_input.schema
        csv_file_path = save_input.csv_file_path
        
        # Store CSV file path in schema data if provided
        if csv_file_path:
            schema_data['csv_file_path'] = csv_file_path
            print(f"DEBUG: Storing CSV file path in schema: {csv_file_path}")
        
        # Ensure schema has a name
        if not schema_data.get('name'):
            schema_data['name'] = f"Schema_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            print(f"DEBUG: Using default name: {schema_data['name']}")
        
        # Check if schema with the same name already exists
        schema_name = schema_data.get('name')
        existing_schema = db.query(Schema).filter(Schema.name == schema_name).first()
        if existing_schema:
            error_message = f"Schema with name '{schema_name}' already exists. Please use a different name."
            print(f"ERROR: {error_message}")
            # Return 409 Conflict with detailed error message
            raise HTTPException(
                status_code=409, 
                detail=error_message
            )
        
        # Ensure schema has a source_id
        if not schema_data.get('source_id'):
            print(f"WARNING: No source_id provided in schema data")
            schema_data['source_id'] = "unknown_source"
        
        # Ensure schema has Cypher statements
        if not schema_data.get('cypher'):
            print(f"DEBUG: No cypher statements found in schema. Generating from nodes and relationships.")
            
            # Generate Cypher statements from nodes and relationships
            cypher_statements = []
            
            # Create node labels and constraints
            for node in schema_data.get('nodes', []):
                node_label = node.get('label')
                if node_label:
                    # Create node label constraint on id property if it exists
                    properties = node.get('properties', {})
                    
                    # Handle properties as dictionary or list
                    if isinstance(properties, dict):
                        id_properties = [p for p in ['id', 'ID', 'Id', 'CustomerID', 'customer_id'] if p in properties]
                        # Comment out constraint creation
                        # if id_properties:
                        #     id_property = id_properties[0]
                        #     # Use IF NOT EXISTS to avoid errors if constraint already exists
                        #     cypher_statements.append(
                        #         f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{node_label}) REQUIRE n.{id_property} IS UNIQUE"
                        #     )
                            
                        # Comment out index creation
                        # if node_label not in created_indexes:
                        #     cypher_statements.append(
                        #         f"CREATE INDEX IF NOT EXISTS FOR (n:{node_label}) ON (n.id)"
                        #     )
                        #     created_indexes.add(node_label)
                            
                        # Add a node creation example with properties
                        prop_list = []
                        for i, (k, v) in enumerate(properties.items()):
                            if i >= 3:  # Limit to 3 properties for brevity
                                break
                            if isinstance(v, str):
                                prop_list.append(f"{k}: 'example-{k.lower()}'")
                            elif v in ["integer", "float", "number"]:
                                prop_list.append(f"{k}: 0")
                            elif v == "boolean":
                                prop_list.append(f"{k}: false")
                            else:
                                prop_list.append(f"{k}: 'example'")
                        
                        # Always include id property
                        props = f"id: 'example-{node_label.lower()}-id'"
                        if prop_list:
                            props += ", " + ", ".join(prop_list)
                        
                        # Use the node label as part of the variable name to make it unique
                        var_name = node_label.lower()
                        cypher_statements.append(
                            f"CREATE ({var_name}:{node_label} {{{props}}})"
                        )
                
                elif isinstance(properties, list):
                    # If properties is a list, look for property with name 'id'
                    id_property = next((p.get('name') for p in properties if p.get('name') in ['id', 'ID', 'Id', 'CustomerID', 'customer_id']), None)
                    if id_property:
                        # Comment out constraint creation
                        # if id_properties:
                        #     id_property = id_properties[0]
                        #     # Use IF NOT EXISTS to avoid errors if constraint already exists
                        #     cypher_statements.append(
                        #         f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{node_label}) REQUIRE n.{id_property} IS UNIQUE"
                        #     )
                                
                        # Comment out index creation
                        # if node_label not in created_indexes:
                        #     cypher_statements.append(
                        #         f"CREATE INDEX IF NOT EXISTS FOR (n:{node_label}) ON (n.id)"
                        #     )
                        #     created_indexes.add(node_label)
                        
                        # Add a node creation example
                        cypher_statements.append(
                            f"CREATE ({node_label.lower()}:{node_label} {{id: 'example-{node_label.lower()}-id'}})"
                        )
        
            # Create relationship types
            created_indexes = set()
            for rel in schema_data.get('relationships', []):
                rel_type = rel.get('type')
                source_label = rel.get('source')
                target_label = rel.get('target')
                if rel_type and source_label and target_label:
                    # Comment out index creation
                    # if source_label not in created_indexes:
                    #     cypher_statements.append(
                    #         f"CREATE INDEX IF NOT EXISTS FOR (n:{source_label}) ON (n.id)"
                    #     )
                    #     created_indexes.add(source_label)
                    
                    # if target_label not in created_indexes:
                    #     cypher_statements.append(
                    #         f"CREATE INDEX IF NOT EXISTS FOR (n:{target_label}) ON (n.id)"
                    #     )
                    #     created_indexes.add(target_label)
                    
                    # Add example of creating a relationship
                    cypher_statements.append(
                        f"MATCH ({source_label.lower()}:{source_label} {{id: 'example-{source_label.lower()}-id'}}), "
                        f"({target_label.lower()}:{target_label} {{id: 'example-{target_label.lower()}-id'}}) "
                        f"CREATE ({source_label.lower()})-[r:{rel_type}]->({target_label.lower()})"
                    )
            
            # Join all statements
            if cypher_statements:
                schema_data['cypher'] = ';\n'.join(cypher_statements) + ';'
                print(f"DEBUG: Generated cypher statements: {schema_data['cypher'][:200]}...")
            else:
                # Add a minimal placeholder if we couldn't generate anything
                schema_data['cypher'] = "// No schema elements to create"
                print(f"WARNING: Could not generate cypher statements from schema")
            
        # Create schemas directory if it doesn't exist
        schemas_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saved_schemas")
        os.makedirs(schemas_dir, exist_ok=True)
        
        # Generate a filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        schema_name = schema_data.get('name', 'unnamed').replace(' ', '_').lower()
        output_path = os.path.join(schemas_dir, f"{schema_name}_{timestamp}.json")
        
        # Write the schema to the file
        with open(output_path, 'w') as f:
            json.dump(schema_data, f, indent=2)
            
        print(f"DEBUG: Schema saved to file: {output_path}")
        
        try:
            # Save schema to database
            schema_record = Schema(
                name=schema_data.get('name', f"schema_{datetime.now().isoformat()}"),
                source_id=str(current_user.id),  # Using user ID as source_id
                description=schema_data.get('description', ''),
                schema=json.dumps(save_input.schema),
                csv_file_path=save_input.csv_file_path
                # created_at and updated_at have default values
            )
            db.add(schema_record)
            db.commit()
            print(f"DEBUG: Schema record created: {schema_record}")
            return {
            'message': f'Schema "{schema_data.get("name")}" saved successfully',
            'file_path': output_path
            }
        except Exception as db_error:
            print(f"WARNING: Could not save schema to database: {db_error}")
            # Continue even if database save fails - we still have the file
            raise HTTPException(status_code=500, detail=f"Failed to save schema:")
        

    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR in save_schema: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save schema: {e}")

@router.get('/schemas', response_model=list)
async def get_schemas(
    current_user: User = Depends(has_any_permission(["kginsights:read", "datapuur:read"])),
    db: SessionLocal = Depends(get_db)
):
    """Get all saved schemas from the database."""
    try:
        # Query all schemas from the database
        schemas = db.query(Schema).order_by(Schema.created_at.desc()).all()
        print("DEBUG: Fetched schemas:")
        for schema in schemas:
            print(f"DEBUG: Schema {schema.id}: {schema.name} (source_id={schema.source_id})")
            
        # Format the schemas for the frontend
        result = []
        for schema in schemas:
            try:
                schema_data = json.loads(schema.schema) if schema.schema else {}
                result.append({
                    "id": schema.id,
                    "name": schema.name,
                    "source_id": schema.source_id,
                    "description": schema.description or "",
                    "created_at": schema.created_at.isoformat() if schema.created_at else None,
                    "updated_at": schema.updated_at.isoformat() if schema.updated_at else None,
                    "csv_file_path": schema.csv_file_path or ""
                })
            except Exception as e:
                print(f"Error processing schema {schema.id}: {e}")
                # Skip this schema if there's an error
                continue
                
        return result
    except Exception as e:
        print(f"Error in get_schemas: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch schemas: {e}")

@router.get('/schemas/{schema_id}', response_model=dict)
async def get_schema(
    schema_id: int,
    current_user: User = Depends(has_any_permission(["kginsights:read", "datapuur:read"])),
    db: SessionLocal = Depends(get_db)
):
    """Get a specific schema by ID."""
    try:
        # Query the schema from the database
        schema = db.query(Schema).filter(Schema.id == schema_id).first()
        
        if not schema:
            print(f"ERROR: Schema {schema_id} not found")
            raise HTTPException(status_code=404, detail=f"Schema with ID {schema_id} not found")
        
        # Check for uploaded files if no CSV file path is specified
        csv_file_path = schema.csv_file_path or ""
        if not csv_file_path and schema.source_id:
            try:
                # Look for uploaded files - use the id field since UploadedFile doesn't have source_id
                # The schema.source_id might be the file ID in some cases
                uploaded_file = db.query(UploadedFile).filter(UploadedFile.id == schema.source_id).first()
                if uploaded_file and uploaded_file.path:
                    csv_file_path = uploaded_file.path
                    print(f"DEBUG: Found uploaded file for schema {schema_id}: {csv_file_path}")
                    
                    # Update the schema with this CSV file path for future use
                    schema.csv_file_path = csv_file_path
                    db.commit()
                    print(f"DEBUG: Updated schema with CSV file path from uploaded file")
            except Exception as e:
                print(f"DEBUG: Error checking for uploaded files: {e}")
                # Continue even if this check fails
        
        # Check for ingestion jobs if still no CSV file path
        if not csv_file_path and schema.source_id:
            try:
                # Look for ingestion jobs associated with this source_id
                ingestion_job = db.query(IngestionJob).filter(IngestionJob.source_id == schema.source_id).first()
                if ingestion_job and ingestion_job.file_path:
                    csv_file_path = ingestion_job.file_path
                    print(f"DEBUG: Found ingestion job for schema {schema_id}: {csv_file_path}")
                    
                    # Update the schema with this CSV file path for future use
                    schema.csv_file_path = csv_file_path
                    db.commit()
                    print(f"DEBUG: Updated schema with CSV file path from ingestion job")
            except Exception as e:
                print(f"DEBUG: Error checking for ingestion jobs: {e}")
                # Continue even if this check fails
            
        # Return the schema data
        return {
            "id": schema.id,
            "name": schema.name,
            "source_id": schema.source_id,
            "description": schema.description or "",
            "created_at": schema.created_at.isoformat() if schema.created_at else None,
            "updated_at": schema.updated_at.isoformat() if schema.updated_at else None,
            "schema": schema.schema,
            "csv_file_path": csv_file_path
        }
                
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_schema_by_id: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch schema: {e}")

@router.delete("/{schema_id}")
async def delete_schema(
    schema_id: str,
    current_user: User = Depends(has_any_permission(["kginsights:manage"])),
    db: SessionLocal = Depends(get_db)
):
    """
    Delete a schema by ID.
    
    First removes the database record, then cleans up any associated files.
    """
    try:
        # Validate schema ID
        try:
            schema_id_int = int(schema_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Schema ID must be an integer")
            
        # Get schema from database
        schema = db.query(Schema).filter(Schema.id == schema_id_int).first()
        if not schema:
            raise HTTPException(status_code=404, detail=f"Schema {schema_id} not found")
            
        # Store file paths before deletion
        files_to_clean = []
        if schema.csv_file_path and os.path.exists(schema.csv_file_path):
            files_to_clean.append(schema.csv_file_path)
            
        # Delete database record
        db.delete(schema)
        db.commit()
        
        # Clean up files
#        for file_path in files_to_clean:
#            try:
#                if os.path.exists(file_path):
#                    os.remove(file_path)
#            except Exception as e:
#                print(f"Warning: Could not delete file {file_path}: {str(e)}")
                
        return {"message": f"Schema {schema_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, 
            detail=f"Error deleting schema: {str(e)}"
        )

@router.post("/cleanup-schemas")
async def cleanup_schemas(
    current_user: User = Depends(has_any_permission(["kginsights:manage"])),
    db: SessionLocal = Depends(get_db)
):
    """
    Clean up the schemas table by removing entries where the associated CSV files don't exist.
    
    Args:
        current_user: Current authenticated user with manage permissions
        db: Database session
        
    Returns:
        Dict with cleanup results
    """
    try:
        # Get all schemas
        schemas = db.query(Schema).all()
        removed_count = 0
        preserved_count = 0
        
        for schema in schemas:
            # Check if CSV file exists
            # Normalize path for cross-platform compatibility
            csv_path = Path(schema.csv_file_path).resolve() if schema.csv_file_path else None
            if csv_path and not csv_path.exists():
                print(f"Removing schema {schema.id}: CSV file not found at {csv_path}")
                db.delete(schema)
                removed_count += 1
            else:
                preserved_count += 1
                
        # Commit changes
        db.commit()
        
        return {
            "message": f"Schema cleanup completed",
            "removed": removed_count,
            "preserved": preserved_count
        }
        
    except Exception as e:
        db.rollback()
        print(f"Error in cleanup_schemas: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error cleaning up schemas: {str(e)}")


@router.post("/clean-neo4j-database")
async def clean_neo4j_database(
    current_user: User = Depends(has_any_permission(["kginsights:manage"])),
    graph_name: str = "default_graph"
):
    """
    Clean the Neo4j database by removing all nodes, relationships, constraints, and indexes.
    
    Args:
        current_user: Current authenticated user with manage permissions
        graph_name: Name of the Neo4j graph to clean (default: "default")
        
    Returns:
        Dict with cleanup results
    """
    try:
        # Initialize Neo4j loader
        neo4j_loader = Neo4jLoader(graph_name=graph_name)
        
        # Connect to Neo4j
        connected = await neo4j_loader.connect()
        if not connected:
            raise HTTPException(status_code=500, detail="Failed to connect to Neo4j database")
            
        # Clean the database
        result = await neo4j_loader.clean_database()
        
        # Update schema record to mark database as cleaned
        reset_schemas_for_db_id(graph_name)
        
        # Close the connection
        neo4j_loader.close()
        
        if not result.get("success", False):
            errors = result.get("errors", [])
            error_message = "\n".join(errors) if errors else "Unknown error"
            raise HTTPException(status_code=500, detail=f"Failed to clean Neo4j database: {error_message}")
        
        return {
            "message": "Neo4j database cleaned successfully",
            "details": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error cleaning Neo4j database: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error cleaning Neo4j database: {str(e)}")

@router.post("/load-data")
@router.post("/schemas/{schema_id}/load-data")
async def load_data_to_neo4j(
    load_input: LoadDataInput = None,
    schema_id: int = None,
    graph_name: str = None,
    drop_existing: bool = False,
    current_user: User = Depends(has_any_permission(["kginsights:write"])),
    db: SessionLocal = Depends(get_db)
):
    """
    Load data into Neo4j from a CSV file based on a schema.
    
    Args:
        load_input: Input parameters for data loading
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Dict with loading results
    """
    try:
        # Handle both URL patterns
        # If called via /schemas/{schema_id}/load-data with query parameters
        if schema_id is not None and load_input is None:
            # Create load_input from path and query parameters
            load_input = LoadDataInput(
                schema_id=schema_id,
                graph_name=graph_name or "default_graph",
                drop_existing=drop_existing,
                use_source_data=True,
                data_path=''  # Empty string instead of None to avoid validation error
            )
            print(f"DEBUG: Using path parameters: schema_id={schema_id}, graph_name={graph_name}")
        
        print(f"DEBUG: Starting data loading process for schema ID: {load_input.schema_id}")
        
        # Validate schema_id
        schema = db.query(Schema).filter(Schema.id == load_input.schema_id).first()
        if not schema:
            raise HTTPException(status_code=404, detail=f"Schema with ID {load_input.schema_id} not found")
            
        # Determine data path and normalize for cross-platform compatibility
        data_path = None
        
        print(f"DEBUG: Using schema: {schema}, CSV Path : {schema.csv_file_path}")
        # Check if a custom data path was provided
        if load_input.data_path and load_input.data_path.strip():
            data_path = Path(load_input.data_path).resolve()
            print(f"DEBUG: Using provided data path: {data_path}")
            
        # If no custom path, try to use schema's CSV file path
        elif load_input.use_source_data:
            if schema.csv_file_path and schema.csv_file_path.strip():
                data_path = Path(schema.csv_file_path).resolve()
                print(f"DEBUG: Using CSV file path from schema: {data_path}")
            else:
                # Try to find a default sample CSV file
                sample_dir = Path(os.path.dirname(os.path.abspath(__file__))) / "samples"
                if sample_dir.exists():
                    # Look for CSV files in the samples directory
                    csv_files = list(sample_dir.glob("*.csv"))
                    if csv_files:
                        data_path = csv_files[0]  # Use the first CSV file found
                        print(f"DEBUG: Using default sample CSV file: {data_path}")
                        
                        # Update the schema with this CSV file path for future use
                        schema.csv_file_path = str(data_path)
                        db.commit()
                        print(f"DEBUG: Updated schema with CSV file path: {data_path}")
                    
        # If we still don't have a data path, check for uploaded files associated with the schema
        if not data_path and schema.source_id:
            try:
                # Check if there are any uploaded files with ID matching the source_id
                uploaded_file = db.query(UploadedFile).filter(UploadedFile.id == schema.source_id).first()
                if uploaded_file and uploaded_file.path:
                    data_path = Path(uploaded_file.path).resolve()
                    print(f"DEBUG: Using uploaded file path: {data_path}")
                    
                    # Update the schema with this CSV file path for future use
                    schema.csv_file_path = str(data_path)
                    db.commit()
                    print(f"DEBUG: Updated schema with CSV file path from uploaded file: {data_path}")
            except Exception as e:
                print(f"DEBUG: Error checking for uploaded files: {e}")
                # Continue with the process even if this check fails
                    
        # If we still don't have a data path, raise an error
        if not data_path:
            raise HTTPException(
                status_code=400, 
                detail="No data path available. Either provide data_path parameter, "
                       "update the schema with a csv_file_path, or upload a CSV file."
            )
                
        # Verify data path exists
        if not data_path.exists():
            raise HTTPException(
                status_code=400,
                detail=f"Data path does not exist: {data_path}"
            )
            
        # Initialize data loader
        loader = DataLoader(
            schema_id=load_input.schema_id,
            data_path=str(data_path),  # Convert Path to string
            graph_name=load_input.graph_name,
            batch_size=load_input.batch_size,
            drop_existing=load_input.drop_existing
        )
        
        # Load data
        print(f"DEBUG: Loading data from {data_path} into Neo4j graph {load_input.graph_name}")
        result = await loader.load_data(db)
        
        # Check for errors
        if result["status"] == "failed":
            error_message = "Data loading failed"
            if result["errors"]:
                error_message = f"Data loading failed: {result['errors'][0]}"
            raise HTTPException(status_code=500, detail=error_message)
        
        # Update schema record to mark data as loaded
        update_schema_status(
            db=db,
            schema=schema,
            db_id=load_input.graph_name,
            schema_id=load_input.schema_id,
            db_loaded='yes'
        )
            
        return {
            "message": "Data loaded successfully",
            "result": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR: Unhandled exception in load_data_to_neo4j: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error loading data: {str(e)}")

# Neo4j graphs endpoint removed - now using database configuration directly in other endpoints

@router.post("/schemas/{schema_id}/load-data")
async def load_data_from_schema(
    schema_id: int,
    graph_name: str = "default",
    drop_existing: bool = False,
    current_user: User = Depends(has_any_permission(["kginsights:write"])),
    db: SessionLocal = Depends(get_db)
):
    """
    Load data directly from a schema's associated file path.
    
    Args:
        schema_id: ID of the schema
        graph_name: Name of the Neo4j graph to load data into
        drop_existing: Whether to drop existing data in the graph
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Dict with loading results
    """
    try:
        print(f"DEBUG: Starting direct data loading process for schema ID: {schema_id}")
        
        # Validate schema_id
        schema = db.query(Schema).filter(Schema.id == schema_id).first()
        if not schema:
            raise HTTPException(status_code=404, detail=f"Schema with ID {schema_id} not found")
            
        # Check if schema has an associated file path
        if not schema.csv_file_path:
            raise HTTPException(
                status_code=400, 
                detail="Schema does not have an associated CSV file path"
            )
            
        # Initialize data loader
        loader = DataLoader(
            schema_id=schema_id,
            data_path=schema.csv_file_path,
            graph_name=graph_name,
            batch_size=1000,  # Default batch size
            drop_existing=drop_existing
        )
        
        # Load data
        print(f"DEBUG: Loading data from {schema.csv_file_path} into Neo4j graph {graph_name}")
        result = await loader.load_data(db)
        
        # Check for errors
        if result["status"] == "failed":
            error_message = "Data loading failed"
            if result["errors"]:
                error_message = f"Data loading failed: {result['errors'][0]}"
            raise HTTPException(status_code=500, detail=error_message)
        
        # Update schema record to mark data as loaded
        update_schema_status(
            db=db,
            schema=schema,
            db_id=graph_name,
            schema_generated='yes',
            db_loaded='yes'
        )
            
        return {
            "message": "Data loaded successfully",
            "result": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR: Unhandled exception in load_data_from_schema: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error loading data: {str(e)}")