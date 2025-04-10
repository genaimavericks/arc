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
        
        print(f'Input data:{data}')
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
    
    # Log the structured data for debugging
    logger.info(f"Converting LLM visualization result to GraphData. Type: {viz_type}")
    logger.info(f"Structured data keys: {list(structured_data.keys()) if isinstance(structured_data, dict) else 'Not a dict'}")
    
    # Basic GraphData with info from LLM
    graph_data = GraphData(
        type=viz_type,
        title=llm_result.title,
        description=llm_result.description,
        raw_data=structured_data
    )
    
    # Try to extract axis data if available for bar/line/histogram charts
    if viz_type in [VisualizationType.BAR, VisualizationType.LINE, VisualizationType.HISTOGRAM]:
        # First check if data is in the expected Neo4j result format
        if "result" in structured_data and isinstance(structured_data["result"], str):
            # Try to extract data from the text result and create axis data
            extract_axis_data_from_text_result(structured_data["result"], graph_data)
        
        # Check for Cypher execution results
        elif "intermediate_steps" in structured_data:
            steps = structured_data["intermediate_steps"]
            if isinstance(steps, list) and len(steps) > 0:
                # Try to extract from last step which likely has the data
                last_step = steps[-1]
                if isinstance(last_step, dict) and "action" in last_step and last_step["action"] == "Final Answer":
                    extract_axis_data_from_text_result(last_step.get("action_input", ""), graph_data)
        
        # Handle common data structures like lists of items
        elif isinstance(structured_data, dict):
            # Handle data in "data" field if present
            data_field = None
            if "data" in structured_data and structured_data["data"]:
                data_field = structured_data["data"]
            else:
                data_field = structured_data  # Use top-level data
                
            # Common pattern: List of items under various keys
            items = []
            for key in ["items", "results", "records", "rows", "data"]:
                if key in data_field and isinstance(data_field[key], list):
                    items = data_field[key]
                    break
            
            # Also check for direct arrays at top level in common keys
            if not items:
                for key in data_field.keys():
                    if isinstance(data_field[key], list) and len(data_field[key]) > 0:
                        items = data_field[key]
                        break
            
            # Handle direct nested dictionaries with values (common for pie charts or simple bar charts)
            if not items and any(isinstance(data_field.get(k), dict) for k in data_field.keys()):
                for k in data_field.keys():
                    if isinstance(data_field[k], dict) and len(data_field[k]) > 0:
                        # Convert to items format
                        items = [{"category": key, "value": val} for key, val in data_field[k].items()]
                        break
            
            # If we found items, try to extract axes
            if items and all(isinstance(item, dict) for item in items):
                # Find good candidates for x and y axes
                sample_item = items[0]
                x_candidates = []
                y_candidates = []
                
                # First look for ideal matches based on LLM-suggested axis labels
                x_label = llm_result.x_axis_label or "Category"
                y_label = llm_result.y_axis_label or "Value"
                
                # Categorize item fields
                for key, value in sample_item.items():
                    # Skip empty or null values
                    if value is None:
                        continue
                        
                    # For Y-axis (numeric values)
                    if isinstance(value, (int, float)) or (isinstance(value, str) and value.replace('.', '', 1).isdigit()):
                        # Convert string numbers to float
                        if isinstance(value, str):
                            try:
                                value = float(value)
                            except:
                                continue
                                
                        # Score this field as y-axis candidate
                        score = 0
                        if y_label.lower() in key.lower():
                            score += 3
                        if "value" in key.lower() or "count" in key.lower() or "amount" in key.lower():
                            score += 2
                        if "total" in key.lower() or "sum" in key.lower():
                            score += 1
                            
                        y_candidates.append((key, score))
                    
                    # For X-axis (string labels, dates, categories)
                    elif isinstance(value, str):
                        # Score this field as x-axis candidate
                        score = 0
                        if x_label.lower() in key.lower():
                            score += 3
                        if "name" in key.lower() or "title" in key.lower():
                            score += 2
                        if "category" in key.lower() or "type" in key.lower() or "label" in key.lower():
                            score += 2
                        if "date" in key.lower() or "time" in key.lower():
                            score += 2
                            
                        x_candidates.append((key, score))
                
                # Sort candidates by score
                x_candidates.sort(key=lambda x: x[1], reverse=True)
                y_candidates.sort(key=lambda y: y[1], reverse=True)
                
                # Use best candidates
                x_field = x_candidates[0][0] if x_candidates else None
                y_field = y_candidates[0][0] if y_candidates else None
                
                # If we found good axes, extract values
                if x_field and y_field:
                    x_values = []
                    y_values = []
                    
                    for item in items:
                        x_val = item.get(x_field)
                        if x_val is not None:
                            x_values.append(str(x_val))
                        else:
                            x_values.append("")
                            
                        y_val = item.get(y_field)
                        if y_val is not None:
                            # Convert string numbers to float
                            if isinstance(y_val, str) and y_val.replace('.', '', 1).isdigit():
                                try:
                                    y_val = float(y_val)
                                except:
                                    y_val = 0
                            elif not isinstance(y_val, (int, float)):
                                y_val = 0
                                
                            y_values.append(y_val)
                        else:
                            y_values.append(0)
                    
                    # Set axis data
                    graph_data.x_axis = AxisData(label=x_field, values=x_values)
                    graph_data.y_axis = AxisData(label=y_field, values=y_values)
                    
                    logger.info(f"Extracted axis data: X={x_field} with {len(x_values)} values, Y={y_field} with {len(y_values)} values")
        
        # If we couldn't extract axes data, fall back to rule-based approach
        if not graph_data.x_axis or not graph_data.y_axis:
            logger.info("Falling back to rule-based approach for axis data")
            rule_based_graph = suggest_visualization(structured_data)
            if rule_based_graph.x_axis and rule_based_graph.y_axis:
                graph_data.x_axis = rule_based_graph.x_axis
                graph_data.y_axis = rule_based_graph.y_axis
            else:
                # Last resort - create sample data for testing
                logger.warning("No axis data found, creating sample data")
                graph_data.type = VisualizationType.NONE
                
    
    # For pie charts, extract labels and values
    elif viz_type == VisualizationType.PIE:
        # Try to extract from structured data first
        if isinstance(structured_data, dict):
            # Check for distribution data (key-value pairs)
            for key in ["data", "distribution", "counts", "values"]:
                if key in structured_data and isinstance(structured_data[key], dict):
                    distribution = structured_data[key]
                    graph_data.labels = list(distribution.keys())
                    graph_data.values = list(distribution.values())
                    break
        
        # If not found, fall back to rule-based approach
        if not graph_data.labels or not graph_data.values:
            rule_based_graph = suggest_visualization(structured_data)
            if rule_based_graph.labels and rule_based_graph.values:
                graph_data.labels = rule_based_graph.labels
                graph_data.values = rule_based_graph.values
            else:
                # Last resort - create sample data for testing
                logger.warning("No pie chart data found, creating sample data")
                graph_data.type = VisualizationType.NONE
    
    # Log the result
    if viz_type != VisualizationType.NONE:
        logger.info(f"Final visualization data: type={viz_type}, has_x_axis={graph_data.x_axis is not None}, "
                   f"has_y_axis={graph_data.y_axis is not None}, has_labels={graph_data.labels is not None}, "
                   f"has_values={graph_data.values is not None}")
    
    return graph_data

