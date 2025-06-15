import os
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from api.auth import has_permission, has_any_permission
from typing import Dict, List, Any, Optional

router = APIRouter(
    prefix="/api/static_dashboards/churn_dashboard",
    tags=["churn_dashboard"]
)

def load_churn_data():
    """Load and preprocess the telecom churn dataset"""
    try:
        csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "TelecomChurn.csv")
        df = pd.read_csv(csv_path)
        
        # Convert SeniorCitizen from 0/1 to No/Yes for consistency with other binary fields
        df["SeniorCitizen"] = df["SeniorCitizen"].map({0: "No", 1: "Yes"})
        
        # Convert TotalCharges to numeric (handling any non-numeric values)
        df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce")
        df["TotalCharges"] = df["TotalCharges"].fillna(0)
        
        # Convert monthly charges to ensure it's numeric
        df["MonthlyCharges"] = pd.to_numeric(df["MonthlyCharges"], errors="coerce")
        df["MonthlyCharges"] = df["MonthlyCharges"].fillna(0)
        
        # Convert tenure to numeric
        df["tenure"] = pd.to_numeric(df["tenure"], errors="coerce")
        df["tenure"] = df["tenure"].fillna(0)
        
        # Convert Churn to binary 0/1 for easier calculations
        df["ChurnBinary"] = df["Churn"].map({"No": 0, "Yes": 1})
        
        # Group tenure into categories for easier visualization
        tenure_bins = [0, 6, 12, 24, 36, 48, 60, 72]
        tenure_labels = ['0-6 months', '7-12 months', '1-2 years', '2-3 years', '3-4 years', '4-5 years', '5+ years']
        df['TenureGroup'] = pd.cut(df['tenure'], bins=tenure_bins, labels=tenure_labels, right=False)
        
        return df
    except Exception as e:
        print(f"Error loading churn data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load churn data: {str(e)}")

