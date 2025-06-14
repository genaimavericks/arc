import pandas as pd

def encode_data(df):
    print('Starting encode_data')
    print('Input DataFrame shape:', df.shape)
    """Encodes categorical features appropriately for ML without get_dummies."""

    # Binary encoding (Yes/No)
    binary_cols = ["Partner", "Dependents", "PhoneService", "PaperlessBilling"]
    for col in binary_cols:
        df[col] = df[col].map({"Yes": 1, "No": 0})
    print('After binary encoding:', df.to_csv(index=False))

    gender = {"Male": 0, "Female": 1}
    df["gender"] = df["gender"].map(gender)

    # Ordinal encoding (Multiple Lines, Contract)
    multiple_lines_mapping = {"No": 0, "Yes": 1, "No phone service": 2}
    df["MultipleLines"] = df["MultipleLines"].map(multiple_lines_mapping)

    contract_mapping = {"Month-to-month": 0, "One year": 1, "Two year": 2}
    df["Contract"] = df["Contract"].map(contract_mapping)
    print('After contract encoding:', df.to_csv(index=False))

    # One-hot encoding (Internet Service, Payment Method, Additional Services)
    one_hot_cols = ["OnlineSecurity", "OnlineBackup",
                    "DeviceProtection", "TechSupport", "StreamingTV", "StreamingMovies"]
    for col in one_hot_cols:
        df[col] = df[col].map({"Yes": 2, "No": 0, "No internet service": 1})
    
    conn_type = {"DSL":1, "Fiber optic":2, "No":0}
    df["InternetService"] = df["InternetService"].map(conn_type)

    payment = {"Electronic check":0, "Mailed check":1, 
                    "Bank transfer (automatic)":2, "Credit card (automatic)":3}
    df["PaymentMethod"] = df["PaymentMethod"].map(payment)
    print('After payment method encoding:', df.to_csv(index=False))

    print('Completed encode_data')
    return df

def encode_data_7(df):
    print('Starting encode_data')
    print('Input DataFrame shape:', df.shape)
    """Encodes categorical features appropriately for ML without get_dummies."""

    contract_mapping = {"Month-to-month": 0, "One year": 1, "Two year": 2}
    df["Contract"] = df["Contract"].map(contract_mapping)
    print('After contract encoding:', df.to_csv(index=False))

    # One-hot encoding (Internet Service, Payment Method, Additional Services)
    one_hot_cols = ["OnlineSecurity", "OnlineBackup",
                     "TechSupport"]
    for col in one_hot_cols:
        df[col] = df[col].map({"Yes": 2, "No": 0, "No internet service": 1})

    print('Completed encode_data')
    return df

def clean_and_encode_data(df):
    """
    Transforms input dataframe to match the structure of tel_churn_clean.csv
    Args:
        df: Input dataframe from sample_csv_for_input.csv
    Returns:
        Cleaned and encoded dataframe matching tel_churn_clean.csv
    """
    # Strip whitespace and normalize case for string columns
    string_cols = df.select_dtypes(include=['object']).columns
    df[string_cols] = df[string_cols].apply(lambda x: x.str.strip().str.title())
    
    # Handle missing values
    df = df.fillna(0)

    #print('After binary encoding:', df.to_csv(index=False))
    
    # Encode categorical features with robust handling
    # Gender
    df['gender'] = df['gender'].map({'Male': 1, 'Female': 0, '': 0}).fillna(0).astype(int)
    
    # SeniorCitizen encoding
    df['SeniorCitizen'] = df['SeniorCitizen'].map({
        0: 0, 
        1: 1,
        'No': 0,
        'Yes': 1
    }).fillna(0).astype(int)

    # Binary columns
    binary_cols = ['Partner', 'Dependents', 'PhoneService', 'PaperlessBilling']
    for col in binary_cols:
        df[col] = df[col].map({'Yes': 1, 'No': 0, '': 0}).fillna(0).astype(int)
    
    # MultipleLines
    df['MultipleLines'] = df['MultipleLines'].map({
        'No': 0, 
        'Yes': 1, 
        'No Phone Service': 2,
        '': 2
    }).fillna(2).astype(int)
    
    # InternetService
    df['InternetService'] = df['InternetService'].map({
        'No': 0, 
        'Dsl': 1, 
        'Fiber Optic': 2,
        '': 0
    }).fillna(0).astype(int)
    
    # Additional services
    service_cols = ['OnlineSecurity', 'OnlineBackup', 'DeviceProtection', 
                   'TechSupport', 'StreamingTV', 'StreamingMovies']
    for col in service_cols:
        df[col] = df[col].map({
            'No': 0, 
            'Yes': 2, 
            'No Internet Service': 1,
            '': 1
        }).fillna(2).astype(int)
    
    # Contract
    df['Contract'] = df['Contract'].map({
        'Month-To-Month': 0, 
        'One Year': 1, 
        'Two Year': 2,
        '': 0
    }).fillna(0).astype(int)
    
    # PaymentMethod
    df['PaymentMethod'] = df['PaymentMethod'].map({
        'Electronic Check': 0,
        'Mailed Check': 1,
        'Bank Transfer (Automatic)': 2,
        'Credit Card (Automatic)': 3,
        '': 0
    }).fillna(0).astype(int)
    
    # Numeric columns - handle strings and missing values
    numeric_cols = ['MonthlyCharges', 'TotalCharges']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    
    # Ensure correct column order and types
    clean_columns = ['gender', 'SeniorCitizen', 'Partner', 'Dependents', 'tenure',
                    'PhoneService', 'MultipleLines', 'InternetService', 'OnlineSecurity',
                    'OnlineBackup', 'DeviceProtection', 'TechSupport', 'StreamingTV',
                    'StreamingMovies', 'Contract', 'PaperlessBilling', 'PaymentMethod',
                    'MonthlyCharges', 'TotalCharges']
    
    return df[clean_columns]


