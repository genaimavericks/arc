"""
Factory Astro API Module for RSW

This module provides FastAPI endpoints for the Factory Astro functionality.
"""
from fastapi import APIRouter, Depends, HTTPException, WebSocket
from typing import Dict, List, Any, Optional
import sys
import os
from pathlib import Path
import json
import numpy as np
import pandas as pd
import asyncio
from pydantic import BaseModel


def convert_numpy_types(obj):
    """Convert NumPy types to native Python types for JSON serialization"""
    if isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return convert_numpy_types(obj.tolist())
    elif isinstance(obj, pd.DataFrame):
        # Convert DataFrame to dict and then process
        return convert_numpy_types(obj.to_dict(orient='records'))
    elif isinstance(obj, pd.Series):
        return convert_numpy_types(obj.to_dict())
    elif obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    else:
        # Try to convert to a serializable format, or use string representation as fallback
        try:
            return str(obj)
        except:
            return "[Object not serializable]"

# Add the parent directory to Python path to find the api package
parent_path = Path(__file__).parent.parent
if str(parent_path) not in sys.path:
    sys.path.append(str(parent_path))

# Import astro_data modules from the new location
try:
    from api.astro_data.api import get_factory_prediction as original_get_factory_prediction
    from api.astro_data.api import get_example_questions, clear_chat_history
    
    # Create a wrapped version of get_factory_prediction with better error handling
    def get_factory_prediction(query):
        try:
            return original_get_factory_prediction(query)
        except Exception as e:
            error_message = str(e)
            print(f"Error in original_get_factory_prediction: {error_message}")
            
            # Handle the specific HalfSquaredError issue
            if "HalfSquaredError" in error_message and "get_init_raw_predictions" in error_message:
                return {
                    "status": "error",
                    "message": "The model encountered a compatibility issue with this specific query. Please try a different question or time period.",
                    "summary": "Unable to process this specific factory query due to a model compatibility issue. Please try a different question or time period."
                }
            return {"status": "error", "message": f"An unexpected error occurred: {error_message}", "summary": "An error occurred while processing your request."}
    
    # Function for generating autocomplete suggestions
    def get_factory_autocomplete_suggestions(partial_text, cursor_position, max_suggestions=5):
        """Generate autocomplete suggestions for Factory Astro based on partial text"""
        try:
            # Get example questions to use as a knowledge base for suggestions
            examples = get_example_questions()
            
            # If we have no partial text, return some example questions as suggestions
            if not partial_text:
                return [{'text': example, 'type': 'example'} for example in examples[:max_suggestions]]
                
            # For now, filter examples that match the partial text
            matching_examples = [
                {'text': example, 'type': 'example'}
                for example in examples
                if partial_text.lower() in example.lower()
            ]
            
            # Prioritize examples that match at the beginning
            beginning_matches = [
                suggestion for suggestion in matching_examples
                if suggestion['text'].lower().startswith(partial_text.lower())
            ]
            
            # Combine and limit
            suggestions = beginning_matches + [s for s in matching_examples if s not in beginning_matches]
            return suggestions[:max_suggestions]
            
        except Exception as e:
            print(f"Error generating autocomplete suggestions: {str(e)}")
            return []
            
except ImportError as e:
    print(f"Error importing astro_data: {e}")
    # Create fallback functions in case imports fail
    def get_factory_prediction(query):
        return {"status": "error", "message": "Factory Astro module not available", "summary": "Factory Astro module is not available."}
    
    def get_example_questions():
        return []
    
    def clear_chat_history():
        pass
        
    def get_factory_autocomplete_suggestions(partial_text, cursor_position, max_suggestions=5):
        """Provide autocomplete suggestions for Factory Astro queries"""
        # Common Factory Astro query patterns
        factory_astro_queries = [
            "What will the revenue for factory 3 be over the next 6 months?",
            "What will the profit margin of factory 1 over the next quarter?",
            "What will the production volume for factory 3 be over the next 6 months?",
            "What will the revenue over the next 2 months for factory 3?",
            "What will the production volume for factory 3 be over the next 2 months?",
            "What will be the expected downtime for factory 2 in the next quarter?",
            "What will be the production efficiency for factory 1 over the next month?",
            "What will be the maintenance costs for factory 3 in the next 6 months?",
            "What will be the inventory levels for factory 2 over the next quarter?",
            "What will be the supply chain delays for factory 1 in the next month?"
        ]
        
        # Get text up to cursor position for matching
        active_text = partial_text[:cursor_position].lower().strip()
        
        # If no text or not relevant to Factory Astro, return empty suggestions
        if not active_text or not (active_text.startswith("what will") or active_text.startswith("what")):
            return []
        
        # Find matching queries
        matching_queries = []
        for query in factory_astro_queries:
            if query.lower().startswith(active_text):
                matching_queries.append({
                    "text": query,
                    "description": "Factory Astro prediction query",
                    "source": "factory_astro"
                })
        
        # Return top suggestions limited by max_suggestions
        return matching_queries[:max_suggestions]

