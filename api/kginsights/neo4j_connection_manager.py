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
            
        self._drivers = {}
        self._last_refresh_time = time.time()
        self._initialized = True
    
    def get_driver(self, uri: str, username: str, password: str) -> Any:
        """
        Get a Neo4j driver for the given connection parameters.
        Will create a new driver if one doesn't exist or if connections need refreshing.
        
        Args:
            uri: Neo4j URI
            username: Neo4j username
            password: Neo4j password
            
        Returns:
            Neo4j driver instance
        """
        connection_key = f"{uri}:{username}"
        
        # If we have a driver and it's still valid, return it
        if connection_key in self._drivers:
            driver = self._drivers[connection_key]
            try:
                # Test the connection with a simple query
                with driver.session() as session:
                    result = session.run("RETURN 1 as test")
                    test_value = result.single()["test"]
                    if test_value == 1:
                        return driver
            except Exception:
                # Connection failed, we'll create a new one
                self._close_driver(connection_key)
        
        # Create a new driver
        driver = GraphDatabase.driver(uri, auth=(username, password))
        self._drivers[connection_key] = driver
        return driver
    
    def _close_driver(self, connection_key: str) -> None:
        """
        Close a specific driver by its connection key.
        
        Args:
            connection_key: The connection key for the driver to close
        """
        if connection_key in self._drivers:
            try:
                self._drivers[connection_key].close()
            except Exception:
                pass  # Ignore errors when closing
            del self._drivers[connection_key]
    
    def close_all_drivers(self) -> None:
        """
        Close all active Neo4j drivers.
        """
        for connection_key in list(self._drivers.keys()):
            self._close_driver(connection_key)
    
    def refresh_connections(self) -> None:
        """
        Force refresh all Neo4j connections.
        """
        self.close_all_drivers()
        self._last_refresh_time = time.time()
    
    async def restart_neo4j(self, neo4j_home: Optional[str] = None) -> bool:
        """
        Restart the Neo4j service to ensure changes are visible.
        
        Args:
            neo4j_home: Path to Neo4j home directory
            
        Returns:
            True if restart successful, False otherwise
        """
        # First close all active connections
        self.close_all_drivers()
        
        try:
            system = platform.system()
            restart_cmd = None
            
            if system == "Windows":
                # For Windows, try to use the Neo4j batch file or service commands
                if neo4j_home:
                    neo4j_bin_path = os.path.join(neo4j_home, "bin", "neo4j.bat")
                    if os.path.exists(neo4j_bin_path):
                        # Use neo4j.bat restart
                        restart_cmd = [neo4j_bin_path, "restart"]
                    else:
                        # Fallback to Windows service commands
                        restart_cmd = ["powershell", "-Command", "Restart-Service neo4j"]
                else:
                    restart_cmd = ["powershell", "-Command", "Restart-Service neo4j"]
            elif system == "Linux":
                # For Linux, use systemctl if available
                restart_cmd = ["sudo", "systemctl", "restart", "neo4j"]
            elif system == "Darwin":  # macOS
                # For macOS with Homebrew
                restart_cmd = ["brew", "services", "restart", "neo4j"]
            
            if not restart_cmd:
                print("Could not determine how to restart Neo4j on this platform")
                return False
                
            print(f"Restarting Neo4j service with command: {' '.join(restart_cmd)}")
            process = subprocess.Popen(
                restart_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                print(f"Neo4j restart failed with code {process.returncode}")
                for line in stderr.splitlines():
                    print(f"Restart error: {line}")
                return False
            
            # Wait for Neo4j to fully restart
            print("Waiting for Neo4j to fully restart...")
            time.sleep(15)  # Give Neo4j time to restart
            
            # Refresh all connections
            self.refresh_connections()
            
            return True
        except Exception as e:
            print(f"Error restarting Neo4j: {str(e)}")
            return False

# Create a singleton instance
neo4j_connection_manager = Neo4jConnectionManager()
