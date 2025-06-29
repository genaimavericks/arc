"use client"

import React from 'react'
import { 
  LineChart, 
  Line, 
  BarChart, 
  Bar,
  AreaChart,
  Area,
  PieChart,
  Pie,
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ResponsiveContainer, 
  LabelList,
  Cell
} from 'recharts'
import { Progress } from "@/components/ui/progress"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { BarChart2, PieChartIcon, LineChartIcon, AlertTriangle } from 'lucide-react'
import { UnifiedChatMessage } from './unified-chat'

// Props for the visualization component
interface MessageVisualizationProps {
  message: UnifiedChatMessage
}

// Chart color palette
const CHART_COLORS = [
  "#6366f1", // Indigo
  "#8b5cf6", // Violet
  "#ec4899", // Pink
  "#f43f5e", // Rose
  "#f97316", // Orange
  "#eab308", // Amber
  "#22c55e", // Green
  "#06b6d4"  // Cyan
]

// Helper to get chart type from query
const getChartType = (query: string, data: any[]): string => {
  const q = query.toLowerCase();
  if (q.includes('trend') || q.includes('time series') || q.includes('over time')) {
    return 'line';
  }
  if (q.includes('compare') || q.includes('distribution') || q.includes('breakdown')) {
    return 'bar';
  }
  if (data.length <= 5) {
    return 'pie';
  }
  return 'bar';
};

// Helper to format data for charting
const formatPredictionData = (data: any, query: string, source: string): { name: any; value: any }[] => {
  try {
    if (!data) return [];

    // Handle KG Insights data structure (typically an object with a 'visualization' key)
    if (source === 'kginsights') {
      const viz = data.visualization || data;

      // Case 1: x_axis and y_axis format
      if (viz.x_axis?.values && viz.y_axis?.values) {
        const xValues = viz.x_axis.values;
        const yValues = viz.y_axis.values;
        if (xValues.length === yValues.length) {
          return xValues.map((x: any, i: number) => ({ name: String(x), value: Number(yValues[i]) }));
        }
      }

      // Case 2: labels and values format
      if (viz.labels && viz.values) {
        const labels = viz.labels;
        const values = viz.values;
        if (labels.length === values.length) {
          return labels.map((label: any, i: number) => ({ name: String(label), value: Number(values[i]) }));
        }
      }

      // Case 3: raw_data with explicit keys
      if (viz.raw_data && Array.isArray(viz.raw_data) && viz.raw_data.length > 0) {
          const rawData = viz.raw_data;
          const xAxisKey = viz.x_axis_label || Object.keys(rawData[0])[0];
          const yAxisKey = viz.y_axis_label || Object.keys(rawData[0])[1];
          if (xAxisKey && yAxisKey) {
              return rawData.map((item: any) => ({ name: String(item[xAxisKey]), value: Number(item[yAxisKey]) }));
          }
      }
      
      return [];
    }

    // Handle Astro data structure (typically an array of objects)
        if (source === 'factory_astro' && Array.isArray(data) && data.length > 0) {
      const yAxisKey = 'prediction';
      const potentialXAxisKeys = Object.keys(data[0]).filter(
        key => !['prediction', 'year', 'factory'].includes(key.toLowerCase())
      );
      
      const q = query.toLowerCase();
      let xAxisKey = potentialXAxisKeys[0] || 'name';

      if (q.includes('month')) {
          const monthKey = Object.keys(data[0]).find(k => k.toLowerCase() === 'month');
          if (monthKey) xAxisKey = monthKey;
      } else if (q.includes('factory')) {
          const factoryKey = Object.keys(data[0]).find(k => k.toLowerCase() === 'factory');
          if (factoryKey) xAxisKey = factoryKey;
      }
      
      if (!data[0].hasOwnProperty(xAxisKey) || !data[0].hasOwnProperty(yAxisKey)) {
          console.error("Astro data items are missing required keys for charting:", { xAxisKey, yAxisKey });
          return [];
      }

      return data.map(item => ({
        name: item[xAxisKey],
        value: item[yAxisKey]
      }));
    }

    return [];
  } catch (error) {
    console.error("Error formatting chart data:", error);
    return [];
  }
};

// Helper to get Y-axis label from query
const getYAxisLabel = (query: string): string => {
    const q = query.toLowerCase();
    if (q.includes('profit margin')) return 'Profit Margin (%)';
    if (q.includes('production volume')) return 'Production Volume (units)';
    if (q.includes('co2 emissions')) return 'CO2 Emissions (kg)';
    if (q.includes('energy consumption')) return 'Energy Consumption (kWh)';
    if (q.includes('machine utilization')) return 'Machine Utilization (%)';
    if (q.includes('water usage')) return 'Water Usage (liters)';
    return 'Prediction';
};

