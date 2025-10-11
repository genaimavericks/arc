"""
Dataset validation service using existing DataPuur APIs
Ensures no dummy data and validates dataset availability
"""

import asyncio
import httpx
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class DatasetValidator:
    """Validates datasets using existing DataPuur APIs - ensures no dummy data"""
    
    def __init__(self):
        # Use absolute URL for internal API calls
        import os
        self.base_url = os.getenv("API_BASE_URL", "http://127.0.0.1:9090")
        self.timeout = 30.0
        
    async def validate_selected_datasets(self, dataset_selection: Dict) -> Dict:
        """Validate datasets using existing DataPuur APIs"""
        
        validation_results = {
            "source_datasets": [],
            "transformed_datasets": [],
            "all_valid": True,
            "total_records": 0,
            "can_create_dashboard": False,
            "validation_timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            # Validate source datasets
            if dataset_selection.get("source_ids"):
                source_results = await self._validate_source_datasets(
                    dataset_selection["source_ids"]
                )
                validation_results["source_datasets"] = source_results["datasets"]
                validation_results["total_records"] += source_results["total_records"]
                if not source_results["all_valid"]:
                    validation_results["all_valid"] = False
            
            # Validate transformed datasets
            if dataset_selection.get("transformed_ids"):
                transformed_results = await self._validate_transformed_datasets(
                    dataset_selection["transformed_ids"]
                )
                validation_results["transformed_datasets"] = transformed_results["datasets"]
                validation_results["total_records"] += transformed_results["total_records"]
                if not transformed_results["all_valid"]:
                    validation_results["all_valid"] = False
            
            # Final validation check
            validation_results["can_create_dashboard"] = (
                validation_results["all_valid"] and 
                validation_results["total_records"] > 0 and
                (len(validation_results["source_datasets"]) > 0 or 
                 len(validation_results["transformed_datasets"]) > 0)
            )
            
        except Exception as e:
            logger.error(f"Error during dataset validation: {str(e)}")
            validation_results["all_valid"] = False
            validation_results["can_create_dashboard"] = False
            validation_results["error"] = str(e)
        
        return validation_results
    
    async def _validate_source_datasets(self, dataset_ids: List[str]) -> Dict:
        """Validate source datasets by getting all sources and finding matches"""
        
        results = {
            "datasets": [],
            "all_valid": True,
            "total_records": 0
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                # Get all sources first (this endpoint works correctly)
                # Note: Internal API call with absolute URL
                sources_url = f"{self.base_url}/api/datapuur/sources"
                logger.info(f"Backend validation: Calling {sources_url}")
                response = await client.get(sources_url)
                logger.info(f"Backend validation: Sources API response status: {response.status_code}")
                
                if response.status_code == 200:
                    all_sources = response.json()
                    logger.info(f"Backend validation: Found {len(all_sources)} total sources")
                    
                    # Create lookup dict for quick access
                    sources_by_id = {source["id"]: source for source in all_sources}
                    logger.info(f"Backend validation: Looking for dataset IDs: {dataset_ids}")
                    logger.info(f"Backend validation: Available source IDs: {list(sources_by_id.keys())[:5]}...")  # Show first 5 IDs
                    
                    for dataset_id in dataset_ids:
                        if dataset_id in sources_by_id:
                            dataset = sources_by_id[dataset_id]
                            logger.info(f"Backend validation: Found dataset {dataset_id}")
                            logger.info(f"Backend validation: Dataset details: {dataset}")
                            
                            # Check dataset status and record count - Accept both completed and active
                            valid_statuses = ["completed", "active", "Active", "Completed"]
                            record_count = dataset.get("row_count", 0)
                            
                            logger.info(f"Backend validation: Status='{dataset.get('status')}', RecordCount={record_count}")
                            
                            is_valid = (
                                dataset.get("status") in valid_statuses and 
                                record_count > 0
                            )
                            
                            logger.info(f"Backend validation: Dataset {dataset_id} is_valid={is_valid}")
                            
                            dataset_info = {
                                "id": dataset_id,
                                "valid": is_valid,
                                "name": dataset.get("name", "Unknown"),
                                "record_count": record_count,
                                "status": dataset.get("status", "unknown"),
                                "type": dataset.get("type", "unknown"),
                                "uploaded_at": dataset.get("last_updated"),
                                "size_bytes": dataset.get("file_size", 0)
                            }
                            
                            if is_valid:
                                results["total_records"] += record_count
                            else:
                                results["all_valid"] = False
                                dataset_info["error"] = f"Dataset status '{dataset.get('status')}' or empty ({record_count} records)"
                        else:
                            # Dataset ID not found in sources
                            logger.error(f"Backend validation: Dataset {dataset_id} NOT FOUND in sources")
                            logger.error(f"Backend validation: Available IDs: {list(sources_by_id.keys())}")
                            results["all_valid"] = False
                            dataset_info = {
                                "id": dataset_id,
                                "valid": False,
                                "name": "Unknown",
                                "record_count": 0,
                                "status": "not_found",
                                "type": "unknown",
                                "error": "Dataset not found in sources list"
                            }
                        
                        results["datasets"].append(dataset_info)
                else:
                    # HTTP request failed
                    results["all_valid"] = False
                    for dataset_id in dataset_ids:
                        results["datasets"].append({
                            "id": dataset_id,
                            "valid": False,
                            "error": f"Failed to fetch sources (HTTP {response.status_code})"
                        })
                        
            except Exception as e:
                logger.error(f"Error validating source datasets: {str(e)}")
                results["all_valid"] = False
                for dataset_id in dataset_ids:
                    results["datasets"].append({
                        "id": dataset_id,
                        "valid": False,
                        "error": f"Validation error: {str(e)}"
                    })
        
        return results
    
    async def _validate_transformed_datasets(self, dataset_ids: List[str]) -> Dict:
        """Validate transformed datasets using existing AI API"""
        
        results = {
            "datasets": [],
            "all_valid": True,
            "total_records": 0
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for dataset_id in dataset_ids:
                try:
                    # REUSE: Existing transformed dataset API
                    response = await client.get(f"/api/datapuur_ai/transformed-datasets/{dataset_id}")
                    
                    if response.status_code == 200:
                        dataset = response.json()
                        
                        # Check for actual data - NO DUMMY DATA
                        is_valid = dataset.get("row_count", 0) > 0
                        
                        dataset_info = {
                            "id": dataset_id,
                            "valid": is_valid,
                            "name": dataset.get("name", "Unknown"),
                            "record_count": dataset.get("row_count", 0),
                            "transformation_type": dataset.get("transformation_type"),
                            "created_at": dataset.get("created_at"),
                            "status": dataset.get("status", "completed")
                        }
                        
                        if is_valid:
                            results["total_records"] += dataset.get("row_count", 0)
                        else:
                            results["all_valid"] = False
                            dataset_info["error"] = "Transformed dataset is empty"
                        
                        results["datasets"].append(dataset_info)
                        
                    else:
                        results["all_valid"] = False
                        results["datasets"].append({
                            "id": dataset_id,
                            "valid": False,
                            "error": f"Transformed dataset not found (HTTP {response.status_code})"
                        })
                        
                except Exception as e:
                    logger.error(f"Error validating transformed dataset {dataset_id}: {str(e)}")
                    results["all_valid"] = False
                    results["datasets"].append({
                        "id": dataset_id,
                        "valid": False,
                        "error": f"Validation error: {str(e)}"
                    })
        
        return results
    
    async def get_dataset_schema(self, dataset_id: str, dataset_type: str) -> Dict:
        """Get dataset schema using existing APIs"""
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                if dataset_type == "source":
                    # REUSE: Existing schema API
                    response = await client.get(f"/api/datapuur/datasets/{dataset_id}/schema")
                else:
                    # REUSE: Existing transformed schema API  
                    response = await client.get(f"/api/datapuur_ai/transformed-datasets/{dataset_id}/schema")
                
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"error": f"Schema not available (HTTP {response.status_code})"}
                    
        except Exception as e:
            logger.error(f"Failed to get schema for {dataset_type} dataset {dataset_id}: {str(e)}")
            return {"error": f"Failed to get schema: {str(e)}"}
    
    async def analyze_datasets_for_charts(self, validated_datasets: Dict) -> Dict:
        """Analyze validated datasets to recommend chart types"""
        
        chart_recommendations = {
            "numeric_fields": [],
            "categorical_fields": [], 
            "datetime_fields": [],
            "recommended_charts": [],
            "interactive_features": []
        }
        
        try:
            # Analyze source datasets
            for dataset in validated_datasets.get("source_datasets", []):
                if dataset["valid"]:
                    schema = await self.get_dataset_schema(dataset["id"], "source")
                    if "fields" in schema:
                        self._extract_field_types(schema["fields"], chart_recommendations)
            
            # Analyze transformed datasets
            for dataset in validated_datasets.get("transformed_datasets", []):
                if dataset["valid"]:
                    schema = await self.get_dataset_schema(dataset["id"], "transformed")
                    if "fields" in schema:
                        self._extract_field_types(schema["fields"], chart_recommendations)
            
            # Generate chart recommendations based on field types
            chart_recommendations["recommended_charts"] = self._generate_chart_recommendations(
                chart_recommendations
            )
            
        except Exception as e:
            logger.error(f"Error analyzing datasets for charts: {str(e)}")
            chart_recommendations["error"] = str(e)
        
        return chart_recommendations
    
    def _extract_field_types(self, fields: List[Dict], recommendations: Dict):
        """Extract field types from schema"""
        
        for field in fields:
            field_type = field.get("type", "").lower()
            field_name = field.get("name", "")
            
            if field_type in ["integer", "float", "decimal", "number"]:
                recommendations["numeric_fields"].append({
                    "name": field_name,
                    "type": field_type,
                    "sample": field.get("sample")
                })
            elif field_type in ["string", "text", "varchar", "category"]:
                recommendations["categorical_fields"].append({
                    "name": field_name,
                    "type": field_type,
                    "sample": field.get("sample")
                })
            elif field_type in ["date", "datetime", "timestamp"]:
                recommendations["datetime_fields"].append({
                    "name": field_name,
                    "type": field_type,
                    "sample": field.get("sample")
                })
    
    def _generate_chart_recommendations(self, field_analysis: Dict) -> List[str]:
        """Generate chart type recommendations based on field analysis"""
        
        charts = []
        numeric_count = len(field_analysis["numeric_fields"])
        categorical_count = len(field_analysis["categorical_fields"])
        datetime_count = len(field_analysis["datetime_fields"])
        
        # Recommend charts based on field combinations
        if numeric_count >= 2:
            charts.extend(["scatter_plot", "bubble_chart", "correlation_heatmap"])
        
        if numeric_count >= 1 and categorical_count >= 1:
            charts.extend(["bar_chart", "column_chart", "pie_chart", "donut_chart"])
        
        if datetime_count >= 1 and numeric_count >= 1:
            charts.extend(["line_chart", "area_chart", "timeline"])
        
        if categorical_count >= 2:
            charts.extend(["treemap", "sunburst"])
        
        if numeric_count >= 1:
            charts.extend(["histogram", "box_plot"])
        
        # Remove duplicates and return
        return list(set(charts))
