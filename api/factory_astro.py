"""
Factory Astro API Module for RSW

This module provides FastAPI endpoints for the Factory Astro functionality.
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, List, Any
import sys
import os
from pathlib import Path
import json
import numpy as np
import pandas as pd


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

# Add astro_data to the Python path
astro_data_path = Path(__file__).parent.parent / "astro_data"
if astro_data_path.exists() and str(astro_data_path) not in sys.path:
    sys.path.append(str(astro_data_path))

# Import astro_data modules
try:
    from astro_data.api import get_factory_prediction as original_get_factory_prediction
    from astro_data.api import get_example_questions, clear_chat_history
    
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
            
except ImportError as e:
    print(f"Error importing astro_data: {e}")
    # Create fallback functions in case imports fail
    def get_factory_prediction(query):
        return {"status": "error", "message": "Factory Astro module not available", "summary": "Factory Astro module is not available."}
    
    def get_example_questions():
        return []
    
    def clear_chat_history():
        pass

from api.auth import get_current_user, has_any_permission

router = APIRouter(
    prefix="/api/factory-astro",
    tags=["factory-astro"],
    responses={404: {"description": "Not found"}},
)

from fastapi import Body

@router.post("/predict")
async def predict(query: Dict[str, str] = Body(...), user=Depends(get_current_user)):
    """Process a factory data query and return predictions"""
    try:
        # Ensure the user has the required permissions
        has_any_permission(["datapuur:read"])(user)
        
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
async def examples(user=Depends(get_current_user)):
    """Get example questions for factory data queries"""
    try:
        # Ensure the user has the required permissions
        has_any_permission(["datapuur:read"])(user)
        
        return {"examples": get_example_questions()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting examples: {str(e)}")

@router.post("/clear-history")
async def clear_history(user=Depends(get_current_user)):
    """Clear chat history for factory data queries"""
    try:
        # Ensure the user has the required permissions
        has_any_permission(["datapuur:read"])(user)
        
        clear_chat_history()
        return {"status": "success", "message": "Chat history cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing history: {str(e)}")
