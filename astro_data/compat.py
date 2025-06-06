"""
Compatibility layer for astro_data to work with RSW dependencies
"""
import importlib
import sys

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

def init_compatibility():
    """Initialize compatibility adaptations"""
    check_langchain_version()
