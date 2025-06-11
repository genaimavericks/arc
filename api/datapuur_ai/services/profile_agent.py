"""
Profile Agent - AI-powered data profiling assistant
"""

import json
import logging
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np
from pathlib import Path

from api.gen_ai_layer.models import create_model
from api.profiler.services.engine import DataProfiler

logger = logging.getLogger(__name__)


class ProfileAgent:
    """AI agent for intelligent data profiling and analysis"""
    
    def __init__(self, model_name: Optional[str] = None):
        self.model = create_model(model_name=model_name)
        self.data_dir = Path(__file__).parent.parent.parent / "data"
        
    def analyze_profile(self, profile_data: Dict[str, Any], file_path: str) -> Dict[str, Any]:
        """Analyze profile data and generate insights"""
        try:
            # Load sample data for deeper analysis
            df = pd.read_parquet(self.data_dir / file_path, engine='pyarrow').head(1000)
            
            # Prepare context for AI analysis
            context = self._prepare_profile_context(profile_data, df)
            
            # Generate AI insights
            insights = self._generate_insights(context)
            
            # Identify data quality issues
            quality_issues = self._identify_quality_issues(profile_data, df)
            
            # Generate improvement suggestions
            suggestions = self._generate_suggestions(quality_issues, context)
            
            return {
                "summary": insights,
                "quality_issues": quality_issues,
                "suggestions": suggestions
            }
            
        except Exception as e:
            logger.error(f"Error analyzing profile: {str(e)}")
            raise
    
    def _prepare_profile_context(self, profile_data: Dict, df: pd.DataFrame) -> str:
        """Prepare context for AI analysis"""
        context = f"""
Data Profile Summary:
- Total Rows: {profile_data.get('total_rows', 0):,}
- Total Columns: {profile_data.get('total_columns', 0)}
- Data Quality Score: {profile_data.get('data_quality_score', 0):.2f}%
- Missing Values: {profile_data.get('missing_values_count', 0):,}
- Duplicate Rows: {profile_data.get('exact_duplicates_count', 0):,}

Column Details:
"""
        
        # Add column information - handle columns as a list
        columns = profile_data.get('columns', [])
        if isinstance(columns, list):
            for col_info in columns:
                if not isinstance(col_info, dict) or 'column_name' not in col_info:
                    continue
                    
                col_name = col_info.get('column_name')
                context += f"\n- {col_name}:"
                context += f"\n  Type: {col_info.get('data_type', 'unknown')}"
                context += f"\n  Missing: {col_info.get('missing_count', 0)} ({col_info.get('missing_percentage', 0):.1f}%)"
                context += f"\n  Unique: {col_info.get('unique_count', 0)}"
                
                if col_info.get('data_type') in ['int64', 'float64']:
                    context += f"\n  Mean: {col_info.get('mean', 0):.2f}"
                    context += f"\n  Std: {col_info.get('std', 0):.2f}"
        else:
            # Fallback for dictionary format (for backward compatibility)
            for col_name, col_info in columns.items():
                context += f"\n- {col_name}:"
                context += f"\n  Type: {col_info.get('data_type', 'unknown')}"
                context += f"\n  Missing: {col_info.get('missing_count', 0)} ({col_info.get('missing_percentage', 0):.1f}%)"
                context += f"\n  Unique: {col_info.get('unique_count', 0)}"
                
                if col_info.get('data_type') in ['int64', 'float64']:
                    context += f"\n  Mean: {col_info.get('mean', 0):.2f}"
                    context += f"\n  Std: {col_info.get('std', 0):.2f}"
        
        return context
    
    def _generate_insights(self, context: str) -> str:
        """Generate AI insights about the data"""
        prompt = f"""
Analyze this data profile and provide a concise summary of key findings:

{context}

Provide:
1. Overview of data characteristics
2. Notable patterns or anomalies
3. Data quality assessment
4. Potential use cases for this data

Keep the response concise and actionable.
"""
        
        response = self.model.chat(
            messages=[{"role": "user", "content": prompt}],
            system_message="You are a data analysis expert helping users understand their data."
        )
        
        return response.content
    
    def _identify_quality_issues(self, profile_data: Dict, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Identify data quality issues"""
        issues = []
        
        # Check for high missing values - handle columns as a list
        columns = profile_data.get('columns', [])
        if isinstance(columns, list):
            for col_info in columns:
                if not isinstance(col_info, dict) or 'column_name' not in col_info:
                    continue
                    
                col_name = col_info.get('column_name')
                missing_pct = col_info.get('missing_percentage', 0)
                if missing_pct > 20:
                    issues.append({
                        "type": "high_missing_values",
                        "severity": "high" if missing_pct > 50 else "medium",
                        "column": col_name,
                        "details": f"{missing_pct:.1f}% missing values",
                        "impact": "May affect analysis accuracy"
                    })
        else:
            # Fallback for dictionary format
            for col_name, col_info in columns.items():
                missing_pct = col_info.get('missing_percentage', 0)
                if missing_pct > 20:
                    issues.append({
                        "type": "high_missing_values",
                        "severity": "high" if missing_pct > 50 else "medium",
                        "column": col_name,
                        "details": f"{missing_pct:.1f}% missing values",
                        "impact": "May affect analysis accuracy"
                    })
        
        # Check for duplicates
        dup_count = profile_data.get('exact_duplicates_count', 0)
        if dup_count > 0:
            dup_pct = (dup_count / profile_data.get('total_rows', 1)) * 100
            issues.append({
                "type": "duplicate_rows",
                "severity": "high" if dup_pct > 10 else "medium",
                "details": f"{dup_count:,} duplicate rows ({dup_pct:.1f}%)",
                "impact": "May skew analysis results"
            })
        
        # Check for potential outliers in numeric columns - handle columns as a list
        if isinstance(columns, list):
            for col_info in columns:
                if not isinstance(col_info, dict) or 'column_name' not in col_info:
                    continue
                
                col_name = col_info.get('column_name')
                if col_info.get('data_type') in ['int64', 'float64']:
                    if 'outliers' in col_info and col_info['outliers'].get('count', 0) > 0:
                        outlier_pct = (col_info['outliers']['count'] / profile_data.get('total_rows', 1)) * 100
                        if outlier_pct > 1:
                            issues.append({
                                "type": "outliers",
                                "severity": "medium",
                                "column": col_name,
                                "details": f"{col_info['outliers']['count']:,} outliers ({outlier_pct:.1f}%)",
                                "impact": "May indicate data entry errors or legitimate edge cases"
                            })
        else:
            # Fallback for dictionary format
            for col_name, col_info in columns.items():
                if col_info.get('data_type') in ['int64', 'float64']:
                    if 'outliers' in col_info and col_info['outliers'].get('count', 0) > 0:
                        outlier_pct = (col_info['outliers']['count'] / profile_data.get('total_rows', 1)) * 100
                        if outlier_pct > 1:
                            issues.append({
                                "type": "outliers",
                                "severity": "medium",
                                "column": col_name,
                                "details": f"{col_info['outliers']['count']:,} outliers ({outlier_pct:.1f}%)",
                                "impact": "May indicate data entry errors or legitimate edge cases"
                            })
        
        return issues
    
    def _generate_suggestions(self, issues: List[Dict], context: str) -> List[Dict[str, Any]]:
        """Generate improvement suggestions based on issues"""
        if not issues:
            return [{
                "type": "general",
                "suggestion": "Data appears to be of good quality. Consider creating data validation rules to maintain quality.",
                "priority": "low"
            }]
        
        # Create issue summary for AI
        issue_summary = "\n".join([
            f"- {issue['type']}: {issue['details']}" 
            for issue in issues
        ])
        
        prompt = f"""
Based on these data quality issues:
{issue_summary}

And this data context:
{context}

Suggest 3-5 specific, actionable improvements for this dataset. For each suggestion:
1. Describe the improvement
2. Explain the expected benefit
3. Suggest implementation approach

Format as JSON array with fields: type, suggestion, benefit, approach, priority (high/medium/low)
"""
        
        response = self.model.chat(
            messages=[{"role": "user", "content": prompt}],
            system_message="You are a data quality expert. Provide practical suggestions in valid JSON format."
        )
        
        try:
            suggestions = json.loads(response.content)
            if isinstance(suggestions, list):
                return suggestions
        except:
            pass
        
        # Fallback suggestions
        suggestions = []
        
        for issue in issues[:3]:  # Top 3 issues
            if issue['type'] == 'high_missing_values':
                suggestions.append({
                    "type": "missing_values",
                    "suggestion": f"Handle missing values in column '{issue.get('column', 'unknown')}'",
                    "benefit": "Improve data completeness and analysis accuracy",
                    "approach": "Consider imputation, removal, or creating a missing indicator variable",
                    "priority": issue['severity']
                })
            elif issue['type'] == 'duplicate_rows':
                suggestions.append({
                    "type": "duplicates",
                    "suggestion": "Remove or consolidate duplicate rows",
                    "benefit": "Ensure data uniqueness and prevent biased analysis",
                    "approach": "Identify duplicate criteria and decide on deduplication strategy",
                    "priority": issue['severity']
                })
            elif issue['type'] == 'outliers':
                suggestions.append({
                    "type": "outliers",
                    "suggestion": f"Investigate outliers in column '{issue.get('column', 'unknown')}'",
                    "benefit": "Improve data reliability and model performance",
                    "approach": "Analyze outlier patterns and apply appropriate treatment",
                    "priority": "medium"
                })
        
        return suggestions
    
    def generate_profile_script(self, 
                              file_path: str,
                              custom_requirements: Optional[str] = None,
                              focus_areas: Optional[List[str]] = None) -> str:
        """Generate custom profiling script based on requirements"""
        
        prompt = f"""
Generate a Python script for advanced data profiling of a parquet file.

File path: {file_path}
Custom requirements: {custom_requirements or 'Standard profiling'}
Focus areas: {', '.join(focus_areas) if focus_areas else 'All aspects'}

The script should:
1. Load the parquet file
2. Perform requested profiling analysis
3. Generate visualizations if applicable
4. Return results as a structured dictionary

Include proper error handling and progress reporting.
Use pandas, numpy, and other standard data science libraries.

Generate only the Python code, no explanations.
"""
        
        response = self.model.chat(
            messages=[{"role": "user", "content": prompt}],
            system_message="You are a Python data science expert. Generate clean, efficient code."
        )
        
        return response.content
    
    def refine_profile_script(self, 
                            current_script: str,
                            refinement_request: str) -> str:
        """Refine existing profiling script based on user feedback"""
        
        prompt = f"""
Current profiling script:
```python
{current_script}
```

User refinement request: {refinement_request}

Modify the script according to the request. Maintain the same structure and return format.
Generate only the updated Python code.
"""
        
        response = self.model.chat(
            messages=[{"role": "user", "content": prompt}],
            system_message="You are a Python data science expert. Modify code based on requirements."
        )
        
        return response.content
