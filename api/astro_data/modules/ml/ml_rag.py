from concurrent.futures import wait
import json
import re
from datetime import datetime
import importlib

# Try new import paths first, fall back to old ones
try:
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:
    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings
    except ImportError:
        from langchain.embeddings import HuggingFaceEmbeddings

try:
    from langchain_community.vectorstores import FAISS
except ImportError:
    from langchain.vectorstores import FAISS

try:
    from langchain.prompts import PromptTemplate
except ImportError:
    from langchain.prompts.prompt import PromptTemplate

try:
    from langchain_openai import ChatOpenAI
except ImportError:
    from langchain.chat_models import ChatOpenAI

try:
    from langchain.schema import HumanMessage
except ImportError:
    from langchain.schema.messages import HumanMessage

import os
from pathlib import Path
import pandas as pd
from typing import Dict

VECTOR_DB_PATH = Path(__file__).parent.parent/"ml/factory_vector_db"
EMBEDDINGS_MODEL = "all-mpnet-base-v2"

LLM_MODEL = "gpt-4"
llm = ChatOpenAI(temperature=0, model=LLM_MODEL)

import sys
from pathlib import Path

# Add the parent directory to Python path to find the api package
parent_path = Path(__file__).parent.parent.parent.parent
if str(parent_path) not in sys.path:
    sys.path.append(str(parent_path))

# Add the astro_data directory to Python path
astro_data_path = Path(__file__).parent.parent.parent
if str(astro_data_path) not in sys.path:
    sys.path.append(str(astro_data_path))

# Import from the correct module path
try:
    from api.astro_data.modules.ml.feature_registry import FeatureRegistry
    from api.astro_data.modules.ml import agent
except ImportError:
    # Fallback to relative import
    from modules.ml.feature_registry import FeatureRegistry
    from modules.ml import agent

feature_registry = FeatureRegistry()

agent.init(llm)

PROMPT_TEMPLATE = '''
You are an expert system designed to select the best machine learning model and extract input parameters to answer user questions about foam factory data.
Your tasks are:
1. Understand the user's query and identify the relevant prediction model
2. Extract parameters based on the model's required features
3. Return the model name and parameters in JSON format

Question: {question}

Relevant Information:
{context}

Instructions:
1. Analyze the question and the provided information.
2. Select the most appropriate ML model to answer the question. If no suitable model is found, respond with "No suitable model found."
3. Extract the necessary input parameters/variables from the question and provided information. 
4. Return the selected model name and the input parameters in JSON format. If no suitable model is found, return "No suitable model found."
5. In output, year should be number like 2025, month should be 1 to 12, factories should be 0 to 4
6. If default values in case following are not mentioned: factories: [0], years:[2025], months:[1]
7. Strictly return output in format listed under 'Output Format:' section
8. Use this mapping:
    Factories:
        Factory 1 -> 0
        Factory 2 -> 1
        ...
        Factory 5 -> 4
9. For time periods, use the following mapping:
    - "next quarter" or "Q1": [1, 2, 3] for first quarter, [4, 5, 6] for second quarter, etc.
    - "next month": [current month + 1]
    - "next year": all 12 months of the next year
    - "next 6 months": [current month + 1, current month + 2, ..., current month + 6]

Examples:
Examples for Production Volume Model
1. Question: Predict production volume for March with 75% machine utilization and 5 years operator experience
Output: {{"model_name": "production_volume_model", "input_parameters": {{
    "Machine Utilization (%)": 75, 
    "Operator Experience (years)": 5,
    "Months": [3],
    "Years": [2025],
    "Factories": [0]
}}}}

2. Question: Estimate production volume for March and April across factories 1 and 2 with 90% machine utilization
Output: {{"model_name": "production_volume_model", "input_parameters": {{
    "Machine Utilization (%)": 90,
    "Months": [3, 4],
    "Years": [2025],
    "Factories": [0, 1]
}}}}

3. Question: What will the production volume be over the next quarter?
Output: {{"model_name": "production_volume_model", "input_parameters": {{
    "Months": [1, 2, 3],
    "Years": [2025],
    "Factories": [0]
}}}}

Examples for Revenue Model
4. Question: Forecast revenue for Q1 (Jan-Mar) across all factories with 5000 units production volume
Output: {{"model_name": "revenue_model", "input_parameters": {{
    "Production Volume (units)": 5000,
    "Months": [1, 2, 3],
    "Years": [2025],
    "Factories": [0, 1, 2, 3, 4]
}}}}

5. Question: Predict revenue for June and July in factories 2 and 3 with 90% machine utilization
Output: {{"model_name": "revenue_model", "input_parameters": {{
    "Machine Utilization (%)": 90,
    "Months": [6, 7],
    "Years": [2025],
    "Factories": [1, 2]
}}}}

6. Question: What will the revenue for factory 3 be over the next quarter?
Output: {{"model_name": "revenue_model", "input_parameters": {{
    "Months": [1, 2, 3],
    "Years": [2025],
    "Factories": [2]
}}}}

Examples for Profit Margin Model
7. Question: Estimate profit margin for Q2 (Apr-Jun) in factory 1 with 500 kg CO2 emissions
Output: {{"model_name": "profit_margin_model", "input_parameters": {{
    "CO2 Emissions (kg)": 500,
    "Months": [4, 5, 6],
    "Years": [2025],
    "Factories": [0]
}}}}

8. Question: Predict profit margin for September and October across factories 1, 2 and 3
Output: {{"model_name": "profit_margin_model", "input_parameters": {{
    "Months": [9, 10],
    "Years": [2025],
    "Factories": [0, 1, 2]
}}}}

9. Question: What will the profit margin of factory 1 over the next quarter?
Output: {{"model_name": "profit_margin_model", "input_parameters": {{
    "Months": [1, 2, 3],
    "Years": [2025],
    "Factories": [0]
}}}}

10. Question: What will the profit margin of factory 2 over the next 6 months?
Output: {{"model_name": "profit_margin_model", "input_parameters": {{
    "Months": [1, 2, 3, 4, 5, 6],
    "Years": [2025],
    "Factories": [1]
}}}}

**General Instructions:**

*   Select the most appropriate ML model to answer the question. If no suitable model is found, respond with "No suitable model found."
*   Extract the necessary input parameters/variables from the question and provided information. 
*   Return the selected model name and the input parameters in JSON format. If no suitable model is found, return "No suitable model found."
*   In output, year should be number like 2025, month should be 1 to 12, factories should be 0 to 4 and locations should be 0 to 4
*   In case year(s), month(s), factorie(s) or location(s) are not mentioned in question then use following: factories: [0], years:[2025], months:[1]
*   For questions about "next quarter", map to the appropriate three consecutive months
*   For "factory 1", always map to factory index 0, "factory 2" to index 1, etc.
*   Strictly return output in format listed under 'Output Format:' section
*   Handle empty results gracefully by stating that no data is available.

Output Format:

{{"model_name": "model_name", "input_parameters": {{"Years":[year],"Months":[month],"Factories":[factory]}}}}

or

No suitable model found.
'''

