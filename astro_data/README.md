# Factory Astro

Factory Astro is a predictive analytics feature that allows users to ask questions about factory performance and get ML-powered predictions with visualizations.

## Setup Instructions

### 1. Environment Setup

Create a `.env` file in the root directory with your OpenAI API key:

```
OPENAI_API_KEY=your_openai_api_key_here
```

### 2. Install Dependencies

Install the required packages:

```bash
pip install -r requirements.txt
```

### 3. Directory Structure

Ensure your project maintains the following structure:

```
project_root/
├── .env                    # Environment variables
├── app.py                  # Main application file
├── page/                   # Page components
│   ├── __init__.py         # Exports Show_Factoryastro
│   └── Factory_Astro.py    # Factory Astro UI implementation
└── modules/                # Backend modules
    └── ml/                 # Machine learning modules
        ├── __init__.py
        ├── ml_rag.py       # RAG implementation
        ├── agent.py        # Agent functionality
        ├── feature_registry.py
        ├── prediction.py
        ├── predictor.py
        ├── performance_pred.py
        ├── data_descriptions.json
        ├── model_descriptions.json
        ├── prod_volume_prediction_model.pkl
        ├── prof_margin_prediction_model.pkl
        ├── revenue_prediction_model.pkl
        └── factory_vector_db/  # Vector database files
```

### 4. Running the Application

Run the Streamlit application:

```bash
streamlit run app.py
```

## Integration with Existing Projects
```python
from astro_data.api import get_factory_prediction, get_example_questions

# Get a prediction
response = get_factory_prediction("What will the revenue for factory 3 be over the next 6 months?")

# Check if the prediction was successful
if response["status"] == "success":
    # Get the prediction data
    prediction_data = response["data"]["Predicted_data"]
    summary = response["summary"]
    
    # Use the data in your GUI
    # ...

# Get example questions
example_questions = get_example_questions()
```

## Models

The module uses three machine learning models:

1. Production Volume Model
2. Revenue Model
3. Profit Margin Model

Each model takes specific input parameters and returns predictions for the specified time periods and factories.

## Usage Examples

The module can be used to answer questions about factory performance, such as:

- "What will the revenue for factory 3 be over the next 6 months?"
- "What will the profit margin be from July to December for factory 2?"
- "What will the production volume be over the next 6 months?"

The module will analyze the question, select the appropriate model, extract the necessary parameters, and return a prediction that can be displayed in your GUI.

## Response Format

The `get_factory_prediction` function returns a dictionary with the following structure:

```python
{
    "status": "success",  # or "error"
    "data": {  # Only present if status is "success"
        "Predicted_data": [...],  # Array of prediction data
        "llm_output_text_summmary": "..."  # Summary text
    },
    "summary": "..."  # Summary text (same as llm_output_text_summmary)
}
```

In case of an error, the response will have the following structure:

```python
{
    "status": "error",
    "message": "Error message",
    "raw_response": "..."  # Optional, only present if the error is due to parsing
}
