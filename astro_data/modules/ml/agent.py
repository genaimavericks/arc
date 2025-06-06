from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import StructuredTool
import json
import os
from pathlib import Path
import pandas as pd
from modules.ml import predictor as predictor
from datetime import datetime
from modules.ml.feature_registry import FeatureRegistry

if "OPENAI_API_KEY" not in os.environ:
    os.environ["OPENAI_API_KEY"] = ""

feature_registry = FeatureRegistry()

MODEL_DESCRTIPTIONS_FILE = Path(__file__).parent.parent/"ml/model_descriptions.json"
DATA_DESCRIPTIONS_FILE = Path(__file__).parent.parent/"ml/data_descriptions.json"

LLM_MODEL = "gpt-4"
ALL_MONTHS = list(range(1, 13))  # All 12 months
ALL_LOCATIONS = [0,1,2,3] # All 4 locations

def generate_sample_data(model_name: str, **kwargs) -> pd.DataFrame:
    """Generates sample data for multiple months and factories.

    Args:
        model_name (str): Name of the model
        **kwargs: Additional features to include in the sample data

    Returns:
        pd.DataFrame: Generated sample data
    """
    print("INPUT PARAMS: "+str(kwargs))

    # Get required features for the model
    print("MODEL NAME: " + model_name)
    required_features = feature_registry.get_features(model_name)
    print("Required Features: " + str(required_features))
    # Initialize empty DataFrame
    future_data = pd.DataFrame()
    
    # Extract base parameters
    years = kwargs.get('year', [datetime.now().year])
    months = kwargs.get('month', ALL_MONTHS)
    factories = kwargs.get('Factory', [0])
    
    for year in years:
        for month in months:
            for factory in factories:
                # Create base data with year, month and factory
                temp_data = pd.DataFrame({
                    'month': [month],
                    'year': [year],
                    'Factory': [factory]
                })
                
                # Add any additional features from kwargs
                for feature, value in kwargs.items():
                    if feature not in temp_data.columns and feature in required_features:
                        temp_data[feature] = value
                
                # Fill any missing required features with mean values
                for feature in required_features:
                    if feature not in temp_data.columns:
                        temp_data[feature] = predictor.get_mean_value(model_name, feature)
                future_data = pd.concat([future_data, temp_data], ignore_index=True)
    
    #reselect since order might have change
    future_data = future_data[required_features]
    return future_data

def predict(model_name, **kwargs):
    """Generalized prediction function for multiple inputs."""
    try:
        input_data = generate_sample_data(model_name, **kwargs)
        print("Generated/combined input data for prediction: \n"+input_data.to_csv(index=False))
        if input_data is None:
            return "Unknown model name or no data generated."
        
        predictions = predictor.getPrediction(model_name, input_data)
        input_data['prediction'] = predictions
        
        filtered_data = input_data[['year', 'month', 'Factory', 'prediction']]
        
        return input_data.to_json(orient='records')  # Return only the filtered data as JSON string
    
    except (KeyError, IndexError, ValueError, TypeError) as e:
        return f"Error during prediction for {model_name}: {e}"

tools = []

try:
    with open(MODEL_DESCRTIPTIONS_FILE, 'r') as f:
        model_descriptions = json.load(f)
except FileNotFoundError:
    print(f"Error: {MODEL_DESCRTIPTIONS_FILE} not found. Create this file.")
    exit()

for model_name, model_data in model_descriptions.items():
    tool_name = model_name
    description = f"Useful for predicting {model_data['target_variable'].lower()}. Input should be "
    description += ", ".join([f"{feature} ({'array of integer' if str(feature).lower() in ['year','month'] else 'array of integer'})" for feature in model_data['input_features']]) + "."
    input_params = model_data['input_features']
    tools.append(
        StructuredTool.from_function(
            name=tool_name,
            func=lambda model_name=model_name, input_params=input_params: predict(model_name, **input_params),
            description=description
        )
    )


# Get features for all models
features = {
    'production_volume_model': feature_registry.get_features('production_volume_model'),
    'revenue_model': feature_registry.get_features('revenue_model'),
    'profit_margin_model': feature_registry.get_features('profit_margin_model')
}

# Format prompt with feature information
json_features = json.dumps(features, indent=2)
json_features = json_features.replace('{','{{').replace('}','}}')

sysmsg = """
    You are an advanced ML model assistant. Your job is to predict values based on the given data
    and always provide the output in the requested format.

    Example of incorrect intermidiate input for given question-
        Question:
        Predict production volume (units) for years [2025], months [1, 2, 3, 4, 5], factories [2]
        
        Incorrect intermidiate output:
        `production_volume_model` with `{{'year': [2025, 2025, 2025, 2025, 2025], 'month': [1, 2, 3, 4, 5], 'factory': [2, 2, 2, 2, 2]}}`

        Correct intermidiate output:
        `production_volume_model` with `{{'year': [2025], 'month': [1, 2, 3, 4, 5], 'factory': [2]}}`

    Make sure the output strictly adheres to the specified format. If the user provides custom output requirements,
    adjust your response accordingly.


    Output Format: {{"Predicted_data":ml_model_output_dataframe, "llm_output_text_summmary":Text Summary}}
    """

prompt = ChatPromptTemplate.from_messages([
    ("system", sysmsg),
    ("placeholder", "{chat_history}"),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}")
])

agent_executor = None

def init(llm):
    global agent_executor
    
    agent = create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)


def run_agent(model_name, **kwargs):
    """Runs the agent with the specified model and parameters."""
   
    years = kwargs.get('years', [])
    months = kwargs.get("months", [])
    factories = kwargs.get("factories", [])

    if not years:
        years = [datetime.now().year]
    if not months:
        months = ALL_MONTHS
    if not factories:
        factories = [0] # default factory
    
    prompt_string = f"Predict {model_descriptions[model_name]['target_variable'].lower()} for "
    prompt_string += ", ".join([f"{key} {value}" for key,value in kwargs.items()]) + "."

    print("Prompt to AGENT :"+prompt_string)
    return agent_executor.invoke({"input": prompt_string})