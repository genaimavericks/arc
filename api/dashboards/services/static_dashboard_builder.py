"""
Static Dashboard Builder Service
Generates static HTML/JS/CSS files from dashboard configurations
"""

import os
import json
import asyncio
import httpx
import logging
import uuid
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime
from jinja2 import Template

logger = logging.getLogger(__name__)

class StaticDashboardBuilder:
    """Builds static dashboard files from dashboard configurations"""
    
    def __init__(self):
        self.output_dir = Path(__file__).parent.parent.parent.parent / "out" / "dashboards"
        self.template_dir = Path(__file__).parent.parent / "templates"
        self.ensure_directories()
        
    def ensure_directories(self):
        """Ensure output directories exist"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.template_dir.mkdir(parents=True, exist_ok=True)
        
    async def build_static_dashboard(
        self, 
        dashboard_id: str,
        dashboard_config: Dict,
        validation_result: Dict
    ) -> Dict[str, Any]:
        """Build static dashboard files"""
        
        try:
            logger.info(f"Starting static build for dashboard {dashboard_id}")
            
            # Fetch real data from datasets using existing APIs
            dashboard_data = await self.fetch_dashboard_data(dashboard_config, validation_result)
            
            # Generate static HTML
            html_content = await self.generate_dashboard_html(dashboard_config, dashboard_data)
            
            # Generate CSS with theme
            css_content = await self.generate_dashboard_css(dashboard_config)
            
            # Generate JavaScript for interactivity
            js_content = await self.generate_dashboard_js(dashboard_config, dashboard_data)
            
            # Save files
            static_files = await self.save_static_files(
                dashboard_id,
                dashboard_config.get("user_id", "unknown"),
                {
                    "index.html": html_content,
                    "dashboard.css": css_content,
                    "dashboard.js": js_content
                }
            )
            
            logger.info(f"Static build completed for dashboard {dashboard_id}")
            
            return {
                "success": True,
                "static_path": static_files["html_path"],
                "asset_manifest": {
                    "html": f"{dashboard_id}.html",
                    "css": f"{dashboard_id}.css", 
                    "js": f"{dashboard_id}.js"
                }
            }
            
        except Exception as e:
            logger.error(f"Static build failed for dashboard {dashboard_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def fetch_dashboard_data(self, config: Dict, validation_result: Dict) -> Dict:
        """Fetch real data from datasets using existing APIs"""
        
        dashboard_data = {
            "datasets": {},
            "metadata": {
                "total_records": validation_result.get("total_records", 0),
                "data_sources": len(validation_result.get("source_datasets", [])) + len(validation_result.get("transformed_datasets", [])),
                "generated_at": datetime.utcnow().isoformat()
            }
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Fetch source dataset data
            for dataset in validation_result.get("source_datasets", []):
                if dataset.get("valid"):
                    try:
                        response = await client.get(f"/api/datapuur/datasets/{dataset['id']}/preview?rows=1000")
                        if response.status_code == 200:
                            data = response.json()
                            dashboard_data["datasets"][f"source_{dataset['id']}"] = {
                                "data": data.get("data", []),
                                "name": dataset.get("name", "Unknown"),
                                "type": "source",
                                "record_count": dataset.get("record_count", 0)
                            }
                        else:
                            dashboard_data["datasets"][f"source_{dataset['id']}"] = {
                                "error": f"Failed to load data (HTTP {response.status_code})",
                                "name": dataset.get("name", "Unknown"),
                                "type": "source"
                            }
                    except Exception as e:
                        logger.error(f"Error fetching source dataset {dataset['id']}: {str(e)}")
                        dashboard_data["datasets"][f"source_{dataset['id']}"] = {
                            "error": str(e),
                            "name": dataset.get("name", "Unknown"),
                            "type": "source"
                        }
            
            # Fetch transformed dataset data
            for dataset in validation_result.get("transformed_datasets", []):
                if dataset.get("valid"):
                    try:
                        response = await client.get(f"/api/datapuur_ai/transformed-datasets/{dataset['id']}/preview?rows=1000")
                        if response.status_code == 200:
                            data = response.json()
                            dashboard_data["datasets"][f"transformed_{dataset['id']}"] = {
                                "data": data.get("data", []),
                                "name": dataset.get("name", "Unknown"),
                                "type": "transformed",
                                "record_count": dataset.get("record_count", 0)
                            }
                        else:
                            dashboard_data["datasets"][f"transformed_{dataset['id']}"] = {
                                "error": f"Failed to load data (HTTP {response.status_code})",
                                "name": dataset.get("name", "Unknown"),
                                "type": "transformed"
                            }
                    except Exception as e:
                        logger.error(f"Error fetching transformed dataset {dataset['id']}: {str(e)}")
                        dashboard_data["datasets"][f"transformed_{dataset['id']}"] = {
                            "error": str(e),
                            "name": dataset.get("name", "Unknown"),
                            "type": "transformed"
                        }
        
        return dashboard_data
    
    async def generate_dashboard_html(self, config: Dict, data: Dict) -> str:
        """Generate HTML for the dashboard"""
        
        html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ dashboard_name }}</title>
    <link rel="stylesheet" href="./dashboard.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/date-fns@2.29.3/index.min.js"></script>
</head>
<body>
    <div class="dashboard-container">
        <!-- Header -->
        <header class="dashboard-header">
            <div class="header-content">
                <h1 class="dashboard-title">{{ dashboard_name }}</h1>
                <p class="dashboard-description">{{ description }}</p>
            </div>
            <div class="header-controls">
                <button class="btn btn-secondary" onclick="refreshDashboard()">
                    <span class="icon">🔄</span> Refresh
                </button>
                <button class="btn btn-secondary" onclick="exportDashboard()">
                    <span class="icon">📥</span> Export
                </button>
                <button class="btn btn-secondary" onclick="toggleFullscreen()">
                    <span class="icon">⛶</span> Fullscreen
                </button>
            </div>
        </header>
        
        <!-- Dashboard Grid -->
        <main class="dashboard-grid">
            {% for widget in widgets %}
            <div class="widget-container" id="widget-{{ widget.id }}" 
                 style="grid-column: span {{ widget.position.w or 6 }}; grid-row: span {{ widget.position.h or 4 }};">
                <div class="widget-card">
                    <div class="widget-header">
                        <h3 class="widget-title">{{ widget.title }}</h3>
                        <div class="widget-controls">
                            <button class="widget-btn" onclick="refreshWidget('{{ widget.id }}')">🔄</button>
                            <button class="widget-btn" onclick="exportWidget('{{ widget.id }}')">📥</button>
                        </div>
                    </div>
                    <div class="widget-content">
                        {% if widget.type in ['bar_chart', 'line_chart', 'pie_chart', 'area_chart', 'scatter_plot'] %}
                        <canvas id="chart-{{ widget.id }}" class="chart-canvas"></canvas>
                        {% else %}
                        <div class="empty-chart">
                            <div class="empty-icon">📊</div>
                            <p>Chart type "{{ widget.type }}" not yet implemented</p>
                        </div>
                        {% endif %}
                    </div>
                </div>
            </div>
            {% endfor %}
            
            {% if not widgets %}
            <div class="empty-dashboard">
                <div class="empty-icon">📊</div>
                <h2>Dashboard Ready</h2>
                <p>Your dashboard has been generated but contains no widgets yet.</p>
            </div>
            {% endif %}
        </main>
        
        <!-- Footer -->
        <footer class="dashboard-footer">
            <p>Generated on {{ generated_at }} • {{ total_records }} records from {{ data_sources }} data source(s)</p>
        </footer>
    </div>
    
    <!-- Data -->
    <script>
        window.DASHBOARD_DATA = {{ data_json }};
        window.DASHBOARD_CONFIG = {{ config_json }};
    </script>
    <script src="./dashboard.js"></script>
</body>
</html>
        """.strip()
        
        template = Template(html_template)
        
        return template.render(
            dashboard_name=config.get("name", "Dashboard"),
            description=config.get("description", "AI-generated interactive dashboard"),
            widgets=config.get("widgets", []),
            generated_at=data["metadata"]["generated_at"],
            total_records=data["metadata"]["total_records"],
            data_sources=data["metadata"]["data_sources"],
            data_json=json.dumps(data, default=str),
            config_json=json.dumps(config, default=str)
        )
    
    async def generate_dashboard_css(self, config: Dict) -> str:
        """Generate CSS with theme consistency"""
        
        return """
/* Modern Dashboard CSS with Theme Consistency */
:root {
    --primary: 222.2 84% 4.9%;
    --primary-foreground: 210 40% 98%;
    --secondary: 210 40% 96%;
    --secondary-foreground: 222.2 84% 4.9%;
    --accent: 210 40% 96%;
    --accent-foreground: 222.2 84% 4.9%;
    --background: 0 0% 100%;
    --foreground: 222.2 84% 4.9%;
    --card: 0 0% 100%;
    --card-foreground: 222.2 84% 4.9%;
    --muted: 210 40% 96%;
    --muted-foreground: 215.4 16.3% 46.9%;
    --border: 214.3 31.8% 91.4%;
    --radius: 0.5rem;
}

* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background-color: hsl(var(--background));
    color: hsl(var(--foreground));
    line-height: 1.5;
}

.dashboard-container {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
}

.dashboard-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem 2rem;
    border-bottom: 1px solid hsl(var(--border));
    background: hsl(var(--card));
}

.header-content h1 {
    font-size: 1.5rem;
    font-weight: 600;
    margin-bottom: 0.25rem;
}

.header-content p {
    color: hsl(var(--muted-foreground));
    font-size: 0.875rem;
}

.header-controls {
    display: flex;
    gap: 0.5rem;
}

.btn {
    padding: 0.5rem 1rem;
    border: 1px solid hsl(var(--border));
    border-radius: var(--radius);
    background: hsl(var(--card));
    color: hsl(var(--foreground));
    cursor: pointer;
    transition: all 0.2s ease;
    font-size: 0.875rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.btn:hover {
    background: hsl(var(--accent));
}

.btn-secondary {
    background: hsl(var(--secondary));
}

.dashboard-grid {
    flex: 1;
    display: grid;
    grid-template-columns: repeat(12, 1fr);
    gap: 1rem;
    padding: 1rem 2rem;
}

.widget-container {
    min-height: 200px;
}

.widget-card {
    height: 100%;
    background: hsl(var(--card));
    border: 1px solid hsl(var(--border));
    border-radius: var(--radius);
    display: flex;
    flex-direction: column;
    box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
    transition: all 0.2s ease;
}

.widget-card:hover {
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

.widget-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem;
    border-bottom: 1px solid hsl(var(--border));
}

.widget-title {
    font-size: 1rem;
    font-weight: 500;
}

.widget-controls {
    display: flex;
    gap: 0.25rem;
}

.widget-btn {
    padding: 0.25rem;
    background: transparent;
    border: none;
    cursor: pointer;
    border-radius: calc(var(--radius) * 0.5);
    transition: all 0.2s ease;
}

.widget-btn:hover {
    background: hsl(var(--accent));
}

.widget-content {
    flex: 1;
    padding: 1rem;
    display: flex;
    align-items: center;
    justify-content: center;
}

.chart-canvas {
    width: 100% !important;
    height: 100% !important;
    max-height: 300px;
}

.empty-chart, .empty-dashboard {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    color: hsl(var(--muted-foreground));
    padding: 2rem;
}

.empty-icon {
    font-size: 3rem;
    margin-bottom: 1rem;
    opacity: 0.5;
}

.dashboard-footer {
    padding: 1rem 2rem;
    border-top: 1px solid hsl(var(--border));
    text-align: center;
    color: hsl(var(--muted-foreground));
    font-size: 0.75rem;
    background: hsl(var(--card));
}

/* Responsive Design */
@media (max-width: 768px) {
    .dashboard-grid {
        grid-template-columns: 1fr;
        padding: 1rem;
    }
    
    .widget-container {
        grid-column: span 1 !important;
    }
    
    .dashboard-header {
        flex-direction: column;
        gap: 1rem;
        text-align: center;
        padding: 1rem;
    }
    
    .header-controls {
        justify-content: center;
    }
}

/* Loading States */
.loading {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 2rem;
}

.spinner {
    width: 2rem;
    height: 2rem;
    border: 2px solid hsl(var(--border));
    border-top: 2px solid hsl(var(--primary));
    border-radius: 50%;
    animation: spin 1s linear infinite;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}
        """.strip()
    
    async def generate_dashboard_js(self, config: Dict, data: Dict) -> str:
        """Generate JavaScript for chart rendering and interactivity"""
        
        return """
// Modern Dashboard JavaScript
class DashboardApp {
    constructor() {
        this.charts = new Map();
        this.data = window.DASHBOARD_DATA;
        this.config = window.DASHBOARD_CONFIG;
        this.init();
    }
    
    init() {
        console.log('Initializing dashboard with data:', this.data);
        this.renderCharts();
        this.setupEventListeners();
    }
    
    renderCharts() {
        const widgets = this.config.widgets || [];
        
        widgets.forEach(widget => {
            if (this.isChartType(widget.type)) {
                this.renderChart(widget);
            }
        });
    }
    
    isChartType(type) {
        return ['bar_chart', 'line_chart', 'pie_chart', 'area_chart', 'scatter_plot'].includes(type);
    }
    
    renderChart(widget) {
        const canvas = document.getElementById(`chart-${widget.id}`);
        if (!canvas) {
            console.warn(`Canvas not found for widget ${widget.id}`);
            return;
        }
        
        const ctx = canvas.getContext('2d');
        const chartData = this.getChartData(widget);
        
        if (!chartData || chartData.datasets.length === 0) {
            this.renderEmptyChart(canvas, 'No data available');
            return;
        }
        
        const chartConfig = this.getChartConfig(widget.type, chartData);
        
        try {
            const chart = new Chart(ctx, chartConfig);
            this.charts.set(widget.id, chart);
            console.log(`Rendered ${widget.type} for widget ${widget.id}`);
        } catch (error) {
            console.error(`Failed to render chart for widget ${widget.id}:`, error);
            this.renderEmptyChart(canvas, 'Failed to render chart');
        }
    }
    
    getChartData(widget) {
        // Get data from the widget's data source
        const dataSource = widget.data_source || widget.config?.data_source;
        if (!dataSource) {
            console.warn(`No data source specified for widget ${widget.id}`);
            return null;
        }
        
        const datasetData = this.data.datasets[dataSource];
        if (!datasetData || datasetData.error) {
            console.warn(`No valid data found for source ${dataSource}`);
            return null;
        }
        
        const rawData = datasetData.data || [];
        if (rawData.length === 0) {
            return null;
        }
        
        // Extract chart configuration
        const config = widget.config || {};
        const xField = config.x_field || Object.keys(rawData[0] || {})[0];
        const yField = config.y_field || Object.keys(rawData[0] || {})[1];
        
        if (!xField || !yField) {
            console.warn(`Missing field configuration for widget ${widget.id}`);
            return null;
        }
        
        // Process data based on chart type
        return this.processChartData(widget.type, rawData, xField, yField);
    }
    
    processChartData(chartType, rawData, xField, yField) {
        const labels = rawData.map(row => row[xField]).slice(0, 20); // Limit to 20 points
        const values = rawData.map(row => parseFloat(row[yField]) || 0).slice(0, 20);
        
        switch (chartType) {
            case 'pie_chart':
                return {
                    labels: labels,
                    datasets: [{
                        data: values,
                        backgroundColor: this.getChartColors(labels.length),
                        borderWidth: 1
                    }]
                };
                
            default:
                return {
                    labels: labels,
                    datasets: [{
                        label: yField,
                        data: values,
                        backgroundColor: 'hsl(222.2, 84%, 4.9%)',
                        borderColor: 'hsl(222.2, 84%, 4.9%)',
                        borderWidth: 2,
                        fill: chartType === 'area_chart'
                    }]
                };
        }
    }
    
    getChartConfig(type, data) {
        const baseConfig = {
            data: data,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: type === 'pie_chart'
                    }
                }
            }
        };
        
        switch (type) {
            case 'bar_chart':
                return { ...baseConfig, type: 'bar' };
            case 'line_chart':
                return { ...baseConfig, type: 'line' };
            case 'area_chart':
                return { ...baseConfig, type: 'line' };
            case 'pie_chart':
                return { ...baseConfig, type: 'pie' };
            case 'scatter_plot':
                return { ...baseConfig, type: 'scatter' };
            default:
                return { ...baseConfig, type: 'bar' };
        }
    }
    
    getChartColors(count) {
        const colors = [
            'hsl(222.2, 84%, 4.9%)',
            'hsl(210, 40%, 96%)',
            'hsl(210, 40%, 96%)',
            'hsl(215.4, 16.3%, 46.9%)',
            'hsl(214.3, 31.8%, 91.4%)'
        ];
        
        return Array(count).fill(0).map((_, i) => colors[i % colors.length]);
    }
    
    renderEmptyChart(canvas, message) {
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = 'hsl(215.4, 16.3%, 46.9%)';
        ctx.font = '14px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(message, canvas.width / 2, canvas.height / 2);
    }
    
    setupEventListeners() {
        // Global functions for button clicks
        window.refreshDashboard = () => {
            window.location.reload();
        };
        
        window.exportDashboard = () => {
            this.exportDashboard();
        };
        
        window.toggleFullscreen = () => {
            if (document.fullscreenElement) {
                document.exitFullscreen();
            } else {
                document.documentElement.requestFullscreen();
            }
        };
        
        window.refreshWidget = (widgetId) => {
            const chart = this.charts.get(widgetId);
            if (chart) {
                chart.update();
            }
        };
        
        window.exportWidget = (widgetId) => {
            const canvas = document.getElementById(`chart-${widgetId}`);
            if (canvas) {
                const link = document.createElement('a');
                link.download = `widget-${widgetId}.png`;
                link.href = canvas.toDataURL();
                link.click();
            }
        };
    }
    
    exportDashboard() {
        // Simple implementation - could be enhanced
        const dashboardName = this.config.name || 'Dashboard';
        const exportData = {
            name: dashboardName,
            data: this.data,
            config: this.config,
            exported_at: new Date().toISOString()
        };
        
        const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `${dashboardName.replace(/[^a-z0-9]/gi, '_').toLowerCase()}_export.json`;
        link.click();
        URL.revokeObjectURL(url);
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new DashboardApp();
});
        """.strip()
    
    async def save_static_files(
        self, 
        dashboard_id: str,
        user_id: str, 
        files: Dict[str, str]
    ) -> Dict[str, str]:
        """Save static files to disk"""
        
        # Create user directory
        user_dir = self.output_dir / user_id
        user_dir.mkdir(exist_ok=True)
        
        saved_files = {}
        
        for filename, content in files.items():
            if filename == "index.html":
                file_path = user_dir / f"{dashboard_id}.html"
                saved_files["html_path"] = f"/out/dashboards/{user_id}/{dashboard_id}.html"
            else:
                file_path = user_dir / f"{dashboard_id}_{filename}"
                saved_files[filename] = str(file_path)
            
            # Write file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"Saved static file: {file_path}")
        
        return saved_files
