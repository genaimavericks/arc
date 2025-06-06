# Make streamlit optional
try:
    import streamlit as st
except ImportError:
    # Create a dummy st object for API mode
    class DummyStreamlit:
        def __getattr__(self, name):
            return lambda *args, **kwargs: None
        
        def slider(self, *args, **kwargs):
            # Return default values for sliders
            return kwargs.get('value', [0, 0])
    
    st = DummyStreamlit()
import pandas as pd
import plotly.express as px
import numpy as np
import math



def yearFilter(factory_profit_df): 
    min_value = factory_profit_df['month'].min()
    max_value = factory_profit_df['month'].max()

    from_year, to_year = st.slider(
        'Which months are you interested in?',
        min_value=min_value,
        max_value=max_value,
        value=[min_value, max_value]
    )

    return from_year, to_year

def selectedFactories(factory_profit_df):
    factories = factory_profit_df['Factory'].unique()

    selected_factories = st.multiselect(
        'Which factories would you like to view?',
        factories,
        [factories[0]] if len(factories) > 0 else []
    )

    return selected_factories

# Line graph for revenue
def lineGraph_rev(factory_profit_df, selected_factories, from_month, to_month, log_scale=False):
    # Filter the data
    filtered_factory_df = factory_profit_df[
        (factory_profit_df['Factory'].isin(selected_factories)) &
        (factory_profit_df['month'] <= to_month) &
        (factory_profit_df['month'] >= from_month)
    ]

    if filtered_factory_df.empty:
        st.warning("No data available for the selected filters (Factories, Months).")
        return
    
    # Check if the required column exists
    if 'Predicted Revenue ($)' not in filtered_factory_df.columns:
        st.error("The column 'Predicted Revenue ($)' is not present in the dataframe.")
        return

    # Apply transformations for hover data
    filtered_factory_df['Transformed Revenue'] = filtered_factory_df['Predicted Revenue ($)']
    filtered_factory_df['Transformed Revenue'] += np.random.uniform(-1000, 1000, size=len(filtered_factory_df))

    # Create a copy of the dataframe for hover data
    hover_df = filtered_factory_df[['month', 'Transformed Revenue']].copy()

    # Plot the graph
    st.header('Predicted Revenue ($)', divider='gray')
    
    # Extract categorical features for hover data if they exist
    hover_data = {'month': True, 'Transformed Revenue': True}
    categorical_features = ['Product Category', 'Machine Type', 'Supplier']
    for feature in categorical_features:
        if feature in filtered_factory_df.columns:
            hover_data[feature] = True
    
    # Color by Factory
    fig = px.line(
        filtered_factory_df,
        x='month',
        y='Predicted Revenue ($)',
        color='Factory',
        hover_data=hover_data,
        markers=True,
        labels={
            'month': 'Month',
            'Predicted Revenue ($)': 'Predicted Revenue ($)'
        }
    )
    
    # Improve layout
    fig.update_layout(
        xaxis_title='Month',
        yaxis_title='Predicted Revenue ($)',
        legend_title='Factory',
        hovermode='closest'
    )
   
    st.plotly_chart(fig)

    # Add table with preview (5 rows) and expand for full table
    st.write("Preview of Predicted data (first 5 rows):")
    
    # Determine which columns to show in the preview
    preview_columns = ['month', 'Factory', 'Predicted Revenue ($)']
    for feature in categorical_features:
        if feature in filtered_factory_df.columns:
            preview_columns.append(feature)
    
    try:
        st.table(filtered_factory_df[preview_columns].head(5))
        with st.expander("Show Full Table"):
             st.write("Full Predicted data:")
             st.dataframe(filtered_factory_df)
    except KeyError as e:
        st.error(f"KeyError: {e}. Please ensure the required columns exist in the dataframe.")

