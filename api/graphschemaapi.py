from fastapi import APIRouter, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from agent.graph_schema_agent import GraphSchemaAgent
from langchain_openai import ChatOpenAI
import os
import plotly.graph_objects as go
import io
import base64
import json
from datetime import datetime

# Models
class SchemaResult(BaseModel):
    schema: dict
    cypher: str
    graph_image: str  # Base64 encoded image

class FilePathInput(BaseModel):
    file_path: str

class SaveSchemaInput(BaseModel):
    schema: dict
    output_path: str = None  # Optional output path, if not provided will use default location

class SaveSchemaResponse(BaseModel):
    message: str
    file_path: str

# Router
router = APIRouter(prefix="/api/graphschema", tags=["graphschema"])

# Initialize LLM
llm = ChatOpenAI(
    model='gpt-4',
    api_key=os.getenv('OPENAI_API_KEY'),
    temperature=0
)

# Helper Functions
def generate_graph_image(schema):
    """Generate Plotly graph image from schema"""
    if not schema or not isinstance(schema, dict):
        return None
        
    # Create nodes and edges
    nodes = [node.get('label', f'Node_{i}') for i, node in enumerate(schema.get('nodes', []))]
    edges = [(rel['startNode'], rel['endNode']) 
             for rel in schema.get('relationships', [])]
    
    # Create graph visualization
    edge_trace = go.Scatter(
        x=[], y=[], 
        line=dict(width=0.5, color='#888'),
        hoverinfo='none',
        mode='lines'
    )
    
    node_trace = go.Scatter(
        x=[], y=[],
        mode='markers+text',
        text=nodes,
        marker=dict(
            size=20,
            line=dict(width=2)
        )
    )
    
    # Add positions to nodes and edges
    for i, node in enumerate(nodes):
        node_trace['x'] += (i,)
        node_trace['y'] += (i % 2,)
        
    for edge in edges:
        x0, y0 = nodes.index(edge[0]), nodes.index(edge[0]) % 2
        x1, y1 = nodes.index(edge[1]), nodes.index(edge[1]) % 2
        edge_trace['x'] += (x0, x1, None)
        edge_trace['y'] += (y0, y1, None)
    
    fig = go.Figure(data=[edge_trace, node_trace],
                 layout=go.Layout(
                    showlegend=False,
                    hovermode='closest',
                    margin=dict(b=20,l=5,r=5,t=40),
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
                )
    
    # Convert to base64 image
    buf = io.BytesIO()
    fig.write_image(buf, format='png')
    return base64.b64encode(buf.getvalue()).decode('utf-8')



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
        
        # Generate graph image if schema is available
        try:
            graph_image = generate_graph_image(schema) if schema else ""
        except Exception as img_err:
            print(f"Error generating graph image: {str(img_err)}")
            graph_image = ""
        
        # Debug logging
        print(f"Schema: {schema}")
        print(f"Graph image generated: {bool(graph_image)}")
        print(f"Image length: {len(graph_image) if graph_image else 0}")
            
        return {
            'schema': schema,
            'cypher': cypher,
            'graph_image': graph_image
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in build_schema_from_path: {str(e)}")
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