"""
Churn Astro module for RSW
"""
import sys
import os
from pathlib import Path

# Add module paths to make relative imports work
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.append(str(current_dir))

# Import compatibility layer
from .compat import init_compatibility

# Initialize compatibility layer
init_compatibility()

# Make key modules available at package level
try:
    from .page.churn_bot import parse_query_to_input, chatbot_prediction
    from .page.churn_prediction import make_predictions, clean_and_encode_data
    from .utils.data_processing import clean_and_encode_data_for_7
    
    __all__ = [
        'parse_query_to_input',
        'chatbot_prediction',
        'make_predictions',
        'clean_and_encode_data',
        'clean_and_encode_data_for_7'
    ]
except ImportError as e:
    print(f"Warning: Could not import some churn_astro modules: {e}")
