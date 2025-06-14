"""
Transformation Agent - AI-powered data transformation assistant
"""

import json
import logging
from typing import Dict, List, Any, Optional
import pandas as pd

from api.gen_ai_layer.models import create_model

logger = logging.getLogger(__name__)


class TransformationAgent:
    """AI agent for intelligent data transformation planning and code generation"""
    
    def __init__(self, model_name: Optional[str] = None):
        self.model = create_model(model_name=model_name)
    
    def create_transformation_plan(self,
                                 profile_summary: Dict[str, Any],
                                 quality_issues: List[Dict[str, Any]],
                                 suggestions: List[Dict[str, Any]],
                                 user_requirements: Optional[str] = None,
                                 schema_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a transformation plan based on profile findings"""
        
        # Prepare context
        context = self._prepare_transformation_context(
            profile_summary, quality_issues, suggestions, user_requirements
        )
        
        # Extract schema information if available
        schema_description = ""
        if schema_info:
            columns_info = []
            for col_name, col_details in schema_info.items():
                data_type = col_details.get('type', 'unknown')
                nullable = col_details.get('nullable', True)
                columns_info.append(f"- {col_name}: {data_type}, {'nullable' if nullable else 'not nullable'}")
            
            schema_description = "\nData Schema:\n" + "\n".join(columns_info)
        
        # Generate transformation plan
        prompt = f"""
Based on this data profile analysis:

{context}
{schema_description if schema_info else ''}

Create a comprehensive data transformation plan. Include:
1. Transformation steps in order of priority
2. Expected improvements for each step
3. Dependencies between steps
4. Estimated impact on data quality

Format the response as a JSON object with:
- name: Brief plan name
- description: Plan overview
- steps: Array of transformation steps
- expected_improvements: Object with quality metrics

Each step should have:
- order: integer (1, 2, 3, etc.)
- operation: string (e.g., "remove_columns", "impute_missing", etc.)
- description: string describing the action
- parameters: MUST BE A DICTIONARY with configuration options for the operation, not a string or list

Example of a valid step:
{{
  "order": 1,
  "operation": "remove_columns",
  "description": "Remove irrelevant columns from dataset",
  "parameters": {{
    "columns": ["col1", "col2"],
    "reason": "low information content"
  }}
}}
"""
        
        response = self.model.chat(
            messages=[{"role": "user", "content": prompt}],
            system_message="You are a data engineering expert. Create practical transformation plans in valid JSON format. IMPORTANT: All transformation steps must have 'parameters' as a DICTIONARY object, not a string or list. If user requirements is missing, you should provide a plan related to removing irrelevant data, handling missing values, fixing structural errors, standardizing data formats, and removing duplicate records. Each parameter must be an object with key-value pairs, never a string or list."
        )
        
        try:
            plan_data = json.loads(response.content)
            
            # Ensure required fields
            if 'steps' not in plan_data:
                plan_data['steps'] = []
            
            # Add default improvements if not provided
            if 'expected_improvements' not in plan_data:
                plan_data['expected_improvements'] = {
                    "data_quality_score": "+10-15%",
                    "completeness": "Improved",
                    "consistency": "Enhanced"
                }
                
            return plan_data
            
        except json.JSONDecodeError:
            # Fallback plan based on issues
            return self._create_fallback_plan(quality_issues, suggestions)
    
    def _prepare_transformation_context(self,
                                      profile_summary: str,
                                      quality_issues: List[Dict],
                                      suggestions: List[Dict],
                                      user_requirements: Optional[str]) -> str:
        """Prepare context for transformation planning"""
        
        context = f"Profile Summary:\n{profile_summary}\n\n"
        
        if quality_issues:
            context += "Quality Issues:\n"
            for issue in quality_issues:
                context += f"- {issue['type']}: {issue['details']} (Severity: {issue['severity']})\n"
            context += "\n"
        
        if suggestions:
            context += "Improvement Suggestions:\n"
            for suggestion in suggestions:
                context += f"- {suggestion['suggestion']} (Priority: {suggestion.get('priority', 'medium')})\n"
            context += "\n"
        
        if user_requirements:
            context += f"User Requirements:\n{user_requirements}\n"
        
        return context
    
    def _create_fallback_plan(self, 
                            quality_issues: List[Dict],
                            suggestions: List[Dict]) -> Dict[str, Any]:
        """Create a fallback transformation plan"""
        
        steps = []
        order = 1
        
        # Handle duplicates first
        if any(issue['type'] == 'duplicate_rows' for issue in quality_issues):
            steps.append({
                "order": order,
                "operation": "remove_duplicates",
                "description": "Remove duplicate rows from the dataset",
                "parameters": {
                    "subset": None,  # Check all columns
                    "keep": "first"
                }
            })
            order += 1
        
        # Handle missing values
        missing_issues = [i for i in quality_issues if i['type'] == 'high_missing_values']
        for issue in missing_issues[:3]:  # Limit to top 3
            column = issue.get('column', 'unknown')
            steps.append({
                "order": order,
                "operation": "handle_missing",
                "description": f"Handle missing values in column '{column}'",
                "parameters": {
                    "column": column,
                    "strategy": "drop" if float(issue['details'].split('%')[0]) > 50 else "fill",
                    "fill_value": "mean"  # For numeric, will be adjusted in script
                }
            })
            order += 1
        
        # Handle outliers
        outlier_issues = [i for i in quality_issues if i['type'] == 'outliers']
        for issue in outlier_issues[:2]:  # Limit to top 2
            column = issue.get('column', 'unknown')
            steps.append({
                "order": order,
                "operation": "handle_outliers",
                "description": f"Handle outliers in column '{column}'",
                "parameters": {
                    "column": column,
                    "method": "iqr",
                    "action": "cap"  # Cap to limits instead of removing
                }
            })
            order += 1
        
        return {
            "name": "Automated Data Quality Improvement Plan",
            "description": "Systematic approach to address identified data quality issues",
            "steps": steps,
            "expected_improvements": {
                "data_quality_score": f"+{len(steps) * 3}-{len(steps) * 5}%",
                "missing_values": "Reduced",
                "duplicates": "Eliminated",
                "outliers": "Handled"
            }
        }
    
    def generate_transformation_script(self,
                                     input_file_path: str,
                                     transformation_steps: List[Dict[str, Any]],
                                     output_file_path: Optional[str] = None,
                                     schema_info: Optional[Dict[str, Any]] = None,
                                     profile_summary: Optional[Dict[str, Any]] = None) -> str:
        """Generate Python script for transformation plan based on actual data schema"""
        
        steps_description = "\n".join([
            f"{step['order']}. {step['description']} - {step['operation']}"
            for step in transformation_steps
        ])
        
        # Extract schema information if available
        schema_description = ""
        if schema_info:
            columns_info = []
            for col_name, col_details in schema_info.items():
                data_type = col_details.get('type', 'unknown')
                nullable = col_details.get('nullable', True)
                columns_info.append(f"- {col_name}: {data_type}, {'nullable' if nullable else 'not nullable'}")
            
            schema_description = "\nData Schema:\n" + "\n".join(columns_info)
        
        print("AGENT SCHEMA - ", schema_description)
        
        # Extract profile summary information if available
        profile_description = ""
        if profile_summary:
            total_rows = profile_summary.get('total_rows', 0)
            total_columns = profile_summary.get('total_columns', 0)
            missing_values = profile_summary.get('missing_values_count', 0)
            duplicates = profile_summary.get('exact_duplicates_count', 0)
            
            profile_description = f"""
            
Data Profile Summary:
- Total Rows: {total_rows:,}
- Total Columns: {total_columns}
- Missing Values: {missing_values:,}
- Duplicate Rows: {duplicates:,}
            """
            
            # Include column type distribution if available
            if 'column_types' in profile_summary:
                col_types = [f"- {ctype}: {count}" for ctype, count in profile_summary['column_types'].items()]
                profile_description += "\nColumn Type Distribution:\n" + "\n".join(col_types)
        
        prompt = f"""
Generate a Python script to transform data according to this plan:

Input file: {input_file_path}
Output file: {output_file_path or 'auto-generated'}
{schema_description}
{profile_description}

Transformation steps:
{steps_description}

Step details:
{json.dumps(transformation_steps, indent=2)}

Requirements:
1. Load parquet file using pandas
2. Implement each transformation step exactly as specified, but ONLY IF they apply to columns that exist in the data
3. Always check if columns exist before performing operations on them
4. Add proper error handling for each step
5. CRITICAL: Continue execution of next steps even if a particular step fails (use try/except around each step)
6. Log progress, errors, and statistics for each step
7. Save transformed data to parquet
8. Return transformation summary with before/after statistics including which steps succeeded/failed
9. Use efficient pandas operations
10. NEVER assume columns exist - always check first
11. CRITICAL: Do NOT create placeholder functions that don't have implementations (such as ai_* functions)
12. CRITICAL: Use ONLY standard pandas, numpy, scikit-learn, or Python standard library functions
13. CRITICAL: EVERY function you reference in the code MUST be defined within the script itself or imported from specific libraries
14. If a transformation step requires specialized logic, implement that logic directly using pandas/numpy methods

PROVIDE ONLY VALID PYTHON CODE WITH NO EXPLANATORY TEXT, MARKDOWN, OR ANYTHING ELSE. Your response must be 100% valid Python that can be executed without modification.
"""
        
        response = self.model.chat(
            messages=[{"role": "user", "content": prompt}],
            system_message="You are a Python data engineering expert. Generate ONLY production-ready transformation code that handles edge cases and never assumes columns exist without checking. ONLY OUTPUT VALID PYTHON CODE WITH NO EXPLANATORY TEXT BEFORE OR AFTER THE CODE. Your entire response must be valid Python syntax."
        )
        
        return response.content
    
    def refine_transformation_plan(self,
                                 current_plan: Dict[str, Any],
                                 refinement_request: str,
                                 schema_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Refine transformation plan based on user feedback"""
        
        # Extract schema information if available
        schema_description = ""
        if schema_info:
            columns_info = []
            for col_name, col_details in schema_info.items():
                data_type = col_details.get('type', 'unknown')
                nullable = col_details.get('nullable', True)
                columns_info.append(f"- {col_name}: {data_type}, {'nullable' if nullable else 'not nullable'}")        
            schema_description = "\nData Schema:\n" + "\n".join(columns_info)
        
        prompt = f"""
Current transformation plan:
{json.dumps(current_plan, indent=2)}

User refinement request: {refinement_request}
{schema_description if schema_info else ''}

Modify the transformation plan according to the request. You can:
1. Add new transformation steps
2. Remove unnecessary steps
3. Modify step parameters
4. Reorder steps
5. Update expected improvements

IMPORTANT: Each transformation step MUST have exactly these required fields:
- order: A sequential integer (1, 2, 3, etc.)
- operation: String indicating the operation type (like 'filter', 'transform', etc.)
- description: String describing what the step does
- parameters: MUST BE A DICTIONARY with configuration options as key-value pairs, never a string or list
- continue_on_error: Boolean (default should be true) indicating whether subsequent steps should continue if this step fails

Examples of valid parameter dictionaries:
1. For removing columns: {{"columns": ["col1", "col2"], "reason": "low information"}}
2. For imputation: {{"method": "mean", "columns": ["col1", "col2"]}}
3. For normalization: {{"method": "minmax", "feature_range": [0, 1]}}

Example of a valid step:
{{
  "order": 1,
  "operation": "remove_duplicates",
  "description": "Remove duplicate records based on ID field",
  "parameters": {{
    "columns": ["id"],
    "keep": "first"
  }},
  "continue_on_error": true
}}

Your entire response must be valid JSON with the exact required field names. Do not use fields like 'id' or 'action' instead of 'order' or 'operation'.

Ensure the transformation plan generates code that can continue execution of next steps even if previous steps fail.
"""
        
        response = self.model.chat(
            messages=[{"role": "user", "content": prompt}],
            system_message="You are a data engineering expert. CRITICAL: Each step's parameters field MUST be a dictionary object with key-value pairs, never a string or list. Your response must be valid JSON only with no explanations outside of the JSON structure."
        )
        
        try:
            # Try to find a valid JSON structure in the response
            content = response.content.strip()
            
            # Look for the first { and the last } to extract potential JSON
            json_start = content.find('{')
            json_end = content.rfind('}')
            
            if json_start >= 0 and json_end > json_start:
                potential_json = content[json_start:json_end+1]
                refined_plan = json.loads(potential_json)
                return refined_plan
            else:
                # No valid JSON delimiters found
                raise json.JSONDecodeError("No JSON structure found", content, 0)
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse refined plan: {str(e)}")
            # Add response text as a note (safely)   
            try:
                # Safely add user feedback even if there's a parsing error
                if 'user_notes' not in current_plan:
                    current_plan['user_notes'] = []
                elif not isinstance(current_plan['user_notes'], list):
                    current_plan['user_notes'] = [current_plan['user_notes']]
                    
                current_plan['user_notes'].append({
                    "request": refinement_request,
                    "timestamp": datetime.utcnow().isoformat()
                })
            except Exception:
                # If all else fails, create a minimal plan structure
                logger.error("Failed to update plan with user note")
                
            return current_plan
    
    def refine_transformation_script(self,
                                   current_script: str,
                                   refinement_request: str,
                                   schema_info: Optional[Dict[str, Any]] = None,
                                   profile_summary: Optional[Dict[str, Any]] = None) -> str:
        """Refine transformation script based on user feedback and actual data schema"""
        
        # Extract schema information if available
        schema_description = ""
        if schema_info:
            columns_info = []
            for col_name, col_details in schema_info.items():
                data_type = col_details.get('type', 'unknown')
                nullable = col_details.get('nullable', True)
                columns_info.append(f"- {col_name}: {data_type}, {'nullable' if nullable else 'not nullable'}")
            
            schema_description = "\nData Schema:\n" + "\n".join(columns_info)
        
        # Extract profile summary information if available
        profile_description = ""
        if profile_summary:
            total_rows = profile_summary.get('total_rows', 0)
            total_columns = profile_summary.get('total_columns', 0)
            missing_values = profile_summary.get('missing_values_count', 0)
            duplicates = profile_summary.get('exact_duplicates_count', 0)
            
            profile_description = f"""
            
Data Profile Summary:
- Total Rows: {total_rows:,}
- Total Columns: {total_columns}
- Missing Values: {missing_values:,}
- Duplicate Rows: {duplicates:,}
            """
            
            # Include column type distribution if available
            if 'column_types' in profile_summary:
                col_types = [f"- {ctype}: {count}" for ctype, count in profile_summary['column_types'].items()]
                profile_description += "\nColumn Type Distribution:\n" + "\n".join(col_types)
        
        prompt = f"""
Current transformation script:
```python
{current_script}
```

User refinement request: {refinement_request}
{schema_description}
{profile_description}

Modify the script according to the request while maintaining:
1. The same input/output structure
2. Error handling
3. Progress logging
4. Return format with statistics

Requirements:
1. ONLY modify operations on columns that actually exist in the data schema
2. Always check if columns exist before performing operations on them
3. Never assume columns exist without checking
4. CRITICAL: Ensure execution continues to next steps even if a particular step fails (use try/except around each step)
5. For each transformation step, catch and log errors but continue executing subsequent steps
6. Maintain proper error handling for each step
7. Keep detailed logging of each transformation step including errors encountered
8. Include information about succeeded/failed steps in the final summary
9. CRITICAL: Do NOT create placeholder functions that don't have implementations (such as ai_* functions)
10. CRITICAL: Use ONLY standard pandas, numpy, scikit-learn, or Python standard library functions
11. CRITICAL: EVERY function you reference in the code MUST be defined within the script itself or imported from specific libraries
12. If a transformation step requires specialized logic, implement that logic directly using pandas/numpy methods
13. If you're unsure how to implement a specific transformation, use a simple but complete implementation rather than a placeholder

PROVIDE ONLY VALID PYTHON CODE WITH NO EXPLANATORY TEXT, MARKDOWN, OR ANYTHING ELSE. Your response must be 100% valid Python that can be executed without modification.
"""
        
        response = self.model.chat(
            messages=[{"role": "user", "content": prompt}],
            system_message="You are a Python data engineering expert. Modify code based on requirements. ONLY OUTPUT VALID PYTHON CODE WITH NO EXPLANATORY TEXT BEFORE OR AFTER THE CODE. Your entire response must be valid Python syntax."
        )
        
        return response.content
    
    def suggest_advanced_transformations(self,
                                       data_profile: Dict[str, Any],
                                       domain: Optional[str] = None) -> List[Dict[str, Any]]:
        """Suggest advanced transformations based on data characteristics"""
        
        prompt = f"""
Based on this data profile:
{json.dumps(data_profile, indent=2)}

Domain: {domain or 'General'}

Suggest advanced transformations that could enhance this dataset:
1. Feature engineering opportunities
2. Data enrichment possibilities
3. Normalization/standardization needs
4. Encoding strategies for categorical data
5. Time-based transformations if applicable

Format as JSON array with: type, description, rationale, complexity (low/medium/high)
"""
        
        response = self.model.chat(
            messages=[{"role": "user", "content": prompt}],
            system_message="You are a data science expert. Suggest valuable transformations in valid JSON format."
        )
        
        try:
            suggestions = json.loads(response.content)
            return suggestions if isinstance(suggestions, list) else []
        except:
            return []
