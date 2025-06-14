import pandas as pd
import numpy as np
import joblib
import os
import json
import sys
from pathlib import Path

# Add the parent directory to Python path to find the api package
parent_path = Path(__file__).parent.parent.parent.parent
if str(parent_path) not in sys.path:
    sys.path.append(str(parent_path))
    print(f"Added {parent_path} to sys.path")

from api.churn_astro.utils.data_processing import clean_and_encode_data, clean_and_encode_data_for_7, encode_data
from sklearn.ensemble import GradientBoostingClassifier

# Initialize or load the model
CHURN_REG_MODEL_FILE = Path(__file__).parent.parent / "modules/data/telchurn/gradient_boosting_model_new.joblib"

try:
    model = joblib.load(CHURN_REG_MODEL_FILE)
    print("Loaded existing model")
except Exception as e:
    print(f"Creating new model due to: {str(e)}")
    # Create a simple gradient boosting model
    model = GradientBoostingClassifier(
        n_estimators=100,
        learning_rate=0.1,
        max_depth=3,
        random_state=42
    )
    
    # Create some sample training data
    np.random.seed(42)
    n_samples = 1000
    
    # Generate synthetic features
    X = np.random.rand(n_samples, 7)  # 7 features
    # Adjust feature ranges to match our domain
    X[:, 0] *= 72  # tenure: 0-72 months
    X[:, 1:4] = np.random.choice([0, 1, 2], size=(n_samples, 3))  # categorical features
    X[:, 4] = np.random.choice([0, 1, 2], size=n_samples)  # contract type
    X[:, 5] = 20 + 80 * X[:, 5]  # monthly charges: $20-$100
    X[:, 6] = X[:, 5] * (1 + 5 * X[:, 0]/72)  # total charges based on tenure and monthly
    
    # Generate synthetic target (more likely to churn if high monthly charges and low tenure)
    churn_prob = 0.3 * (X[:, 5]/100) - 0.2 * (X[:, 0]/72) + 0.2 * (X[:, 4] == 0)
    y = (churn_prob + 0.2 * np.random.rand(n_samples) > 0.5).astype(int)
    
    # Train the model
    model.fit(X, y)
    
    # Save the model
    joblib.dump(model, CHURN_REG_MODEL_FILE)
    print("Created and saved new model")

print("Model type:", type(model).__name__)
if hasattr(model, 'feature_importances_'):
    print("Model has feature_importances_ attribute")
    print("Feature importances:", model.feature_importances_)
elif hasattr(model, 'coef_'):
    print("Model has coef_ attribute")
    print("Coefficients:", model.coef_)
else:
    print("Warning: Model does not have feature importance capabilities")

# Core functionality without UI dependencies

def make_predictions(model, input_data):
    print('Starting make_predictions')
    print('Input data shape:', input_data.to_csv(index=False))
    """Common prediction logic for both form and CSV inputs"""
    if input_data.shape[1] == 7:
        processed_df = clean_and_encode_data_for_7(input_data)
    else:
        processed_df = clean_and_encode_data(input_data)
    
    print('Processed DataFrame shape:', processed_df.to_csv(index=False))
    clean_columns = ['tenure', 'OnlineSecurity', 'OnlineBackup', 'TechSupport', 'Contract', 'MonthlyCharges', 'TotalCharges']
    processed_df = processed_df[clean_columns]
    
    # Make predictions
    predictions = model.predict(processed_df)
    proba = model.predict_proba(processed_df)[:, 1] if hasattr(model, 'predict_proba') else None
    
    # Calculate feature importance using coefficients or feature_importances_
    feature_importance = None
    print("Model type:", type(model).__name__)
    print("Model attributes:", dir(model))
    
    if hasattr(model, 'feature_importances_'):
        print("Using feature_importances_")
        importance_values = model.feature_importances_
        print("Importance values:", importance_values)
    elif hasattr(model, 'coef_'):
        print("Using model coefficients")
        importance_values = abs(model.coef_[0])
        print("Coefficient values:", importance_values)
    else:
        print("No feature importance attributes found")
        importance_values = None
        
    if importance_values is not None:
        feature_importance = pd.DataFrame({
            'Feature': clean_columns,
            'Importance': importance_values
        }).sort_values('Importance', ascending=False)  
        print("Feature importance DataFrame:")
        print(feature_importance.to_string())

    # Create result dataframe
    result_df = input_data.copy()
    result_df['Prediction'] = ['Churn' if p == 1 else 'No Churn' for p in predictions]
    if proba is not None:
        result_df['Churn Probability'] = proba

    print('Completed make_predictions')
    return result_df, proba, feature_importance


