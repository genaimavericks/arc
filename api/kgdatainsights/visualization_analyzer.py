"""
Visualization Analyzer for Knowledge Graph Insights
This module analyzes data from knowledge graph query results and determines
appropriate visualization types and formats data accordingly.
"""

import json
import os
from typing import Dict, List, Any, Optional, Union, Tuple
import logging
from pydantic import BaseModel, Field
import re
import ast
import numpy as np
from datetime import datetime
from enum import Enum
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain

# Load environment variables
load_dotenv()

# Configure logger
logger = logging.getLogger(__name__)

class VisualizationType(str, Enum):
    BAR = "bar"
    PIE = "pie"
    LINE = "line"
    HISTOGRAM = "histogram"
    HEATMAP = "heatmap"
    NONE = "none"  # When no visualization is appropriate

class AxisData(BaseModel):
    label: str
    values: List[Any]

class LLMVisualizationResponse(BaseModel):
    """Response format for the LLM visualization recommendation"""
    visualization_type: str = Field(description="The recommended visualization type (bar, pie, line, histogram, heatmap, or none)")
    title: str = Field(description="A descriptive title for the visualization")
    description: str = Field(description="Brief explanation of what the visualization shows")
    reasoning: str = Field(description="Your reasoning for choosing this visualization type")
    x_axis_label: Optional[str] = Field(None, description="Label for x-axis (if applicable)")
    y_axis_label: Optional[str] = Field(None, description="Label for y-axis (if applicable)")
    data_format: Optional[str] = Field(None, description="How the data should be transformed for visualization")

class GraphData(BaseModel):
    type: VisualizationType
    title: str
    description: Optional[str] = None
    x_axis: Optional[AxisData] = None
    y_axis: Optional[AxisData] = None
    labels: Optional[List[str]] = None
    values: Optional[List[float]] = None
    series: Optional[List[Dict[str, Any]]] = None
    raw_data: Optional[Dict[str, Any]] = None

def extract_numerical_data(text: str) -> Optional[List[float]]:
    """Extract numerical values from a text string."""
    number_pattern = r'-?\d+(?:\.\d+)?'
    matches = re.findall(number_pattern, text)
    
    if not matches:
        return None
    
    return [float(match) for match in matches]

def detect_data_structure(data: Any) -> Tuple[bool, Dict[str, Any]]:
    """
    Detect structured data in various formats and convert to a consistent format.
    Returns (is_structured, structured_data)
    """
    if isinstance(data, dict):
        return True, data
    
    if isinstance(data, list):
        # Check if this is a list of dictionaries with a common structure
        if all(isinstance(item, dict) for item in data):
            return True, {"items": data}
        
        # Check if this might be a list of values
        if all(isinstance(item, (int, float, str)) for item in data):
            return True, {"values": data}
    
    if isinstance(data, str):
        # Try to parse as JSON
        try:
            parsed = json.loads(data)
            return True, parsed
        except json.JSONDecodeError:
            pass
        
        # Try to parse as Python literal (dict, list, etc.)
        try:
            parsed = ast.literal_eval(data)
            if isinstance(parsed, (dict, list)):
                return detect_data_structure(parsed)
        except (SyntaxError, ValueError):
            pass
        
        # Check for tabular data with common delimiters
        if "\t" in data or "," in data:
            lines = data.strip().split("\n")
            if len(lines) > 1:
                delimiter = "\t" if "\t" in lines[0] else ","
                rows = [line.split(delimiter) for line in lines]
                headers = rows[0]
                data_rows = rows[1:]
                
                # Convert to list of dicts
                result = []
                for row in data_rows:
                    if len(row) >= len(headers):
                        result.append({headers[i]: value for i, value in enumerate(row)})
                
                if result:
                    return True, {"items": result, "headers": headers}
    
    # Not structured data we can recognize
    return False, {}

