"""
Neo4j Graph Schema Agent for generating graph schemas from CSV data.
"""
from typing import Dict, List, Optional, TypedDict, Sequence
import pandas as pd
import networkx as nx
import plotly.graph_objects as go
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
import json
import os

class AgentState(TypedDict):
    """Type definition for agent state."""
    csv_path: str
    messages: Sequence[BaseMessage]
    data_info: Optional[Dict]
    schema: Optional[Dict]
    cypher: Optional[str]
    error: Optional[str]
    domain: Optional[str]  # Domain information for schema generation

class GraphSchemaAgent:
    """
    Agent that analyzes CSV data and generates Neo4j graph schemas using LLM.
    
    Features:
    - CSV data analysis and validation
    - Entity and relationship identification
    - Neo4j schema generation
    - Property type inference
    - Index recommendations
    - Schema visualization
    """
    
    def __init__(
        self,
        model,
        csv_path: str = None,
        metadata: str = None,
        current_schema: dict = None,
        human_in_the_loop: bool = False,
        log: bool = False,
        log_path: str = None,
        checkpointer = None,
        domain: str = None
    ):
        self._params = {
            "model": model,
            "csv_path": csv_path,
            "metadata": metadata,
            "current_schema": current_schema,
            "human_in_the_loop": human_in_the_loop,
            "log": log,
            "log_path": log_path,
            "checkpointer": checkpointer,
            "domain": domain
        }
        self._compiled_graph = self._make_compiled_graph()
        self.response = None
        self._graph = None

    def _validate_csv_data(self, df: pd.DataFrame) -> Dict:
        """Validate CSV data quality."""
        print(f"DEBUG: Validating CSV data with shape: {df.shape}")
        validation = {
            "is_valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Check for empty dataframe
        if df.empty:
            validation["is_valid"] = False
            validation["errors"].append("CSV file is empty")
            return validation
            
        # Check for missing values
        missing = df.isnull().sum()
        if missing.any():
            validation["warnings"].extend([
                f"Column '{col}' has {count} missing values"
                for col, count in missing[missing > 0].items()
            ])
            
        # Check for potential ID columns
        for col in df.columns:
            if "id" in col.lower():
                unique_count = df[col].nunique()
                total_count = len(df)
                if unique_count < total_count:
                    validation["warnings"].append(
                        f"Column '{col}' appears to be an ID but contains duplicate values"
                    )
        
        print(f"DEBUG: Validation complete. Valid: {validation['is_valid']}, Warnings: {len(validation['warnings'])}, Errors: {len(validation['errors'])}")
        return validation

    def _analyze_csv_data(self, csv_path: str) -> Dict:
        """Analyze CSV data for schema inference."""
        print(f"DEBUG: Analyzing CSV file at path: {csv_path}")
        print(f"DEBUG: File exists: {os.path.exists(csv_path)}")
        print(f"DEBUG: File size: {os.path.getsize(csv_path) if os.path.exists(csv_path) else 'N/A'} bytes")
        
        try:
            # Try different encodings if the default fails
            encodings = ['utf-8', 'latin1', 'cp1252', 'ISO-8859-1']
            df = None
            exception = None
            
            for encoding in encodings:
                try:
                    print(f"DEBUG: Attempting to read CSV with encoding: {encoding}")
                    df = pd.read_csv(csv_path, encoding=encoding)
                    print(f"DEBUG: Successfully read CSV with encoding: {encoding}")
                    break
                except Exception as e:
                    print(f"DEBUG: Failed to read CSV with encoding {encoding}: {str(e)}")
                    exception = e
            
            if df is None:
                print(f"ERROR: Failed to read CSV with all attempted encodings")
                return {
                    "is_valid": False,
                    "error": f"Failed to read CSV file: {str(exception)}",
                    "num_columns": 0,
                    "num_rows": 0,
                    "validation": {"warnings": [], "errors": [f"Failed to read CSV file: {str(exception)}"]}
                }
            
            print(f"DEBUG: Successfully loaded CSV with shape: {df.shape}")
            
            # Basic validation
            validation = self._validate_csv_data(df)
            
            # Get basic data info
            sample_data = df.head(5).to_dict(orient='records')
            # Convert sample data to strings for better LLM processing
            for row in sample_data:
                for key, value in row.items():
                    row[key] = str(value)
            
            data_info = {
                "num_rows": len(df),
                "num_columns": len(df.columns),
                "columns": list(df.columns),
                "sample_data": sample_data,
                "data_types": {
                    col: str(dtype) for col, dtype in df.dtypes.items()
                },
                "validation": validation
            }
            
            return data_info
            
        except Exception as e:
            return {
                "is_valid": False,
                "error": str(e),
                "validation": {"warnings": []}
            }

    def _transform_schema_format(self, schema):
        """
        Transform schema from the API format to the format expected by the LLM prompt.
        
        API format:
        {
            "nodes": [
                {
                    "label": "Customer",
                    "properties": {
                        "CustomerID": "string",
                        "Gender": "string"
                    }
                }
            ]
        }
        
        LLM expected format:
        {
            "nodes": [
                {
                    "label": "Customer",
                    "properties": [
                        {"name": "CustomerID", "type": "string", "constraints": ["UNIQUE"]},
                        {"name": "Gender", "type": "string", "constraints": []}
                    ]
                }
            ]
        }
        """
        if not schema:
            return None
            
        transformed = {
            "nodes": [],
            "relationships": [],
            "indexes": []
        }
        
        # Transform nodes
        if "nodes" in schema:
            for node in schema["nodes"]:
                transformed_node = {
                    "label": node["label"],
                    "properties": []
                }
                
                # Transform properties from object to array
                if "properties" in node:
                    props = node["properties"]
                    if isinstance(props, dict):
                        for prop_name, prop_type in props.items():
                            # Check if this property might be a unique identifier
                            constraints = []
                            if prop_name.lower().endswith('id') or prop_name.lower() == 'id':
                                constraints = ["UNIQUE"]
                                
                            transformed_node["properties"].append({
                                "name": prop_name,
                                "type": prop_type,
                                "constraints": constraints
                            })
                    elif isinstance(props, list):
                        # Already in the right format
                        transformed_node["properties"] = props
                        
                transformed["nodes"].append(transformed_node)
        
        # Transform relationships
        if "relationships" in schema:
            for rel in schema["relationships"]:
                transformed_rel = {
                    "type": rel["type"],
                    "source": rel["source"],
                    "target": rel["target"],
                    "properties": []
                }
                
                # Transform properties if they exist
                if "properties" in rel:
                    props = rel["properties"]
                    if isinstance(props, dict):
                        for prop_name, prop_type in props.items():
                            transformed_rel["properties"].append({
                                "name": prop_name,
                                "type": prop_type
                            })
                    elif isinstance(props, list):
                        # Already in the right format
                        transformed_rel["properties"] = props
                        
                transformed["relationships"].append(transformed_rel)
        
        # Transform indexes
        if "indexes" in schema:
            transformed["indexes"] = schema["indexes"]
            
        return transformed

    def _make_compiled_graph(self):
        """Create the agent workflow graph."""
        
        # Define the workflow
        workflow = StateGraph(AgentState)
        
        # Add nodes to the graph
        workflow.add_node("analyze_data", self.analyze_data)
        workflow.add_node("infer_schema", self.infer_schema)
        workflow.add_node("generate_cypher", self.generate_cypher)
        
        # Define the edges
        workflow.add_edge("analyze_data", "infer_schema")
        workflow.add_edge("infer_schema", "generate_cypher")
        
        # Set the entry point
        workflow.set_entry_point("analyze_data")
        
        # Return the compiled graph
        return workflow.compile()

    def analyze_data(self, state: AgentState) -> AgentState:
        """Analyze CSV data and prepare for schema inference."""
        print("\nAnalyzing CSV data...")
        csv_path = state["csv_path"]
        data_info = self._analyze_csv_data(csv_path)
        
        if not data_info.get("is_valid", True):
            error_msg = data_info.get("error", "Unknown error during CSV analysis")
            state["error"] = error_msg
            state["messages"] = state.get("messages", []) + [
                AIMessage(content=f"Error: {error_msg}")
            ]
            return state
            
        state["data_info"] = data_info
        
        # Preserve current_schema in the state if it exists
        # This ensures it's available to the infer_schema function
        if "current_schema" in state and state["current_schema"] is not None:
            print(f"DEBUG: Preserving current_schema in state during analyze_data")
        elif self._params.get("current_schema") is not None:
            # If current_schema is not in state but is in params, add it to state
            state["current_schema"] = self._params.get("current_schema")
            print(f"DEBUG: Adding current_schema from params to state")
        
        print(f"\nData analysis complete. Found {data_info['num_columns']} columns and {data_info['num_rows']} rows.")
        state["messages"] = state.get("messages", []) + [
            AIMessage(content="CSV data analyzed successfully")
        ]
        
        # Add validation warnings
        if data_info["validation"]["warnings"]:
            print("\nValidation warnings:")
            for warning in data_info["validation"]["warnings"]:
                print(f"- {warning}")
            state["messages"].extend([
                AIMessage(content=f"Warning: {warning}")
                for warning in data_info["validation"]["warnings"]
            ])
        
        return state

    def infer_schema(self, state: AgentState) -> AgentState:
        """Use LLM to infer Neo4j schema from CSV data."""
        print("\nInferring schema...")
        if state.get("error") is not None:
            print(f"\nSkipping schema inference due to error: {state['error']}")
            return state
            
        llm = self._params["model"]
        data_info = state["data_info"]
        
        print("\nData info being sent to LLM:")
        print(json.dumps(data_info, indent=2))
        
        # First check if current_schema is in state
        current_schema = state.get("current_schema")
        
        # If not in state, check if it's in params
        if current_schema is None:
            current_schema = self._params.get("current_schema")
            if current_schema:
                print(f"DEBUG: Using current_schema from params in infer_schema")
                # Add it to state for future steps
                state["current_schema"] = current_schema
        
        if current_schema:
            print("\nUsing refinement prompt with existing schema")
            
            # Transform the schema to the format expected by the LLM prompt
            transformed_schema = self._transform_schema_format(current_schema)
            if transformed_schema:
                print(f"\nTransformed schema format for LLM compatibility")
                current_schema = transformed_schema
                print(f"DEBUG: Transformed schema: {json.dumps(current_schema, indent=2)[:200]}...")
            
            # Use refinement prompt
            prompt = PromptTemplate(
                template="""You are a Neo4j database expert. Analyze this CSV data and refine the existing graph schema based on user feedback.

User feedback:
{metadata_section}

Domain Metadata:
{domain_section}

Current Schema:
{current_schema_section}

CSV Analysis:
- Columns: {data_info[columns]}
- Sample Data (first 5 rows): {data_info[sample_data]}
- Data Types: {data_info[data_types]}
- Number of Rows: {data_info[num_rows]}

Instructions:
1. Carefully review the user's feedback about the current schema
2. Make the requested modifications to the schema
3. Ensure the modified schema still accurately represents the data
4. Maintain appropriate relationships between entities
5. Keep any useful elements from the original schema that weren't mentioned in the feedback
6. Use the information provided in the domain metadata to guide the schema generation. This will be used to generate graphs and gather insights from the data.

Return ONLY a valid JSON object with this exact structure (no explanation, just the JSON):
{{
    "nodes": [
        {{
            "label": "string",
            "properties": [
                {{"name": "string", "type": "string", "constraints": ["string"]}}
            ]
        }}
    ],
    "relationships": [
        {{
            "type": "string",
            "source": "string",
            "target": "string",
            "properties": [
                {{"name": "string", "type": "string"}}
            ]
        }}
    ],
    "indexes": [
        {{"label": "string", "properties": ["string"]}}
    ],
    "changes": [
        {{"type": "added|removed|modified", "entity": "node|relationship|index", "details": "string"}}
    ]
}}

Notes:
- Use UNIQUE constraint for identifier properties
- Valid property types: string, integer, float, boolean, datetime
- Relationship types should be in UPPERCASE
- Choose meaningful and descriptive names for entities and relationships
- Add indexes for properties that will be frequently queried
- IMPORTANT: Always use the exact CSV column names as property names to ensure compatibility with the data loader
- DO NOT rename properties from their original CSV column names
- Include a "changes" array that describes what modifications were made based on the feedback""",
                input_variables=["data_info", "metadata_section", "domain_section", "current_schema_section"]
            )
            
            # Prepare metadata section
            metadata = self._params.get("metadata", "")
            metadata_section = ""
            if metadata:
                metadata_section = f"User Feedback:\n{metadata}\n"
            
            # Prepare domain section
            domain_section = ""
            # Use domain data directly from the params (which now contains the file content)
            domain_data = self._params.get("domain", "")
            if domain_data:
                domain_section = domain_data
            # Fallback to state domain if no domain data is available
            elif state.get("domain", ""):
                domain = state.get("domain", "")
                domain_section = f"Domain: {domain}"
            
            # Prepare current schema section
            current_schema_section = json.dumps(current_schema, indent=2)
            
            print("\nSending refinement request to LLM...")
            print(f"Current schema being sent: {current_schema_section[:200]}...")
            print(f"User feedback being sent: {metadata_section}")
            print(f"Domain information being sent: {domain_section}")
            
            formatted_prompt = prompt.format(
                data_info=data_info, 
                metadata_section=metadata_section,
                domain_section=domain_section,
                current_schema_section=current_schema_section
            )
        else:
            # Use standard schema generation prompt
            prompt = PromptTemplate(
                template="""You are a Neo4j database expert. Analyze this CSV data and generate an optimal graph schema.

User Inputs:
{metadata_section}

Domain Metadata:
{domain_section}

CSV Analysis:
- Columns: {data_info[columns]}
- Sample Data (first 5 rows): {data_info[sample_data]}
- Data Types: {data_info[data_types]}
- Number of Rows: {data_info[num_rows]}

Instructions:
1. Analyze the CSV structure and identify potential entities (nodes) based on the columns
2. Identify columns that could be unique identifiers for each entity
3. Determine meaningful relationships between the entities
4. Consider appropriate data types and constraints for properties
5. Recommend indexes for frequently queried properties
6. Use the information provided in the domain metadata to guide the schema generation. This will be used to generate graphs and gather insights from the data.

Return ONLY a valid JSON object with this exact structure (no explanation, just the JSON):
{{
    "nodes": [
        {{
            "label": "string",
            "properties": [
                {{"name": "string", "type": "string", "constraints": ["string"]}}
            ]
        }}
    ],
    "relationships": [
        {{
            "type": "string",
            "source": "string",
            "target": "string",
            "properties": [
                {{"name": "string", "type": "string"}}
            ]
        }}
    ],
    "indexes": [
        {{"label": "string", "properties": ["string"]}}
    ]
}}

Notes:
- Use UNIQUE constraint for identifier properties
- Valid property types: string, integer, float, boolean, datetime
- Relationship types should be in UPPERCASE
- Choose meaningful and descriptive names for entities and relationships
- Add indexes for properties that will be frequently queried
- IMPORTANT: Always use the exact CSV column names as property names to ensure compatibility with the data loader
- DO NOT rename properties from their original CSV column names""",
                input_variables=["data_info", "metadata_section"]
            )
            
            # Prepare metadata section
            metadata = self._params.get("metadata", "")
            metadata_section = ""
            if metadata:
                metadata_section = f"Metadata about the data:\n{metadata}\n"
            
            # Prepare domain section
            domain_section = ""
            # Use domain data directly from the params (which now contains the file content)
            domain_data = self._params.get("domain", "")
            if domain_data:
                domain_section = domain_data
            # Fallback to state domain if no domain data is available
            elif state.get("domain", ""):
                domain = state.get("domain", "")
                domain_section = f"Domain: {domain}"
            
            print("\nSending request to LLM...")
            formatted_prompt = prompt.format(data_info=data_info, metadata_section=metadata_section, domain_section=domain_section)
        
        print("\nFormatted prompt:")
        print(formatted_prompt)
        
        try:
            result = llm.invoke(formatted_prompt)
            
            # Handle different response formats (dict or object with content attribute)
            if isinstance(result, dict):
                result_content = result.get("content", json.dumps(result))
            else:
                result_content = result.content
            
            print(f"\nRaw LLM Response:\n{result_content}")
            
            # Extract JSON from the response if it's wrapped in markdown code blocks
            json_content = result_content
            
            # Check if the response is wrapped in markdown code blocks
            if "```json" in result_content and "```" in result_content:
                # Extract content between ```json and ```
                start_idx = result_content.find("```json") + 7
                end_idx = result_content.find("```", start_idx)
                if start_idx > 6 and end_idx > start_idx:
                    json_content = result_content[start_idx:end_idx].strip()
                    print(f"\nExtracted JSON from markdown:\n{json_content}")
            elif "```" in result_content:
                # Extract content between ``` and ```
                start_idx = result_content.find("```") + 3
                end_idx = result_content.find("```", start_idx)
                if start_idx > 2 and end_idx > start_idx:
                    json_content = result_content[start_idx:end_idx].strip()
                    print(f"\nExtracted JSON from markdown:\n{json_content}")
            
            # Validate schema is valid JSON
            try:
                schema = json.loads(json_content)
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
                # Try to clean the string and parse again
                cleaned_json = json_content.strip()
                # Remove any BOM or invisible characters at the beginning
                while cleaned_json and not cleaned_json[0] in '{["':
                    cleaned_json = cleaned_json[1:]
                
                # Fix common JSON issues (trailing commas, etc.)
                # 1. Fix trailing commas in arrays/objects
                cleaned_json = re.sub(r',\s*([\]\}])', r'\1', cleaned_json)
                # 2. Fix empty property arrays with trailing commas
                cleaned_json = re.sub(r'\{\s*"name":\s*"[^"]+"\s*,\s*"type":\s*"[^"]+"\s*,\s*\}', r'{"name": "Supplier", "type": "string"}', cleaned_json)
                
                print(f"\nCleaned JSON:\n{cleaned_json}")
                try:
                    schema = json.loads(cleaned_json)
                except json.JSONDecodeError as e2:
                    print(f"Still failed to parse JSON after cleaning: {e2}")
                    # Last resort: try to manually fix the JSON structure
                    try:
                        # Use a more permissive JSON parser or manually fix known issues
                        import re
                        # Remove trailing commas in lists and objects
                        fixed_json = re.sub(r',\s*([\]\}])', r'\1', cleaned_json)
                        schema = json.loads(fixed_json)
                        print("Successfully parsed JSON after additional fixing")
                    except Exception as e3:
                        print(f"All JSON parsing attempts failed: {e3}")
                        state["error"] = f"Failed to parse schema: {e2}"
                        state["messages"] = state.get("messages", []) + [
                            AIMessage(content=f"Error: Failed to parse schema - {e2}")
                        ]
                        return state
            # Validate schema structure
            required_keys = ["nodes", "relationships", "indexes"]
            for key in required_keys:
                if key not in schema:
                    raise ValueError(f"Missing required key: {key}")
            
            # Validate nodes
            if not isinstance(schema["nodes"], list):
                raise ValueError("'nodes' must be a list")
            for node in schema["nodes"]:
                if not all(k in node for k in ["label", "properties"]):
                    raise ValueError("Each node must have 'label' and 'properties'")
            
            # Validate relationships
            if not isinstance(schema["relationships"], list):
                raise ValueError("'relationships' must be a list")
            for rel in schema["relationships"]:
                if not all(k in rel for k in ["type", "source", "target"]):
                    raise ValueError("Each relationship must have 'type', 'source', and 'target'")
            
            state["schema"] = schema
            print("\nSchema validation successful")
        except (json.JSONDecodeError, ValueError) as e:
            print(f"\nError parsing schema: {e}")
            state["error"] = f"Failed to parse schema: {e}"
            state["messages"] = state.get("messages", []) + [
                AIMessage(content=f"Error: Failed to parse schema - {e}")
            ]
            return state
        except Exception as e:
            print(f"\nUnexpected error: {str(e)}")
            state["error"] = f"Unexpected error: {str(e)}"
            state["messages"] = state.get("messages", []) + [
                AIMessage(content=f"Error: Unexpected error - {str(e)}")
            ]
            return state
            
        state["messages"] = state.get("messages", []) + [
            AIMessage(content="Schema inference completed")
        ]
        return state

    def generate_cypher(self, state: AgentState) -> AgentState:
        """Generate Cypher statements for schema creation."""
        print("\nGenerating Cypher statements...")
        if "error" in state:
            # Even if there's an error, set an empty cypher string
            state["cypher"] = ""
            return state
            
        schema = state["schema"]
        cypher = []
        
        # Node constraints and indexes
        for node in schema["nodes"]:
            label = node["label"]
            # Create node creation statements
            props_list = []
            for prop in node["properties"]:
                prop_name = prop["name"]
                prop_type = prop["type"]
                props_list.append(f"{prop_name}: ${prop_name}")
                if "UNIQUE" in prop.get("constraints", []):
                    cypher.append(
                        f"CREATE CONSTRAINT {label}_{prop_name}_unique "
                        f"IF NOT EXISTS FOR (n:{label}) REQUIRE n.{prop_name} IS UNIQUE"
                    )
            
            # Add CREATE statement for this node type
            if props_list:
                props_str = ", ".join(props_list)
                cypher.append(f"// Create {label} nodes\nCREATE (n:{label} {{{props_str}}})")
        
        # Relationship creation statements
        for rel in schema["relationships"]:
            source = rel["source"]
            target = rel["target"]
            rel_type = rel["type"]
            
            # Add CREATE statement for this relationship type
            props_list = []
            if "properties" in rel and rel["properties"]:
                for prop in rel["properties"]:
                    prop_name = prop["name"]
                    props_list.append(f"{prop_name}: ${prop_name}")
            
            if props_list:
                props_str = ", ".join(props_list)
                cypher.append(
                    f"// Create {rel_type} relationships\n"
                    f"MATCH (a:{source}), (b:{target}) "
                    f"CREATE (a)-[r:{rel_type} {{{props_str}}}]->(b)"
                )
            else:
                cypher.append(
                    f"// Create {rel_type} relationships\n"
                    f"MATCH (a:{source}), (b:{target}) "
                    f"CREATE (a)-[r:{rel_type}]->(b)"
                )
        
        # Indexes
        for index in schema["indexes"]:
            props = ", ".join(index["properties"])
            cypher.append(
                f"CREATE INDEX {index['label']}_{'_'.join(index['properties'])}_idx "
                f"IF NOT EXISTS FOR (n:{index['label']}) ON (n.{props})"
            )
        
        state["cypher"] = "\n".join(cypher)
        print("\nCypher generation complete")
        state["messages"] = state.get("messages", []) + [
            AIMessage(content="Cypher generation completed")
        ]
        
        # Create NetworkX graph for visualization
        G = nx.DiGraph()
        
        # Add nodes
        for node in schema["nodes"]:
            G.add_node(node["label"], type="node", properties=node["properties"])
            
        # Add edges
        for rel in schema["relationships"]:
            G.add_edge(
                rel["source"],
                rel["target"],
                type="relationship",
                label=rel["type"],
                properties=rel.get("properties", [])
            )
        
        self._graph = G
        return state

    def invoke_agent(self, state: Dict = None):
        """Run the agent workflow."""
        if state is None:
            state = {
                "csv_path": self._params["csv_path"],
                "messages": [],
                "data_info": None,
                "schema": None,
                "cypher": None,
                "error": None
            }
        elif "csv_path" not in state and self._params["csv_path"]:
            state["csv_path"] = self._params["csv_path"]
            
        # If we're refining an existing schema, add it to the state
        current_schema = self._params.get("current_schema")
        if current_schema:
            # We'll use this as a starting point for refinement
            # The actual refinement happens in the infer_schema function
            print("Using existing schema as starting point for refinement")
            print(f"Current schema structure: {json.dumps(current_schema, indent=2)[:200]}...")
            # Store the current schema in the state so it can be accessed by the infer_schema function
            state["current_schema"] = current_schema
            
            # Also add it to self._params to ensure it's available throughout the workflow
            self._params["current_schema"] = current_schema
            
        self.response = self._compiled_graph.invoke(state)
        return self.response

    def get_schema(self) -> Dict:
        """Get the inferred Neo4j schema."""
        return self.response.get("schema") if self.response else None
    
    def get_cypher(self) -> str:
        """Get the generated Cypher statements."""
        return self.response.get("cypher") if self.response else None
        
    def get_validation_results(self) -> Dict:
        """Get data validation results."""
        if self.response and "data_info" in self.response:
            return self.response["data_info"].get("validation")
        return None
        
    def visualize_schema(self) -> go.Figure:
        """Create an interactive visualization of the schema."""
        if not self._graph:
            return None
            
        # Create Plotly figure
        pos = nx.spring_layout(self._graph)
        
        # Create edges (relationships)
        edge_x = []
        edge_y = []
        edge_text = []
        
        for edge in self._graph.edges(data=True):
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
            edge_text.append(edge[2]["label"])
            
        edges_trace = go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=1, color='#888'),
            hoverinfo='text',
            text=edge_text,
            mode='lines'
        )
        
        # Create nodes
        node_x = []
        node_y = []
        node_text = []
        
        for node in self._graph.nodes(data=True):
            x, y = pos[node[0]]
            node_x.append(x)
            node_y.append(y)
            props = [f"{p['name']}: {p['type']}" for p in node[1]["properties"]]
            node_text.append(f"{node[0]}<br>" + "<br>".join(props))
            
        nodes_trace = go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text',
            hoverinfo='text',
            text=node_text,
            marker=dict(
                size=20,
                line_width=2
            )
        )
        
        # Create figure
        fig = go.Figure(data=[edges_trace, nodes_trace],
                     layout=go.Layout(
                         title='Graph Schema Visualization',
                         showlegend=False,
                         hovermode='closest',
                         margin=dict(b=20,l=5,r=5,t=40),
                         xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                         yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
                     ))
                     
        return fig
