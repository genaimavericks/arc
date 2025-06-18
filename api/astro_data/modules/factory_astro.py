"""
Factory Astro Core Module

This module provides the core functionality of Factory Astro without the Streamlit GUI.
It can be integrated with any GUI framework.
"""
import json
import pandas as pd
import sys
from pathlib import Path

# Add the parent directory to Python path to find the api package
parent_path = Path(__file__).parent.parent.parent
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

class FactoryAstro:
    def __init__(self):
        """Initialize the Factory Astro module"""
        self.chat_history = []
        self.last_response = None
    
    def process_query(self, query):
        """
        Process a query and return the prediction results
        
        Args:
            query (str): The question to ask Factory Astro
            
        Returns:
            dict: A dictionary containing the prediction data and summary text
        """
        try:
            llm_response = ml_rag.get_ml_answer(query)
            
            # Parse the response
            try:
                parsed_response = json.loads(llm_response)
                response_text = parsed_response.get("llm_output_text_summmary", "")
                
                # Add to chat history
                self.chat_history.append(('User', query))
                self.chat_history.append(('Bot', response_text))
                self.last_response = parsed_response
                
                # Process prediction data if available
                prediction_data = None
                if 'Predicted_data' in parsed_response:
                    try:
                        prediction_data = pd.DataFrame(parsed_response['Predicted_data'])
                    except:
                        prediction_data = None
                
                response_dict = {
                    "status": "success",
                    "data": parsed_response,
                    "summary": response_text,
                    "prediction_data": prediction_data
                }
                return response_dict
            except json.JSONDecodeError:
                # Add to chat history
                self.chat_history.append(('User', query))
                self.chat_history.append(('Bot', "Error: Could not process request."))
                
                return {
                    "status": "error",
                    "message": "Error parsing response from model",
                    "raw_response": llm_response
                }
                
        except Exception as e:
            # Add to chat history
            self.chat_history.append(('User', query))
            self.chat_history.append(('Bot', f"An unexpected error occurred: {str(e)}"))
            
            return {
                "status": "error",
                "message": f"An unexpected error occurred: {str(e)}"
            }
    
    def get_chat_history(self):
        """
        Get the chat history
        
        Returns:
            list: A list of tuples (role, message)
        """
        return self.chat_history
    
    def clear_chat_history(self):
        """Clear the chat history"""
        self.chat_history = []
        self.last_response = None
    
    def get_example_questions(self):
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
