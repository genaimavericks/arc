"""
Factory Astro API Module

This module provides the core functionality of Factory Astro without the Streamlit GUI.
It can be integrated with any GUI framework.
"""
import os
from dotenv import load_dotenv
from api.astro_data.modules.factory_astro import FactoryAstro

# Load environment variables
load_dotenv()
if "OPENAI_API_KEY" not in os.environ:
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        os.environ["OPENAI_API_KEY"] = openai_key
        print("OpenAI API key loaded successfully.")
    else:
        print("OPENAI_API_KEY not found in environment variables. Please add it to your .env file.")

# Create a singleton instance of FactoryAstro
_factory_astro = FactoryAstro()

def get_factory_prediction(query):
    """
    Get prediction from Factory Astro based on the query.
    
    Args:
        query (str): The question to ask Factory Astro
        
    Returns:
        dict: A dictionary containing the prediction data and summary text
    """
    return _factory_astro.process_query(query)

def get_example_questions():
    """
    Returns a list of example questions that can be used with Factory Astro
    
    Returns:
        list: A list of example questions
    """
    return _factory_astro.get_example_questions()

def get_chat_history():
    """
    Get the chat history from Factory Astro
    
    Returns:
        list: A list of tuples (role, message)
    """
    return _factory_astro.get_chat_history()

def clear_chat_history():
    """
    Clear the chat history in Factory Astro
    """
    _factory_astro.clear_chat_history()