// Main visualization component
export default function MessageVisualization({ message }: MessageVisualizationProps) {
  const { predictionData, source, content, userQuery } = message;


  if (!predictionData) {
    return (
      <Alert className="mt-3">
        <AlertTriangle className="h-4 w-4" />
        <AlertDescription>No visualization data available.</AlertDescription>
      </Alert>
    );
  }

  // Handle Churn Astro specific visualizations
  if (source === 'churn_astro') {
    if (predictionData && predictionData.probability !== undefined && predictionData.feature_importance) {
      return (
        <div className="space-y-4 mt-3 w-full max-w-2xl mx-auto">
          {renderChurnProbability(predictionData)}
          {renderFeatureImportance(predictionData.feature_importance)}
        </div>
      );
    }
    // Fallback for churn if data is not in the expected format
    return (
      <Alert className="mt-3">
        <AlertTriangle className="h-4 w-4" />
        <AlertDescription>Could not display Churn Astro visualization. Data format is incorrect.</AlertDescription>
      </Alert>
    );
  }

  // Handle KG Insights and Factory Astro visualizations
  if (source === 'kginsights' || source === 'factory_astro') {
    const queryForFormatting = userQuery || content;
    const formattedData = formatPredictionData(predictionData, queryForFormatting, source);

    if (!formattedData || formattedData.length === 0) {
      return (
        <Alert className="mt-3">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>No visualization data available or data could not be formatted.</AlertDescription>
        </Alert>
      );
    }

    const chartType = getChartType(queryForFormatting, formattedData);
    const xAxisLabel = predictionData?.visualization?.x_axis_label || predictionData?.x_axis?.label || 'Category';
    let yAxisLabel = predictionData?.visualization?.y_axis_label || predictionData?.y_axis?.label || 'Value';
    let yAxisDomain: [number, number] | undefined = undefined;

    if (source === 'factory_astro') {
      yAxisLabel = getYAxisLabel(queryForFormatting);
      yAxisDomain = calculateYAxisDomain(formattedData, queryForFormatting);
    }

    const chartTitle = predictionData.title || predictionData.visualization?.title || (
      chartType === 'line' ? 'Trend Analysis' :
      chartType === 'bar' ? 'Comparative Analysis' :
      chartType === 'pie' ? 'Distribution Analysis' : 'Data Visualization'
    );

    const sourceName = source === 'kginsights' ? 'KG Insights' : 'Factory Astro';

    return (
      <Card className="mt-3 overflow-hidden">
        <CardHeader className="py-3 px-4 bg-muted/40">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              {chartType === 'line' && <LineChartIcon className="h-4 w-4" />}
              {chartType === 'bar' && <BarChart2 className="h-4 w-4" />}
              {chartType === 'pie' && <PieChartIcon className="h-4 w-4" />}
              {chartTitle}
            </CardTitle>
            <Badge variant="outline" className="text-xs">{sourceName}</Badge>
          </div>
        </CardHeader>
        <CardContent className="p-4">
          <div style={{ width: '100%', height: '300px' }}>
            <ResponsiveContainer width="100%" height="100%">
              {renderChart(chartType, formattedData, xAxisLabel, yAxisLabel, yAxisDomain)}
            </ResponsiveContainer>
          </div>
          {predictionData.description && (
            <p className="mt-3 text-sm text-muted-foreground">{predictionData.description}</p>
          )}
        </CardContent>
      </Card>
    );
  }

  // Fallback for any other source type
  return (
    <Alert className="mt-3">
      <AlertTriangle className="h-4 w-4" />
      <AlertDescription>This message type does not support visualization.</AlertDescription>
    </Alert>
  );
};

