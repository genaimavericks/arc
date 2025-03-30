"""
Sample environment configurations for database connections.
Copy this file to set_db_env.py and modify as needed.

Usage:
- Run with SQLite: python set_db_env.py sqlite
- Run with PostgreSQL: python set_db_env.py postgres
"""

import os
import sys

def set_sqlite_env():
    """Set environment variables for SQLite database"""
    os.environ["DB_TYPE"] = "sqlite"
    print("Environment set for SQLite database")

def set_postgres_env():
    """Set environment variables for PostgreSQL database"""
    os.environ["DB_TYPE"] = "postgresql"
    os.environ["DB_HOST"] = "localhost"
    os.environ["DB_PORT"] = "5432"
    os.environ["DB_USER"] = "dhani"
    os.environ["DB_PASSWORD"] = ""  # Set your password here if needed
    os.environ["DB_NAME"] = "rsw"
    print("Environment set for PostgreSQL database")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python set_db_env.py [sqlite|postgres]")
        sys.exit(1)
        
    db_type = sys.argv[1].lower()
    
    if db_type == "sqlite":
        set_sqlite_env()
    elif db_type in ["postgres", "postgresql"]:
        set_postgres_env()
    else:
        print(f"Unsupported database type: {db_type}")
        print("Usage: python set_db_env.py [sqlite|postgres]")
        sys.exit(1)