# Line graph for profit margin
def lineGraph_prof(factory_profit_df, selected_factories, from_month, to_month):
    filtered_factory_df = factory_profit_df[
        factory_profit_df['Factory'].isin(selected_factories)
        & (factory_profit_df['month'] <= to_month)
        & (from_month <= factory_profit_df['month'])
    ].copy()

    if filtered_factory_df.empty:
        st.warning("No data available for the selected filters (Factories, Months).")
        return

    if not filtered_factory_df.empty:
        def adjust_prof(row): #same logic for profit margin
            Predicted_Profit_Margin = row['Predicted Profit Margin (%)']  # assuming you have a 'Profit Margin' column
            return Predicted_Profit_Margin

        filtered_factory_df['Predicted Profit Margin (%)'] = filtered_factory_df.apply(adjust_prof, axis=1)

    st.header('Predicted Profit Margin (%)', divider='gray')
    
    # Extract categorical features for hover data if they exist
    hover_data = {'month': True}
    categorical_features = ['Product Category', 'Supplier', 'Machine Type']
    for feature in categorical_features:
        if feature in filtered_factory_df.columns:
            hover_data[feature] = True
    
    # Color by Factory
    fig = px.line(
        filtered_factory_df, 
        x='month', 
        y='Predicted Profit Margin (%)',
        color='Factory',
        hover_data=hover_data,
        markers=True,
        labels={
            'month': 'Month',
            'Predicted Profit Margin (%)': 'Predicted Profit Margin (%)'
        }
    )
    
    # Improve layout
    fig.update_layout(
        xaxis_title='Month',
        yaxis_title="Predicted Profit Margin (%)<br><sup>(Divide the given value by 120000 to see the exact prediction)</sup>",
        legend_title='Factory',
        hovermode='closest'
    )
    
    st.plotly_chart(fig)

    # Add table with preview (5 rows) and expand for full table
    st.write("Preview of Predicted data (first 5 rows):")
    
    # Determine which columns to show in the preview
    preview_columns = ['month', 'Factory', 'Predicted Profit Margin (%)']
    for feature in categorical_features:
        if feature in filtered_factory_df.columns:
            preview_columns.append(feature)
    
    try:
        st.table(filtered_factory_df[preview_columns].head(5))
        with st.expander("Show Full Table"):
            st.write("Full Predicted data:")
            st.dataframe(filtered_factory_df)
    except KeyError as e:
        st.error(f"KeyError: {e}. Please ensure the required columns exist in the dataframe.")


# Line graph for production volume
def lineGraph_vol(factory_profit_df, selected_factories, from_month, to_month, log_scale=False):
    # Filter the data
    filtered_factory_df = factory_profit_df[
        (factory_profit_df['Factory'].isin(selected_factories)) &
        (factory_profit_df['month'] <= to_month) &
        (factory_profit_df['month'] >= from_month)
    ].copy()

    if filtered_factory_df.empty:
        st.warning("No data available for the selected filters (Factories, Months).")
        return

    # Check if the required column exists
    if 'Predicted Production Volume (units)' not in filtered_factory_df.columns:
        st.error("The column 'Predicted Production Volume (units)' is not present in the dataframe.")
        return

    # Apply transformations for hover data
    filtered_factory_df['Transformed Volume'] = filtered_factory_df['Predicted Production Volume (units)']
    filtered_factory_df['Transformed Volume'] += np.random.uniform(-10, 10, size=len(filtered_factory_df))

    st.header('Predicted Production Volume (units)', divider='gray')
    
    # Extract categorical features for hover data if they exist
    hover_data = {'month': True, 'Transformed Volume': True}
    categorical_features = ['Raw Material Quality']
    for feature in categorical_features:
        if feature in filtered_factory_df.columns:
            hover_data[feature] = True
    
    # Color by Factory
    fig = px.line(
        filtered_factory_df,
        x='month',
        y='Predicted Production Volume (units)',
        color='Factory',
        hover_data=hover_data,
        markers=True,
        labels={
            'month': 'Month',
            'Predicted Production Volume (units)': 'Predicted Production Volume (units)'
        }
    )
    
    # Improve layout
    fig.update_layout(
        xaxis_title='Month',
        yaxis_title='Predicted Production Volume (units)',
        legend_title='Factory',
        hovermode='closest'
    )
    
    st.plotly_chart(fig)

    # Add table with preview (5 rows) and expand for full table
    st.write("Preview of Predicted data (first 5 rows):")
    
    # Determine which columns to show in the preview
    preview_columns = ['month', 'Factory', 'Predicted Production Volume (units)']
    for feature in categorical_features:
        if feature in filtered_factory_df.columns:
            preview_columns.append(feature)
    
    try:
        st.table(filtered_factory_df[preview_columns].head(5))
        with st.expander("Show Full Table"):
            st.write("Full Predicted data:")
            st.dataframe(filtered_factory_df)
    except KeyError as e:
        st.error(f"KeyError: {e}. Please ensure the required columns exist in the dataframe.")


# Prediction page combining all graphs
def predictionPage(result_rev_df, result_prof_df):
    from_year, to_year = yearFilter(result_rev_df)
    selected_factories = selectedFactories(result_rev_df)

    #log_scale = st.checkbox("Use Logarithmic Scale for Y-Axis", value=False)

    lineGraph_rev(result_rev_df, selected_factories, from_year, to_year)
    lineGraph_prof(result_prof_df, selected_factories, from_year, to_year)
