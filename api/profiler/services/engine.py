import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import re
from datetime import datetime
import jellyfish  # For fuzzy string matching
from collections import defaultdict
import uuid
from scipy import stats  # Import scipy.stats properly
import math

class DataProfiler:
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.total_rows = len(df)
        self.total_columns = len(df.columns)
        # Cache data types to avoid repeated detection
        self.column_data_types = {}
        # Pre-compute data types for all columns
        for col in df.columns:
            self.column_data_types[col] = self._detect_data_type(df[col])

    def profile_column(self, column_name: str) -> Dict:
        """
        Profile a specific column in the DataFrame.
        Returns a dictionary with column statistics and metrics.
        """
        series = self.df[column_name]
        
        # Use cached data type instead of detecting it multiple times
        data_type = self.column_data_types[column_name]
        
        # Identify empty strings for string columns using vectorized operations
        empty_string_count = 0
        has_empty_string = False
        if data_type == "string":
            # Use vectorized string operations instead of apply+lambda
            non_null_series = series.dropna()
            if len(non_null_series) > 0:
                empty_string_mask = (non_null_series.astype(str).str.strip() == "")
                empty_string_count = empty_string_mask.sum()
                has_empty_string = empty_string_count > 0
        
        # Calculate quality metrics - include empty strings as missing values for completeness
        total_missing = series.isnull().sum() + empty_string_count
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
            "count": len(series) - series.isnull().sum() - empty_string_count,  # Count of valid values only
            "null_count": series.isnull().sum(),
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
        
        # Try to convert string columns to numeric if they contain numeric data
        numeric_series = series
        is_numeric = pd.api.types.is_numeric_dtype(series)
        
        if not is_numeric and series.dtype == 'object':
            # Try to convert string to numeric
            try:
                numeric_series = pd.to_numeric(series, errors='coerce')
                # If we have at least 80% of values that could be converted to numeric, consider it numeric
                if numeric_series.notna().mean() >= 0.8:
                    is_numeric = True
            except:
                pass

        # Numeric statistics if applicable
        if is_numeric:
            try:
                profile.update({
                    "min_value": str(numeric_series.min()) if not pd.isna(numeric_series.min()) else None,
                    "max_value": str(numeric_series.max()) if not pd.isna(numeric_series.max()) else None,
                    "mean_value": float(numeric_series.mean()) if not pd.isna(numeric_series.mean()) else None,
                    "median_value": float(numeric_series.median()) if not pd.isna(numeric_series.median()) else None,
                    "mode_value": str(numeric_series.mode().iloc[0]) if not numeric_series.empty and len(numeric_series.mode()) > 0 else None,
                    "std_dev": float(numeric_series.std()) if not pd.isna(numeric_series.std()) else None,
                })
            except:
                # Fallback if any calculation fails
                profile.update({
                    "min_value": None,
                    "max_value": None,
                    "mean_value": None,
                    "median_value": None,
                    "mode_value": None,
                    "std_dev": None,
                })
        else:
            profile.update({
                "min_value": None,
                "max_value": None,
                "mean_value": None,
                "median_value": None,
                "mode_value": None,
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

    def generate_profile(self) -> Tuple[Dict, List[Dict]]:
        column_profiles = []
        for column in self.df.columns:
            profile = self.profile_column(column)
            column_profiles.append(profile)

        quality_score = self.calculate_data_quality_score()

        return {
            "total_rows": self.total_rows,
            "total_columns": self.total_columns,
            "data_quality_score": quality_score
        }, column_profiles

    def detect_exact_duplicates(self) -> Dict:
        """
        Detect exact duplicates across all columns in the DataFrame.
        Returns a dictionary with duplicate counts and their values.
        """
        # Only process a sample if the DataFrame is large
        if len(self.df) > 10000:
            # Sample at most 10,000 rows for performance
            sample_df = self.df.sample(min(10000, len(self.df)))
            duplicates = sample_df.duplicated().sum()
            # Store only a reasonable number of examples
            duplicate_values = sample_df[sample_df.duplicated()].head(10).to_dict(orient='records')
        else:
            duplicates = self.df.duplicated().sum()
            duplicate_values = self.df[self.df.duplicated()].head(10).to_dict(orient='records')
        
        return {
            "count": duplicates,
            "values": duplicate_values
        }

    def detect_fuzzy_duplicates(self, threshold: float = 0.95, max_rows: int = 1000) -> Dict:
        """
        Detect fuzzy duplicates across string columns in the DataFrame using Jaro-Winkler similarity.
        
        Args:
            threshold: Similarity threshold (0.0-1.0), higher means more similar
            max_rows: Maximum number of rows to process for performance
            
        Returns:
            Dictionary with duplicate counts and their values
        """
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
                
                # Add the row data with the index for tracking
                row1_dict = df_sample.loc[idx1].to_dict()
                row1_dict['__index__'] = idx1
                row2_dict = df_sample.loc[idx2].to_dict()
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
        
        return {
            "count": total_count,
            "values": fuzzy_groups[:5]  # Only return up to 5 groups
        }
