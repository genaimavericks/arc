"""
Data Profiler API package.
This package contains all profiling-related API endpoints.
"""

from fastapi import APIRouter

# Import the router directly from router.py
from .router import router

# No need to include it in another router - this is the main router
# that will be used in main.py
