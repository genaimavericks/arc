"""
Custom logging configuration for the RSW API.
This configuration removes access logs for specific URL patterns and filters out excessive debug output.
"""
import logging
import sys
from uvicorn.logging import AccessFormatter, DefaultFormatter
import re
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path

# Create a custom filter for application logs
class AppLogFilter(logging.Filter):
    def __init__(self):
        super().__init__()
        # Patterns to filter out from application logs
        self.filtered_patterns = [
            re.compile(r'DEBUG: Found \d+ jobs'),
            re.compile(r'DEBUG: get_jobs endpoint called'),
            re.compile(r'Using graph name:'),
            re.compile(r'Total nodes:'),
            re.compile(r'Total relationships:'),
            re.compile(r'Node counts:'),
            re.compile(r'Relationship counts:'),
            re.compile(r'Neo4j stats:'),
            re.compile(r'Active jobs:'),
            re.compile(r'Last update:')
        ]
    
    def filter(self, record):
        # If it's not a log message (no msg attribute), let it through
        if not hasattr(record, 'msg') or not isinstance(record.msg, str):
            return True
            
        # Check if the message matches any of our filtered patterns
        for pattern in self.filtered_patterns:
            if pattern.search(str(record.msg)):
                return False  # Filter out this message
                
        return True  # Let all other messages through

# Create a custom access filter that checks the request state
class RequestStateFilter(logging.Filter):
    def filter(self, record):
        # Check if this is an access log record with scope
        if hasattr(record, 'scope'):
            # Get the request state from the scope
            request_state = record.scope.get('state', {})
            
            # Check if the request is marked to skip access logging
            if getattr(request_state, 'skip_access_log', False):
                return False  # Skip this log record
        
        return True  # Log all other records

# Create a custom access formatter for better formatting
class CustomAccessFormatter(AccessFormatter):
    def __init__(self, fmt=None, datefmt=None, style='%', use_colors=False):
        super().__init__(fmt, datefmt, style, use_colors)
    
    def format(self, record):
        # For all records, use the normal formatter
        return super().format(record)

# Configure logging for the entire application
def configure_logging():
    # Create logs directory if it doesn't exist
    logs_dir = Path(__file__).parent / 'logs'
    logs_dir.mkdir(exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    
    # Add our custom filter to the console handler
    app_filter = AppLogFilter()
    console_handler.addFilter(app_filter)
    
    # Create file handler for important logs
    file_handler = RotatingFileHandler(
        logs_dir / 'api.log',
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    
    # Add handlers to root logger
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Configure specific loggers
    for logger_name in ['uvicorn', 'uvicorn.error', 'fastapi']:
        logger = logging.getLogger(logger_name)
        logger.handlers = []  # Remove default handlers
        logger.propagate = True  # Let the root logger handle it
    
    # Configure access logger separately
    access_logger = logging.getLogger('uvicorn.access')
    access_logger.handlers = []  # Remove default handlers
    access_logger.propagate = False  # Don't propagate to root logger
    
    # Create a special handler for access logs
    access_handler = logging.StreamHandler()
    access_handler.setFormatter(CustomAccessFormatter("%(levelprefix)s %(client_addr)s - \"%(request_line)s\" %(status_code)s"))
    
    # Add our request state filter to the access logger
    request_filter = RequestStateFilter()
    access_logger.addFilter(request_filter)
    
    access_logger.addHandler(access_handler)
    access_logger.setLevel(logging.INFO)
    
    # Set lower log levels for noisy libraries
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    logging.getLogger('neo4j').setLevel(logging.WARNING)
    
    return root_logger, access_logger

# Configure logging for Uvicorn (for backward compatibility)
def configure_uvicorn_logging():
    root_logger, access_logger = configure_logging()
    return access_logger