def suggest_visualization(data: Dict[str, Any]) -> GraphData:
    """
    Analyze data and suggest appropriate visualization type and format.
    """
    # Check for table or list-like data
    if "items" in data and isinstance(data["items"], list) and len(data["items"]) > 0:
        items = data["items"]
        
        # Check if items have consistent numerical keys that could be visualized
        if all(isinstance(item, dict) for item in items):
            # Find numerical columns
            numeric_columns = []
            category_columns = []
            
            # Sample the first item to find potential columns
            sample_item = items[0]
            
            for key, value in sample_item.items():
                # Check if all items have this column as numerical
                if all(isinstance(item.get(key, 0), (int, float)) for item in items):
                    numeric_columns.append(key)
                else:
                    # Check if it's a consistent string column - could be categories
                    if all(isinstance(item.get(key, ""), str) for item in items):
                        category_columns.append(key)
            
            # If we have one category column and one numeric column, bar chart might be good
            if len(category_columns) >= 1 and len(numeric_columns) >= 1:
                category_col = category_columns[0]
                numeric_col = numeric_columns[0]
                
                # Extract data for axes
                categories = [str(item.get(category_col, "")) for item in items]
                values = [float(item.get(numeric_col, 0)) for item in items]
                
                # If fewer than 8 categories, a pie chart could be appropriate
                if len(set(categories)) <= 8 and len(set(categories)) > 1:
                    return GraphData(
                        type=VisualizationType.PIE,
                        title=f"Distribution of {numeric_col} by {category_col}",
                        description=f"Pie chart showing {numeric_col} distribution across {category_col} categories",
                        labels=categories,
                        values=values,
                        raw_data=data
                    )
                    
                # Otherwise, a bar chart is more appropriate
                return GraphData(
                    type=VisualizationType.BAR,
                    title=f"{numeric_col} by {category_col}",
                    description=f"Bar chart showing {numeric_col} for each {category_col}",
                    x_axis=AxisData(label=category_col, values=categories),
                    y_axis=AxisData(label=numeric_col, values=values),
                    raw_data=data
                )
            
            # If we have date/time column and numeric column, line chart might be good
            date_columns = []
            for key in category_columns:
                # Check for date-like strings
                if any(item.get(key, "").count("-") >= 2 for item in items[:5]):
                    date_columns.append(key)
            
            if date_columns and numeric_columns:
                date_col = date_columns[0]
                numeric_col = numeric_columns[0]
                
                # Try to parse dates and sort chronologically
                date_items = []
                for item in items:
                    date_str = item.get(date_col, "")
                    try:
                        # Flexible date parsing
                        date_obj = date_str  # In a real implementation, convert to date
                        date_items.append((date_str, item))
                    except Exception:
                        date_items.append((date_str, item))
                
                # Sort by date string as a simple approach
                date_items.sort(key=lambda x: x[0])
                
                # Extract sorted data
                dates = [item[0] for item in date_items]
                values = [float(item[1].get(numeric_col, 0)) for item in date_items]
                
                return GraphData(
                    type=VisualizationType.LINE,
                    title=f"{numeric_col} Over Time",
                    description=f"Line chart showing {numeric_col} trend over time",
                    x_axis=AxisData(label=date_col, values=dates),
                    y_axis=AxisData(label=numeric_col, values=values),
                    raw_data=data
                )
            
            # If we have multiple numeric columns, consider a multi-series bar or line chart
            if len(numeric_columns) > 1 and category_columns:
                category_col = category_columns[0]
                
                # Create series data
                series = []
                categories = list(set(str(item.get(category_col, "")) for item in items))
                categories.sort()
                
                for numeric_col in numeric_columns[:3]:  # Limit to 3 series for readability
                    series_data = []
                    for category in categories:
                        matching_items = [item for item in items if str(item.get(category_col, "")) == category]
                        value = sum(float(item.get(numeric_col, 0)) for item in matching_items)
                        series_data.append(value)
                    
                    series.append({
                        "name": numeric_col,
                        "data": series_data
                    })
                
                return GraphData(
                    type=VisualizationType.BAR,
                    title=f"Comparison by {category_col}",
                    description=f"Multi-series bar chart comparing {', '.join(numeric_columns[:3])} by {category_col}",
                    x_axis=AxisData(label=category_col, values=categories),
                    series=series,
                    raw_data=data
                )
                
            # If we have two numeric columns, a scatter plot could be appropriate
            if len(numeric_columns) >= 2:
                x_col = numeric_columns[0]
                y_col = numeric_columns[1]
                
                x_values = [float(item.get(x_col, 0)) for item in items]
                y_values = [float(item.get(y_col, 0)) for item in items]
                
                return GraphData(
                    type=VisualizationType.LINE,  # Using line as proxy for scatter
                    title=f"Relationship between {x_col} and {y_col}",
                    description=f"Scatter plot showing relationship between {x_col} and {y_col}",
                    x_axis=AxisData(label=x_col, values=x_values),
                    y_axis=AxisData(label=y_col, values=y_values),
                    raw_data=data
                )
                
            # If we have a single numeric column, histogram could be appropriate
            if numeric_columns and len(items) >= 5:
                numeric_col = numeric_columns[0]
                values = [float(item.get(numeric_col, 0)) for item in items]
                
                # Create histogram bins
                bins = min(10, len(set(values)))
                hist, bin_edges = np.histogram(values, bins=bins)
                
                bin_labels = [f"{round(bin_edges[i], 2)}-{round(bin_edges[i+1], 2)}" for i in range(len(bin_edges)-1)]
                
                return GraphData(
                    type=VisualizationType.HISTOGRAM,
                    title=f"Distribution of {numeric_col}",
                    description=f"Histogram showing the distribution of {numeric_col} values",
                    x_axis=AxisData(label="Value Ranges", values=bin_labels),
                    y_axis=AxisData(label="Frequency", values=hist.tolist()),
                    raw_data=data
                )
    
    # Check for simple key-value pairs that could make a pie chart
    simple_kv_pairs = {}
    for key, value in data.items():
        if isinstance(value, (int, float)) and not key.startswith("_"):
            simple_kv_pairs[key] = value
    
    if len(simple_kv_pairs) >= 2 and len(simple_kv_pairs) <= 10:
        return GraphData(
            type=VisualizationType.PIE,
            title="Data Distribution",
            description="Pie chart showing the distribution of values",
            labels=list(simple_kv_pairs.keys()),
            values=list(simple_kv_pairs.values()),
            raw_data=data
        )
    
    # If we reach here, we couldn't find an appropriate visualization
    return GraphData(
        type=VisualizationType.NONE,
        title="No visualization available",
        description="The data structure doesn't match any supported visualization type",
        raw_data=data
    )

