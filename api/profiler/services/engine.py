import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import re
from datetime import datetime
from scipy import stats
import uuid

class DataProfiler:
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.total_rows = len(df)
        self.total_columns = len(df.columns)

    def profile_column(self, column_name: str) -> Dict:
        series = self.df[column_name]
        profile = {
            "column_name": column_name,
            "data_type": self._detect_data_type(series),
            "null_count": series.isnull().sum(),
            "unique_count": series.nunique(),
            "frequent_values": self._get_frequent_values(series),
            "patterns": self._detect_patterns(series)
        }

        # Numeric statistics if applicable
        if pd.api.types.is_numeric_dtype(series):
            profile.update({
                "min_value": str(series.min()),
                "max_value": str(series.max()),
                "mean_value": float(series.mean()),
                "median_value": float(series.median()),
                "std_dev": float(series.std()),
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

    def _detect_patterns(self, series: pd.Series) -> Dict:
        # Convert NumPy bool_ to Python native bool to avoid JSON serialization issues
        patterns = {
            "has_nulls": bool(series.isnull().any()),
            "completeness": float(1 - (series.isnull().sum() / len(series)))
        }

        if pd.api.types.is_numeric_dtype(series):
            patterns["outliers"] = self._detect_outliers(series)

        return patterns

    def _detect_outliers(self, series: pd.Series) -> List[str]:
        clean_series = series.dropna()
        if len(clean_series) < 2:  # Need at least 2 values for z-score
            return []
        z_scores = np.abs(stats.zscore(clean_series))
        outliers = clean_series[z_scores > 3]
        return [str(x) for x in outliers.head(5).tolist()]

    def calculate_data_quality_score(self) -> float:
        scores = []
        for column in self.df.columns:
            column_score = 1.0
            series = self.df[column]
            
            # Penalize for nulls
            null_ratio = series.isnull().mean()
            column_score *= (1 - null_ratio)
            
            # Penalize for high cardinality in categorical columns
            if not pd.api.types.is_numeric_dtype(series):
                unique_ratio = series.nunique() / len(series)
                if unique_ratio > 0.9:  # High cardinality
                    column_score *= 0.8
            
            scores.append(column_score)
        
        return float(np.mean(scores))

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
