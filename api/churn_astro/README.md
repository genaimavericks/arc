# Churn Prediction

A comprehensive telecom customer churn prediction system with both form-based and natural language interfaces.

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
│   ├── __init__.py         # Exports show_churn_pred
│   ├── churn_prediction.py # Churn prediction UI implementation
│   └── churn_bot.py        # Chatbot interface for churn prediction
├── utils/                  # Utility modules
│   ├── data_processing.py  # Data preprocessing utilities
│   └── rag.py              # Retrieval-augmented generation
└── modules/                # Backend modules
    └── data/               # Data files
        └── telchurn/       # Telecom churn data
            ├── gradient_boosting_model_new.joblib  # ML model
            └── TelecomChurn.csv                   # Dataset
```

### 4. Running the Application

Run the Streamlit application:

```bash
streamlit run app.py
```

## Integration with Existing Projects

To integrate the churn prediction feature into an existing project:

1. Copy the `page`, `utils`, and `modules` directories into your project
2. Import the `show_churn_pred` function from `page`
3. Ensure your application has access to the OpenAI API key
4. Call the `show_churn_pred()` function where you want to display the churn prediction interface

## Example Integration

```python
import streamlit as st
from page import show_churn_pred

# Your existing app code...

# When you want to show churn prediction
show_churn_pred()
```

## Feature Overview

The churn prediction system offers:

1. **Form-based Interface**
   - Input customer details through a user-friendly form
   - Upload CSV files for batch predictions
   - View prediction results with visualizations

2. **Natural Language Interface**
   - Ask questions about customer churn in plain English
   - Get predictions and explanations based on your queries
   - Configure default values for unspecified parameters

3. **Explanation System**
   - Understand the factors influencing churn predictions
   - Get context-aware explanations using retrieval-augmented generation
   - Visualize feature importance for better insights

## Example Questions for Chatbot

- "Will a customer with 12 months tenure and $75 monthly charges churn?"
- "What's the churn risk for a customer on a month-to-month contract with no online security?"
- "Predict churn for a customer with 24 months tenure, two-year contract, and tech support"