def get_llm_visualization_suggestion(data: Dict[str, Any]) -> Optional[LLMVisualizationResponse]:
    """
    Use LangChain's ChatOpenAI to analyze the data and suggest the best visualization type.
    
    Args:
        data: The structured data to analyze
        
    Returns:
        LLMVisualizationResponse object with the recommended visualization settings
    """
    try:
        # Create a parser for the output
        parser = PydanticOutputParser(pydantic_object=LLMVisualizationResponse)
        
        # Define the prompt template for visualization analysis
        template = """
        You are a data visualization expert. Analyze the data below to determine the most appropriate visualization type.
        Choose from: bar chart, pie chart, line chart, histogram, heatmap, or recommend 'none' if no visualization is appropriate.
        
        Data to analyze: {data}
        
        Focus on identifying patterns and relationships in the data that would be best revealed through visualization.
        Consider factors like data distribution, number of variables, categorical vs. continuous data, etc.
        
        {format_instructions}
        """
        
        # Create the prompt
        prompt = ChatPromptTemplate.from_template(
            template=template,
            partial_variables={"format_instructions": parser.get_format_instructions()}
        )
        
        # Initialize the language model
        model = ChatOpenAI(temperature=0.2, model="gpt-3.5-turbo")
        
        # Create the chain
        chain = LLMChain(llm=model, prompt=prompt)
        
        # Run the chain
        response = chain.run(data=str(data))
        
        # Parse the response
        try:
            return parser.parse(response)
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}\nResponse: {response}")
            return None
            
    except Exception as e:
        logger.error(f"Error getting LLM visualization suggestion: {e}")
        return None

