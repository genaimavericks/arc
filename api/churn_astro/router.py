"""
Churn Astro Router Module for RSW

This module provides FastAPI router for the Churn Prediction functionality.
"""
from fastapi import APIRouter, Depends, HTTPException, Body
from typing import Dict, List, Any, Optional
import sys
import os
from pathlib import Path
import json
import pandas as pd
import numpy as np

# Add the parent directory to Python path to find the api package
parent_path = Path(__file__).parent.parent
if str(parent_path) not in sys.path:
    sys.path.append(str(parent_path))

# Import from the churn_astro module
from api.churn_astro import parse_query_to_input, make_predictions, clean_and_encode_data_for_7
from api.auth import get_current_user, has_any_permission

# Create the router
router = APIRouter(
    prefix="/api/churn-astro",
    tags=["churn-astro"],
    responses={404: {"description": "Not found"}},
)

# Helper function to convert NumPy types to native Python types
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

# Function to extract features from natural language query
def extract_features_from_query(query, default_values=None):
    """
    Extract features from a natural language query for the churn prediction model
    
    Args:
        query (str): The natural language query
        default_values (dict): Default values for features
        
    Returns:
        dict: A dictionary of extracted features
    """
    if default_values is None:
        default_values = {
            'tenure': 12,
            'OnlineSecurity': 'No',
            'OnlineBackup': 'No',
            'TechSupport': 'No',
            'Contract': 'Month-to-month',
            'MonthlyCharges': 70.0,
            'TotalCharges': 840.0
        }
    
    try:
        # Use the parse_query_to_input function to extract features
        features = parse_query_to_input(query, default_values)
        
        # Fill in any missing features with default values
        for key, value in default_values.items():
            if key not in features:
                features[key] = value
        
        return features
    except Exception as e:
        print(f"Error extracting features from query: {e}")
        return default_values

# Example questions for churn prediction
def get_example_questions():
    """Get example questions for churn prediction"""
    return [
        "Will a customer with 12 months tenure, no online security, no online backup, no tech support, on a month-to-month contract, and paying $70 monthly likely churn?",
        "Is a customer with 36 months tenure, with online security, with online backup, with tech support, on a two-year contract, and paying $100 monthly likely to churn?",
        "What's the churn prediction for a customer with 6 months tenure, no online security, with online backup, no tech support, on a month-to-month contract, and paying $65 monthly?",
        "Predict churn for a customer with 24 months tenure, with online security, no online backup, with tech support, on a one-year contract, and paying $80 monthly."
    ]

@router.post("/predict")
async def predict(query: Dict[str, str] = Body(...), user=Depends(get_current_user)):
    """Process a churn prediction query and return predictions"""
    try:
        # Ensure the user has the required permissions
        has_any_permission(["datapuur:read"])(user)
        
        # Extract the question from the request body
        question = ""
        if isinstance(query, dict):
            question = query.get("question", "")
        
        if not question:
            raise HTTPException(status_code=400, detail="Question is required")
        
        # Define default values for features not found in the query
        default_values = {
            'tenure': 3,
            'OnlineSecurity': 'No',
            'OnlineBackup': 'No',
            'TechSupport': 'No',
            'Contract': 'Month-to-month',
            'MonthlyCharges': 70.0,
            'TotalCharges': 210.0
        }
        
        # Extract features from the question
        features = extract_features_from_query(question, default_values)
        
        # Clean and encode the data
        encoded_data = clean_and_encode_data_for_7(pd.DataFrame([features]))
        
        # Import the model from churn_prediction
        from api.churn_astro.page.churn_prediction import model
        
        # Make predictions - returns a tuple (result_df, proba, feature_importance)
        result_df, proba, feature_importance = make_predictions(model, encoded_data)
        
        # Process the prediction results
        # Convert DataFrame to dict
        result_dict = result_df.to_dict('records')
        
        # Convert NumPy types to native Python types for JSON serialization
        result_dict = convert_numpy_types(result_dict)
        
        # Process feature importance if available
        feature_imp_dict = None
        if feature_importance is not None:
            feature_imp_dict = feature_importance.to_dict('records')
            feature_imp_dict = convert_numpy_types(feature_imp_dict)
        
        # Process probability if available
        probability = None
        if proba is not None:
            probability = float(proba[0]) if len(proba) > 0 else None
        
        # Prepare the response in the format expected by the frontend
        # Frontend expects: { status, summary, data: { prediction, probability, input_data, input_features, feature_importance } }
        
        # Generate a summary based on the prediction result
        prediction_value = result_dict[0].get("Prediction", "Unknown") if result_dict else "Unknown"
        churn_status = "will churn" if prediction_value == "Yes" else "is not likely to churn"
        prob_percentage = f"{int(probability * 100)}%" if probability is not None else "unknown probability"
        summary = f"I processed your request about customer churn. The customer {churn_status} ({prob_percentage})."
        
        # Format feature importance in the expected format
        formatted_feature_importance = []
        if feature_imp_dict:
            formatted_feature_importance = [
                {"feature": item["Feature"], "importance": item["Importance"]} 
                for item in feature_imp_dict
            ]
        
        response = {
            "status": "success",
            "summary": summary,
            "data": {
                "prediction": prediction_value,
                "probability": probability,
                "input_data": features,  # Original input data
                "input_features": features,  # Same as input_data for now
                "feature_importance": formatted_feature_importance
            }
        }
        
        return response
    except Exception as e:
        print(f"Error in churn prediction: {e}")
        error_message = str(e)
        return {
            "status": "error",
            "summary": f"Sorry, I encountered an error: {error_message}",
            "message": error_message,
            "query": question if 'question' in locals() else ""
        }

@router.get("/examples")
async def examples(user=Depends(get_current_user)):
    """Get example questions for churn prediction queries"""
    try:
        # Ensure the user has the required permissions
        has_any_permission(["datapuur:read"])(user)
        
        return {
            "status": "success",
            "examples": get_example_questions()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
