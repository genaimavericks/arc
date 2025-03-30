import os
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import logging
from typing import Generator

# Configure logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# Base declarative class
Base = declarative_base()

# Get database configuration from environment variables
DB_TYPE = os.getenv("DB_TYPE", "sqlite").lower()
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "dhani")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "rsw")

# Configure database URL based on DB_TYPE
if DB_TYPE == "sqlite":
    # Create database directory if it doesn't exist
    os.makedirs(os.path.dirname(os.path.abspath(__file__)), exist_ok=True)
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.db')}"
    connect_args = {"check_same_thread": False}
elif DB_TYPE == "postgresql" or DB_TYPE == "postgres":
    SQLALCHEMY_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    connect_args = {}
else:
    raise ValueError(f"Unsupported database type: {DB_TYPE}")

# Create engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args=connect_args,
    echo=True  # Enable SQL query logging
)

# Add event listeners to log all queries
@event.listens_for(engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault('query_start_time', []).append(datetime.utcnow())
    print(f"\n[SQL Query] {statement}")
    print(f"[SQL Parameters] {parameters}")

@event.listens_for(engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = datetime.utcnow() - conn.info['query_start_time'].pop(-1)
    print(f"[SQL Time] {total.total_seconds():.3f}s\n")

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency to get the database
def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize the database by creating all tables"""
    Base.metadata.create_all(bind=engine)
