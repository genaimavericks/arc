import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict, List, Optional, Any, Union

from api.auth import has_permission

# Router instance for factory dashboard endpoints
router = APIRouter()

# Path to the CSV file
CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "FoamFactory_V3_27K.csv")

def load_factory_data():
    """Load and cache the factory dataset"""
    try:
        df = pd.read_csv(CSV_PATH)
        # Convert date strings to datetime objects
        df['Date'] = pd.to_datetime(df['Date'])
        
        # Print column names for debugging
        print("Available columns in the dataset:", df.columns.tolist())
        
        return df
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load factory data: {str(e)}")

# ---- API Endpoints ----

@router.get("/summary")
async def get_summary(user_info: dict = Depends(has_permission("command:read"))):
    """Get summary metrics for the main dashboard page"""
    df = load_factory_data()
    
    # Calculate key metrics
    total_production = float(df['Production_Volume__units'].sum())
    avg_machine_utilization = float(df['Machine_Utilization__percent'].mean())
    total_revenue = float(df['Revenue__dollars'].sum())
    avg_profit_margin = float(df['Profit_Margin__percent'].mean())
    
    # Calculate downtime metrics
    total_downtime = float(df['Machine_Downtime__hours'].sum())
    downtime_cost = float(df['Cost_of_Downtime__dollars'].sum())
    
    # Calculate environmental metrics
    total_emissions = float(df['CO2_Emissions__kg'].sum())
    total_energy = float(df['Energy_Consumption__kWh'].sum())
    total_waste = float(df['Waste_Generated__kg'].sum())
    
    # Calculate quality metrics
    avg_quality = float(df['Batch_Quality__Pass_percent'].mean())
    avg_defect_rate = float(df['Defect_Rate__percent'].mean())
    
    # Production by month
    df['Month'] = df['Date'].dt.strftime('%Y-%m')
    monthly_production = df.groupby('Month')['Production_Volume__units'].sum().reset_index()
    monthly_production_data = [
        {"month": str(row['Month']), "production": float(row['Production_Volume__units'])} 
        for _, row in monthly_production.iterrows()
    ]
    
    return {
        "key_metrics": {
            "total_production": total_production,
            "avg_machine_utilization": avg_machine_utilization,
            "total_revenue": total_revenue,
            "avg_profit_margin": avg_profit_margin,
            "total_downtime": total_downtime,
            "downtime_cost": downtime_cost,
            "avg_quality": avg_quality,
            "avg_defect_rate": avg_defect_rate,
        },
        "environmental_impact": {
            "total_emissions": total_emissions,
            "total_energy": total_energy,
            "total_waste": total_waste,
        },
        "production_trend": monthly_production_data
    }

@router.get("/operations-metrics")
async def get_operations_metrics(user_info: dict = Depends(has_permission("command:read"))):
    """Get metrics for the Operations & Maintenance page"""
    df = load_factory_data()
    
    # Machine performance metrics
    machine_uptime = df.groupby('Machine_Type')['Machine_Utilization__percent'].mean().reset_index()
    machine_downtime = df.groupby('Machine_Type')['Machine_Downtime__hours'].sum().reset_index()
    
    # Create machine profile data
    machine_profile = []
    for machine_type in df['Machine_Type'].unique():
        machine_df = df[df['Machine_Type'] == machine_type]
        profile = {
            "machine_type": str(machine_type),
            "avg_utilization": float(machine_df['Machine_Utilization__percent'].mean()),
            "total_downtime": float(machine_df['Machine_Downtime__hours'].sum()),
            "avg_age": float(machine_df['Machine_Age__years'].mean()),
            "breakdown_count": float(machine_df['Breakdowns__count'].sum()),
            "avg_cycle_time": float(machine_df['Cycle_Time__minutes'].mean()),
            "avg_energy": float(machine_df['Energy_Consumption__kWh'].mean())
        }
        machine_profile.append(profile)
    
    # Calculate maintenance impact
    maintenance_impact = df.groupby('Maintenance_History')[
        ['Machine_Downtime__hours', 'Machine_Utilization__percent', 'Cost_of_Downtime__dollars']
    ].mean().reset_index()
    
    maintenance_impact_data = [
        {
            "frequency": str(row['Maintenance_History']),
            "avg_downtime": float(row['Machine_Downtime__hours']),
            "avg_utilization": float(row['Machine_Utilization__percent']),
            "avg_cost": float(row['Cost_of_Downtime__dollars'])
        } for _, row in maintenance_impact.iterrows()
    ]
    
    # Calculate age vs breakdown correlation
    age_breakdown = df.groupby('Machine_Age__years')[['Breakdowns__count']].mean().reset_index()
    age_breakdown_data = [
        {"age": float(row['Machine_Age__years']), "breakdowns": float(row['Breakdowns__count'])} 
        for _, row in age_breakdown.iterrows()
    ]
    
    # Monthly downtime trend
    df['Month'] = df['Date'].dt.strftime('%Y-%m')
    monthly_downtime = df.groupby('Month')['Machine_Downtime__hours'].sum().reset_index()
    monthly_downtime_data = [
        {"month": str(row['Month']), "downtime": float(row['Machine_Downtime__hours'])} 
        for _, row in monthly_downtime.iterrows()
    ]
    
    # Machine utilization heatmap data
    machine_location_util = df.groupby(['Machine_Type', 'Location'])['Machine_Utilization__percent'].mean().reset_index()
    machine_location_util_data = [
        {
            "machine_type": str(row['Machine_Type']),
            "location": str(row['Location']),
            "utilization": float(row['Machine_Utilization__percent'])
        } for _, row in machine_location_util.iterrows()
    ]
    
    return {
        "machine_profile": machine_profile,
        "maintenance_impact": maintenance_impact_data,
        "age_breakdown_correlation": age_breakdown_data,
        "monthly_downtime": monthly_downtime_data,
        "machine_location_utilization": machine_location_util_data
    }