def extract_axis_data_from_text_result(text: str, graph_data: GraphData) -> None:
    """
    Extract axis data from a text result string - useful for Neo4j query results
    """
    if not text or not isinstance(text, str):
        return
    
    # Try to find patterns in the text that suggest data (e.g., lists, counts, etc.)
    # Common pattern: "X: 10, Y: 20, Z: 15" or similar
    try:
        # Look for key-value pairs separated by commas
        import re
        pattern = r'([\w\s]+):\s*(\d+)'  # matches "Key: 123" patterns
        matches = re.findall(pattern, text)
        
        if matches and len(matches) >= 2:
            x_values = []
            y_values = []
            
            for key, value in matches:
                x_values.append(key.strip())
                try:
                    y_values.append(float(value.strip()))
                except ValueError:
                    y_values.append(0)
            
            graph_data.x_axis = AxisData(label="Category", values=x_values)
            graph_data.y_axis = AxisData(label="Value", values=y_values)
            return
    except Exception as e:
        logger.warning(f"Error extracting axis data from text: {e}")
        return
    
def analyze_data_for_visualization(intermediate_steps: Dict[str, Any]) -> GraphData:
    """
    Analyze intermediate_steps data to determine if it can be visualized
    and suggest an appropriate visualization type.
    
    Uses both rule-based analysis and LLM-based analysis to determine the best visualization.
    """
    if not intermediate_steps:
        logger.info("No intermediate steps provided for visualization")
        return GraphData(
            type=VisualizationType.NONE,
            title="No data available",
            description="No intermediate data was provided for visualization"
        )
    
    # Log what we received for debugging
    logger.info(f"Analyzing intermediate steps with keys: {list(intermediate_steps.keys() if isinstance(intermediate_steps, dict) else [])}")
    
    # Try to extract structured data
    structured = False
    structured_data = {}
    
    # Special handling for Neo4j context format with steps/context
    if "steps" in intermediate_steps and isinstance(intermediate_steps["steps"], list):
        logger.info(f"Found steps array with {len(intermediate_steps['steps'])} steps")
        
        # First look for context array in any step
        for step_index, step in enumerate(intermediate_steps["steps"]):
            if isinstance(step, dict) and "context" in step and isinstance(step["context"], list):
                context_data = step["context"]
                logger.info(f"Found context data in step {step_index} with {len(context_data)} items")
                
                # Check if context contains an array of objects with consistent keys (Neo4j records)
                if context_data and all(isinstance(item, dict) for item in context_data):
                    # This is likely query result data we can visualize
                    # Extract first record to check keys
                    sample = context_data[0]
                    keys = list(sample.keys())
                    logger.info(f"Context data has keys: {keys}")
                    
                    # Try to identify time series data (common in Neo4j queries)
                    time_series = False
                    time_key = None
                    value_key = None
                    
                    # Look for date/time and numeric value pairs
                    for key in keys:
                        if key.lower().find("date") >= 0 or key.lower().find("time") >= 0 or \
                           key.lower().find("month") >= 0 or key.lower().find("year") >= 0:
                            time_key = key
                        elif isinstance(sample[key], (int, float)) or \
                             (isinstance(sample[key], str) and sample[key].replace('.', '', 1).isdigit()):
                            value_key = key
                    
                    if time_key and value_key:
                        # Create a line chart for time series data
                        logger.info(f"Creating time series visualization with x={time_key}, y={value_key}")
                        x_values = [item[time_key] for item in context_data]
                        y_values = []
                        
                        for item in context_data:
                            val = item[value_key]
                            if isinstance(val, str):
                                try:
                                    val = float(val)
                                except:
                                    val = 0
                            y_values.append(val)
                        
                        return GraphData(
                            type=VisualizationType.LINE,
                            title=f"{value_key} over Time",
                            description=f"Time series analysis of {value_key} data",
                            x_axis=AxisData(label=time_key, values=x_values),
                            y_axis=AxisData(label=value_key, values=y_values),
                            raw_data={"data": context_data}  # Wrap the list in a dictionary
                        )
                    
                    # If not time series, use regular processing with the context array
                    structured = True
                    structured_data = {"items": context_data}
                    break
    
    # Continue with regular processing if we haven't created a visualization yet
    
    # Check if there's a 'data' key with potential structured content
    if not structured and "data" in intermediate_steps:
        structured, structured_data = detect_data_structure(intermediate_steps["data"])
        logger.info(f"Checked 'data' key: structured={structured}")
    
    # If no structured data in 'data', check if there are 'steps' with data
    if not structured and "steps" in intermediate_steps and isinstance(intermediate_steps["steps"], list):
        # Check the last few steps for structured data
        for step in reversed(intermediate_steps["steps"]):
            if isinstance(step, dict) and "data" in step:
                structured, structured_data = detect_data_structure(step["data"])
                if structured:
                    logger.info("Found structured data in a step's 'data' field")
                    break
    
    # If still no structured data, try to analyze the whole intermediate_steps
    if not structured:
        structured, structured_data = detect_data_structure(intermediate_steps)
        logger.info(f"Tried whole object: structured={structured}")
    
    # If we found structured data, suggest visualization
    if structured and structured_data:
        try:
            # First try using LLM-based recommendation
            logger.info("Getting LLM recommendation for visualization")
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
    logger.warning("No suitable data structure found for visualization")
    return GraphData(
        type=VisualizationType.NONE,
        title="No visualization available",
        description="Could not identify a data structure suitable for visualization"
    )
    
    