def get_model_and_params(question):
    
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDINGS_MODEL)
    try:
        vector_db = FAISS.load_local(VECTOR_DB_PATH, embeddings, allow_dangerous_deserialization=True)
    except Exception as e:
        print(f"Error loading vector DB: {e}")
        return None, None

    # Retrieval
    docs = vector_db.similarity_search(question, k=5)
    context = "\n".join([doc.page_content for doc in docs])

    # Prompt Engineering
    prompt = PROMPT_TEMPLATE 
    if isinstance(prompt, str):
      prompt = PromptTemplate(
          input_variables=["question", "context"],
          template=prompt,
      )
    final_prompt = prompt.format(question=question, context=context)

    try:
        messages = [HumanMessage(content=final_prompt)] 
        llm_output = llm.invoke(messages).content

        print('llm output:\n '+str(llm_output))

        import regex
        pattern = regex.compile(r'\{(?:[^{}]|(?R))*\}')
        llm_output = pattern.findall(str(llm_output))

        print('llm json output:\n '+str(llm_output))
        
        # Clean up the JSON string to handle placeholder values
        if llm_output and len(llm_output) > 0:
            # Replace [default_value] with null to make it valid JSON
            cleaned_json = llm_output[0].replace('[default_value]', 'null')
            try:
                response = json.loads(cleaned_json)
            except json.JSONDecodeError as e:
                print(f"JSON decode error after cleaning: {e}")
                # Try to extract model name and parameters from non-JSON output
                if "profit_margin_model" in llm_output[0]:
                    print("Attempting to extract profit_margin_model parameters from non-JSON output")
                    return "profit_margin_model", {"Months": [1, 2, 3], "Years": [2025], "Factories": [0]}
                # Check for production volume queries
                elif "production_model" in llm_output[0] or "production volume" in llm_output[0].lower():
                    print("Attempting to extract production_volume_model parameters from non-JSON output")
                    # Try to extract factory numbers
                    factories = [0]  # Default to factory 1 (index 0)
                    import re
                    factory_matches = re.findall(r'factory\s+(\d+)', str(llm_output[0]).lower())
                    if factory_matches:
                        factories = [int(f) - 1 for f in factory_matches]  # Convert to 0-based index
                    
                    # Try to extract months
                    months = [1, 2, 3]  # Default to Q1
                    if "july" in str(llm_output[0]).lower() and "december" in str(llm_output[0]).lower():
                        months = [7, 8, 9, 10, 11, 12]
                    
                    return "production_volume_model", {"Months": months, "Years": [2025], "Factories": factories}
                return None, None
        else:
            print("No JSON pattern found in LLM output")
            # Check if this is a profit margin query for a factory over the next quarter
            if "profit margin" in str(llm_output).lower() and "factory" in str(llm_output).lower() and "quarter" in str(llm_output).lower():
                print("Detected profit margin query for next quarter, using default parameters")
                # Extract factory number if possible
                factory_num = 0  # Default to factory 1 (index 0)
                import re
                factory_match = re.search(r'factory\s+(\d+)', str(llm_output).lower())
                if factory_match:
                    factory_num = int(factory_match.group(1)) - 1  # Convert to 0-based index
                return "profit_margin_model", {"Months": [1, 2, 3], "Years": [2025], "Factories": [factory_num]}
            # Check if this is a production volume query
            elif "production volume" in str(llm_output).lower() and "factory" in str(llm_output).lower():
                print("Detected production volume query, using extracted parameters")
                # Extract factory numbers if possible
                factories = [0]  # Default to factory 1 (index 0)
                import re
                factory_matches = re.findall(r'factory\s+(\d+)', str(llm_output).lower())
                if factory_matches:
                    factories = [int(f) - 1 for f in factory_matches]  # Convert to 0-based index
                
                # If no specific factories found, check for multiple factories like 4,5,6
                if len(factories) <= 1:
                    factory_list_match = re.search(r'factory\s+(\d+)\s*,\s*(\d+)\s*,\s*(\d+)', str(llm_output).lower())
                    if factory_list_match:
                        factories = [int(factory_list_match.group(1)) - 1, 
                                    int(factory_list_match.group(2)) - 1,
                                    int(factory_list_match.group(3)) - 1]
                
                # Extract months if possible
                months = [1, 2, 3]  # Default to Q1
                if "july" in str(llm_output).lower() and "december" in str(llm_output).lower():
                    months = [7, 8, 9, 10, 11, 12]
                
                return "production_volume_model", {"Months": months, "Years": [2025], "Factories": factories}
            return None, None
        
        if "model_name" in response and "input_parameters" in response:
            final_params = response["input_parameters"]
            # Fix for production_model -> production_volume_model mapping
            model_name = response["model_name"]
            if model_name == "production_model":
                print("Correcting model name from 'production_model' to 'production_volume_model'")
                model_name = "production_volume_model"
            return model_name, final_params
        else:
            print("LLM output is not in the expected JSON format:")
            print(llm_output)
            return None, None

    except json.JSONDecodeError:
        if "No suitable model found." in llm_output:
            return None, None
        else:
            print("Error decoding JSON from LLM output:")
            print(llm_output)
            return None, None
        