// Function to render the appropriate chart based on type
const renderChart = (chartType: string, data: any[], xAxisLabel: string, yAxisLabel: string, yAxisDomain?: [number, number]) => {
  switch(chartType) {
    case 'line':
      return (
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis 
            dataKey="name" 
            label={xAxisLabel ? { value: xAxisLabel, position: 'insideBottom', offset: -5 } : undefined} 
            tick={{ fontSize: 12 }}
          />
          <YAxis 
            label={yAxisLabel ? { value: yAxisLabel, angle: -90, position: 'insideLeft' } : undefined}
            tick={{ fontSize: 12 }}
          />
          <Tooltip />
          <Legend />
          <Line 
            type="monotone" 
            dataKey="value" 
            stroke={CHART_COLORS[0]} 
            activeDot={{ r: 8 }}
            name={yAxisLabel || 'Value'} 
          />
        </LineChart>
      )
      
    case 'bar':
      return (
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis 
            dataKey="name" 
            label={xAxisLabel ? { value: xAxisLabel, position: 'insideBottom', offset: -5 } : undefined}
            tick={{ fontSize: 12 }}
          />
          <YAxis 
            label={yAxisLabel ? { value: yAxisLabel, angle: -90, position: 'insideLeft' } : undefined}
            tick={{ fontSize: 12 }}
          />
          <Tooltip />
          <Legend />
          <Bar 
            dataKey="value" 
            fill={CHART_COLORS[0]}
            name={yAxisLabel || 'Value'}
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
            ))}
          </Bar>
        </BarChart>
      )
      
    case 'pie':
      return (
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            labelLine={false}
            outerRadius={80}
            fill="#8884d8"
            dataKey="value"
            nameKey="name"
            label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
            ))}
          </Pie>
          <Tooltip />
          <Legend />
        </PieChart>
      )
      
    default:
      return (
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="name" />
          <YAxis domain={yAxisDomain} />
          <Tooltip />
          <Legend />
          <Bar dataKey="value" fill={CHART_COLORS[0]} />
        </BarChart>
      )
  }
}

// Render churn probability
function renderChurnProbability(data: any) {
  const probability = data.probability || 0
  const formattedProbability = (probability * 100).toFixed(1)
  const riskLevel = getRiskLevel(probability)
  
  return (
    <Card className="mt-3">
      <CardHeader className="py-3 px-4 bg-muted/40">
        <CardTitle className="text-sm font-medium">Churn Probability</CardTitle>
      </CardHeader>
      
      <CardContent className="p-4">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Risk Level:</span>
            <Badge 
              className={
                riskLevel === 'High' ? 'bg-red-500' : 
                riskLevel === 'Medium' ? 'bg-yellow-500' : 
                'bg-green-500'
              }
            >
              {riskLevel}
            </Badge>
          </div>
          
          <div>
            <div className="flex justify-between text-xs mb-1">
              <span>0%</span>
              <span>{formattedProbability}%</span>
              <span>100%</span>
            </div>
            <Progress value={parseFloat(formattedProbability)} className="h-3" />
          </div>
          
          <p className="text-sm text-muted-foreground mt-2">
            The customer has a {formattedProbability}% probability of churning based on the provided information.
          </p>
        </div>
      </CardContent>
    </Card>
  )
}

// Render feature importance
function renderFeatureImportance(featureImportance: any[]) {
  // Sort features by importance
  const sortedFeatures = [...featureImportance].sort((a, b) => b.importance - a.importance)
  
  return (
    <Card className="mt-3">
      <CardHeader className="py-3 px-4 bg-muted/40">
        <CardTitle className="text-sm font-medium">Feature Importance</CardTitle>
      </CardHeader>
      
      <CardContent className="p-4">
        <div className="space-y-3">
          {sortedFeatures.map((feature, index) => (
            <div key={index} className="space-y-1">
              <div className="flex justify-between text-sm">
                <span>{feature.feature}</span>
                <span className="font-medium">{(feature.importance * 100).toFixed(1)}%</span>
              </div>
              <Progress value={feature.importance * 100} className="h-2" />
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

// Calculate optimal Y-axis domain based on data range
const calculateYAxisDomain = (data: any[], query: string): [number, number] => {
  if (!data || data.length === 0) {
    return [0, 100]; // Default domain
  }

  const values = data.map(d => d.value).filter(v => typeof v === 'number');
  if (values.length === 0) {
    return [0, 100];
  }

  let min = Math.min(...values);
  let max = Math.max(...values);

  // If the query is about profit margin, the domain should be percentage-based
  if (query.toLowerCase().includes('profit margin')) {
    min = Math.max(0, min); // Margin shouldn't be negative in this context
    max = Math.min(100, max);
    return [min, max];
  }

  // Add padding to the domain for better visualization
  const range = max - min;
  let padding = range * 0.1;
  if (range === 0) {
    padding = max * 0.1 || 10; // Handle case where all values are the same
  }

  let domainMin = Math.floor(min - padding);
  let domainMax = Math.ceil(max + padding);

  // Ensure domain is not negative unless data is negative
  if (min >= 0) {
    domainMin = Math.max(0, domainMin);
  }

  return [domainMin, domainMax];
};


// Helper to determine risk level based on probability
function getRiskLevel(probability: number): 'Low' | 'Medium' | 'High' {
  if (probability < 0.3) return 'Low'
  if (probability < 0.7) return 'Medium'
  return 'High'
}
