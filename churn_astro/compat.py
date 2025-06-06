"""
Compatibility layer for churn_astro to work with RSW dependencies
"""
import importlib
import sys
import os
import numpy as np
import pandas as pd
from pathlib import Path
import joblib

def init_compatibility():
    """Initialize compatibility adaptations"""
    print("Initializing churn_astro compatibility layer")
    
    # Set up model path
    model_path = Path(__file__).parent / "modules/data/telchurn/gradient_boosting_model_new.joblib"
    
    # Check if model exists
    if not model_path.exists():
        print(f"Model file not found at {model_path}")
        create_fallback_model(model_path)
    else:
        print(f"Found model at {model_path}")
        
    # Check pandas and numpy compatibility
    check_numpy_pandas_compatibility()

def check_numpy_pandas_compatibility():
    """Check if numpy and pandas versions are compatible"""
    try:
        print(f"Using numpy version: {np.__version__}")
        print(f"Using pandas version: {pd.__version__}")
        
        # Test basic operations to ensure compatibility
        test_df = pd.DataFrame({'A': np.array([1, 2, 3]), 'B': np.array([4, 5, 6])})
        test_df['C'] = test_df['A'] + test_df['B']
        print("Pandas and NumPy compatibility check passed")
    except Exception as e:
        print(f"Pandas and NumPy compatibility issue: {str(e)}")

def create_fallback_model(model_path):
    """Create a fallback model if the original one is not found"""
    try:
        print("Creating fallback churn prediction model")
        from sklearn.ensemble import GradientBoostingClassifier
        
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
        
        # Create directory if it doesn't exist
        model_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save the model
        joblib.dump(model, model_path)
        print(f"Fallback model created and saved to {model_path}")
    except Exception as e:
        print(f"Error creating fallback model: {str(e)}")

# Initialize compatibility layer when module is imported
init_compatibility()
