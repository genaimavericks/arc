import os
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import logging
from typing import Generator

# Configure logging
logging.basicConfig(level=logging.ERROR)  # Set root logger to ERROR level

# Output directories
OUTPUT_DIR = Path("runtime-data/output/db")
LOG_DIR = OUTPUT_DIR / "logs"
DATA_DIR = OUTPUT_DIR / "data"

# Create directories if they don't exist
LOG_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Set up file logging for SQL queries
sql_logger = logging.getLogger('sql_queries')
sql_logger.setLevel(logging.INFO)
log_file_path = os.path.join(LOG_DIR, 'db.logs')
file_handler = logging.FileHandler(log_file_path)
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(message)s')
file_handler.setFormatter(formatter)
sql_logger.addHandler(file_handler)
sql_logger.propagate = False  # Prevent logs from being sent to parent loggers

# Completely disable SQLAlchemy's built-in logging
sqlalchemy_loggers = [
    'sqlalchemy',
    'sqlalchemy.engine',
    'sqlalchemy.engine.base',
    'sqlalchemy.dialects',
    'sqlalchemy.pool',
    'sqlalchemy.orm'
]

for logger_name in sqlalchemy_loggers:
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.ERROR)  # Set to ERROR instead of WARNING
    logger.propagate = False  # Prevent propagation to parent loggers
    # Add file handler to redirect logs to file instead of console
    logger.addHandler(file_handler)

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
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{os.path.join(DATA_DIR, 'database.db')}"
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
    echo=False  # Disable SQL query logging through SQLAlchemy's built-in mechanism
)

# Add event listeners to log all queries
@event.listens_for(engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault('query_start_time', []).append(datetime.utcnow())
    sql_logger.info(f"[SQL Query] {statement}")
    sql_logger.info(f"[SQL Parameters] {parameters}")

@event.listens_for(engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = datetime.utcnow() - conn.info['query_start_time'].pop(-1)
    sql_logger.info(f"[SQL Time] {total.total_seconds():.3f}s\n")

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
