import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Generator
import re
from datetime import datetime, date
import jellyfish  # For fuzzy string matching
from collections import defaultdict
import uuid
from scipy import stats  # Import scipy.stats properly
import math
import os
import gc
import time
import logging
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import partial

# Configure logger
logger = logging.getLogger("profiler.engine")

# Helper function for JSON serialization
def json_serializable(obj):
    """Convert objects to JSON serializable types."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif pd.isna(obj):
        return None
    elif isinstance(obj, (np.int64, np.int32, np.int16, np.int8)):
        return int(obj)
    elif isinstance(obj, (np.float64, np.float32, np.float16)):
        return float(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    return obj

class DataProfiler:
    def __init__(self, df: pd.DataFrame, max_memory_mb: int = 1000, chunk_size: int = 100000):
        """Initialize the DataProfiler with a DataFrame.
        
        Args:
            df: The DataFrame to profile
            max_memory_mb: Maximum memory usage in MB (default: 1000MB/1GB)
            chunk_size: Number of rows to process in each chunk for large files
        """
        self.df = df
        self.total_rows = len(df)
        self.total_columns = len(df.columns)
        self.max_memory_mb = max_memory_mb
        self.chunk_size = chunk_size
        self.column_data_types = {}
        
        # Determine if we need chunked processing based on DataFrame size
        df_size_mb = self.df.memory_usage(deep=True).sum() / (1024 * 1024)
        self.use_chunked_processing = df_size_mb > (max_memory_mb / 2)
        logger.info(f"DataFrame size: {df_size_mb:.2f} MB, Using chunked processing: {self.use_chunked_processing}")
        
        # Pre-compute data types for all columns (using sample for large dataframes)
        if self.use_chunked_processing:
            # Use a sample for initial data type detection
            sample_size = min(10000, self.total_rows)
            sample_df = self.df.sample(sample_size) if self.total_rows > sample_size else self.df
            for col in self.df.columns:
                self.column_data_types[col] = self._detect_data_type(sample_df[col])
        else:
            # For smaller dataframes, use the full dataset
            for col in self.df.columns:
                self.column_data_types[col] = self._detect_data_type(self.df[col])

    def generate_profile(self) -> Tuple[Dict, Dict]:
        """Generate a complete profile of the DataFrame.
        
        Returns:
            Tuple containing (profile_summary, column_profiles)
        """
        start_time = time.time()
        logger.info(f"Starting profile generation for DataFrame with {self.total_rows} rows and {self.total_columns} columns")
        
        # Calculate overall data quality score and summary statistics
        profile_summary = {
            "total_rows": self.total_rows,
            "total_columns": self.total_columns,
            "data_quality_score": 0.0,  # Will be updated after column profiling
            "column_names": list(self.df.columns),
            "original_headers": list(self.df.columns),
            "exact_duplicates_count": 0,  # Will be set later
            "fuzzy_duplicates_count": 0,  # Will be set later
        }
        
        # Profile columns
        if self.use_chunked_processing:
            logger.info(f"Using chunked processing for {self.total_columns} columns")
            column_profiles = self._profile_columns_chunked()
        else:
            logger.info(f"Using standard processing for {self.total_columns} columns")
            column_profiles = {}
            for col in self.df.columns:
                column_profiles[col] = self.profile_column(col)
        
        # Calculate overall data quality score (average of column scores)
        if column_profiles:
            if isinstance(column_profiles, dict):
                quality_scores = [col_profile.get('quality_score', 0) 
                                for col_profile in column_profiles.values() 
                                if isinstance(col_profile, dict)]
            else:  # List of column profiles
                quality_scores = [col_profile.get('quality_score', 0) 
                                for col_profile in column_profiles 
                                if isinstance(col_profile, dict)]
                
            if quality_scores:
                profile_summary["data_quality_score"] = float(sum(quality_scores) / len(quality_scores))
        
        duration = time.time() - start_time
        logger.info(f"Profile generation completed in {duration:.2f} seconds")
        
        return profile_summary, column_profiles
    
    def _profile_columns_chunked(self) -> Dict:
        """Profile columns using chunked processing to reduce memory usage.
        
        Returns:
            Dictionary of column profiles
        """
        column_profiles = {}
        
        # Process columns in parallel with a maximum of 4 workers
        # This helps with CPU-bound operations while controlling memory usage
        with ThreadPoolExecutor(max_workers=4) as executor:
            # Submit all column profiling tasks
            future_to_column = {}
            for col in self.df.columns:
                future = executor.submit(self._profile_column_chunked, col)
                future_to_column[future] = col
            
            # Process results as they complete
            for future in as_completed(future_to_column):
                col = future_to_column[future]
                try:
                    column_profiles[col] = future.result()
                except Exception as e:
                    logger.error(f"Error profiling column {col}: {str(e)}")
                    # Provide a minimal profile for failed columns
                    column_profiles[col] = {
                        "column_name": col,
                        "data_type": self.column_data_types.get(col, "unknown"),
                        "count": 0,
                        "null_count": 0,
                        "unique_count": 0,
                        "quality_score": 0.0,
                        "error": str(e)
                    }
                
                # Force garbage collection after each column to free memory
                gc.collect()
        
        return column_profiles
    
    def _profile_column_chunked(self, column_name: str) -> Dict:
        """Profile a column using chunked processing for large datasets.
        
        Args:
            column_name: Name of the column to profile
            
        Returns:
            Column profile dictionary
        """
        # Get the data type from cache
        data_type = self.column_data_types[column_name]
        
        # Initialize counters and aggregators
        null_count = 0
        empty_string_count = 0
        value_counts = defaultdict(int)
        unique_values = set()
        numeric_values = []
        
        # Process in chunks
        chunk_size = self.chunk_size
        for i in range(0, self.total_rows, chunk_size):
            # Get chunk
            chunk_end = min(i + chunk_size, self.total_rows)
            chunk = self.df.iloc[i:chunk_end][column_name]
            
            # Count nulls
            null_count += chunk.isnull().sum()
            
            # Process non-null values
            non_null_chunk = chunk.dropna()
            
            # Count empty strings for ALL column types, not just string columns
            empty_string_mask = (non_null_chunk.astype(str).str.strip() == "")
            empty_string_count += empty_string_mask.sum()
            
            # Update value counts (limit to most frequent values)
            chunk_value_counts = non_null_chunk.value_counts().head(20).to_dict()
            for val, count in chunk_value_counts.items():
                value_counts[str(val)] += count
            
            # Update unique values (limit to reasonable number to avoid memory issues)
            if len(unique_values) < 1000:  # Cap unique values to avoid memory explosion
                unique_values.update(non_null_chunk.unique())
            
            # Collect numeric values for statistics (sample to avoid memory issues)
            if data_type in ['integer', 'float'] and len(numeric_values) < 10000:
                # Take a sample if the chunk is large
                if len(non_null_chunk) > 1000:
                    numeric_values.extend(non_null_chunk.sample(1000).tolist())
                else:
                    numeric_values.extend(non_null_chunk.tolist())
            
            # Free memory
            del chunk
            del non_null_chunk
            gc.collect()
        
        # Check if potentially numeric column
        is_potential_numeric = data_type in ['integer', 'float']
        
        # Enhanced missing value detection for potentially numeric columns
        numeric_conversion_nan_count = 0
        
        if is_potential_numeric:
            # Process in chunks to detect numeric missing values
            for i in range(0, self.total_rows, chunk_size):
                chunk_end = min(i + chunk_size, self.total_rows)
                chunk = self.df.iloc[i:chunk_end][column_name]
                
                try:
                    # Convert to numeric to detect additional missing values
                    numeric_chunk = pd.to_numeric(chunk, errors='coerce')
                    numeric_conversion_nan_count += numeric_chunk.isna().sum()
                except Exception as e:
                    logger.debug(f"Error in numeric conversion for column {column_name} chunk {i}-{chunk_end}: {str(e)}")
                
                # Free memory
                del chunk
                gc.collect()
            
            # Log only if we find additional missing values
            additional_missing = numeric_conversion_nan_count - (null_count + empty_string_count)
            if additional_missing > 0:
                logger.debug(f"Column {column_name}: Detected {additional_missing} additional missing values after numeric conversion")
        
        # Calculate total missing - take max of standard count and numeric conversion count
        total_missing = null_count + empty_string_count
        if is_potential_numeric and numeric_conversion_nan_count > total_missing:
            logger.debug(f"Column {column_name}: Using numeric conversion missing count={numeric_conversion_nan_count} "
                        f"instead of standard missing count={total_missing}")
            total_missing = numeric_conversion_nan_count
        
        # Calculate metrics
        completeness = float(1 - (total_missing / self.total_rows)) if self.total_rows > 0 else 0.0
        
        # Calculate uniqueness (capped by our unique value collection)
        unique_count = min(len(unique_values), self.total_rows - null_count)
        uniqueness = float(unique_count / self.total_rows) if self.total_rows > 0 else 0.0
        
        # Calculate validity (simplified for chunked processing)
        validity = 0.9  # Default validity score
        
        # Calculate quality score
        quality_score = self._calculate_column_quality_score(completeness, uniqueness, validity)
        
        # Create profile
        profile = {
            "column_name": column_name,
            "data_type": data_type,
            "count": self.total_rows - total_missing,
            "null_count": null_count,
            "missing_count": total_missing,  # Explicitly include missing_count for frontend
            "unique_count": unique_count,
            "frequent_values": dict(sorted(value_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
            "quality_score": quality_score,
            "completeness": completeness,
            "uniqueness": uniqueness,
            "validity": validity
        }
        
        # Add numeric statistics if applicable
        if data_type in ['integer', 'float'] and numeric_values:
            try:
                numeric_array = np.array(numeric_values, dtype=float)
                profile.update({
                    "min_value": str(float(np.min(numeric_array))),
                    "max_value": str(float(np.max(numeric_array))),
                    "mean_value": float(np.mean(numeric_array)),
                    "median_value": float(np.median(numeric_array)),
                    "std_dev": float(np.std(numeric_array))
                })
                
                # Simple outlier detection on the sample
                z_scores = np.abs(stats.zscore(numeric_array))
                outliers = numeric_array[z_scores > 3]
                if len(outliers) > 0:
                    outlier_dict = {str(float(o)): 1 for o in outliers[:5]}
                    profile["outliers"] = {"z_score": outlier_dict, "iqr": {}}
                else:
                    profile["outliers"] = {"z_score": {}, "iqr": {}}
            except Exception as e:
                logger.warning(f"Error calculating numeric statistics for {column_name}: {str(e)}")
                profile.update({
                    "min_value": None,
                    "max_value": None,
                    "mean_value": None,
                    "median_value": None,
                    "std_dev": None,
                    "outliers": {"z_score": {}, "iqr": {}}
                })
        else:
            profile.update({
                "min_value": None,
                "max_value": None,
                "mean_value": None,
                "median_value": None,
                "std_dev": None,
                "outliers": {"z_score": {}, "iqr": {}}
            })
        
        return profile

    def profile_column(self, column_name: str) -> Dict:
        """
        Profile a specific column in the DataFrame.
        Returns a dictionary with column statistics and metrics.
        """
        series = self.df[column_name]
        
        # Use cached data type instead of detecting it multiple times
        data_type = self.column_data_types[column_name]
        
        # Check if this is a potentially numeric column based on data type or content
        is_potential_numeric = data_type in ['integer', 'float']
        
        # Only perform additional checks if not already identified as numeric by data type
        if not is_potential_numeric and not series.empty:
            # Sample up to 10 non-null values to check if they appear to be numeric
            sample_values = series.dropna().head(10).astype(str)
            if not sample_values.empty:
                # Check if all sampled values could be numeric
                # A truly numeric column should have values that are mostly convertible to numbers
                # Text with numbers like "Factory 1" should not match this pattern
                numeric_pattern = r'^[-+]?[0-9]*\.?[0-9]+$'
                is_potential_numeric = (sample_values.str.match(numeric_pattern).mean() > 0.5)
                
                logger.debug(f"Column {column_name}: Sampled {len(sample_values)} values, {is_potential_numeric=}")
                
                # If type is string but appears numeric, log for visibility
                if is_potential_numeric:
                    logger.info(f"Column {column_name} has string data type but appears to contain numeric values")
                elif data_type == 'string' and is_potential_numeric:
                    logger.info(f"Column {column_name} detected as not numeric despite having numeric data type")
        
        
        # Identify empty strings and common placeholder values for ALL column types
        empty_string_count = 0
        placeholder_count = 0
        has_empty_string = False
        non_null_series = series.dropna()
        
        if len(non_null_series) > 0:
            # Enhanced check for empty strings and whitespace-only strings
            # Convert to string first to handle any data type
            str_series = non_null_series.astype(str)
            
            # Check for completely empty strings or strings with only whitespace
            empty_string_mask = (str_series.str.strip() == "")
            empty_string_count = empty_string_mask.sum()
            
            # Also check for strings that are just spaces, tabs, or other whitespace characters
            whitespace_only_mask = str_series.str.match(r'^\s+$')
            whitespace_count = whitespace_only_mask.sum()
            
            # Combine both counts
            empty_string_count += whitespace_count
            has_empty_string = empty_string_count > 0
            
            if empty_string_count > 0:
                logger.info(f"Column {column_name}: Detected {empty_string_count} empty or whitespace-only values")

            
            # Check for common placeholder values that indicate missing data
            # Case-insensitive check for common placeholder strings like 'n/a', 'NA', 'NULL', etc.
            placeholder_values = ['n/a', 'na', 'null', 'none', 'missing', '?', '-']
            
            # Convert to lowercase for case-insensitive comparison
            str_series = non_null_series.astype(str).str.lower().str.strip()
            
            # Create mask for placeholder values
            placeholder_mask = str_series.isin(placeholder_values)
            placeholder_count = placeholder_mask.sum()
            
            if placeholder_count > 0:
                logger.info(f"Column {column_name}: Detected {placeholder_count} values matching common placeholder patterns like 'n/a'")
        
        
        # Enhanced missing value detection for potentially numeric columns
        numeric_conversion_nan_count = 0
        numeric_series = series
        is_numeric = pd.api.types.is_numeric_dtype(series)
        
        if is_potential_numeric:
            try:
                # Convert to numeric to detect additional missing values
                numeric_series = pd.to_numeric(series, errors='coerce')
                numeric_conversion_nan_count = numeric_series.isna().sum()
                
                # Log more detailed information about missing values detection
                logger.info(f"Column {column_name}: Original null count={series.isnull().sum()}, empty strings={empty_string_count}, numeric conversion NaN count={numeric_conversion_nan_count}")
                
                # Log only if we find additional missing values
                additional_missing = numeric_conversion_nan_count - (series.isnull().sum() + empty_string_count)
                if additional_missing > 0:
                    logger.info(f"Column {column_name}: Detected {additional_missing} additional missing values after numeric conversion")
            except Exception as e:
                logger.error(f"Error in numeric conversion for column {column_name}: {str(e)}")
                numeric_conversion_nan_count = 0
        
        # Calculate quality metrics - include empty strings and placeholder values as missing values for all column types
        total_missing = series.isnull().sum() + empty_string_count + placeholder_count
        
        if placeholder_count > 0:
            logger.info(f"Column {column_name}: Including {placeholder_count} placeholder values in total missing count (new total: {total_missing})")
        
        
        # For potentially numeric columns, use the higher of calculated missing counts
        # This ensures we catch non-numeric entries in numeric columns
        original_missing = total_missing
        
        # ONLY use numeric conversion for truly numeric columns to avoid misclassifying text with numbers as missing
        if is_potential_numeric and numeric_conversion_nan_count > total_missing:
            # Extra validation: If the difference is extremely large (>90% of total rows), 
            # this is likely a text column being misclassified as numeric
            additional_missing = numeric_conversion_nan_count - total_missing
            total_rows = len(series)
            if additional_missing > (0.9 * total_rows):
                logger.warning(f"Column {column_name}: Rejecting numeric conversion due to excessive missing values. "
                             f"This appears to be a text column with numbers rather than a true numeric column. "
                             f"Missing: {total_missing}, Numeric conversion missing: {numeric_conversion_nan_count}, Total rows: {total_rows}")
            else:
                logger.info(f"Column {column_name}: Using numeric conversion missing count={numeric_conversion_nan_count} "
                          f"instead of standard missing count={total_missing}")
                total_missing = numeric_conversion_nan_count
            
        # Log the final decision on missing count
        if original_missing != total_missing:
            logger.info(f"Column {column_name}: FINAL missing count={total_missing} (updated from {original_missing})")
        else:
            logger.debug(f"Column {column_name}: FINAL missing count={total_missing} (unchanged)")
        
        
        # Calculate completeness based on total missing values
        completeness = float(1 - (total_missing / len(series))) if len(series) > 0 else 0.0
        
        # Calculate uniqueness (ratio of unique values to total values)
        uniqueness = float(series.nunique() / len(series)) if len(series) > 0 else 0.0
        
        # Calculate validity based on data type and patterns
        validity = self._calculate_validity(series)
        
        # Calculate overall quality score for this column
        quality_score = self._calculate_column_quality_score(completeness, uniqueness, validity)
        
        # Calculate unique count excluding nulls and empty strings if present
        unique_count = series.nunique()
        if has_empty_string and "" in series.dropna().unique():
            unique_count -= 1  # Subtract 1 for the empty string
        
        profile = {
            "column_name": column_name,
            "data_type": data_type,  # Use cached data type
            "count": len(series) - total_missing,  # Count of valid values using our enhanced missing detection
            "null_count": series.isnull().sum(),
            "missing_count": total_missing,  # Explicitly include the missing_count for the frontend
            "unique_count": unique_count,  # Unique count excluding empty strings
            "frequent_values": self._get_frequent_values(series),
            "invalid_values": self._get_invalid_values(series, data_type),  # Use cached data type
            "patterns": self._detect_patterns(series),
            # Add quality metrics
            "quality_score": quality_score,
            "completeness": completeness,
            "uniqueness": uniqueness,
            "validity": validity
        }

        # Add outliers for numeric columns
        if data_type in ['integer', 'float']:
            profile["outliers"] = self._detect_outliers(series)
        else:
            profile["outliers"] = {"z_score": {}, "iqr": {}}
            
        # Add enhanced debug logging to track missing values detection
        if total_missing > 0:
            logger.debug(f"Column {column_name}: Final profile - missing_count={total_missing}, count={len(series) - total_missing}")
            if is_potential_numeric and numeric_conversion_nan_count > 0:
                logger.debug(f"Column {column_name}: Numeric conversion helped identify {numeric_conversion_nan_count - series.isnull().sum()} additional missing values")
            logger.debug(f"Column {column_name} completeness: {completeness}")
        
        # Numeric statistics using already converted numeric_series if available
        if is_numeric or (is_potential_numeric and numeric_conversion_nan_count > 0):
            try:
                non_null_numeric = numeric_series.dropna()
                if len(non_null_numeric) > 0:
                    profile.update({
                        "min_value": str(float(non_null_numeric.min())) if not pd.isna(non_null_numeric.min()) else None,
                        "max_value": str(float(non_null_numeric.max())) if not pd.isna(non_null_numeric.max()) else None,
                        "mean_value": float(non_null_numeric.mean()) if not pd.isna(non_null_numeric.mean()) else None,
                        "median_value": float(non_null_numeric.median()) if not pd.isna(non_null_numeric.median()) else None,
                        "std_dev": float(non_null_numeric.std()) if len(non_null_numeric) > 1 and not pd.isna(non_null_numeric.std()) else 0.0,
                    })
            except Exception as e:
                logger.debug(f"Error calculating numeric statistics for {column_name}: {str(e)}")
                profile.update({
                    "min_value": None,
                    "max_value": None,
                    "mean_value": None,
                    "median_value": None,
                    "std_dev": None,
                })
        else:
            profile.update({
                "min_value": None,
                "max_value": None,
                "mean_value": None,
                "median_value": None,
                "std_dev": None,
            })

        return profile
        
    def _calculate_validity(self, series: pd.Series) -> float:
        """
        Calculate the validity score for a column based on its data type and values.
        Returns a float between 0.0 and 1.0.
        """
        if series.empty:
            return 0.0
            
        # Remove nulls for validity calculation
        clean_series = series.dropna()
        if clean_series.empty:
            return 0.0
            
        # Use cached data type if available, otherwise detect it
        if hasattr(self, 'column_data_types') and series.name in self.column_data_types:
            data_type = self.column_data_types[series.name]
        else:
            data_type = self._detect_data_type(series)
        
        # For numeric types, check for outliers
        if data_type in ['integer', 'float']:
            try:
                # Count outliers (Z-score > 3)
                z_scores = np.abs(stats.zscore(clean_series))
                outlier_count = (z_scores > 3).sum()
                outlier_ratio = outlier_count / len(clean_series)
                # Higher outlier ratio means lower validity
                return float(1.0 - min(outlier_ratio, 0.5) * 2)  # Scale outlier impact
            except:
                return 0.8  # Default if calculation fails
                
        # For dates, check if they can be parsed
        elif data_type == 'date':
            try:
                # Try multiple date formats, starting with DD-MM-YYYY
                try_formats = [
                    '%d-%m-%Y',  # DD-MM-YYYY
                    '%d/%m/%Y',  # DD/MM/YYYY
                    '%Y-%m-%d',  # ISO format
                    '%m-%d-%Y',  # US format
                    '%m/%d/%Y',  # US format with slashes
                ]
                
                # Try each format and use the one that works best
                best_format = None
                best_success_rate = 0
                
                for date_format in try_formats:
                    try:
                        # Try to convert using this specific format
                        converted = pd.to_datetime(clean_series, format=date_format, errors='coerce')
                        success_rate = converted.notna().mean()
                        
                        # If this format works better than previous ones, keep it
                        if success_rate > best_success_rate:
                            best_success_rate = success_rate
                            best_format = date_format
                            
                        # If we get a very high success rate, no need to try other formats
                        if success_rate > 0.9:
                            break
                    except:
                        continue
                
                # If we found a good format, use it, otherwise fall back to the default parser
                if best_format and best_success_rate > 0:
                    return float(best_success_rate)
                else:
                    # Fallback to default parser with dayfirst=True for DD-MM-YYYY preference
                    converted = pd.to_datetime(clean_series, dayfirst=True, errors='coerce')
                    return float(converted.notna().mean())
            except:
                return 0.5
                
        # For emails, check against regex pattern
        elif data_type == 'email':
            valid_emails = clean_series.str.match(r'^[\w\.-]+@[\w\.-]+\.\w+$')
            return float(valid_emails.mean())
            
        # For phone numbers, check against regex pattern
        elif data_type == 'phone':
            valid_phones = clean_series.str.match(r'^\+?[\d\s-]{10,}$')
            return float(valid_phones.mean())
            
        # For UUIDs, check against regex pattern
        elif data_type == 'uuid':
            valid_uuids = clean_series.str.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$', case=False)
            return float(valid_uuids.mean())
            
        # For postal codes, check against regex pattern
        elif data_type == 'postal_code':
            valid_postal = clean_series.str.match(r'^(?!(?:[0-9]{1,3}|No|Yes|NA|N\/A)$)[A-Z0-9]{2,10}(-[A-Z0-9]{2,10})?$', case=False)
            return float(valid_postal.mean())
            
        # For strings, check for extreme values like very long strings
        elif data_type == 'string':
            # Check for strings that are unreasonably long
            str_lengths = clean_series.astype(str).str.len()
            avg_length = str_lengths.mean()
            std_length = str_lengths.std() if len(clean_series) > 1 else 0
            # If standard deviation is 0, all strings are same length
            if std_length == 0:
                return 1.0
            # Check for strings that are more than 3 std devs away from mean
            extreme_values = (np.abs(str_lengths - avg_length) > (3 * std_length)).sum()
            return float(1.0 - (extreme_values / len(clean_series)))
            
        # Default case
        return 0.9  # Default for other types
        
    def _calculate_column_quality_score(self, completeness: float, uniqueness: float, validity: float) -> float:
        """
        Calculate overall quality score for a column, weighted by importance of different metrics.
        Returns a float between 0.0 and 1.0.
        """
        # Weights for different components (add up to 1.0)
        completeness_weight = 0.5  # Completeness is most important
        validity_weight = 0.48     # Validity is equally important
        uniqueness_weight = 0.02   # Uniqueness is less important (some columns should have low uniqueness)
        
        # Calculate weighted score
        score = (completeness * completeness_weight + 
                 validity * validity_weight + 
                 uniqueness * uniqueness_weight)
                 
        return float(score)

    def _detect_data_type(self, series: pd.Series) -> str:
        if series.dtype == 'object':
            # Check for date
            try:
                pd.to_datetime(series.dropna().iloc[0])
                return 'date'
            except:
                pass
            
            # Check for email
            valid_emails = series.dropna().str.match(r'^[\w\.-]+@[\w\.-]+\.\w+$')
            if valid_emails.mean() > 0.5:  # If more than 50% match email pattern
                return 'email'
            
            # Check for phone
            valid_phones = series.dropna().str.match(r'^\+?[\d\s-]{10,}$')
            if valid_phones.mean() > 0.5:  # If more than 50% match phone pattern
                return 'phone'
                
            # Check for UUID
            valid_uuids = series.dropna().str.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$', case=False)
            if valid_uuids.mean() > 0.5:  # If more than 50% match UUID pattern
                return 'uuid'
                
            # Check for postal code (supporting various formats from different countries)
            # This regex covers common postal code formats from US, UK, Canada, and many other countries
            # Enhanced to ignore simple 2-3 digit numbers and common words like "No", "Yes"
            valid_postal = series.dropna().str.match(r'^(?!(?:[0-9]{1,3}|No|Yes|NA|N\/A)$)[A-Z0-9]{2,10}(-[A-Z0-9]{2,10})?$', case=False)
            if valid_postal.mean() > 0.5 and len(series.dropna().unique()) > 3:  # Require more than 3 unique values for a postal code column
                return 'postal_code'
            
            # Check for numeric strings
            try:
                numeric_series = pd.to_numeric(series.dropna(), errors='coerce')
                # If at least 80% of non-null values can be converted to numeric, consider it numeric
                if numeric_series.notna().mean() >= 0.8:
                    # Check if all values are integers
                    if all(float(x).is_integer() for x in numeric_series.dropna()):
                        return 'integer'
                    else:
                        return 'float'
            except:
                pass
            
            return 'string'
        
        elif pd.api.types.is_integer_dtype(series):
            return 'integer'
        elif pd.api.types.is_float_dtype(series):
            return 'float'
        else:
            return str(series.dtype)

    def _get_frequent_values(self, series: pd.Series) -> Dict:
        value_counts = series.value_counts().head(10).to_dict()
        return {str(k): int(v) for k, v in value_counts.items()}

    def _get_invalid_values(self, series: pd.Series, data_type: str) -> Dict:
        """
        Identify and return invalid values for special data types.
        Returns a dictionary with invalid values and their counts.
        """
        # Skip if not a special data type or series is empty
        if data_type not in ['email', 'phone', 'uuid', 'postal_code'] or series.empty:
            return {}
            
        # Drop null values for validation
        clean_series = series.dropna()
        if clean_series.empty:
            return {}
            
        # Apply appropriate validation based on data type
        valid_mask = None
        if data_type == 'email':
            valid_mask = clean_series.str.match(r'^[\w\.-]+@[\w\.-]+\.\w+$')
        elif data_type == 'phone':
            valid_mask = clean_series.str.match(r'^\+?[\d\s-]{10,}$')
        elif data_type == 'uuid':
            valid_mask = clean_series.str.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$', case=False)
        elif data_type == 'postal_code':
            valid_mask = clean_series.str.match(r'^(?!(?:[0-9]{1,3}|No|Yes|NA|N\/A)$)[A-Z0-9]{2,10}(-[A-Z0-9]{2,10})?$', case=False)
            
        # If validation couldn't be applied, return empty dict
        if valid_mask is None:
            return {}
            
        # Get invalid values
        invalid_series = clean_series[~valid_mask]
        if invalid_series.empty:
            return {}
            
        # Count invalid values (limit to 3 most frequent)
        invalid_counts = invalid_series.value_counts().head(3).to_dict()
        return {str(k): int(v) for k, v in invalid_counts.items()}

    def _detect_patterns(self, series: pd.Series) -> Dict:
        # Convert NumPy bool_ to Python native bool to avoid JSON serialization issues
        patterns = {
            "has_nulls": bool(series.isnull().any()),
            "completeness": float(1 - (series.isnull().sum() / len(series)))
        }

        if pd.api.types.is_numeric_dtype(series):
            patterns["outliers"] = self._detect_outliers(series)

        return patterns

    def _detect_outliers(self, series: pd.Series) -> Dict:
        """
        Detect outliers in a numeric series using both Z-score and IQR methods.
        Returns a dictionary with outlier values and their counts.
        """
        if not pd.api.types.is_numeric_dtype(series) or series.empty:
            return {"z_score": {}, "iqr": {}}
            
        # Drop null values for outlier detection
        clean_series = series.dropna()
        if len(clean_series) < 4:  # Need reasonable sample size for outlier detection
            return {"z_score": {}, "iqr": {}}
            
        outliers = {"z_score": {}, "iqr": {}}
        
        # Z-score method (values beyond 3 standard deviations)
        try:
            mean = clean_series.mean()
            std = clean_series.std()
            if std > 0:  # Avoid division by zero
                z_scores = np.abs(stats.zscore(clean_series))
                z_outliers = clean_series[z_scores > 3]
                if not z_outliers.empty:
                    # Get top outlier values with their counts
                    outlier_counts = z_outliers.value_counts().head(3).to_dict()
                    outliers["z_score"] = {str(k): int(v) for k, v in outlier_counts.items()}
        except Exception as e:
            # Log error and continue with other methods
            print(f"Error in Z-score outlier detection: {str(e)}")
            
        # IQR method (values beyond 1.5 * IQR from Q1/Q3)
        try:
            q1 = clean_series.quantile(0.25)
            q3 = clean_series.quantile(0.75)
            iqr = q3 - q1
            lower_bound = q1 - (1.5 * iqr)
            upper_bound = q3 + (1.5 * iqr)
            iqr_outliers = clean_series[(clean_series < lower_bound) | (clean_series > upper_bound)]
            if not iqr_outliers.empty:
                # Get top outlier values with their counts
                outlier_counts = iqr_outliers.value_counts().head(3).to_dict()
                outliers["iqr"] = {str(k): int(v) for k, v in outlier_counts.items()}
        except Exception as e:
            # Log error and continue
            print(f"Error in IQR outlier detection: {str(e)}")
            
        return outliers

    def calculate_data_quality_score(self) -> float:
        column_quality_scores = []
        
        # Get the quality score for each column that was already computed in profile_column
        for column in self.df.columns:
            profile = self.profile_column(column)
            column_quality_scores.append(profile["quality_score"])
        
        # Calculate the mean of all column quality scores
        if column_quality_scores:
            return float(np.mean(column_quality_scores))
        else:
            return 0.0


    def detect_exact_duplicates(self, sample_size: int = 100000) -> Dict:
        """Detect exact duplicate rows in the DataFrame.
        
        For large DataFrames, this uses sampling to avoid memory issues.
        
        Args:
            sample_size: Maximum number of rows to sample for duplicate detection
            
        Returns:
            Dictionary with count of duplicates and sample values
        """
        start_time = time.time()
        logger.info(f"Starting exact duplicate detection on {self.total_rows} rows")
        """
        Detect exact duplicates across all columns in the DataFrame.
        Returns a dictionary with duplicate counts and their values.
        """
        # For all datasets, use a sample to avoid excessive computation
        # For large datasets, use an even smaller sample
        if self.total_rows > 10000:
            sample_size = min(sample_size, 1000)  # Cap at 1000 for very large datasets
            
        # Sample rows for fuzzy matching
        df_sample = self.df.sample(min(sample_size, self.total_rows))
        
        # Find duplicates in the sample
        duplicates = df_sample[df_sample.duplicated(keep='first')]
        # Scale up the count based on sampling ratio
        scaling_factor = self.total_rows / len(df_sample)
        duplicate_count = int(len(duplicates) * scaling_factor)
        logger.info(f"Found {len(duplicates)} duplicates in sample, estimated {duplicate_count} in full dataset")
        
        # Store only a reasonable number of examples and ensure all values are JSON serializable
        duplicate_values = []
        for record in duplicates.head(10).to_dict(orient='records'):
            # Convert each value to a JSON serializable format
            serialized_record = {k: json_serializable(v) for k, v in record.items()}
            duplicate_values.append(serialized_record)
        
        duration = time.time() - start_time
        logger.info(f"Exact duplicate detection completed in {duration:.2f} seconds")
        
        return {
            "count": duplicate_count,
            "values": duplicate_values
        }

    def detect_fuzzy_duplicates(self, threshold: float = 0.95, max_rows: int = 1000) -> Dict:
        """Detect fuzzy duplicate rows in the DataFrame.
        
        For large DataFrames, this uses aggressive sampling to avoid memory issues.
        
        Args:
            threshold: Similarity threshold (0.0-1.0), higher means more similar
            max_rows: Maximum number of rows to process for performance
            
        Returns:
            Dictionary with count of fuzzy duplicates and sample values
        """
        start_time = time.time()
        logger.info(f"Starting fuzzy duplicate detection with threshold {threshold}")
        
        # This is a performance optimization to make the feature usable
        # Only examine a sample of rows for fuzzy duplicates
        sample_size = min(max_rows, len(self.df))
        if sample_size < len(self.df):
            df_sample = self.df.sample(sample_size)
        else:
            df_sample = self.df
            
        # Only use string columns for fuzzy matching
        string_cols = [col for col in df_sample.columns 
                      if df_sample[col].dtype == 'object' 
                      and df_sample[col].map(lambda x: isinstance(x, str)).sum() > 0]
        
        # Identify potential date columns
        date_cols = []
        for col in df_sample.columns:
            # Skip already identified string columns
            if col in string_cols:
                continue
                
            # Check if column is datetime type
            if pd.api.types.is_datetime64_any_dtype(df_sample[col]):
                date_cols.append(col)
                continue
                
            # Check if string column contains date-like strings
            if df_sample[col].dtype == 'object':
                # Sample the column to check for date patterns
                sample_vals = df_sample[col].dropna().head(10)
                date_patterns = 0
                
                for val in sample_vals:
                    if not isinstance(val, str):
                        continue
                        
                    # Check for common date patterns
                    # YYYY-MM-DD or MM/DD/YYYY or DD-MM-YYYY
                    if (re.search(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}', val) or
                        re.search(r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}', val)):
                        date_patterns += 1
                
                # If more than half the samples have date patterns, consider it a date column
                if date_patterns > len(sample_vals) / 2:
                    date_cols.append(col)
        
        # If no string columns and no date columns, return empty result
        if not string_cols and not date_cols:
            return {"count": 0, "values": []}
        
        # Focus on columns that are most likely to contain identifying information
        # These are typically columns with medium cardinality (not too unique, not too repetitive)
        col_weights = {}
        
        # Weight string columns
        for col in string_cols:
            non_null_count = df_sample[col].count()
            if non_null_count == 0:
                continue
                
            unique_ratio = df_sample[col].nunique() / non_null_count
            # Columns with unique ratios between 0.1 and 0.8 are most informative
            # Give higher weight to columns in the sweet spot
            if 0.1 <= unique_ratio <= 0.8:
                # Assign weights based on how close to the ideal 0.5 ratio
                weight = 1.0 - abs(0.5 - unique_ratio)
                col_weights[col] = max(0.3, weight)
            else:
                # Still include other columns but with lower weight
                col_weights[col] = 0.2
        
        # Add date columns with high weight - dates are valuable for matching
        for col in date_cols:
            col_weights[col] = 0.8  # Date columns get high weight
        
        # Sort columns by weight
        weighted_cols = sorted(col_weights.items(), key=lambda x: x[1], reverse=True)
        
        # Build inverted index for faster candidate selection
        # Group similar values to quickly identify potential matches
        inverted_index = {}
        for col, weight in weighted_cols[:5]:  # Focus on top 5 weighted columns
            # Skip if all values are null
            if df_sample[col].isna().all():
                continue
                
            for idx, val in df_sample[col].items():
                if pd.isna(val) or not isinstance(val, str) or len(val) < 3:
                    continue
                
                # For each value, add multiple keys:
                # 1. First 3 characters
                # 2. Last 3 characters if string is longer than 5 chars
                # 3. Some characters from the middle for longer strings
                keys = [str(val).lower()[:3]]
                
                if len(val) > 5:
                    keys.append(str(val).lower()[-3:])
                
                if len(val) > 10:
                    keys.append(str(val).lower()[len(val)//2-1:len(val)//2+2])
                
                for key in keys:
                    if key not in inverted_index:
                        inverted_index[key] = set()
                    inverted_index[key].add(idx)
        
        # Find candidate pairs using the inverted index
        candidate_pairs = set()
        for indices in inverted_index.values():
            if len(indices) > 1:
                indices = list(indices)
                for i in range(len(indices)):
                    for j in range(i+1, len(indices)):
                        candidate_pairs.add((min(indices[i], indices[j]), max(indices[i], indices[j])))
        
        # Calculate similarity for candidate pairs
        fuzzy_groups = []
        processed_indices = set()
        
        for idx1, idx2 in candidate_pairs:
            if idx1 in processed_indices or idx2 in processed_indices:
                continue
            
            # Calculate weighted column-level similarity
            total_weight = 0
            weighted_similarity = 0
            
            for col, weight in weighted_cols:
                val1 = df_sample.loc[idx1, col]
                val2 = df_sample.loc[idx2, col]
                
                # Skip if either value is NaN
                if pd.isna(val1) or pd.isna(val2):
                    continue
                
                # Handle date columns specially
                if col in date_cols:
                    try:
                        # Convert to datetime if needed
                        if not pd.api.types.is_datetime64_any_dtype(val1):
                            val1 = pd.to_datetime(val1, errors='coerce')
                        if not pd.api.types.is_datetime64_any_dtype(val2):
                            val2 = pd.to_datetime(val2, errors='coerce')
                        
                        # Skip if conversion failed
                        if pd.isna(val1) or pd.isna(val2):
                            continue
                        
                        # Calculate date similarity - closer dates are more similar
                        # Get days difference between dates
                        days_diff = abs((val1 - val2).total_seconds()) / (24 * 3600)
                        
                        # If dates are more than 00 days (approximately 6 months) apart,
                        # they are very likely unrelated records - consider this a blocking factor
                        if days_diff > 90:
                            # Add a strong negative signal for dates too far apart
                            weighted_similarity -= 5.0  # Strong penalty
                            total_weight += 1.0  # Still count this in total weight
                            continue  # Skip further processing for this column
                        
                        # Convert to similarity score:
                        # - Exact match: 1.0
                        # - Within 1 day: 0.9
                        # - Within 1 week: 0.7
                        # - Beyond 7 days under 6 months: small positive
                        if days_diff == 0:
                            similarity = 1.0
                        elif days_diff <= 1:
                            similarity = 0.5
                        elif days_diff <= 7:
                            similarity = 0.3
                        else:
                            similarity = 0.1  # Small positive for 90-180 days
                        
                        # Date columns get additional weight - they're critical for matching
                        weighted_similarity += similarity * weight * 2.0  # Double importance of dates
                        total_weight += weight * 2.0  # Adjust total weight accordingly
                    except Exception:
                        # Skip on error
                        continue
                # Skip if not a string for string columns
                elif col in string_cols:
                    if (not isinstance(val1, str) or not isinstance(val2, str) or
                        len(val1) < 2 or len(val2) < 2):
                        continue
                    
                    try:
                        # Use jaro_winkler for short to medium strings, and a faster
                        # approach for very long strings
                        if len(val1) < 100 and len(val2) < 100:
                            similarity = jellyfish.jaro_winkler_similarity(val1.lower(), val2.lower())
                        else:
                            # For long strings, check n-gram overlap
                            ngrams1 = set(val1.lower()[i:i+3] for i in range(len(val1)-2))
                            ngrams2 = set(val2.lower()[i:i+3] for i in range(len(val2)-2))
                            
                            if len(ngrams1) == 0 or len(ngrams2) == 0:
                                continue
                                
                            overlap = len(ngrams1.intersection(ngrams2))
                            similarity = overlap / max(len(ngrams1), len(ngrams2))
                        
                        weighted_similarity += similarity * weight
                        total_weight += weight
                    except Exception:
                        # Skip on error
                        continue
                # For numeric columns, compare based on relative difference
                elif pd.api.types.is_numeric_dtype(df_sample[col]):
                    try:
                        # Convert to float for comparison
                        num1 = float(val1)
                        num2 = float(val2)
                        
                        # Skip if either is not a valid number
                        if math.isnan(num1) or math.isnan(num2):
                            continue
                        
                        # Calculate similarity based on relative difference
                        max_val = max(abs(num1), abs(num2))
                        if max_val == 0:  # Both values are 0
                            similarity = 1.0
                        else:
                            rel_diff = abs(num1 - num2) / max_val
                            # Convert difference to similarity score
                            # Closer to 0 difference = closer to 1.0 similarity
                            similarity = max(0, 1.0 - min(rel_diff, 1.0))
                        
                        weighted_similarity += similarity * weight
                        total_weight += weight
                    except Exception:
                        # Skip on error
                        continue
            # If we couldn't compare any columns, skip
            if total_weight == 0:
                continue
                
            # Calculate final similarity
            final_similarity = weighted_similarity / total_weight
            
            # If similarity exceeds threshold, create a fuzzy match group
            if final_similarity >= threshold:
                # Check if either of these rows is already in a group
                existing_group = None
                for group in fuzzy_groups:
                    row_indices = {row.get('__index__') for row in group['sample'] if '__index__' in row}
                    if idx1 in row_indices or idx2 in row_indices:
                        existing_group = group
                        break
                
                # Add the row data with the index for tracking and ensure all values are JSON serializable
                row1_dict = {k: json_serializable(v) for k, v in df_sample.loc[idx1].to_dict().items()}
                row1_dict['__index__'] = idx1
                row2_dict = {k: json_serializable(v) for k, v in df_sample.loc[idx2].to_dict().items()}
                row2_dict['__index__'] = idx2
                
                if existing_group:
                    # Add to existing group if not already in it
                    existing_indices = {row.get('__index__') for row in existing_group['sample'] if '__index__' in row}
                    
                    if idx1 not in existing_indices:
                        existing_group['sample'].append(row1_dict)
                        existing_group['count'] += 1
                        processed_indices.add(idx1)
                        
                    if idx2 not in existing_indices:
                        existing_group['sample'].append(row2_dict)
                        existing_group['count'] += 1
                        processed_indices.add(idx2)
                else:
                    # Create new group
                    group = {
                        'group_id': len(fuzzy_groups),
                        'count': 2,
                        'similarity': round(final_similarity * 100),
                        'sample': [row1_dict, row2_dict]
                    }
                    fuzzy_groups.append(group)
                    processed_indices.add(idx1)
                    processed_indices.add(idx2)
                    
                # Limit the number of groups
                if len(fuzzy_groups) >= 10:
                    break
        
        # Clean up the output by removing the temporary index field
        for group in fuzzy_groups:
            for sample in group['sample']:
                if '__index__' in sample:
                    del sample['__index__']
        
        # Calculate total count of fuzzy duplicates and sort groups by count
        total_count = sum(group['count'] - 1 for group in fuzzy_groups)
        fuzzy_groups.sort(key=lambda g: g['count'], reverse=True)
        
        # Log execution time
        duration = time.time() - start_time
        logger.info(f"Fuzzy duplicate detection completed in {duration:.2f} seconds, found {total_count} potential duplicates")
        
        # Force garbage collection to free memory
        gc.collect()
        
        return {
            "count": total_count,
            "values": fuzzy_groups[:5]  # Only return up to 5 groups
        }
