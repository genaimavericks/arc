import pandas as pd
import numpy as np
import json
import jsonschema
import sys
import os
from pathlib import Path

# Add the parent directory to Python path to find the api package
parent_path = Path(__file__).parent.parent.parent.parent
if str(parent_path) not in sys.path:
    sys.path.append(str(parent_path))
    print(f"Added {parent_path} to sys.path")

# Import required modules
from langchain.prompts import ChatPromptTemplate
from langchain.schema import SystemMessage
from langchain_openai import ChatOpenAI
from api.churn_astro.utils.data_processing import encode_data_7
from api.churn_astro.utils.rag import create_rag_layer

prompt = '''
You are a helpful assistant that extracts specific features from natural language queries for churn prediction. 
Extract values only for these features:
- 'tenure': integer (minimum: 0)
- 'OnlineSecurity': string (enum: ['Yes', 'No', 'No internet service'])
- 'OnlineBackup': string (enum: ['Yes', 'No', 'No internet service'])
- 'TechSupport': string (enum: ['Yes', 'No', 'No internet service'])
- 'Contract': string (enum: ['Month-to-month', 'One year', 'Two year'])
- 'MonthlyCharges': number (minimum: 0)
- 'TotalCharges': number (minimum: 0)

Rules:
1. Return only valid JSON containing extracted values
2. For any fields not found in the query, use these default values:
{default_values}
3. Do not include any explanations, notes, or additional text
4. Maintain exact JSON format: {{"key": value}}

Examples:
{{"tenure": 3, "OnlineSecurity": "No", "OnlineBackup": "No", "TechSupport": "No", "Contract": "Month-to-month", "MonthlyCharges": 70.35, "TotalCharges": 211.05}}
or
{{"tenure": 1}}

Question: {query}
Output:
'''

from langchain.prompts.prompt import PromptTemplate


prompt = PromptTemplate(
        input_variables=["query", "default_values"],
        template=prompt,
    )
llm = ChatOpenAI(model="gpt-4", temperature=0)

from langchain.schema import HumanMessage


def parse_query_to_input(query, default_values):
    """Parse natural language query into structured input using LLM
    
    Args:
        query (str): Natural language query about customer churn
        default_values (dict): Default values for missing features
        
    Returns:
        dict: Extracted feature values from the query
    """
    print('Starting parse_query_to_input')
    print('Query:', query)
    print('Default values:', default_values)
    
    final_prompt = prompt.format(query=query, 
                               default_values=json.dumps(default_values, indent=2))

    print('Final prompt:', final_prompt)
    try:
        messages = [HumanMessage(content=final_prompt)]
        print('Messages:', messages)
        content = llm.invoke(messages)
        print('Content:', content)
        extracted = content.content
        print('Extracted data:', extracted)
        extracted = json.loads(extracted)
        print('Extracted data:', type(extracted), extracted)
        if extracted == {}:
            print('Unable to extract values from query')
            return {}
        # Merge extracted values with defaults
        return {**default_values, **extracted}
    except Exception as e:
        print('Unable to parse response', e)
        return {}

def chatbot_prediction(model, query, default_values):
    """Handle chatbot queries for churn prediction with LLM parsing
    
    Args:
        model: The trained churn prediction model
        query (str): Natural language query about customer churn
        default_values (dict): Default values for missing features
        
    Returns:
        tuple: (prediction, probability, explanation, extracted_data)
    """
    print('Starting chatbot_prediction')
    print('Query:', query)
    
    # Parse query to get specific values
    extracted_data = parse_query_to_input(query, default_values)
    print('Final data for encoding:', extracted_data)
    if not extracted_data:
        return None, None, "Unable to extract values from query", extracted_data
    
    # Create dataframe and preprocess
    input_df = pd.DataFrame([extracted_data])
    input_df = encode_data_7(input_df)
    print('Encoded DataFrame:', input_df.head())
    clean_columns = ['tenure', 'OnlineSecurity', 'OnlineBackup', 'TechSupport', 'Contract', 'MonthlyCharges', 'TotalCharges']
    input_df = input_df[clean_columns]
    
    # Make prediction
    prediction = model.predict(input_df)[0]
    print('Prediction:', prediction)
    proba = model.predict_proba(input_df)[0][1] if hasattr(model, 'predict_proba') else None
    print('Probability:', proba)

    # Generate explanation using RAG
    rag = create_rag_layer()
    explanation = rag.run(f"Explain why this customer might {'churn' if prediction == 1 else 'not churn'} given inputs are {extracted_data}")
    print('Explanation:', explanation)
    
    print('Completed chatbot_prediction')
    return prediction, proba, explanation, extracted_data


