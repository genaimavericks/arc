"""
Neo4j connection manager to handle connection pooling and refreshing.
"""
import os
import time
import platform
import subprocess
from typing import Dict, Any, Optional
from neo4j import GraphDatabase
import threading
import logging

logger = logging.getLogger(__name__)

class Neo4jConnectionManager:
    """
    Singleton class to manage Neo4j connections and ensure they're refreshed after data loading.
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(Neo4jConnectionManager, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._drivers = {}
        self._driver_lock = threading.Lock()
    
    def get_driver(self, uri: str, username: str, password: str) -> GraphDatabase.driver:
        """
        Get a Neo4j driver instance for the specified URI and credentials.
        If a driver for the URI already exists, return it, otherwise create a new one.
        
        Args:
            uri: Neo4j URI
            username: Neo4j username
            password: Neo4j password
            
        Returns:
            Neo4j driver instance
        """
        # Create a unique key for this connection
        connection_key = f"{uri}_{username}"
        
        with self._driver_lock:
            # Check if we already have a driver for this connection
            if connection_key in self._drivers:
                return self._drivers[connection_key]
            
            # Create a new driver
            try:
                driver = GraphDatabase.driver(uri, auth=(username, password))
                self._drivers[connection_key] = driver
                logger.info(f"Created new Neo4j driver for {uri}")
                return driver
            except Exception as e:
                logger.error(f"Error creating Neo4j driver: {str(e)}")
                raise
    
    def close_all_drivers(self):
        """
        Close all Neo4j drivers.
        """
        with self._driver_lock:
            for uri, driver in self._drivers.items():
                try:
                    driver.close()
                    logger.info(f"Closed Neo4j driver for {uri}")
                except Exception as e:
                    logger.error(f"Error closing Neo4j driver: {str(e)}")
            
            self._drivers = {}

# Create a singleton instance
neo4j_connection_manager = Neo4jConnectionManager()
