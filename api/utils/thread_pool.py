"""
Thread pool utility for handling blocking operations without blocking the main event loop.
"""
import asyncio
import concurrent.futures
from functools import wraps
import logging

# Create a thread pool executor with a reasonable number of workers
# This will be used for running blocking operations without blocking the main event loop
thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=10)
logger = logging.getLogger(__name__)

async def run_in_threadpool(func, *args, **kwargs):
    """
    Run a blocking function in a thread pool and await its result.
    
    Args:
        func: The blocking function to run
        *args: Positional arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        The result of the function
    """
    return await asyncio.get_event_loop().run_in_executor(
        thread_pool, 
        lambda: func(*args, **kwargs)
    )

def to_thread(func):
    """
    Decorator to run a blocking function in a thread pool.
    
    Example:
        @to_thread
        def blocking_function(arg1, arg2):
            # This will run in a thread pool
            return result
            
        async def my_handler():
            # This won't block the event loop
            result = await blocking_function(arg1, arg2)
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        return await run_in_threadpool(func, *args, **kwargs)
    return wrapper