def process_natural_language_query(query):
    """Process a natural language query about customer churn
    
    Args:
        query (str): Natural language query about customer churn
        
    Returns:
        dict: Dictionary containing prediction results and explanation
    """
    from api.churn_astro.page.churn_prediction import model, DEFAULT_VALUES
    
    if model is None:
        return {
            'error': 'Model could not be loaded',
            'status': 'error'
        }
    
    try:
        # Use chatbot_prediction to process the query
        prediction, probability, explanation, extracted_data = chatbot_prediction(model, query, DEFAULT_VALUES)
        
        if prediction is None:
            return {
                'status': 'error',
                'error': 'Unable to extract customer information from query',
                'query': query
            }
        
        # Format the result
        result = {
            'status': 'success',
            'prediction': 'Churn' if prediction == 1 else 'No Churn',
            'probability': float(probability) if probability is not None else None,
            'explanation': explanation,
            'extracted_data': extracted_data,
            'query': query
        }
        
        return result
    except Exception as e:
        print(f"Error processing query: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'query': query
        }

def validate_default_values(data):
    print('Starting validate_default_values')
    print('Input data:', data)
    """Validate the structure and content of default values"""
    schema = {
        'type': 'object',
        'properties': {
            'tenure': {'type': 'integer', 'minimum': 0},
            'OnlineSecurity': {'type': 'string', 'enum': ['Yes', 'No', 'No internet service']},
            'OnlineBackup': {'type': 'string', 'enum': ['Yes', 'No', 'No internet service']},
            'TechSupport': {'type': 'string', 'enum': ['Yes', 'No', 'No internet service']},
            'Contract': {'type': 'string', 'enum': ['Month-to-month', 'One year', 'Two year']},
            'MonthlyCharges': {'type': 'number', 'minimum': 0},
            'TotalCharges': {'type': 'number', 'minimum': 0}
        },
        'required': ['tenure', 'OnlineSecurity', 'OnlineBackup', 'TechSupport', 'Contract', 'MonthlyCharges', 'TotalCharges'],
        'additionalProperties': False
    }
    try:
        jsonschema.validate(instance=data, schema=schema)
        return True, ""
    except jsonschema.ValidationError as e:
        return False, f"Validation error: {e.message}"
    print('Completed validate_default_values')

# Default values for chatbot predictions when not all features are provided
DEFAULT_VALUES = {
    'tenure': 3,
    'OnlineSecurity': 'No',
    'OnlineBackup': 'No',
    'TechSupport': 'No',
    'Contract': 'Two year',
    'MonthlyCharges': 40.0,
    'TotalCharges': 2279.73
}

def process_natural_language_query(query, model, custom_defaults=None):
    """
    Process a natural language query about customer churn
    
    Args:
        query (str): Natural language query about customer churn
        model: The trained churn prediction model
        custom_defaults (dict, optional): Custom default values for missing features
        
    Returns:
        dict: Dictionary containing prediction results and extracted data
    """
    print('Processing natural language query')
    
    # Use custom defaults if provided, otherwise use global defaults
    default_values = custom_defaults if custom_defaults else DEFAULT_VALUES
    
    # Validate default values
    is_valid, error_msg = validate_default_values(default_values)
    if not is_valid:
        return {
            'error': error_msg,
            'status': 'error'
        }
    
    # Get prediction and explanation
    prediction, proba, explanation, extracted_data = chatbot_prediction(model, query, default_values)
    
    # Format response
    result = {
        'status': 'success',
        'query': query,
        'extracted_data': extracted_data,
        'explanation': explanation
    }
    
    if prediction is not None:
        result['prediction'] = 'Churn' if prediction == 1 else 'No Churn'
        if proba is not None:
            result['probability'] = float(proba)
    else:
        result['status'] = 'error'
        result['error'] = 'Unable to extract values from query'
    
    print('Completed processing natural language query')
    return result
