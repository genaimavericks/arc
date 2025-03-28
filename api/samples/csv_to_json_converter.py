import csv
import json
import sys
import os
import random
import string
from pathlib import Path

def generate_sample_data(num_rows=200000, num_cols=10):
    """
    Generate sample data for testing.
    
    Args:
        num_rows: Number of rows to generate
        num_cols: Number of columns to generate
    
    Returns:
        List of dictionaries representing the data
    """
    headers = [f"field_{i}" for i in range(1, num_cols + 1)]
    data = []
    
    # Generate random data
    for i in range(num_rows):
        row = {}
        for header in headers:
            # Mix of different data types to simulate real data
            data_type = random.choice([0, 1, 2])  # 0: string, 1: number, 2: boolean
            
            if data_type == 0:
                # Generate a random string of length between 10 and 30
                length = random.randint(10, 30)
                row[header] = ''.join(random.choices(string.ascii_letters + string.digits, k=length))
            elif data_type == 1:
                # Generate a random number
                row[header] = random.uniform(0, 1000)
            else:
                # Generate a random boolean
                row[header] = random.choice([True, False])
        
        data.append(row)
        
        # Print progress
        if (i + 1) % 10000 == 0:
            print(f"Generated {i + 1} rows...", end='\r')
    
    return data

def create_sample_csv(csv_file_path, num_rows=200000, num_cols=10):
    """
    Create a sample CSV file with random data.
    
    Args:
        csv_file_path: Path to the output CSV file
        num_rows: Number of rows to generate
        num_cols: Number of columns to generate
    
    Returns:
        Path to the created CSV file
    """
    headers = [f"field_{i}" for i in range(1, num_cols + 1)]
    
    with open(csv_file_path, 'w', newline='', encoding='utf-8') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=headers)
        writer.writeheader()
        
        # Generate and write rows
        for i in range(num_rows):
            row = {}
            for header in headers:
                # Mix of different data types to simulate real data
                data_type = random.choice([0, 1, 2])  # 0: string, 1: number, 2: boolean
                
                if data_type == 0:
                    # Generate a random string of length between 10 and 30
                    length = random.randint(10, 30)
                    row[header] = ''.join(random.choices(string.ascii_letters + string.digits, k=length))
                elif data_type == 1:
                    # Generate a random number
                    row[header] = str(random.uniform(0, 1000))
                else:
                    # Generate a random boolean
                    row[header] = str(random.choice([True, False]))
            
            writer.writerow(row)
            
            # Print progress
            if (i + 1) % 10000 == 0:
                print(f"Generated {i + 1} rows...", end='\r')
    
    return csv_file_path

def convert_csv_to_json(csv_file_path, json_file_path=None):
    """
    Convert a CSV file to JSON format.
    
    Args:
        csv_file_path: Path to the input CSV file
        json_file_path: Path to the output JSON file. If None, will use the same name with .json extension
    
    Returns:
        Path to the created JSON file
    """
    if json_file_path is None:
        json_file_path = str(Path(csv_file_path).with_suffix('.json'))
    
    # Read the CSV file in chunks to handle large files
    data = []
    with open(csv_file_path, 'r', encoding='utf-8') as csv_file:
        csv_reader = csv.DictReader(csv_file)
        # Get column names to ensure consistent structure
        columns = csv_reader.fieldnames
        
        # Process in batches to avoid loading the entire file into memory
        batch_size = 1000
        batch = []
        
        for i, row in enumerate(csv_reader):
            # Create a new row with all columns to ensure consistent structure
            processed_row = {}
            
            # Process each column to ensure consistent types
            for key in columns:
                value = row.get(key, "")
                
                # Handle empty strings or whitespace-only strings
                if value is None or value.strip() == '':
                    processed_row[key] = None
                # Try to convert to numeric if appropriate
                elif key in ['MonthlyCharges', 'TotalCharges', 'tenure'] and value.replace('.', '', 1).isdigit():
                    processed_row[key] = float(value)
                # Convert SeniorCitizen to boolean (it's stored as 0/1 in the CSV)
                elif key == 'SeniorCitizen' and value in ['0', '1']:
                    processed_row[key] = bool(int(value))
                # Keep everything else as string
                else:
                    processed_row[key] = value
            
            batch.append(processed_row)
            
            if len(batch) >= batch_size:
                data.extend(batch)
                batch = []
                print(f"Processed {i+1} rows...", end='\r')
        
        # Add any remaining rows
        if batch:
            data.extend(batch)
    
    # Ensure data is always an array, even if empty
    if not isinstance(data, list):
        data = []
    
    # Write to JSON file
    with open(json_file_path, 'w', encoding='utf-8') as json_file:
        json.dump(data, json_file, indent=2)
    
    print(f"\nJSON file size: {os.path.getsize(json_file_path) / (1024 * 1024):.2f} MB")
    return json_file_path

