"""
AI-powered dashboard template generator using existing GenAI layer
Generates modern, interactive, theme-consistent dashboard templates
"""

import asyncio
import httpx
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid

from .dataset_validator import DatasetValidator

logger = logging.getLogger(__name__)

class ModernDashboardTemplateGenerator:
    """AI-powered template generator using existing GenAI API"""
    
    def __init__(self):
        self.genai_api = "/api/genai/chat"
        self.validator = DatasetValidator()
        self.theme_config = self._load_app_theme()
        self.supported_charts = self._get_supported_chart_types()
        
    def _load_app_theme(self) -> Dict:
        """Load existing app theme for consistency"""
        return {
            "colors": {
                "primary": "hsl(var(--primary))",
                "secondary": "hsl(var(--secondary))", 
                "accent": "hsl(var(--accent))",
                "background": "hsl(var(--background))",
                "card": "hsl(var(--card))",
                "muted": "hsl(var(--muted))",
                "border": "hsl(var(--border))"
            },
            "typography": {
                "heading": "font-semibold text-foreground",
                "body": "text-muted-foreground",
                "caption": "text-xs text-muted-foreground"
            },
            "spacing": "space-y-4",
            "radius": "rounded-lg",
            "shadows": "shadow-sm"
        }
    
    def _get_supported_chart_types(self) -> Dict:
        """Define all supported modern chart types"""
        return {
            "basic_charts": [
                "bar_chart", "column_chart", "line_chart", "area_chart",
                "pie_chart", "donut_chart", "scatter_plot"
            ],
            "advanced_charts": [
                "heatmap", "treemap", "sunburst", "radar_chart", 
                "bubble_chart", "waterfall_chart"
            ],
            "statistical_charts": [
                "box_plot", "violin_plot", "histogram", "density_plot",
                "correlation_matrix"
            ],
            "time_series": [
                "timeline", "candlestick", "area_chart_stacked"
            ],
            "interactive_features": [
                "zoom_pan", "brush_selection", "drill_down", "cross_filter",
                "hover_details", "click_actions", "range_selector"
            ]
        }
    
    async def generate_dashboard_templates(
        self, 
        user_prompt: str,
        dataset_selection: Dict,
        user_context: Dict = None
    ) -> Dict:
        """Generate AI-powered dashboard templates with validation"""
        
        try:
            # Step 1: Validate datasets (NO DUMMY DATA)
            validation_result = await self.validator.validate_selected_datasets(dataset_selection)
            
            if not validation_result["can_create_dashboard"]:
                return {
                    "can_generate": False,
                    "error_type": "invalid_datasets",
                    "message": "Cannot generate templates: Selected datasets are invalid or empty",
                    "validation_result": validation_result,
                    "templates": []
                }
            
            # Step 2: Analyze datasets for chart recommendations
            chart_analysis = await self.validator.analyze_datasets_for_charts(validation_result)
            
            # Step 3: Generate AI templates using existing GenAI API
            ai_templates = await self._generate_ai_templates(
                user_prompt, 
                validation_result, 
                chart_analysis
            )
            
            # Step 4: Enhance templates with theme and interactivity
            enhanced_templates = self._enhance_templates_with_theme(ai_templates, chart_analysis)
            
            return {
                "can_generate": True,
                "templates": enhanced_templates,
                "validation_result": validation_result,
                "chart_analysis": chart_analysis,
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating dashboard templates: {str(e)}")
            return {
                "can_generate": False,
                "error_type": "generation_error",
                "message": f"Template generation failed: {str(e)}",
                "templates": []
            }
    
    async def _generate_ai_templates(
        self, 
        user_prompt: str, 
        validation_result: Dict, 
        chart_analysis: Dict
    ) -> List[Dict]:
        """Generate templates using existing GenAI API"""
        
        # Build comprehensive dataset context
        dataset_context = self._build_dataset_context(validation_result)
        
        # Create AI prompt
        ai_prompt = self._build_ai_prompt(user_prompt, dataset_context, chart_analysis)
        
        try:
            # Call existing GenAI API
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.genai_api,
                    json={
                        "messages": [{"role": "user", "content": ai_prompt}],
                        "model": "gpt-4",
                        "temperature": 0.7,
                        "max_tokens": 4000
                    },
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    ai_response = response.json()
                    return self._parse_ai_response(ai_response["response"])
                else:
                    logger.error(f"GenAI API error: {response.status_code}")
                    return self._create_fallback_templates(validation_result, chart_analysis)
                    
        except Exception as e:
            logger.error(f"Error calling GenAI API: {str(e)}")
            return self._create_fallback_templates(validation_result, chart_analysis)
    
    def _build_dataset_context(self, validation_result: Dict) -> str:
        """Build detailed dataset context for AI"""
        
        context_parts = []
        
        # Source datasets
        if validation_result["source_datasets"]:
            context_parts.append("SOURCE DATASETS:")
            for dataset in validation_result["source_datasets"]:
                if dataset["valid"]:
                    context_parts.append(f"- {dataset['name']}: {dataset['record_count']} records, Type: {dataset['type']}")
        
        # Transformed datasets
        if validation_result["transformed_datasets"]:
            context_parts.append("\nTRANSFORMED DATASETS:")
            for dataset in validation_result["transformed_datasets"]:
                if dataset["valid"]:
                    context_parts.append(f"- {dataset['name']}: {dataset['record_count']} records")
        
        context_parts.append(f"\nTOTAL RECORDS: {validation_result['total_records']:,}")
        
        return "\n".join(context_parts)
    
    def _build_ai_prompt(self, user_prompt: str, dataset_context: str, chart_analysis: Dict) -> str:
        """Build comprehensive AI prompt for template generation"""
        
        recommended_charts = ", ".join(chart_analysis.get("recommended_charts", []))
        
        return f"""
Create 3 modern, interactive dashboard templates based on:

USER REQUEST: "{user_prompt}"

AVAILABLE DATA:
{dataset_context}

FIELD ANALYSIS:
- Numeric fields: {len(chart_analysis.get('numeric_fields', []))}
- Categorical fields: {len(chart_analysis.get('categorical_fields', []))}
- DateTime fields: {len(chart_analysis.get('datetime_fields', []))}

RECOMMENDED CHART TYPES: {recommended_charts}

DESIGN REQUIREMENTS:
1. Use existing app theme colors (primary, secondary, accent, muted)
2. Include interactive features (filters, drill-downs, hover effects)
3. Ensure responsive design for all screen sizes
4. Add real-time data refresh capabilities
5. NO DUMMY DATA - only reference actual dataset fields

THEME COLORS TO USE:
- Primary: hsl(var(--primary))
- Secondary: hsl(var(--secondary))
- Accent: hsl(var(--accent))
- Muted: hsl(var(--muted))

Return 3 dashboard templates as JSON array with this structure:
{{
  "templates": [
    {{
      "id": "template_1",
      "name": "Template Name",
      "description": "What insights it provides",
      "layout": {{
        "grid_columns": 12,
        "responsive_breakpoints": ["lg", "md", "sm"]
      }},
      "widgets": [
        {{
          "id": "widget_1",
          "type": "bar_chart",
          "title": "Widget Title",
          "position": {{"x": 0, "y": 0, "w": 6, "h": 4}},
          "data_source": "dataset_field_reference",
          "config": {{
            "x_field": "actual_field_name",
            "y_field": "actual_numeric_field",
            "color_scheme": "theme_primary"
          }},
          "interactive_features": ["hover_details", "drill_down"]
        }}
      ],
      "filters": [
        {{
          "type": "dropdown",
          "field": "actual_categorical_field",
          "label": "Filter Label"
        }}
      ],
      "theme": {{
        "primary_color": "hsl(var(--primary))",
        "background": "hsl(var(--card))"
      }}
    }}
  ]
}}

Ensure ALL data references use actual field names from the available datasets. NO placeholder or dummy data.
"""
    
    def _parse_ai_response(self, ai_response: str) -> List[Dict]:
        """Parse AI response and extract templates"""
        
        try:
            # Try to extract JSON from response
            json_start = ai_response.find('{')
            json_end = ai_response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_content = ai_response[json_start:json_end]
                parsed = json.loads(json_content)
                
                if "templates" in parsed:
                    return parsed["templates"]
                else:
                    return [parsed] if isinstance(parsed, dict) else []
            else:
                logger.warning("No valid JSON found in AI response")
                return []
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {str(e)}")
            return []
    
    def _enhance_templates_with_theme(self, templates: List[Dict], chart_analysis: Dict) -> List[Dict]:
        """Enhance templates with theme consistency and interactivity"""
        
        enhanced_templates = []
        
        for template in templates:
            enhanced_template = {
                **template,
                "id": template.get("id", str(uuid.uuid4())),
                "theme_applied": True,
                "responsive": True,
                "interactive_features_enabled": True
            }
            
            # Enhance widgets with theme
            if "widgets" in enhanced_template:
                enhanced_widgets = []
                for widget in enhanced_template["widgets"]:
                    enhanced_widget = {
                        **widget,
                        "theme": {
                            "colors": self.theme_config["colors"],
                            "typography": self.theme_config["typography"],
                            "radius": self.theme_config["radius"]
                        },
                        "responsive": True,
                        "interactive": True
                    }
                    enhanced_widgets.append(enhanced_widget)
                enhanced_template["widgets"] = enhanced_widgets
            
            enhanced_templates.append(enhanced_template)
        
        return enhanced_templates
    
    def _create_fallback_templates(self, validation_result: Dict, chart_analysis: Dict) -> List[Dict]:
        """Create fallback templates when AI generation fails"""
        
        fallback_templates = []
        
        # Template 1: Basic Overview
        template1 = {
            "id": str(uuid.uuid4()),
            "name": "Data Overview Dashboard",
            "description": "Basic overview of your datasets with key metrics",
            "layout": {"grid_columns": 12, "responsive_breakpoints": ["lg", "md", "sm"]},
            "widgets": [],
            "filters": [],
            "theme": self.theme_config
        }
        
        # Add widgets based on available data
        if chart_analysis.get("numeric_fields"):
            template1["widgets"].append({
                "id": "overview_chart",
                "type": "bar_chart",
                "title": "Data Overview",
                "position": {"x": 0, "y": 0, "w": 12, "h": 6},
                "interactive_features": ["hover_details"]
            })
        
        fallback_templates.append(template1)
        
        return fallback_templates
