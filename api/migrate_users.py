"""
Migration script to add updated_at column to users table
"""
from sqlalchemy import create_engine, MetaData, Table, Column, DateTime, text
from datetime import datetime
import os

# Database setup
SQLALCHEMY_DATABASE_URL = f"sqlite:///{os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.db')}"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})

def migrate():
    # Create a metadata object
    metadata = MetaData()
    
    # Reflect the users table
    metadata.reflect(bind=engine, only=['users'])
    
    # Get the users table
    users = Table('users', metadata)
    
    # Check if updated_at column already exists
    if 'updated_at' not in users.columns:
        # Create the updated_at column
        print("Adding updated_at column to users table...")
        with engine.connect() as conn:
            conn.execute(text('ALTER TABLE users ADD COLUMN updated_at TIMESTAMP'))
            
            # Update all existing rows to set updated_at = created_at
            print("Setting updated_at to match created_at for existing users...")
            conn.execute(text('UPDATE users SET updated_at = created_at'))
            conn.commit()
        
        print("Migration completed successfully!")
    else:
        print("updated_at column already exists in users table. No migration needed.")

if __name__ == "__main__":
    #migrate()
