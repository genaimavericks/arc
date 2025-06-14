import pandas as pd
from pathlib import Path
import sqlite3
from . import predictor

def generate_sample_data(model_name, years, months, factories, categorical_filters=None):
    """Generates sample data for multiple months and factories with optional categorical filters.

    Args:
        model_name (str): Name of the model
        years (list): List of years to generate data for
        months (list): List of months to generate data for
        factories (list): List of factories to generate data for
        categorical_filters (dict, optional): Dictionary of categorical feature filters. 
                                             Format: {'feature_name': value}

    Returns:
        pd.DataFrame: Generated sample data
    """
    keys = None
    if model_name == 'production_volume_model':
        keys = predictor.keys_prod_volume
        val_dict = predictor.prodvol_mean_dict
    if model_name == 'revenue_model':
        keys = predictor.keys_revenue
        val_dict = predictor.rev_mean_dict
    if model_name == 'profit_margin_model':
        keys = predictor.keys_prof_margin
        val_dict = predictor.prof_margin_mean_dict

    # Initialize with empty dict if None
    if categorical_filters is None:
        categorical_filters = {}

    future_data = pd.DataFrame()
    for year in years:
        for month in months:
            for factory in factories:
                    temp_data = pd.DataFrame({
                        'month': month,
                        'year': [year],
                        'Factory': [factory]
                    })
                    
                    # Apply all other features
                    for col in keys:
                        if col not in temp_data.columns:
                            # If this feature has a filter, use the filter value
                            if col in categorical_filters:
                                temp_data[col] = categorical_filters[col]
                            else:
                                temp_data[col] = val_dict[col]

                    future_data = pd.concat([future_data, temp_data], ignore_index=True)

    return future_data

def get_vol_prediction_for_6month(target, categorical_filters=None):
    """
    Allows the user to interactively predict targets and analyze parameters.
    
    Args:
        target (str): Target variable name
        categorical_filters (dict, optional): Dictionary of categorical feature filters
                                             Format: {'feature_name': value}
    
    Returns:
        pd.DataFrame: DataFrame with predictions
    """
    input_data = generate_sample_data('production_volume_model', [2025], [1,2,3,4,5,6], [0,1,2,3,4], categorical_filters)
    future_predictions = predictor.get_vol_prediction_for_6month(input_data)
    input_data[f'Predicted {target}'] = future_predictions
    
    return input_data

def get_rev_prediction_for_6month(target, categorical_filters=None):
    """
    Allows the user to interactively predict targets and analyze parameters.
    
    Args:
        target (str): Target variable name
        categorical_filters (dict, optional): Dictionary of categorical feature filters
                                             Format: {'feature_name': value}
    
    Returns:
        pd.DataFrame: DataFrame with predictions
    """
    input_data = generate_sample_data('revenue_model', [2025], [1,2,3,4,5,6], [0,1,2,3,4], categorical_filters)
    future_predictions = predictor.get_rev_prediction_for_6month(input_data)
    input_data[f'Predicted {target}'] = future_predictions
    
    return input_data

def get_foam_prediction_for_6month(target, categorical_filters=None):
    """
    Allows the user to interactively predict targets and analyze parameters.
    
    Args:
        target (str): Target variable name
        categorical_filters (dict, optional): Dictionary of categorical feature filters
                                             Format: {'feature_name': value}
    
    Returns:
        pd.DataFrame: DataFrame with predictions
    """
    input_data = generate_sample_data('profit_margin_model', [2025], [1,2,3,4,5,6], [0,1,2,3,4], categorical_filters)
    future_predictions = predictor.get_foam_prediction_for_6month(input_data)
    input_data[f'Predicted {target}'] = future_predictions
    
    return input_data

# Define categorical feature options for each model
def get_categorical_feature_options():
    """
    Returns dictionaries of categorical feature options for each model.
    
    Returns:
        dict: Dictionary containing options for each categorical feature by model
    """
    return {
        'revenue_model': {
            'Product Category': [0, 1, 2, 3],  # Assuming 4 product categories
            'Machine Type': [0, 1, 2],         # Assuming 3 machine types
            'Supplier': [0, 1, 2, 3]           # Assuming 4 suppliers
        },
        'profit_margin_model': {
            'Product Category': [0, 1, 2, 3],  # Assuming 4 product categories
            'Supplier': [0, 1, 2, 3],          # Assuming 4 suppliers
            'Machine Type': [0, 1, 2]          # Assuming 3 machine types
        },
        'production_volume_model': {
            'Raw Material Quality': [0, 1, 2]  # Assuming 3 quality levels
        }
    }
