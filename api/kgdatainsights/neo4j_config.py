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
    try:
        # Load configuration from file
        config = _load_config()
        
        # If the specified graph doesn't exist in the config, use default
        if graph_name not in config:
            logger.warning(f"Graph '{graph_name}' not found in configuration, using default")
            return DEFAULT_CONFIG["default_graph"]
        
        # Get system-specific configuration
        system_config = _get_system_specific_config()
        
        # Merge system-specific configuration with graph configuration
        merged_config = {**config[graph_name], **system_config}
        
        return merged_config
    except Exception as e:
        logger.error(f"Error getting Neo4j configuration: {str(e)}")
        return DEFAULT_CONFIG["default_graph"]

def _load_config() -> Dict[str, Dict[str, Any]]:
    """
    Load configuration from the JSON file.
    
    Returns:
        Dictionary containing the configuration
    """
    try:
        if CONFIG_FILE_PATH.exists():
            with open(CONFIG_FILE_PATH, "r") as f:
                return json.load(f)
        else:
            logger.warning(f"Configuration file not found at {CONFIG_FILE_PATH}, using default")
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
    system_config = {}
    
    # Get Neo4j URI from environment variable if available
    neo4j_uri = os.environ.get("NEO4J_URI")
    if neo4j_uri:
        system_config["uri"] = neo4j_uri
    
    # Get Neo4j username from environment variable if available
    neo4j_username = os.environ.get("NEO4J_USERNAME")
    if neo4j_username:
        system_config["username"] = neo4j_username
    
    # Get Neo4j password from environment variable if available
    neo4j_password = os.environ.get("NEO4J_PASSWORD")
    if neo4j_password:
        system_config["password"] = neo4j_password
    
    return system_config

def get_neo4j_connection_params(graph_name: str = "default_graph") -> Dict[str, Any]:
    """
    Get Neo4j connection parameters for a specific graph.
    
    Args:
        graph_name: Name of the graph to get connection parameters for
        
    Returns:
        Dictionary containing the connection parameters for the specified graph
    """
    config = get_neo4j_config(graph_name)
    return {
        "uri": config.get("uri", "neo4j://localhost:7687"),
        "auth": (config.get("username", "neo4j"), config.get("password", "neo4j123")),
        "database": config.get("database", "neo4j")
    }
