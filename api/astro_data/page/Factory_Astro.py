"""
Factory Astro Module

This module provides access to the Factory Astro functionality.
All UI components have been removed.
"""
import json
import sys
from pathlib import Path

# Add the parent directory to Python path to find the api package
parent_path = Path(__file__).parent.parent.parent.parent
if str(parent_path) not in sys.path:
    sys.path.append(str(parent_path))

# Add the astro_data directory to Python path
astro_data_path = Path(__file__).parent.parent
if str(astro_data_path) not in sys.path:
    sys.path.append(str(astro_data_path))

# Import from the correct module path
try:
    from api.astro_data.modules.ml import ml_rag
except ImportError:
    # Fallback to relative import
    from modules.ml import ml_rag

# Core function to process queries
def process_factory_query(query):
    """
    Process a factory performance query and return the results
    
    Args:
        query (str): The question to ask about factory performance
        
    Returns:
        dict: A dictionary containing the prediction data and summary text
    """
    try:
        llm_response = ml_rag.get_ml_answer(query)
        
        try:
            parsed_response = json.loads(llm_response)
            return parsed_response
        except json.JSONDecodeError:
            return {"error": "Could not parse response", "raw_response": llm_response}
        except Exception as e:
            return {"error": f"An unexpected error occurred: {str(e)}"}
            
    except Exception as e:
        return {"error": f"Failed to process query: {str(e)}"}

# Get example questions that can be used with Factory Astro
def get_example_questions():
    """
    Returns a list of example questions that can be used with Factory Astro
    
    Returns:
        list: A list of example questions
    """
    return [
        "What will the revenue for factory 3 be over the next 6 months?",
        "What will the revenue over the next year for factory 3?",
        "What will the profit margin be from July to December for factory 2?",
        "What will the profit margin of factory 1 over the next quarter?",
        "What will the production volume be over the next 6 months?",
        "Get me the production volume for factory 4 from July to December.",
        "What will the revenue for factory 3 be next year?",
        "What will the revenue over the next 2 months for factory 3?",
        "What will the profit margin be in July for factory 2?",
        "What will the profit margin of factory 1?",
        "What will the production volume be over the next 2 months?",
        "Get me the production volume for factory 4 in the month of July."
    ]