def python_to_json_safe(obj):
    """Convert numpy/pandas types to native Python types for JSON serialization"""
    if isinstance(obj, (pd.Series, pd.DataFrame)):
        return obj.to_dict()
    elif hasattr(obj, 'dtype'):
        return obj.item()  # Convert numpy types to native Python types
    elif isinstance(obj, dict):
        return {k: python_to_json_safe(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [python_to_json_safe(i) for i in obj]
    else:
        return obj

@router.get("/summary")
async def get_churn_summary(
    permission=Depends(has_permission("command:read"))
):
    """Get summary metrics for the churn dashboard"""
    try:
        df = load_churn_data()
        
        # Customer profile overview
        total_customers = len(df)
        avg_monthly_charges = df["MonthlyCharges"].mean()
        total_charges = df["TotalCharges"].sum()
        
        # Churn profile overview
        churners = df[df["Churn"] == "Yes"]
        total_churners = len(churners)
        churn_rate = total_churners / total_customers * 100
        avg_monthly_charges_churners = churners["MonthlyCharges"].mean()
        avg_total_charges_churners = churners["TotalCharges"].mean()
        
        # Key insights
        non_churners = df[df["Churn"] == "No"]
        avg_tenure_non_churners = non_churners["tenure"].mean()
        avg_tenure_churners = churners["tenure"].mean()
        
        # Most common contract type
        most_common_contract = df["Contract"].value_counts().idxmax()
        
        # Most common internet service among churners
        most_common_internet_churners = churners["InternetService"].value_counts().idxmax()
        
        # Customer demographics for pie charts
        gender_distribution = df["gender"].value_counts().to_dict()
        contract_distribution = df["Contract"].value_counts().to_dict()
        internet_service_distribution = df["InternetService"].value_counts().to_dict()
        payment_method_distribution = df["PaymentMethod"].value_counts().to_dict()
        
        # Create tenure distribution for all customers
        tenure_distribution = df["TenureGroup"].value_counts().to_dict()
        
        response = {
            "customer_profile": {
                "total_customers": python_to_json_safe(total_customers),
                "avg_monthly_charges": python_to_json_safe(round(avg_monthly_charges, 2)),
                "total_charges": python_to_json_safe(round(total_charges, 2))
            },
            "churn_profile": {
                "total_churners": python_to_json_safe(total_churners),
                "churn_rate": python_to_json_safe(round(churn_rate, 2)),
                "avg_monthly_charges": python_to_json_safe(round(avg_monthly_charges_churners, 2)),
                "avg_total_charges": python_to_json_safe(round(avg_total_charges_churners, 2))
            },
            "key_insights": {
                "avg_tenure_non_churners": python_to_json_safe(round(avg_tenure_non_churners, 2)),
                "avg_tenure_churners": python_to_json_safe(round(avg_tenure_churners, 2)),
                "most_common_contract": python_to_json_safe(most_common_contract),
                "most_common_internet_churners": python_to_json_safe(most_common_internet_churners)
            },
            "demographics": {
                "gender": python_to_json_safe(gender_distribution),
                "contract": python_to_json_safe(contract_distribution),
                "internet_service": python_to_json_safe(internet_service_distribution),
                "tenure": python_to_json_safe(tenure_distribution)
            }
        }
        
        return response
    except Exception as e:
        print(f"Error in get_churn_summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate summary: {str(e)}")

@router.get("/customer-profile")
async def get_customer_profile(
    permission=Depends(has_permission("command:read"))
):
    """Get customer profile metrics for the churn dashboard"""
    try:
        df = load_churn_data()
        
        # Customer stats
        total_customers = len(df)
        monthly_charges = df["MonthlyCharges"].sum()
        total_charges = df["TotalCharges"].sum()
        
        # Demographics for pie charts
        gender_data = df["gender"].value_counts().reset_index()
        gender_data.columns = ["category", "value"]
        gender_data = gender_data.to_dict('records')
        
        tenure_data = df["TenureGroup"].value_counts().reset_index()
        tenure_data.columns = ["category", "value"]
        tenure_data = tenure_data.to_dict('records')
        
        internet_service_data = df["InternetService"].value_counts().reset_index()
        internet_service_data.columns = ["category", "value"]
        internet_service_data = internet_service_data.to_dict('records')
        
        contract_data = df["Contract"].value_counts().reset_index()
        contract_data.columns = ["category", "value"]
        contract_data = contract_data.to_dict('records')
        
        # Additional stats
        senior_citizen_count = len(df[df["SeniorCitizen"] == "Yes"])
        partner_count = len(df[df["Partner"] == "Yes"])
        phone_service_count = len(df[df["PhoneService"] == "Yes"])
        
        # Payment methods
        payment_methods = df["PaymentMethod"].value_counts().reset_index()
        payment_methods.columns = ["method", "count"]
        payment_methods = payment_methods.to_dict('records')
        
        response = {
            "stats": {
                "total_customers": python_to_json_safe(total_customers),
                "monthly_charges": python_to_json_safe(round(monthly_charges, 2)),
                "total_charges": python_to_json_safe(round(total_charges, 2))
            },
            "pie_charts": {
                "gender": python_to_json_safe(gender_data),
                "tenure": python_to_json_safe(tenure_data),
                "internet_service": python_to_json_safe(internet_service_data),
                "contract": python_to_json_safe(contract_data)
            },
            "additional_stats": {
                "senior_citizen_count": python_to_json_safe(senior_citizen_count),
                "senior_citizen_percentage": python_to_json_safe(round(senior_citizen_count / total_customers * 100, 2)),
                "partner_count": python_to_json_safe(partner_count),
                "partner_percentage": python_to_json_safe(round(partner_count / total_customers * 100, 2)),
                "phone_service_count": python_to_json_safe(phone_service_count),
                "phone_service_percentage": python_to_json_safe(round(phone_service_count / total_customers * 100, 2))
            },
            "payment_methods": python_to_json_safe(payment_methods)
        }
        
        return response
    except Exception as e:
        print(f"Error in get_customer_profile: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate customer profile: {str(e)}")

@router.get("/churner-profile")
async def get_churner_profile(
    permission=Depends(has_permission("command:read"))
):
    """Get churner profile metrics for the churn dashboard"""
    try:
        df = load_churn_data()
        churners = df[df["Churn"] == "Yes"]
        
        # Churner stats
        total_churners = len(churners)
        monthly_charges = churners["MonthlyCharges"].sum()
        total_charges = churners["TotalCharges"].sum()
        
        # Demographics for pie charts
        gender_data = churners["gender"].value_counts().reset_index()
        gender_data.columns = ["category", "value"]
        gender_data = gender_data.to_dict('records')
        
        tenure_data = churners["TenureGroup"].value_counts().reset_index()
        tenure_data.columns = ["category", "value"]
        tenure_data = tenure_data.to_dict('records')
        
        internet_service_data = churners["InternetService"].value_counts().reset_index()
        internet_service_data.columns = ["category", "value"]
        internet_service_data = internet_service_data.to_dict('records')
        
        contract_data = churners["Contract"].value_counts().reset_index()
        contract_data.columns = ["category", "value"]
        contract_data = contract_data.to_dict('records')
        
        # Additional stats
        senior_citizen_count = len(churners[churners["SeniorCitizen"] == "Yes"])
        partner_count = len(churners[churners["Partner"] == "Yes"])
        phone_service_count = len(churners[churners["PhoneService"] == "Yes"])
        
        # Payment methods
        payment_methods = churners["PaymentMethod"].value_counts().reset_index()
        payment_methods.columns = ["method", "count"]
        payment_methods = payment_methods.to_dict('records')
        
        response = {
            "stats": {
                "total_churners": python_to_json_safe(total_churners),
                "monthly_charges": python_to_json_safe(round(monthly_charges, 2)),
                "total_charges": python_to_json_safe(round(total_charges, 2)),
                "churn_rate": python_to_json_safe(round(total_churners / len(df) * 100, 2))
            },
            "pie_charts": {
                "gender": python_to_json_safe(gender_data),
                "tenure": python_to_json_safe(tenure_data),
                "internet_service": python_to_json_safe(internet_service_data),
                "contract": python_to_json_safe(contract_data)
            },
            "additional_stats": {
                "senior_citizen_count": python_to_json_safe(senior_citizen_count),
                "senior_citizen_percentage": python_to_json_safe(round(senior_citizen_count / total_churners * 100, 2)),
                "partner_count": python_to_json_safe(partner_count),
                "partner_percentage": python_to_json_safe(round(partner_count / total_churners * 100, 2)),
                "phone_service_count": python_to_json_safe(phone_service_count),
                "phone_service_percentage": python_to_json_safe(round(phone_service_count / total_churners * 100, 2))
            },
            "payment_methods": python_to_json_safe(payment_methods)
        }
        
        return response
    except Exception as e:
        print(f"Error in get_churner_profile: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate churner profile: {str(e)}")
