#!/usr/bin/env python3

import psycopg2
import sys

# Connection parameters
host = "localhost"
port = "5432"
database = "rsw_test"
user = "dhani"
password = ""  # If using trust authentication, password can be empty

try:
    # First try: Connect to localhost
    print(f"Testing connection to {host}:{port} as {user}...")
    conn = psycopg2.connect(
        host=host,
        port=port,
        database=database,
        user=user,
        password=password
    )
    
    # Test a simple query
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM customers")
    result = cursor.fetchone()
    print(f"Success! Found {result[0]} customers in the database.")
    
    cursor.close()
    conn.close()
    print("Connection test successful!")
    
except Exception as e:
    print(f"Connection failed: {str(e)}")
    
    # Try alternative: Connect via Unix socket (if localhost failed)
    try:
        print("\nTrying alternative connection via Unix socket...")
        conn = psycopg2.connect(
            database=database,
            user=user,
            password=password
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM customers")
        result = cursor.fetchone()
        print(f"Success! Found {result[0]} customers in the database via Unix socket.")
        
        cursor.close()
        conn.close()
        print("Unix socket connection successful!")
        
    except Exception as e2:
        print(f"Unix socket connection also failed: {str(e2)}")
        print("\nSuggested solutions:")
        print("1. Check if PostgreSQL service is running")
        print("2. Verify your username and password")
        print("3. Make sure the database 'rsw_test' exists")
        print("4. Check pg_hba.conf for authentication settings")
        sys.exit(1)
