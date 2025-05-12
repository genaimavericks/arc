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
            stop_cmd = None
            start_cmd = None
            
            if system == "Windows":
                # For Windows, try to use the Neo4j batch file or service commands
                if neo4j_home:
                    neo4j_bin_path = os.path.join(neo4j_home, "bin", "neo4j.bat")
                    if os.path.exists(neo4j_bin_path):
                        # Use separate stop and start commands instead of restart
                        stop_cmd = [neo4j_bin_path, "stop"]
                        start_cmd = [neo4j_bin_path, "start"]
                    else:
                        # Fallback to Windows service commands
                        stop_cmd = ["powershell", "-Command", "Stop-Service neo4j"]
                        start_cmd = ["powershell", "-Command", "Start-Service neo4j"]
                else:
                    stop_cmd = ["powershell", "-Command", "Stop-Service neo4j"]
                    start_cmd = ["powershell", "-Command", "Start-Service neo4j"]
            elif system == "Linux":
                # For Linux, use the direct neo4j command-line tool instead of systemctl
                stop_cmd = ["sudo", "neo4j", "stop"]
                start_cmd = ["sudo", "neo4j", "start"]
            elif system == "Darwin":  # macOS
                # For macOS with Homebrew
                stop_cmd = ["brew", "services", "stop", "neo4j"]
                start_cmd = ["brew", "services", "start", "neo4j"]
            
            if not stop_cmd or not start_cmd:
                print("Could not determine how to restart Neo4j on this platform")
                return False
            
            # First stop Neo4j
            print(f"Stopping Neo4j service with command: {' '.join(stop_cmd)}")
            stop_process = subprocess.Popen(
                stop_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stop_stdout, stop_stderr = stop_process.communicate()
            
            if stop_process.returncode != 0:
                print(f"Neo4j stop failed with code {stop_process.returncode}")
                for line in stop_stderr.splitlines():
                    print(f"Stop error: {line}")
                # Continue anyway, as we'll try to start it
            
            # Wait for Neo4j to fully stop
            print("Waiting for Neo4j to fully stop...")
            time.sleep(10)  # Give Neo4j time to stop
            
            # For Linux, we'll use a more gentle approach instead of SIGKILL
            if system == "Linux" or system == "Darwin":
                try:
                    # Check if Neo4j is still running
                    check_process = subprocess.run(
                        ["pgrep", "-f", "neo4j"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    if check_process.returncode == 0 and check_process.stdout.strip():
                        print("Neo4j is still running after stop command. Trying direct restart instead...")
                        # Instead of force killing, we'll try a full restart with the direct command
                        restart_cmd = ["sudo", "neo4j", "restart"]
                        print(f"Running full service restart: {' '.join(restart_cmd)}")
                        restart_process = subprocess.run(
                            restart_cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                            check=False
                        )
                        # Wait longer after a full restart
                        time.sleep(10)
                        # Set start_cmd to None to skip the regular start command
                        # since we've already tried to restart
                        if restart_process.returncode == 0:
                            start_cmd = None
                except Exception as check_err:
                    print(f"Error checking if Neo4j is still running: {str(check_err)}")
            
            # Now start Neo4j if we haven't already done a full restart
            if start_cmd is not None:
                print(f"Starting Neo4j service with command: {' '.join(start_cmd)}")
                start_process = subprocess.Popen(
                    start_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                start_stdout, start_stderr = start_process.communicate()
                
                if start_process.returncode != 0:
                    print(f"Neo4j start failed with code {start_process.returncode}")
                    for line in start_stderr.splitlines():
                        print(f"Start error: {line}")
                    return False
            else:
                print("Skipping explicit start command as we've already attempted a full restart")
            
            # Wait for Neo4j to fully start - increased wait time for reliability
            print("Waiting for Neo4j to fully start...")
            time.sleep(30)  # Give Neo4j more time to start (increased to 30 seconds)
            
            # Refresh all connections
            self.refresh_connections()
            
            # Verify Neo4j is actually running
            if system == "Linux" or system == "Darwin":
                try:
                    # First check if the process is running
                    check_process = subprocess.run(
                        ["pgrep", "-f", "neo4j"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    if check_process.returncode != 0 or not check_process.stdout.strip():
                        print("Neo4j does not appear to be running after start attempt")
                        # Try one more restart as a last resort
                        print("Attempting one final restart as a last resort...")
                        last_restart_cmd = ["sudo", "neo4j", "restart"]
                        subprocess.run(last_restart_cmd, check=False)
                        time.sleep(30)  # Wait longer for the final restart
                        # Check again
                        check_process = subprocess.run(
                            ["pgrep", "-f", "neo4j"],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True
                        )
                        if check_process.returncode != 0 or not check_process.stdout.strip():
                            print("Neo4j still not running after final restart attempt")
                            return False
                    print(f"Neo4j is running with PID(s): {check_process.stdout.strip()}")
                    
                    # Now verify the port is actually accepting connections
                    print("Verifying Neo4j port is accepting connections...")
                    # Try to connect to the Neo4j port
                    for i in range(3):  # Try 3 times
                        try:
                            import socket
                            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            sock.settimeout(5)
                            result = sock.connect_ex(('localhost', 7687))
                            sock.close()
                            if result == 0:
                                print("Neo4j port 7687 is open and accepting connections")
                                break
                            else:
                                print(f"Neo4j port check attempt {i+1}: Port 7687 is not open yet")
                                time.sleep(5)  # Wait before trying again
                        except Exception as port_err:
                            print(f"Error checking Neo4j port: {str(port_err)}")
                            time.sleep(5)  # Wait before trying again
                    
                except Exception as check_err:
                    print(f"Error checking if Neo4j is running: {str(check_err)}")
            
            return True
        except Exception as e:
            print(f"Error restarting Neo4j: {str(e)}")
            print(traceback.format_exc())
            return False

# Create a singleton instance
neo4j_connection_manager = Neo4jConnectionManager()
