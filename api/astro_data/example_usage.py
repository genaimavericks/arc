"""
Example usage of the Factory Astro API without Streamlit GUI
"""
import json
import sys
from pathlib import Path

# Add the parent directory to Python path to find the api package
parent_path = Path(__file__).parent.parent.parent
if str(parent_path) not in sys.path:
    sys.path.append(str(parent_path))
    print(f"Added {parent_path} to sys.path")

from api.astro_data.api import get_factory_prediction, get_example_questions, get_chat_history, clear_chat_history

def main():
    print("Factory Astro API Example")
    print("-----------------------")
    
    # Display example questions
    print("\nExample questions you can ask:")
    for i, question in enumerate(get_example_questions(), 1):
        print(f"{i}. {question}")
    
    # Get user input
    print("\nEnter your question (or 'exit' to quit):")
    print("Type 'history' to see chat history or 'clear' to clear history")
    
    while True:
        query = input("> ")
        if query.lower() == 'exit':
            break
        elif query.lower() == 'history':
            # Display chat history
            history = get_chat_history()
            if history:
                print("\nChat History:")
                for role, message in history:
                    print(f"{role}: {message}")
            else:
                print("\nNo chat history yet.")
            continue
        elif query.lower() == 'clear':
            clear_chat_history()
            print("\nChat history cleared.")
            continue
            
        # Get prediction
        print("\nAnalyzing data...")
        response = get_factory_prediction(query)
        
        # Display results
        if response["status"] == "success":
            print(f"\nSummary: {response['summary']}")
            
            # Display prediction data if available
            if "prediction_data" in response and response["prediction_data"] is not None:
                print("\nPrediction Data:")
                for _, row in response["prediction_data"].iterrows():
                    # Format the output for better readability
                    year = row.get("year", "N/A")
                    month = row.get("month", "N/A")
                    factory = row.get("Factory", "N/A")
                    prediction = row.get("prediction", "N/A")
                    
                    print(f"  Year: {year}, Month: {month}, Factory: {factory}, Prediction: {prediction}")
            elif "data" in response and "Predicted_data" in response["data"]:
                try:
                    predicted_data = json.loads(response["data"]["Predicted_data"])
                    print("\nPrediction Data:")
                    for item in predicted_data:
                        # Format the output for better readability
                        year = item.get("year", "N/A")
                        month = item.get("month", "N/A")
                        factory = item.get("Factory", "N/A")
                        prediction = item.get("prediction", "N/A")
                        
                        print(f"  Year: {year}, Month: {month}, Factory: {factory}, Prediction: {prediction}")
                except:
                    print("\nPrediction data format is not as expected.")
        else:
            print(f"\nError: {response.get('message', 'Unknown error')}")
        
        print("\nEnter another question (or 'exit' to quit):")

if __name__ == "__main__":
    main()
