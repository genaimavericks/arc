"""
Churn Prediction API Module

This module provides the core functionality of Churn Prediction without the Streamlit GUI.
It can be integrated with any GUI framework or used as a pure API.
"""
import os
from dotenv import load_dotenv
import joblib
from pathlib import Path
import pandas as pd
from utils.data_processing import clean_and_encode_data, clean_and_encode_data_for_7, encode_data
from utils.rag import create_rag_layer

# Load environment variables
load_dotenv()
if "OPENAI_API_KEY" not in os.environ:
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        os.environ["OPENAI_API_KEY"] = openai_key
        print("OpenAI API key loaded successfully.")
    else:
        print("OPENAI_API_KEY not found in environment variables. Please add it to your .env file.")

# Initialize or load the model
CHURN_REG_MODEL_FILE = Path(__file__).parent / "modules/data/telchurn/gradient_boosting_model_new.joblib"

try:
    model = joblib.load(CHURN_REG_MODEL_FILE)
    print("Loaded existing model")
except Exception as e:
    print(f"Error loading model: {str(e)}")
    model = None

def predict_churn(input_data):
    """
    Make churn predictions based on input data
    
    Args:
        input_data (pd.DataFrame): Customer data for prediction
        
    Returns:
        dict: A dictionary containing prediction results and probabilities
    """
    if model is None:
        return {"error": "Model not available"}
        
    try:
        # Process the input data
        processed_data = clean_and_encode_data(input_data)
        
        # Make predictions
        predictions = model.predict(processed_data)
        probabilities = model.predict_proba(processed_data)
        
        # Create result dataframe
        result_df = input_data.copy()
        result_df['Churn_Prediction'] = predictions
        result_df['Churn_Probability'] = probabilities[:, 1]
        
        # Get feature importances if available
        feature_importance = None
        if hasattr(model, 'feature_importances_'):
            feature_importance = dict(zip(processed_data.columns, model.feature_importances_))
        
        return {
            "predictions": result_df.to_dict(orient='records'),
            "feature_importance": feature_importance
        }
    except Exception as e:
        return {"error": str(e)}

def batch_predict_churn(csv_data):
    """
    Make churn predictions on a batch of customers from CSV data
    
    Args:
        csv_data (str): CSV data as string
        
    Returns:
        dict: A dictionary containing prediction results
    """
    try:
        # Convert CSV to DataFrame
        input_data = pd.read_csv(pd.StringIO(csv_data))
        return predict_churn(input_data)
    except Exception as e:
        return {"error": str(e)}

def get_churn_explanation(customer_data):
    """
    Get an explanation for churn prediction using RAG
    
    Args:
        customer_data (dict): Customer data for explanation
        
    Returns:
        str: Explanation text
    """
    try:
        # Convert customer data to a format suitable for RAG
        customer_str = "\n".join([f"{k}: {v}" for k, v in customer_data.items()])
        
        # Use RAG to generate an explanation
        query = f"Explain why this customer might churn: {customer_str}"
        rag_response = create_rag_layer(query)
        
        return rag_response
    except Exception as e:
        return f"Error generating explanation: {str(e)}"