@router.get("/workforce-metrics")
async def get_workforce_metrics(user_info: dict = Depends(has_permission("command:read"))):
    """Get metrics for the Workforce & Resource Efficiency page"""
    df = load_factory_data()
    
    # Extract operator data (need to parse the team members JSON in each row)
    operator_data = []
    operator_exp_quality = []
    
    # Process operator experience vs performance
    # Group experience levels
    experience_bins = [0, 2, 5, 10, 20]
    experience_labels = ['0-2 years', '2-5 years', '5-10 years', '10+ years']
    
    shift_perf = df.groupby('Shift')['Production_Volume__units'].mean().reset_index()
    shift_quality = df.groupby('Shift')['Batch_Quality__Pass_percent'].mean().reset_index()
    shift_performance = []
    for _, row in shift_perf.iterrows():
        quality = shift_quality[shift_quality['Shift'] == row['Shift']]['Batch_Quality__Pass_percent'].values[0]
        shift_performance.append({
            "shift": str(row['Shift']),
            "avg_production": float(row['Production_Volume__units']),
            "avg_quality": float(quality)
        })
    
    # Resource efficiency
    material_quality_impact = df.groupby('Raw_Material_Quality')['Defect_Rate__percent'].mean().reset_index()
    material_quality_data = [
        {"material_quality": int(row['Raw_Material_Quality']), "defect_rate": float(row['Defect_Rate__percent'])} 
        for _, row in material_quality_impact.iterrows()
    ]
    
    # Supplier performance
    supplier_perf = df.groupby('Supplier')[['Supplier_Delays__days', 'Raw_Material_Quality']].mean().reset_index()
    supplier_data = [
        {
            "supplier": str(row['Supplier']),
            "avg_delay": float(row['Supplier_Delays__days']),
            "avg_quality": float(row['Raw_Material_Quality'])
        } for _, row in supplier_perf.iterrows()
    ]
    
    # Resource consumption by product
    resource_by_product = df.groupby('Product_Category')[
        ['Energy_Consumption__kWh', 'Water_Usage__liters', 'Waste_Generated__kg']
    ].mean().reset_index()
    
    resource_data = [
        {
            "product": str(row['Product_Category']),
            "energy": float(row['Energy_Consumption__kWh']),
            "water": float(row['Water_Usage__liters']),
            "waste": float(row['Waste_Generated__kg'])
        } for _, row in resource_by_product.iterrows()
    ]
    
    # Energy efficiency by machine
    energy_efficiency = df.groupby('Machine_Type')[
        ['Energy_Consumption__kWh', 'Energy_Efficiency_Rating', 'Production_Volume__units']
    ].mean().reset_index()
    
    energy_data = [
        {
            "machine_type": str(row['Machine_Type']),
            "consumption": float(row['Energy_Consumption__kWh']),
            "efficiency": float(row['Energy_Efficiency_Rating']),
            "production": float(row['Production_Volume__units']),
            "energy_per_unit": float(row['Energy_Consumption__kWh'] / row['Production_Volume__units'])
        } for _, row in energy_efficiency.iterrows()
    ]
    
    return {
        "shift_performance": shift_performance,
        "material_quality_impact": material_quality_data,
        "supplier_performance": supplier_data,
        "resource_consumption": resource_data,
        "energy_efficiency": energy_data
    }