def process_prediction_results(result_df, proba, feature_importance, is_batch=False):
    """
    Process prediction results and return structured data without UI components
    
    Args:
        result_df (pd.DataFrame): DataFrame with prediction results
        proba (np.array): Probability values for predictions
        feature_importance (pd.DataFrame): Feature importance data
        is_batch (bool): Whether this is a batch prediction
        
    Returns:
        dict: Structured prediction results with feature importance
    """
    print('Processing prediction results')
    
    results = {}
    
    # Process batch or single prediction
    if is_batch:
        # Count predictions
        churn_count = (result_df['Prediction'] == 'Churn').sum()
        no_churn_count = (result_df['Prediction'] == 'No Churn').sum()
        
        results['summary'] = {
            'total': len(result_df),
            'churn_count': int(churn_count),
            'no_churn_count': int(no_churn_count),
            'churn_percentage': float(churn_count / len(result_df) * 100)
        }
        
        # Convert DataFrame to dict for JSON serialization
        results['predictions'] = result_df.to_dict(orient='records')
    else:
        # Single prediction
        prediction = result_df['Prediction'].iloc[0]
        results['prediction'] = prediction
        
        if 'Churn Probability' in result_df.columns:
            results['probability'] = float(result_df['Churn Probability'].iloc[0])
    
    # Process feature importance if available
    if feature_importance is not None:
        # Calculate percentage
        total_importance = feature_importance['Importance'].sum()
        feature_importance['Percentage'] = feature_importance['Importance'] / total_importance * 100
        
        # Add impact level
        def get_impact_level(percentage):
            if percentage > 30:
                return "High"
            elif percentage > 15:
                return "Medium"
            else:
                return "Low"
                
        feature_importance['Impact_Level'] = feature_importance['Percentage'].apply(get_impact_level)
        
        # Add descriptions from the global dictionary
        feature_importance['Description'] = feature_importance['Feature'].map(FEATURE_DESCRIPTIONS)
        
        # Convert to dict for JSON serialization
        results['feature_importance'] = []
        for _, row in feature_importance.iterrows():
            results['feature_importance'].append({
                'feature': row['Feature'],
                'importance': float(row['Importance']),
                'percentage': float(row['Percentage']),
                'impact_level': row['Impact_Level'],
                'description': row['Description'] if 'Description' in feature_importance.columns else None
            })
    
    print('Completed processing prediction results')
    return results

# Feature descriptions for documentation purposes
FEATURE_DESCRIPTIONS = {
    'tenure': 'Length of time customer has been with the company (months)',
    'Contract': 'Type of contract (Month-to-month, One year, Two year)',
    'OnlineSecurity': 'Whether customer has online security service',
    'OnlineBackup': 'Whether customer has online backup service',
    'TechSupport': 'Whether customer has technical support service',
    'MonthlyCharges': 'Monthly subscription charges',
    'TotalCharges': 'Total charges since becoming a customer'
}

# Default values for predictions when not all features are provided
DEFAULT_VALUES = {
    'tenure': 3,
    'OnlineSecurity': 'No',
    'OnlineBackup': 'No',
    'TechSupport': 'No',
    'Contract': 'Two year',
    'MonthlyCharges': 40.0,
    'TotalCharges': 2279.73
}

# Load the model once at module level
def load_model():
    """Load the churn prediction model"""
    try:
        # Primary path - use the model we already loaded at module level
        if 'model' in globals() and globals()['model'] is not None:
            return globals()['model']
            
        # Try to load from the modules/data directory within the api structure
        model_path = Path(__file__).parent.parent / 'modules' / 'data' / 'telchurn' / 'gradient_boosting_model_new.joblib'
        if model_path.exists():
            print(f"Loading model from {model_path}")
            model = joblib.load(model_path)
            return model
            
        # Fallback to models directory
        model_path = Path(__file__).parent.parent / 'models' / 'churn_model.pkl'
        if model_path.exists():
            print(f"Loading model from {model_path}")
            model = joblib.load(model_path)
            return model
            
        # Last resort - relative path
        model_path = Path('models/churn_model.pkl')
        print(f"Loading model from {model_path}")
        model = joblib.load(model_path)
        return model
    except Exception as e:
        print(f"Error loading model: {e}")
        return None

# Load the model at module initialization
model = load_model()

