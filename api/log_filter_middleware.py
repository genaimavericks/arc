"""
Middleware to filter out access logs for specific endpoints.
This middleware works by setting a flag on the request state that can be checked by logging handlers.
"""
import re
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from fastapi import FastAPI

class LogFilterMiddleware(BaseHTTPMiddleware):
    """
    Middleware that marks certain requests to be excluded from access logs.
    This works in conjunction with a custom logging filter.
    """
    
    def __init__(self, app: FastAPI):
        super().__init__(app)
        # Patterns of paths to exclude from access logs
        self.excluded_patterns = [
            re.compile(r'^/api/processing-jobs'),
            re.compile(r'^/api/kginsights/schema-status/'),
            re.compile(r'^/api/graphschema/load-data'),
            re.compile(r'^/api/graphschema/schemas/\d+/load-data'),
            # Add more patterns as needed
            re.compile(r'^/api/kginsights/'),
            re.compile(r'^/api/graphschema/')
        ]
    
    async def dispatch(self, request: Request, call_next):
        """
        Process the request, marking it to be excluded from logs if it matches the patterns.
        """
        path = request.url.path
        
        # Check if the path matches any of the excluded patterns
        for pattern in self.excluded_patterns:
            if pattern.match(path):
                # Set a flag on the request state to indicate this request should not be logged
                request.state.skip_access_log = True
                break
        
        # Continue processing the request
        response = await call_next(request)
        return response
