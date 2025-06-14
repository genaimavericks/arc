"""
Example usage of the Churn Prediction API without Streamlit GUI
"""
import json
import pandas as pd
import sys
from pathlib import Path

# Add the parent directory to Python path to find the api package
parent_path = Path(__file__).parent.parent.parent
if str(parent_path) not in sys.path:
    sys.path.append(str(parent_path))
    print(f"Added {parent_path} to sys.path")

# Import the churn prediction functions
from api.churn_astro.page import predict_customer_churn, predict_batch_churn
from api.churn_astro.page.churn_bot import process_natural_language_query

def get_example_questions():
    """Return a list of example questions for the churn prediction model"""
    return [
        "Will a customer with 12 months tenure, no online security, yes to online backup, no tech support, on a month-to-month contract, and paying $65.50 monthly likely churn?",
        "What's the churn probability for a customer who has been with us for 36 months, has online security, online backup, tech support, is on a two-year contract, and pays $105.80 monthly?",
        "Is a customer with 6 months tenure, no online security or backup, no tech support, month-to-month contract, and $70 monthly charges at risk of churning?",
        "Will a customer on a one-year contract with 18 months tenure, online security, no online backup, tech support, and $85 monthly charges stay with us?",
        "What's the likelihood of churn for a customer who's been with us for 24 months, has no internet service, and pays $45 monthly on a two-year contract?",
        "Predict if a customer will churn if they have no online security, no tech support, 9 months tenure, and $60 monthly charges on a month-to-month contract.",
        "Customer with 48 months tenure, all services enabled, two-year contract, and $120 monthly charges - will they churn?",
        "What's the churn risk for a new customer (3 months) with no services and a month-to-month contract paying $50 monthly?"
    ]

def main():
    print("Churn Prediction API Example")
    print("-----------------------")
    
    # Display example questions
    print("\nAsk Me About Your Churn Data")
    print("\nTry asking:")
    for i, question in enumerate(get_example_questions(), 1):
        print(f"{i}. {question}")
    
    # Get user input
    print("\nEnter your question (or 'exit' to quit):")
    
    while True:
        query = input("> ")
        if query.lower() == 'exit':
            break
        
        # Process the natural language query
        try:
            result = process_natural_language_query(query)
            print("\nResult:")
            print(json.dumps(result, indent=2))
        except Exception as e:
            print(f"Error processing query: {e}")
            
        print("\nEnter another question (or 'exit' to quit):")

if __name__ == "__main__":
    main()