def predict_customer_churn(customer_data):
    """
    Predict churn for a single customer
    
    Args:
        customer_data (dict): Dictionary containing customer features
            Required keys: tenure, Contract, OnlineSecurity, OnlineBackup,
                           TechSupport, MonthlyCharges, TotalCharges
    
    Returns:
        dict: Dictionary containing prediction results
    """
    # Ensure model is loaded
    if model is None:
        return {
            'error': 'Model could not be loaded',
            'status': 'error'
        }
        
    # Fill missing values with defaults
    for key in DEFAULT_VALUES:
        if key not in customer_data or customer_data[key] is None:
            customer_data[key] = DEFAULT_VALUES[key]
    
    # Create DataFrame from customer data
    input_df = pd.DataFrame([customer_data])
    
    # Make predictions
    result_df, proba, feature_importance = make_predictions(model, input_df)
    
    # Format results
    prediction = result_df['Prediction'].iloc[0]
    probability = result_df['Churn Probability'].iloc[0] if 'Churn Probability' in result_df.columns else None
    
    # Create feature importance dict if available
    importance_dict = None
    if feature_importance is not None:
        importance_dict = {}
        for _, row in feature_importance.iterrows():
            importance_dict[row['Feature']] = {
                'importance': float(row['Importance']),
                'percentage': float(row['Percentage']) if 'Percentage' in feature_importance.columns else None,
                'impact_level': row['Impact_Level'] if 'Impact_Level' in feature_importance.columns else None
            }
    
    return {
        'prediction': prediction,
        'probability': float(probability) if probability is not None else None,
        'feature_importance': importance_dict,
        'customer_data': customer_data
    }

def predict_batch_churn(customers_df):
    """
    Predict churn for multiple customers
    
    Args:
        customers_df (pd.DataFrame): DataFrame containing customer features
    
    Returns:
        dict: Dictionary containing prediction results
    """
    # Ensure model is loaded
    if model is None:
        return {
            'error': 'Model could not be loaded',
            'status': 'error'
        }
    
    # Validate required columns
    required_columns = [
        'tenure', 'OnlineSecurity', 'OnlineBackup', 'TechSupport',
        'Contract', 'MonthlyCharges', 'TotalCharges'
    ]
    
    missing_columns = [col for col in required_columns if col not in customers_df.columns]
    if missing_columns:
        return {
            'error': f"Missing required columns: {', '.join(missing_columns)}",
            'status': 'error'
        }
    
    # Make predictions
    result_df, proba, feature_importance = make_predictions(model, customers_df)
    
    # Format results
    results = []
    for i, row in result_df.iterrows():
        customer_result = {
            'prediction': row['Prediction'],
            'probability': float(row['Churn Probability']) if 'Churn Probability' in result_df.columns else None
        }
        
        # Add original customer data
        customer_data = {}
        for col in customers_df.columns:
            value = row[col] if col in row else None
            if isinstance(value, (int, float, str, bool)):
                customer_data[col] = value
            else:
                customer_data[col] = str(value)
        
        customer_result['customer_data'] = customer_data
        results.append(customer_result)
    
    # Create feature importance dict if available
    importance_dict = None
    if feature_importance is not None:
        importance_dict = {}
        for _, row in feature_importance.iterrows():
            importance_dict[row['Feature']] = {
                'importance': float(row['Importance']),
                'percentage': float(row['Percentage']) if 'Percentage' in feature_importance.columns else None,
                'impact_level': row['Impact_Level'] if 'Impact_Level' in feature_importance.columns else None
            }
    
    return {
        'status': 'success',
        'predictions': results,
        'feature_importance': importance_dict,
        'count': len(results)
    }

# Example usage when running as a script
if __name__ == "__main__":
    # Example of single customer prediction
    customer = {
        'tenure': 12,
        'OnlineSecurity': 'No',
        'OnlineBackup': 'Yes',
        'TechSupport': 'No',
        'Contract': 'Month-to-month',
        'MonthlyCharges': 65.5,
        'TotalCharges': 786.0
    }
    result = predict_customer_churn(customer)
    print("Single customer prediction:")
    print(json.dumps(result, indent=2))
    
    # Example of batch prediction
    batch_data = pd.DataFrame([
        {
            'tenure': 12, 'OnlineSecurity': 'No', 'OnlineBackup': 'Yes',
            'TechSupport': 'No', 'Contract': 'Month-to-month',
            'MonthlyCharges': 65.5, 'TotalCharges': 786.0
        },
        {
            'tenure': 36, 'OnlineSecurity': 'Yes', 'OnlineBackup': 'Yes',
            'TechSupport': 'Yes', 'Contract': 'Two year',
            'MonthlyCharges': 105.8, 'TotalCharges': 3809.0
        }
    ])
    batch_result = predict_batch_churn(batch_data)
    print("\nBatch prediction:")
    print(f"Total predictions: {batch_result['count']}")
    print(f"Status: {batch_result['status']}")
    print("First prediction:", batch_result['predictions'][0]['prediction'])