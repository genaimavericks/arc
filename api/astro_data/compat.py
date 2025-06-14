"""
Compatibility layer for astro_data to work with RSW dependencies
"""
import importlib
import sys
import os
from pathlib import Path

def check_langchain_version():
    """Check if langchain version is compatible and provide adapter if needed"""
    try:
        import langchain
        version = langchain.__version__
        print(f"Using langchain version: {version}")
        
        # If using newer langchain (0.3.x), we need to adjust imports
        if version.startswith("0.3"):
            # Patch the module to use the correct imports
            try:
                sys.modules["langchain_huggingface"] = importlib.import_module("langchain_community.embeddings.huggingface")
                print("Patched langchain_huggingface imports")
            except ImportError:
                print("Could not patch langchain_huggingface imports")
    except ImportError:
        print("Could not determine langchain version")

def setup_module_imports():
    """Set up module imports to handle the 'modules' import issue"""
    # Get the current directory (api/astro_data)
    current_dir = Path(__file__).parent
    
    # Create a modules alias that points to api/astro_data/modules
    modules_path = current_dir / 'modules'
    
    # Add the modules path to sys.path
    if str(modules_path) not in sys.path:
        sys.path.append(str(modules_path))
    
    # Create a modules alias in sys.modules
    if 'modules' not in sys.modules:
        sys.modules['modules'] = importlib.import_module('api.astro_data.modules')
        print("Created 'modules' alias for api.astro_data.modules")
    
    # Add the parent directory to Python path to find the api package
    parent_path = current_dir.parent.parent
    if str(parent_path) not in sys.path:
        sys.path.append(str(parent_path))
        print(f"Added {parent_path} to sys.path")

def init_compatibility():
    """Initialize compatibility adaptations"""
    check_langchain_version()
    setup_module_imports()
