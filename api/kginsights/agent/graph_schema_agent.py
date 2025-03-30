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

class AgentState(TypedDict):
    """Type definition for agent state."""
    csv_path: str
    messages: Sequence[BaseMessage]
    data_info: Optional[Dict]
    schema: Optional[Dict]
    cypher: Optional[str]
    error: Optional[str]

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
        human_in_the_loop: bool = False,
        log: bool = False,
        log_path: str = None,
        checkpointer = None
    ):
        self._params = {
            "model": model,
            "csv_path": csv_path,
            "human_in_the_loop": human_in_the_loop,
            "log": log,
            "log_path": log_path,
            "checkpointer": checkpointer
        }
        self._compiled_graph = self._make_compiled_graph()
        self.response = None
        self._graph = None

    def _validate_csv_data(self, df: pd.DataFrame) -> Dict:
        """Validate CSV data quality."""
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
            
        # Check for potential ID columns without unique values
        for col in df.columns:
            if col.lower().endswith(('_id', 'id')):
                if df[col].duplicated().any():
                    validation["warnings"].append(
                        f"Column '{col}' appears to be an ID but contains duplicate values"
                    )
                    
        # Check data types
        for col in df.columns:
            try:
                pd.to_numeric(df[col])
            except:
                pass
            else:
                if df[col].dtype == object:
                    validation["warnings"].append(
                        f"Column '{col}' contains numeric values but is stored as text"
                    )
                    
        return validation

    def _analyze_csv_data(self, csv_path: str) -> Dict:
        """Analyze CSV data for schema inference."""
        try:
            df = pd.read_csv(csv_path)
            
            # Basic validation
            validation = {"warnings": []}
            
            # Check for missing values
            null_counts = df.isnull().sum()
            columns_with_nulls = null_counts[null_counts > 0]
            if not columns_with_nulls.empty:
                for col in columns_with_nulls.index:
                    validation["warnings"].append(
                        f"Column '{col}' has {null_counts[col]} missing values"
                    )
            
            # Check for potential ID columns
            for col in df.columns:
                if "id" in col.lower():
                    unique_count = df[col].nunique()
                    total_count = len(df)
                    if unique_count < total_count:
                        validation["warnings"].append(
                            f"Column '{col}' appears to be an ID but contains duplicate values"
                        )
            
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

    def _make_compiled_graph(self):
        """Create the agent workflow graph."""
        
        def analyze_data(state: AgentState) -> AgentState:
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

        def infer_schema(state: AgentState) -> AgentState:
            """Use LLM to infer Neo4j schema from CSV data."""
            print("\nInferring schema...")
            if state.get("error") is not None:
                print(f"\nSkipping schema inference due to error: {state['error']}")
                return state
                
            llm = self._params["model"]
            data_info = state["data_info"]
            
            print("\nData info being sent to LLM:")
            print(json.dumps(data_info, indent=2))
            
            prompt = PromptTemplate(
                template="""You are a Neo4j database expert. Analyze this CSV data and generate an optimal graph schema.

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
- Add indexes for properties that will be frequently queried""",
                input_variables=["data_info"]
            )
            
            print("\nSending request to LLM...")
            formatted_prompt = prompt.format(data_info=data_info)
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
                
                # Validate schema is valid JSON
                schema = json.loads(result_content)
                
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

        def generate_cypher(state: AgentState) -> AgentState:
            """Generate Cypher statements for schema creation."""
            print("\nGenerating Cypher statements...")
            if "error" in state:
                return state
                
            schema = state["schema"]
            cypher = []
            
            # Node constraints and indexes
            for node in schema["nodes"]:
                label = node["label"]
                for prop in node["properties"]:
                    if "UNIQUE" in prop.get("constraints", []):
                        cypher.append(
                            f"CREATE CONSTRAINT {label}_{prop['name']}_unique "
                            f"IF NOT EXISTS FOR (n:{label}) REQUIRE n.{prop['name']} IS UNIQUE"
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

        # Build the workflow graph with state schema
        workflow = StateGraph(state_schema=AgentState)
        
        # Add nodes
        workflow.add_node("analyze_data", analyze_data)
        workflow.add_node("infer_schema", infer_schema)
        workflow.add_node("generate_cypher", generate_cypher)
        
        # Add edges
        workflow.add_edge("analyze_data", "infer_schema")
        workflow.add_edge("infer_schema", "generate_cypher")
        workflow.add_edge("generate_cypher", END)
        
        # Set entry point
        workflow.set_entry_point("analyze_data")
        
        return workflow.compile()

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