def llm_result_to_graph_data(llm_result: LLMVisualizationResponse, structured_data: Dict[str, Any]) -> GraphData:
    """
    Convert LLM visualization recommendation to GraphData format
    """
    # Map LLM visualization type to VisualizationType enum
    viz_type_map = {
        "bar": VisualizationType.BAR,
        "bar chart": VisualizationType.BAR,
        "pie": VisualizationType.PIE,
        "pie chart": VisualizationType.PIE,
        "line": VisualizationType.LINE,
        "line chart": VisualizationType.LINE,
        "histogram": VisualizationType.HISTOGRAM,
        "heatmap": VisualizationType.HEATMAP,
        "none": VisualizationType.NONE
    }
    
    # Extract the visualization type
    viz_type = viz_type_map.get(
        llm_result.visualization_type.lower(), 
        VisualizationType.NONE
    )
    
    # Basic GraphData with info from LLM
    graph_data = GraphData(
        type=viz_type,
        title=llm_result.title,
        description=llm_result.description,
        raw_data=structured_data
    )
    
    # Try to extract axis data if available
    if viz_type in [VisualizationType.BAR, VisualizationType.LINE, VisualizationType.HISTOGRAM]:
        # Get keys/values for processing based on structured data
        if isinstance(structured_data, dict):
            if "items" in structured_data and isinstance(structured_data["items"], list):
                # Collection of items
                items = structured_data["items"]
                
                # Try to determine x and y axes based on LLM suggestion
                x_values = []
                y_values = []
                x_label = llm_result.x_axis_label or "Category"
                y_label = llm_result.y_axis_label or "Value"
                
                # Handle common case for items list with objects
                if all(isinstance(item, dict) for item in items):
                    # Extract axis data based on available fields
                    sample_item = items[0] if items else {}
                    
                    # Find potential x and y fields
                    for key, value in sample_item.items():
                        if isinstance(value, (int, float)):
                            # This could be a y-axis value
                            if not y_values and (y_label.lower() in key.lower() or "value" in key.lower()):
                                y_values = [item.get(key, 0) for item in items]
                                y_label = key
                        elif isinstance(value, str):
                            # This could be an x-axis label
                            if not x_values and (x_label.lower() in key.lower() or "name" in key.lower() or "category" in key.lower()):
                                x_values = [item.get(key, "") for item in items]
                                x_label = key
                    
                    # If we couldn't find good matches, use first string for x and first number for y
                    if not x_values:
                        for key, value in sample_item.items():
                            if isinstance(value, str):
                                x_values = [item.get(key, "") for item in items]
                                x_label = key
                                break
                    
                    if not y_values:
                        for key, value in sample_item.items():
                            if isinstance(value, (int, float)):
                                y_values = [item.get(key, 0) for item in items]
                                y_label = key
                                break
                
                if x_values and y_values:
                    graph_data.x_axis = AxisData(label=x_label, values=x_values)
                    graph_data.y_axis = AxisData(label=y_label, values=y_values)
        
        # If we couldn't extract axes data, fall back to rule-based approach
        if not graph_data.x_axis or not graph_data.y_axis:
            # Apply rule-based visualization as fallback
            rule_based_graph = suggest_visualization(structured_data)
            if rule_based_graph.x_axis and rule_based_graph.y_axis:
                graph_data.x_axis = rule_based_graph.x_axis
                graph_data.y_axis = rule_based_graph.y_axis
    
    # For pie charts, extract labels and values
    elif viz_type == VisualizationType.PIE:
        # Apply rule-based approach for pie charts
        rule_based_graph = suggest_visualization(structured_data)
        if rule_based_graph.labels and rule_based_graph.values:
            graph_data.labels = rule_based_graph.labels
            graph_data.values = rule_based_graph.values
    
    return graph_data
    
def analyze_data_for_visualization(intermediate_steps: Dict[str, Any]) -> GraphData:
    """
    Analyze intermediate_steps data to determine if it can be visualized
    and suggest an appropriate visualization type.
    
    Uses both rule-based analysis and LLM-based analysis to determine the best visualization.
    """
    if not intermediate_steps:
        return GraphData(
            type=VisualizationType.NONE,
            title="No data available",
            description="No intermediate data was provided for visualization"
        )
    
    # Try to extract structured data
    structured = False
    structured_data = {}
    
    # Check if there's a 'data' key with potential structured content
    if "data" in intermediate_steps:
        structured, structured_data = detect_data_structure(intermediate_steps["data"])
    
    # If no structured data in 'data', check if there are 'steps' with data
    if not structured and "steps" in intermediate_steps and isinstance(intermediate_steps["steps"], list):
        # Check the last few steps for structured data
        for step in reversed(intermediate_steps["steps"]):
            if isinstance(step, dict) and "data" in step:
                structured, structured_data = detect_data_structure(step["data"])
                if structured:
                    break
    
    # If still no structured data, try to analyze the whole intermediate_steps
    if not structured:
        structured, structured_data = detect_data_structure(intermediate_steps)
    
    # If we found structured data, suggest visualization
    if structured and structured_data:
        try:
            # First try using LLM-based recommendation
            llm_result = get_llm_visualization_suggestion(structured_data)
            
            if llm_result and llm_result.visualization_type.lower() != "none":
                # Use LLM-based recommendation
                logger.info(f"Using LLM visualization recommendation: {llm_result.visualization_type}")
                return llm_result_to_graph_data(llm_result, structured_data)
            
            # Fallback to rule-based recommendation
            logger.info("Falling back to rule-based visualization recommendation")
            return suggest_visualization(structured_data)
        except Exception as e:
            logger.error(f"Error suggesting visualization: {e}")
    
    # If we couldn't find structured data or suggest visualization
    return GraphData(
        type=VisualizationType.NONE,
        title="No visualization available",
        description="Could not identify a data structure suitable for visualization"
    )
    
    