import os
import sqlite3

# Direct path to the SQLite database
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'database.db'))

def run_migration():
    """
    Add csv_file_path column to the schemas table if it doesn't exist
    """
    print(f"Using SQLite database at: {DB_PATH}")
    
    # Connect to the SQLite database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if the column already exists
    cursor.execute("PRAGMA table_info(schemas)")
    columns = cursor.fetchall()
    column_names = [column[1] for column in columns]
    
    if 'csv_file_path' not in column_names:
        print("Adding csv_file_path column to schemas table...")
        # Add the column
        cursor.execute("ALTER TABLE schemas ADD COLUMN csv_file_path TEXT")
        conn.commit()
        print("Migration completed successfully.")
    else:
        print("Column csv_file_path already exists in schemas table. No migration needed.")
    
    # Close the connection
    conn.close()

if __name__ == "__main__":
    run_migration()