def clean_and_encode_data_for_7(df):
    print('Starting clean_and_encode_data_for_7')
    print('Input DataFrame:', df.to_csv(index=False))
    
    required_columns = [
        'tenure', 'OnlineSecurity', 'OnlineBackup', 'TechSupport',
        'Contract', 'MonthlyCharges', 'TotalCharges'
    ]
    
    # Validate columns
    missing_cols = set(required_columns) - set(df.columns)
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")
    
    # Create a copy to avoid modifying the original
    df_clean = df[required_columns].copy()
    
    # Handle categorical variables with consistent encoding
    service_mapping = {
        "Yes": 2,
        "No": 0,
        "No internet service": 1
    }
    
    contract_mapping = {
        "Month-to-month": 0,
        "One year": 1,
        "Two year": 2
    }
    
    # Default values for missing categorical data
    default_service_value = 0  # Default to "No"
    default_contract_value = 0  # Default to "Month-to-month"
    
    # Encode categorical columns with fallback to defaults for missing values
    categorical_cols = ['OnlineSecurity', 'OnlineBackup', 'TechSupport']
    for col in categorical_cols:
        # Apply mapping and fill missing values with default
        df_clean[col] = df_clean[col].map(service_mapping).fillna(default_service_value).astype(int)
        print(f'Encoded {col}:', df_clean[col].tolist())
    
    # Apply contract mapping with default for missing values
    df_clean['Contract'] = df_clean['Contract'].map(contract_mapping).fillna(default_contract_value).astype(int)
    print('Encoded Contract:', df_clean['Contract'].tolist())
    
    # Ensure numeric columns are properly typed and handle missing values
    numeric_cols = ['tenure', 'MonthlyCharges', 'TotalCharges']
    default_values = {'tenure': 12, 'MonthlyCharges': 70.0, 'TotalCharges': 840.0}
    
    for col in numeric_cols:
        # Convert to numeric and fill missing values with column-specific defaults
        df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce').fillna(default_values[col])
        print(f'Converted {col} to numeric:', df_clean[col].tolist())
    
    # Double-check for any remaining NaN values and fill them
    if df_clean.isna().any().any():
        print("Warning: NaN values still present after initial processing. Filling with defaults.")
        for col in df_clean.columns:
            if col in default_values:
                df_clean[col] = df_clean[col].fillna(default_values[col])
            elif col in categorical_cols:
                df_clean[col] = df_clean[col].fillna(default_service_value).astype(int)
            elif col == 'Contract':
                df_clean[col] = df_clean[col].fillna(default_contract_value).astype(int)
    
    # Final verification that no NaN values remain
    assert not df_clean.isna().any().any(), "NaN values still present after cleaning"
    
    print('Output DataFrame:', df_clean.to_csv(index=False))
    print('Completed clean_and_encode_data_for_7')
    return df_clean

# df = pd.read_csv("/Users/dhani/foamvenv/telecom_churn/form-factory/modules/data/telchurn/sample_csv_for_input.csv")
# df = clean_and_encode_data(df)
# print(df.to_csv(index=False))