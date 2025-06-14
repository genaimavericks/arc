# UI components removed
import pandas as pd
import numpy as np
import math
import pandas as pd
import plotly.express as px
import numpy as np
import math



def yearFilter(factory_profit_df): 
    min_value = factory_profit_df['month'].min()
    max_value = factory_profit_df['month'].max()
    
    # Default to full range instead of UI slider
    from_year, to_year = min_value, max_value

    return from_year, to_year

def selectedFactories(factory_profit_df):
    factories = factory_profit_df['Factory'].unique()
    
    # Default to all factories instead of UI multiselect
    selected_factories = factories

    return selected_factories

# Process revenue data
def process_revenue_data(factory_profit_df, selected_factories, from_month, to_month):
    """Process revenue data without UI components
    
    Args:
        factory_profit_df (pd.DataFrame): Factory profit dataframe
        selected_factories (list): List of selected factories
        from_month (int): Start month
        to_month (int): End month
        
    Returns:
        pd.DataFrame: Filtered and processed dataframe
    """
    # Filter the data
    filtered_factory_df = factory_profit_df[
        (factory_profit_df['Factory'].isin(selected_factories)) &
        (factory_profit_df['month'] <= to_month) &
        (factory_profit_df['month'] >= from_month)
    ]

    if filtered_factory_df.empty:
        print("No data available for the selected filters (Factories, Months).")
        return None
    
    # Check if the required column exists
    if 'Predicted Revenue ($)' not in filtered_factory_df.columns:
        print("The column 'Predicted Revenue ($)' is not present in the dataframe.")
        return None

    # Apply transformations for data processing
    filtered_factory_df['Transformed Revenue'] = filtered_factory_df['Predicted Revenue ($)']
    filtered_factory_df['Transformed Revenue'] += np.random.uniform(-1000, 1000, size=len(filtered_factory_df))
    
    # Prepare data for output
    categorical_features = ['Product Category', 'Machine Type', 'Supplier']
    preview_columns = ['month', 'Factory', 'Predicted Revenue ($)']
    for feature in categorical_features:
        if feature in filtered_factory_df.columns:
            preview_columns.append(feature)
    
    return filtered_factory_df

# Process profit margin data
def process_profit_margin_data(factory_profit_df, selected_factories, from_month, to_month):
    """Process profit margin data without UI components
    
    Args:
        factory_profit_df (pd.DataFrame): Factory profit dataframe
        selected_factories (list): List of selected factories
        from_month (int): Start month
        to_month (int): End month
        
    Returns:
        pd.DataFrame: Filtered and processed dataframe
    """
    filtered_factory_df = factory_profit_df[
        factory_profit_df['Factory'].isin(selected_factories)
        & (factory_profit_df['month'] <= to_month)
        & (from_month <= factory_profit_df['month'])
    ].copy()

    if filtered_factory_df.empty:
        print("No data available for the selected filters (Factories, Months).")
        return None

    if not filtered_factory_df.empty:
        def adjust_prof(row): #same logic for profit margin
            Predicted_Profit_Margin = row['Predicted Profit Margin (%)']  # assuming you have a 'Profit Margin' column
            return Predicted_Profit_Margin

        filtered_factory_df['Predicted Profit Margin (%)'] = filtered_factory_df.apply(adjust_prof, axis=1)
    
    # Prepare data for output
    categorical_features = ['Product Category', 'Supplier', 'Machine Type']
    preview_columns = ['month', 'Factory', 'Predicted Profit Margin (%)']
    for feature in categorical_features:
        if feature in filtered_factory_df.columns:
            preview_columns.append(feature)
    
    return filtered_factory_df


# Process production volume data
def process_production_volume_data(factory_profit_df, selected_factories, from_month, to_month):
    """Process production volume data without UI components
    
    Args:
        factory_profit_df (pd.DataFrame): Factory profit dataframe
        selected_factories (list): List of selected factories
        from_month (int): Start month
        to_month (int): End month
        
    Returns:
        pd.DataFrame: Filtered and processed dataframe
    """
    # Filter the data
    filtered_factory_df = factory_profit_df[
        (factory_profit_df['Factory'].isin(selected_factories)) &
        (factory_profit_df['month'] <= to_month) &
        (factory_profit_df['month'] >= from_month)
    ].copy()

    if filtered_factory_df.empty:
        print("No data available for the selected filters (Factories, Months).")
        return None

    # Check if the required column exists
    if 'Predicted Production Volume (units)' not in filtered_factory_df.columns:
        print("The column 'Predicted Production Volume (units)' is not present in the dataframe.")
        return None

    # Apply transformations for data processing
    filtered_factory_df['Transformed Volume'] = filtered_factory_df['Predicted Production Volume (units)']
    filtered_factory_df['Transformed Volume'] += np.random.uniform(-10, 10, size=len(filtered_factory_df))
    
    # Prepare data for output
    categorical_features = ['Raw Material Quality']
    preview_columns = ['month', 'Factory', 'Predicted Production Volume (units)']
    for feature in categorical_features:
        if feature in filtered_factory_df.columns:
            preview_columns.append(feature)
    
    return filtered_factory_df


# Process prediction data combining all data types
def process_prediction_data(result_rev_df, result_prof_df):
    """Process all prediction data without UI components
    
    Args:
        result_rev_df (pd.DataFrame): Revenue prediction dataframe
        result_prof_df (pd.DataFrame): Profit margin prediction dataframe
        
    Returns:
        tuple: Processed dataframes (revenue_df, profit_df)
    """
    # Get the min and max months from the data
    min_month = min(result_rev_df['month'].min(), result_prof_df['month'].min())
    max_month = max(result_rev_df['month'].max(), result_prof_df['month'].max())
    
    # Get the filter values
    from_month, to_month = yearFilter(result_rev_df)
    selected_factories = selectedFactories(result_rev_df)
    
    # Process the data
    revenue_df = process_revenue_data(result_rev_df, selected_factories, from_month, to_month)
    profit_df = process_profit_margin_data(result_prof_df, selected_factories, from_month, to_month)
    
    return revenue_df, profit_df