from api.auth import get_current_user, has_any_permission

router = APIRouter(
    prefix="/api/factory-astro",
    tags=["factory-astro"],
    responses={404: {"description": "Not found"}},
)

from fastapi import Body

@router.post("/predict")
async def predict(query: Dict[str, str] = Body(...), user=Depends(has_any_permission(["datapuur:read", "djinni:read"]))):
    """Process a factory data query and return predictions"""
    try:
        
        # Extract the question from the request body
        question = ""
        if isinstance(query, dict):
            question = query.get("question", "")
        elif isinstance(query, str):
            question = query
            
        if not question:
            raise HTTPException(status_code=400, detail="Question is required")
            
        print(f"Processing question: {question}")
        try:
            result = get_factory_prediction(question)
            print(f"Raw result from prediction: {result}")
            
            # Handle agent response format which contains 'output' key
            if isinstance(result, dict) and 'output' in result:
                result = result['output']
                
            # Convert NumPy types to native Python types for JSON serialization
            result = convert_numpy_types(result)
            
            # Ensure the response has the expected structure
            if isinstance(result, str):
                try:
                    # Try to parse if it's a JSON string
                    import json
                    result = json.loads(result)
                except:
                    # If not a valid JSON string, wrap it in a standard response
                    result = {
                        "status": "success",
                        "summary": result,
                        "data": {"llm_output_text_summmary": result}
                    }
            
            # Ensure we have a standard response format
            if not isinstance(result, dict):
                result = {
                    "status": "success",
                    "summary": str(result),
                    "data": {"llm_output_text_summmary": str(result)}
                }
                
            # Ensure summary field exists
            if "summary" not in result and "data" in result and "llm_output_text_summmary" in result["data"]:
                result["summary"] = result["data"]["llm_output_text_summmary"]
                
            return result
        except Exception as e:
            print(f"Error in prediction: {str(e)}")
            return {
                "status": "error",
                "message": f"Error processing prediction: {str(e)}",
                "summary": f"An error occurred while processing your question: {str(e)}"
            }
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error processing query: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")

@router.get("/examples")
async def examples(user=Depends(has_any_permission(["datapuur:read", "djinni:read"]))):
    """Get example questions for factory data queries"""
    try:
        
        return {"examples": get_example_questions()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting examples: {str(e)}")

class AutocompleteRequest(BaseModel):
    partial_text: str
    cursor_position: int
    max_suggestions: int = 5

@router.post("/autocomplete")
async def autocomplete(request: AutocompleteRequest, user=Depends(has_any_permission(["datapuur:read", "djinni:read"]))):
    """Generate autocomplete suggestions for Factory Astro queries"""
    try:
        suggestions = get_factory_autocomplete_suggestions(
            request.partial_text,
            request.cursor_position,
            request.max_suggestions
        )
        return {"suggestions": suggestions}
    except Exception as e:
        print(f"Error in autocomplete endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating suggestions: {str(e)}")

@router.post("/clear-history")
async def clear_history(user=Depends(has_any_permission(["datapuur:read", "djinni:read"]))):
    """Clear chat history for factory data queries"""
    try:
        
        clear_chat_history()
        return {"status": "success", "message": "Chat history cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing history: {str(e)}")

class AutocompleteRequest(BaseModel):
    partial_text: str
    cursor_position: int
    max_suggestions: Optional[int] = 5

@router.post("/autocomplete")
async def autocomplete(request: AutocompleteRequest, user=Depends(has_any_permission(["datapuur:read", "djinni:read"]))):
    """Generate autocomplete suggestions for Factory Astro queries"""
    try:
        suggestions = get_factory_autocomplete_suggestions(
            request.partial_text,
            request.cursor_position,
            request.max_suggestions
        )
        return {"suggestions": suggestions}
    except Exception as e:
        print(f"Error in autocomplete endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating suggestions: {str(e)}")
