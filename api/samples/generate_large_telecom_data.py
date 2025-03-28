import csv
import random
import string
from datetime import datetime
import os

# Define the output file path
output_file = 'TelecomChurn_Large_300.csv'
target_size_mb = 300
approx_row_size_bytes = 150  # Approximate size of each row in bytes
target_rows = int((target_size_mb * 1024 * 1024) / approx_row_size_bytes)

# Sample data from original file
genders = ['Male', 'Female']
senior_citizen = [0, 1]
yes_no = ['Yes', 'No']
phone_service = ['Yes', 'No']
multiple_lines = ['Yes', 'No', 'No phone service']
internet_services = ['DSL', 'Fiber optic', 'No']
online_features = ['Yes', 'No', 'No internet service']
contract_types = ['Month-to-month', 'One year', 'Two year']
payment_methods = ['Electronic check', 'Mailed check', 'Bank transfer (automatic)', 'Credit card (automatic)']
churn = ['Yes', 'No']

# Function to generate random customer ID
def generate_customer_id():
    first_part = ''.join(random.choices(string.digits, k=4))
    second_part = ''.join(random.choices(string.ascii_uppercase, k=5))
    return f"{first_part}-{second_part}"

# Function to generate random monthly charges
def generate_monthly_charges():
    return round(random.uniform(18.0, 120.0), 2)

# Function to generate a row of data
def generate_row():
    customer_id = generate_customer_id()
    gender = random.choice(genders)
    is_senior = random.choice(senior_citizen)
    has_partner = random.choice(yes_no)
    has_dependents = random.choice(yes_no)
    tenure = random.randint(0, 72)
    has_phone = random.choice(phone_service)
    
    if has_phone == 'No':
        multiple_line = 'No phone service'
    else:
        multiple_line = random.choice(['Yes', 'No'])
    
    internet_service = random.choice(internet_services)
    
    if internet_service == 'No':
        online_security = 'No internet service'
        online_backup = 'No internet service'
        device_protection = 'No internet service'
        tech_support = 'No internet service'
        streaming_tv = 'No internet service'
        streaming_movies = 'No internet service'
    else:
        online_security = random.choice(['Yes', 'No'])
        online_backup = random.choice(['Yes', 'No'])
        device_protection = random.choice(['Yes', 'No'])
        tech_support = random.choice(['Yes', 'No'])
        streaming_tv = random.choice(['Yes', 'No'])
        streaming_movies = random.choice(['Yes', 'No'])
    
    contract = random.choice(contract_types)
    paperless = random.choice(yes_no)
    payment = random.choice(payment_methods)
    monthly_charges = generate_monthly_charges()
    total_charges = round(monthly_charges * tenure, 2)
    is_churned = random.choice(churn)
    
    return [
        customer_id, gender, is_senior, has_partner, has_dependents, tenure,
        has_phone, multiple_line, internet_service, online_security,
        online_backup, device_protection, tech_support, streaming_tv,
        streaming_movies, contract, paperless, payment, monthly_charges,
        total_charges, is_churned
    ]

# Headers from the original file
headers = [
    'customerID', 'gender', 'SeniorCitizen', 'Partner', 'Dependents',
    'tenure', 'PhoneService', 'MultipleLines', 'InternetService',
    'OnlineSecurity', 'OnlineBackup', 'DeviceProtection', 'TechSupport',
    'StreamingTV', 'StreamingMovies', 'Contract', 'PaperlessBilling',
    'PaymentMethod', 'MonthlyCharges', 'TotalCharges', 'Churn'
]

print(f"Generating approximately {target_rows:,} rows to create a {target_size_mb}MB CSV file...")
start_time = datetime.now()

# Write the data to the CSV file
with open(output_file, 'w', newline='') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(headers)
    
    for i in range(target_rows):
        writer.writerow(generate_row())
        
        # Print progress every 100,000 rows
        if (i + 1) % 100000 == 0:
            print(f"Generated {i + 1:,} rows ({(i + 1) / target_rows * 100:.1f}% complete)")

end_time = datetime.now()
duration = (end_time - start_time).total_seconds()

# Get the actual file size
file_size_bytes = os.path.getsize(output_file)
file_size_mb = file_size_bytes / (1024 * 1024)

print(f"\nFile generation complete!")
print(f"File: {output_file}")
print(f"Rows generated: {target_rows:,}")
print(f"Actual file size: {file_size_mb:.2f} MB")
print(f"Time taken: {duration:.2f} seconds")