def generate_telecom_json_with_target_size(source_csv, target_size_mb=50, output_path=None):
    """
    Generate a JSON file with approximately the target size using TelecomChurn.csv data.
    
    Args:
        source_csv: Path to the TelecomChurn.csv file
        target_size_mb: Target size in MB
        output_path: Path to save the JSON file
    
    Returns:
        Path to the created JSON file
    """
    if output_path is None:
        output_path = "telecom_data.json"
    
    # Read the original CSV file to get the template data
    template_data = []
    with open(source_csv, 'r', encoding='utf-8') as csv_file:
        csv_reader = csv.DictReader(csv_file)
        # Get column names to ensure consistent structure
        columns = csv_reader.fieldnames
        
        for row in csv_reader:
            # Create a new row with all columns to ensure consistent structure
            processed_row = {}
            
            # Process each column to ensure consistent types
            for key in columns:
                value = row.get(key, "")
                
                # Handle empty strings or whitespace-only strings
                if value is None or value.strip() == '':
                    processed_row[key] = None
                # Try to convert to numeric if appropriate
                elif key in ['MonthlyCharges', 'TotalCharges', 'tenure'] and value.replace('.', '', 1).isdigit():
                    processed_row[key] = float(value)
                # Convert SeniorCitizen to boolean (it's stored as 0/1 in the CSV)
                elif key == 'SeniorCitizen' and value in ['0', '1']:
                    processed_row[key] = bool(int(value))
                # Keep everything else as string
                else:
                    processed_row[key] = value
            
            template_data.append(processed_row)
    
    # Calculate approximately how many copies we need to reach the target size
    # First create a small sample JSON to estimate size per record
    sample_output = "temp_sample.json"
    with open(sample_output, 'w', encoding='utf-8') as json_file:
        json.dump(template_data, json_file, indent=2)
    
    sample_size_mb = os.path.getsize(sample_output) / (1024 * 1024)
    os.remove(sample_output)  # Clean up the temporary file
    
    # Calculate scaling factor
    records_per_mb = len(template_data) / sample_size_mb
    target_records = int(records_per_mb * target_size_mb)
    
    print(f"Original data has {len(template_data)} records ({sample_size_mb:.2f} MB)")
    print(f"Generating approximately {target_records} records to reach ~{target_size_mb} MB...")
    
    # Generate the data by duplicating and slightly modifying the template data
    data = []
    template_len = len(template_data)
    
    for i in range(target_records):
        # Get a random record from the template data
        template_record = template_data[i % template_len].copy()
        
        # Slightly modify some fields to create variation
        if "customerID" in template_record:
            # Create a unique customer ID
            template_record["customerID"] = f"{template_record['customerID']}-{i}"
        
        # Randomly modify some numeric fields if they exist
        for field in ["MonthlyCharges", "TotalCharges", "tenure"]:
            if field in template_record and isinstance(template_record[field], (int, float)):
                # Add some random variation (±10%)
                variation = random.uniform(0.9, 1.1)
                template_record[field] = template_record[field] * variation
        
        data.append(template_record)
        
        # Print progress
        if (i + 1) % 10000 == 0:
            print(f"Generated {i + 1} records...", end='\r')
    
    # Ensure data is always an array, even if empty
    if not isinstance(data, list):
        data = []
    
    # Write to JSON file
    with open(output_path, 'w', encoding='utf-8') as json_file:
        json.dump(data, json_file, indent=2)
    
    # Check file size
    file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"\nGenerated JSON file size: {file_size_mb:.2f} MB")
    
    return output_path

if __name__ == "__main__":
    if len(sys.argv) == 1:
        # No arguments provided, generate a 50 MB JSON file from TelecomChurn.csv
        try:
            telecom_csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "TelecomChurn.csv")
            if not os.path.exists(telecom_csv_path):
                print(f"Error: TelecomChurn.csv not found at {telecom_csv_path}")
                sys.exit(1)
                
            output_path = generate_telecom_json_with_target_size(telecom_csv_path, 50, "telecom_data_50mb.json")
            print(f"Successfully generated a ~50 MB JSON file: {output_path}")
        except Exception as e:
            print(f"Error generating telecom data: {e}")
            sys.exit(1)
    elif len(sys.argv) == 2 and sys.argv[1].endswith(".csv"):
        # Only CSV file provided, convert to JSON
        csv_file_path = sys.argv[1]
        try:
            output_path = convert_csv_to_json(csv_file_path)
            print(f"\nSuccessfully converted CSV to JSON. Output saved to: {output_path}")
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    elif len(sys.argv) == 3 and sys.argv[1].endswith(".csv") and sys.argv[2].endswith(".json"):
        # CSV and JSON file paths provided
        csv_file_path = sys.argv[1]
        json_file_path = sys.argv[2]
        try:
            output_path = convert_csv_to_json(csv_file_path, json_file_path)
            print(f"\nSuccessfully converted CSV to JSON. Output saved to: {output_path}")
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    elif len(sys.argv) == 3 and sys.argv[1] == "--size":
        # Generate telecom data with specified size
        try:
            target_size_mb = int(sys.argv[2])
            telecom_csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "TelecomChurn.csv")
            if not os.path.exists(telecom_csv_path):
                print(f"Error: TelecomChurn.csv not found at {telecom_csv_path}")
                sys.exit(1)
                
            output_path = generate_telecom_json_with_target_size(telecom_csv_path, target_size_mb, f"telecom_data_{target_size_mb}mb.json")
            print(f"Successfully generated a ~{target_size_mb} MB JSON file: {output_path}")
        except Exception as e:
            print(f"Error generating telecom data: {e}")
            sys.exit(1)
    else:
        print("Usage:")
        print("  python csv_to_json_converter.py                       # Generate a 50 MB JSON file from TelecomChurn.csv")
        print("  python csv_to_json_converter.py <csv_file_path>       # Convert CSV to JSON with same name")
        print("  python csv_to_json_converter.py <csv_file_path> <json_file_path>  # Convert CSV to JSON with specified name")
        print("  python csv_to_json_converter.py --size <size_in_mb>   # Generate telecom JSON of specified size in MB")
        sys.exit(1)
