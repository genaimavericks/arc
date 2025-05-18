"""
Centralized Neo4j configuration module.
This module serves as the single source of truth for all Neo4j configuration settings.
"""
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Path to the configuration file
CONFIG_FILE_PATH = Path(__file__).parent / "neo4j.databases.json"

# Default configuration values
DEFAULT_CONFIG = {
    "default_graph": {
        "username": "neo4j",
        "database": "neo4j",
        "uri": "neo4j://localhost:7687",
        "password": "neo4j123"
    }
}

def get_neo4j_config(graph_name: str = "default_graph") -> Dict[str, Any]:
    """
    Get Neo4j configuration for a specific graph.
    
    Args:
        graph_name: Name of the graph to get configuration for
        
    Returns:
        Dictionary containing the configuration for the specified graph
    """
    config = _load_config()
    
    # Try to get configuration for the specified graph
    graph_config = config.get(graph_name, {})
    
    # If not found, fall back to default_graph
    if not graph_config and graph_name != "default_graph":
        logger.warning(f"No configuration found for graph '{graph_name}', falling back to default_graph")
        graph_config = config.get("default_graph", {})
    
    # If still not found, use default configuration
    if not graph_config:
        logger.warning("No configuration found, using default configuration")
        graph_config = DEFAULT_CONFIG.get("default_graph", {})
    
    # Add additional configuration for data loading
    system_specific_config = _get_system_specific_config()
    graph_config.update(system_specific_config)
    
    return graph_config

def _load_config() -> Dict[str, Any]:
    """
    Load configuration from the JSON file.
    
    Returns:
        Dictionary containing the configuration
    """
    try:
        if CONFIG_FILE_PATH.exists():
            with open(CONFIG_FILE_PATH, 'r') as file:
                return json.load(file)
        else:
            logger.warning(f"Configuration file {CONFIG_FILE_PATH} not found, using default configuration")
            return DEFAULT_CONFIG
    except Exception as e:
        logger.error(f"Error loading configuration: {str(e)}")
        return DEFAULT_CONFIG

def _get_system_specific_config() -> Dict[str, Any]:
    """
    Get system-specific configuration based on the operating system.
    
    Returns:
        Dictionary containing system-specific configuration
    """
    import platform
    
    system = platform.system()
    config = {}
    
    if system == "Windows":
        config["neo4j_home"] = os.environ.get("NEO4J_HOME", "C:\\development\\neo4j")
    elif system == "Linux":
        config["neo4j_home"] = os.environ.get("NEO4J_HOME", "/var/lib/neo4j")
        config["neo4j_bin"] = os.environ.get("NEO4J_BIN", "/usr/bin")
    elif system == "Darwin":  # macOS
        config["neo4j_home"] = os.environ.get("NEO4J_HOME", "/opt/homebrew/var/neo4j")
        config["neo4j_bin"] = os.environ.get("NEO4J_BIN", "/opt/homebrew/bin")
    
    # Set bin directory if not already set
    if "neo4j_bin" not in config and "neo4j_home" in config:
        config["neo4j_bin"] = os.path.join(config["neo4j_home"], "bin")
    
    return config

def get_neo4j_connection_params(graph_name: str = "default_graph") -> Dict[str, Any]:
    """
    Get Neo4j connection parameters for a specific graph.
    
    Args:
        graph_name: Name of the graph to get connection parameters for
        
    Returns:
        Dictionary containing the connection parameters for the specified graph
    """
    return get_neo4j_config(graph_name)
