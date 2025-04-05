"""
CSV Connector for loading data from CSV files into Neo4j.
"""
import os
import csv
import logging
from typing import Dict, List, Generator, Any, Optional
import pandas as pd

class CSVConnector:
    """
    Handles reading and processing CSV files for Neo4j data loading.
    Supports various encodings and cross-platform path handling.
    """
    
    def __init__(self, file_path: str, batch_size: int = 1000):
        """
        Initialize the CSV connector.
        
        Args:
            file_path: Path to the CSV file
            batch_size: Number of records to yield in each batch
        """
        self.file_path = self._normalize_path(file_path)
        self.batch_size = batch_size
        self.logger = logging.getLogger(__name__)
        
    def _normalize_path(self, path: str) -> str:
        """
        Normalize file path to handle both Windows and Linux paths.
        
        Args:
            path: The file path to normalize
            
        Returns:
            Normalized path
        """
        # Replace backslashes with forward slashes for consistency
        normalized_path = path.replace('\\', '/')
        
        # Ensure the path exists
        if not os.path.exists(normalized_path):
            # Try the original path in case normalization caused issues
            if os.path.exists(path):
                return path
            else:
                self.logger.warning(f"Path does not exist after normalization: {normalized_path}")
                
        return normalized_path
    
    def validate_file(self) -> Dict[str, Any]:
        """
        Validate that the CSV file exists and is readable.
        
        Returns:
            Dict with validation results
        """
        result = {
            "valid": False,
            "errors": [],
            "warnings": [],
            "file_info": {}
        }
        
        # Check if file exists
        if not os.path.exists(self.file_path):
            result["errors"].append(f"File does not exist: {self.file_path}")
            return result
            
        # Check if file is readable
        if not os.access(self.file_path, os.R_OK):
            result["errors"].append(f"File is not readable: {self.file_path}")
            return result
            
        # Check if file is empty
        file_size = os.path.getsize(self.file_path)
        if file_size == 0:
            result["errors"].append(f"File is empty: {self.file_path}")
            return result
            
        # Get file info
        result["file_info"] = {
            "path": self.file_path,
            "size": file_size,
            "last_modified": os.path.getmtime(self.file_path)
        }
        
        # Try to read the first few lines to verify it's a valid CSV
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader, None)
                if not header:
                    result["errors"].append("CSV file has no header row")
                    return result
                    
                # Get the first row to verify data
                first_row = next(reader, None)
                if not first_row:
                    result["warnings"].append("CSV file has a header but no data rows")
                
                result["file_info"]["columns"] = header
                result["file_info"]["sample_row"] = first_row
                result["valid"] = True
                
        except UnicodeDecodeError:
            # Try with different encodings
            for encoding in ['latin1', 'cp1252', 'ISO-8859-1']:
                try:
                    with open(self.file_path, 'r', encoding=encoding) as f:
                        reader = csv.reader(f)
                        header = next(reader, None)
                        if not header:
                            continue
                            
                        first_row = next(reader, None)
                        result["file_info"]["columns"] = header
                        result["file_info"]["sample_row"] = first_row
                        result["file_info"]["encoding"] = encoding
                        result["valid"] = True
                        result["warnings"].append(f"File uses {encoding} encoding instead of utf-8")
                        break
                except Exception:
                    continue
                    
            if not result["valid"]:
                result["errors"].append("Could not read CSV file with any supported encoding")
                
        except Exception as e:
            result["errors"].append(f"Error reading CSV file: {str(e)}")
            
        return result
    
    def get_column_mapping(self, schema: Dict[str, Any]) -> Dict[str, str]:
        """
        Get mapping between CSV columns and node properties based on schema.
        
        Args:
            schema: The schema definition
            
        Returns:
            Dict mapping CSV columns to node properties
        """
        mapping = {}
        
        # Try to read the header to get column names
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader, None)
                if not header:
                    return mapping
                    
                # For each node in the schema, map columns to properties
                for node in schema.get("nodes", []):
                    node_label = node.get("label")
                    properties = node.get("properties", {})
                    
                    # Handle properties as dictionary
                    if isinstance(properties, dict):
                        for prop_name in properties.keys():
                            if prop_name in header:
                                mapping[prop_name] = {
                                    "node_label": node_label,
                                    "property": prop_name
                                }
                    
                    # Handle properties as list
                    elif isinstance(properties, list):
                        for prop in properties:
                            prop_name = prop.get("name")
                            if prop_name in header:
                                mapping[prop_name] = {
                                    "node_label": node_label,
                                    "property": prop_name
                                }
        except Exception as e:
            self.logger.error(f"Error creating column mapping: {str(e)}")
            
        return mapping
    
    def read_batches(self) -> Generator[List[Dict[str, Any]], None, None]:
        """
        Read the CSV file in batches to efficiently process large files.
        
        Yields:
            Batches of records as dictionaries
        """
        # Try different encodings
        encodings = ['utf-8', 'latin1', 'cp1252', 'ISO-8859-1']
        
        for encoding in encodings:
            try:
                # Use pandas to efficiently read CSV in chunks
                for chunk in pd.read_csv(self.file_path, encoding=encoding, chunksize=self.batch_size):
                    # Convert chunk to list of dictionaries
                    records = chunk.to_dict(orient='records')
                    self.logger.debug(f"Read batch of {len(records)} records")
                    yield records
                    
                # If we get here, we've successfully read the file
                return
            except Exception as e:
                self.logger.warning(f"Failed to read CSV with encoding {encoding}: {str(e)}")
                continue
                
        # If we get here, we've failed with all encodings
        self.logger.error("Failed to read CSV with all attempted encodings")
        raise ValueError(f"Could not read CSV file: {self.file_path}")