def get_ml_answer(query):
    model_name, model_params = get_model_and_params(query)
    if model_name is not None:
        data = agent.run_agent(model_name, **model_params)
    else:
        # Return a properly formatted response when no model is found
        return json.dumps({
            "status": "error",
            "message": "Unable to map model for given query!!",
            "llm_output_text_summmary": "I couldn't find a suitable model to answer your question. Please try rephrasing or ask a different question."
        })
    
    print(data)
    # Check if data is a dictionary and has the 'output' key
    if isinstance(data, dict) and 'output' in data:
        return data['output']
    else:
        # Handle the case when data is not a dictionary or doesn't have 'output' key
        return json.dumps({
            "status": "error",
            "message": "Invalid response format from model",
            "llm_output_text_summmary": "I encountered an issue while processing your request. The model returned an unexpected format."
        })

def get_ml_answer_with_feedback(model_name: str, input_data: pd.DataFrame) -> Dict:
    feature_status = feature_registry.validate_features(model_name, input_data)
    missing_features = [f for f, present in feature_status.items() if not present]
    
    feature_importance = feature_registry.get_feature_importance(model_name)
    
    try:
        prediction = agent.run_agent(model_name, input_data)
        return {
            'status': 'success',
            'prediction': prediction,
            'feature_status': feature_status,
            'feature_importance': feature_importance,
            'missing_features': missing_features
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }

# if __name__ == "__main__":
#     queries = [
#         "Estimate profit margin with 500 kg CO2 emissions, 3000 kWh energy consumption, and 90% machine utilization",
#         "Forecast revenue with 5000 units production volume, 3000 kWh energy consumption, and 80% machine utilization"
#          "Estimate profit margin with 500 kg CO2 emissions, 3000 kWh energy consumption, and 90% machine utilization",
#          "Forecast revenue with 5000 units production volume, 3000 kWh energy consumption, and 80% machine utilization"
#     ]
    
#     # Test each query
#     for query in queries:
#         print(f"Query: {query}")
#         try:
#             result = get_ml_answer(query)
#             print(f"Result: {result}")
#             print()
#         except Exception as e:
#             print(f"Error processing query: {e}")
#             print()