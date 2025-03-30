from fastapi import APIRouter, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from .agent.graph_schema_agent import GraphSchemaAgent
from langchain_openai import ChatOpenAI
import os
import io
import json
from datetime import datetime
from sqlalchemy.orm import Session
from ..models import get_db, IngestionJob
from ..auth import has_any_permission
from ..models import User

# Models
class SchemaResult(BaseModel):
    schema: dict
    cypher: str

class FilePathInput(BaseModel):
    file_path: str

class SourceIdInput(BaseModel):
    source_id: str

class SaveSchemaInput(BaseModel):
    schema: dict
    output_path: str = None  # Optional output path, if not provided will use default location

class SaveSchemaResponse(BaseModel):
    message: str
    file_path: str

# Router
router = APIRouter(prefix="/graphschema", tags=["graphschema"])

# Initialize LLM
try:
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")
    
    llm = ChatOpenAI(
        model='gpt-4',
        api_key=api_key,
        temperature=0
    )
    print("Successfully initialized OpenAI LLM")
except Exception as e:
    print(f"Warning: Could not initialize OpenAI LLM: {e}")
    # Create a placeholder LLM for development/testing
    from unittest.mock import MagicMock
    llm = MagicMock()
    llm.invoke.return_value = {"content": "This is a mock response as OpenAI API key is not configured."}

# Helper Functions
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
        if not schema:
            raise HTTPException(status_code=404, detail='Schema generation failed')
            
        cypher = agent_instance.get_cypher() or ""
        
        # Format data to match what frontend expects
        formatted_schema, formatted_cypher = format_schema_response(schema, cypher)
        
        return {
            'schema': formatted_schema,
            'cypher': formatted_cypher
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in build_schema_from_path: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Schema generation failed: {str(e)}")

@router.post('/build-schema-from-source', response_model=SchemaResult)
async def build_schema_from_source(
    source_input: SourceIdInput,
    current_user: User = Depends(has_any_permission(["kginsights:read", "data:read"])),
    db: Session = Depends(get_db)
):
    """Generate Neo4j schema from a source ID and return the results."""
    print(f"DEBUG: build_schema_from_source called with source_id: {source_input.source_id}")
    try:
        source_id = source_input.source_id
        
        # Get the ingestion job
        job = db.query(IngestionJob).filter(IngestionJob.id == source_id).first()
        print(f"DEBUG: Found job: {job is not None}")
        if not job:
            raise HTTPException(status_code=404, detail=f"Source not found with ID: {source_id}")
            
        # Get the file path from the job config
        config = json.loads(job.config) if job.config else {}
        print(f"DEBUG: Job config: {config}")
        
        if job.type == "file" and "file_id" in config:
            from ..models import UploadedFile
            file_id = config["file_id"]
            file_info = db.query(UploadedFile).filter(UploadedFile.id == file_id).first()
            print(f"DEBUG: Found file info: {file_info is not None}")
            
            if not file_info:
                raise HTTPException(status_code=404, detail=f"File not found for source ID: {source_id}")
                
            file_path = file_info.path
            print(f"DEBUG: File path: {file_path}")
            
            # Detect if the file path is from a different OS and handle it
            if os.name == 'posix' and '\\' in file_path:  # Running on Mac/Linux but Windows path
                print(f"WARNING: Windows path detected on a {os.name} system.")
                # Convert Windows path to a relative path if possible
                try:
                    relative_path = os.path.basename(file_path)
                    # Try to find the file in a local uploads directory
                    local_path = os.path.join(os.path.dirname(__file__), '..', '..', 'uploads', relative_path)
                    if os.path.exists(local_path):
                        file_path = local_path
                        print(f"INFO: Found file at local path: {file_path}")
                    else:
                        print(f"ERROR: Could not find file at converted path: {local_path}")
                        raise HTTPException(
                            status_code=400, 
                            detail=f"File path is from Windows but running on {os.name}. Please upload the file on this system."
                        )
                except Exception as e:
                    print(f"ERROR in path conversion: {str(e)}")
                    raise HTTPException(
                        status_code=400, 
                        detail=f"File path error: {str(e)}. The file appears to be from a different operating system."
                    )
            elif os.name == 'nt' and '/' in file_path:  # Running on Windows but Unix path
                print(f"WARNING: Unix path detected on a {os.name} system.")
                # Convert Unix path to Windows path
                try:
                    # Extract the filename from the Unix path
                    relative_path = os.path.basename(file_path.replace('/', '\\'))
                    # Try to find the file in a local uploads directory
                    local_path = os.path.join(os.path.dirname(__file__), '..', 'uploads', relative_path)
                    if os.path.exists(local_path):
                        file_path = local_path
                        print(f"INFO: Found file at local path: {file_path}")
                    else:
                        # Try alternative path
                        alt_path = os.path.join(os.getcwd(), 'api', 'uploads', relative_path)
                        if os.path.exists(alt_path):
                            file_path = alt_path
                            print(f"INFO: Found file at alternative path: {file_path}")
                        else:
                            print(f"ERROR: Could not find file at converted paths: {local_path} or {alt_path}")
                            raise HTTPException(
                                status_code=404, 
                                detail=f"File not found. Could not locate {relative_path} in uploads directory."
                            )
                except Exception as e:
                    print(f"ERROR in path conversion: {str(e)}")
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
        else:
            raise HTTPException(status_code=400, detail="Only file sources are supported")
        
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
        if not schema:
            raise HTTPException(status_code=404, detail='Schema generation failed')
            
        cypher = agent_instance.get_cypher() or ""
        
        # Format data to match what frontend expects
        formatted_schema, formatted_cypher = format_schema_response(schema, cypher)
        
        return {
            'schema': formatted_schema,
            'cypher': formatted_cypher
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in build_schema_from_source: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Schema generation failed: {str(e)}")

@router.post('/save-schema', response_model=SaveSchemaResponse)
async def save_schema(save_input: SaveSchemaInput):
    """Save the generated schema JSON to a file on the server."""
    try:
        schema = save_input.schema
        
        # Create a default output path if none provided
        if not save_input.output_path:
            # Create schemas directory if it doesn't exist
            schemas_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saved_schemas")
            os.makedirs(schemas_dir, exist_ok=True)
            
            # Generate a filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(schemas_dir, f"schema_{timestamp}.json")
        else:
            output_path = save_input.output_path
            
            # Ensure the directory exists
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            
            # Validate the output path ends with .json
            if not output_path.lower().endswith('.json'):
                output_path += '.json'
        
        # Write the schema to the file
        with open(output_path, 'w') as f:
            json.dump(schema, f, indent=2)
        
        return {
            'message': 'Schema saved successfully',
            'file_path': output_path
        }
    except Exception as e:
        print(f"Error in save_schema: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to save schema: {str(e)}")