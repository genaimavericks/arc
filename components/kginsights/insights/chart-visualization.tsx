"use client"

import { useState } from "react"
import { 
  Card, 
  CardContent, 
  CardHeader, 
  CardTitle, 
  CardDescription 
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { 
  BarChart, 
  LineChart, 
  PieChart, 
  Bar, 
  Cell, 
  Line,
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ResponsiveContainer,
  Pie
} from "recharts"

// Define the theme interface
export interface ChartTheme {
  colors: string[]
  backgroundColor?: string
  textColor?: string
  gridColor?: string
  axisColor?: string
  tooltipBackground?: string
  tooltipText?: string
  tooltipBorder?: string
}

// Default theme settings
const defaultTheme: ChartTheme = {
  colors: ["#6366f1", "#8b5cf6", "#ec4899", "#f43f5e", "#f97316", "#eab308", "#22c55e", "#06b6d4"],
  backgroundColor: "transparent",
  textColor: "#64748b", 
  gridColor: "#e2e8f0",
  axisColor: "#94a3b8",
  tooltipBackground: "#ffffff",
  tooltipText: "#1e293b",
  tooltipBorder: "#e2e8f0"
}

// Sample data for testing
const SAMPLE_DATA = [
  { name: "Jan", value: 40 },
  { name: "Feb", value: 65 },
  { name: "Mar", value: 35 },
  { name: "Apr", value: 78 },
  { name: "May", value: 56 }
]

// Component props interface
interface ChartVisualizationProps {
  data: any
  chartType: "bar" | "pie" | "line" | "histogram" | "heatmap" | "none"
  title?: string
  description?: string
  className?: string
  theme?: ChartTheme
}

export function ChartVisualization({ 
  data, 
  chartType = "bar", 
  title = "Data Visualization", 
  description,
  className = "",
  theme = defaultTheme
}: ChartVisualizationProps) {
  // No debug state needed

  // Normalize chart type to lowercase and map to supported types
  const getNormalizedChartType = () => {
    const type = chartType?.toLowerCase() || "bar"
    
    // Map certain chart types to implementations we support
    if (type === "histogram") return "bar"
    if (type === "heatmap") return "bar"  // Fallback to bar for unsupported types
    if (type === "none") return "bar"
    
    return type
  }
  
  const normalizedChartType = getNormalizedChartType()
  
  // Format the chart data from various possible structures
  const formatChartData = () => {
    
    try {
      // Check for valid data
      if (!data) {
        console.warn("No data provided to ChartVisualization")
        return []
      }
      
      // For API data from visualization_analyzer.py
      if (data.visualization) {
        const viz = data.visualization
        
        // Case 1: x_axis and y_axis format
        if (viz.x_axis?.values && viz.y_axis?.values) {
          const xValues = viz.x_axis.values
          const yValues = viz.y_axis.values
          
          if (xValues.length === yValues.length) {
            return xValues.map((x: any, i: number) => ({
              name: String(x),
              value: Number(yValues[i])
            }))
          }
        }
        
        // Case 2: labels and values format
        if (viz.labels && viz.values) {
          const labels = viz.labels
          const values = viz.values
          
          if (labels.length === values.length) {
            return labels.map((label: any, i: number) => ({
              name: String(label),
              value: Number(values[i])
            }))
          }
        }
        
        // Case 3: Using raw data objects 
        if (viz.data && Array.isArray(viz.data)) {
          return viz.data.map((item: any) => ({
            name: String(item.name || item.label || item.category || ''),
            value: Number(item.value || item.count || 0)
          }))
        }
      }
      
      // Direct access to properties - legacy format 
      if (data.x_axis?.values && data.y_axis?.values) {
        const xValues = data.x_axis.values
        const yValues = data.y_axis.values
        
        if (xValues.length === yValues.length) {
          return xValues.map((x: any, i: number) => ({
            name: String(x),
            value: Number(yValues[i])
          }))
        }
      }
      
      // Direct labels and values
      if (data.labels && data.values) {
        const labels = data.labels
        const values = data.values
        
        if (labels.length === values.length) {
          return labels.map((label: any, i: number) => ({
            name: String(label),
            value: Number(values[i])
          }))
        }
      }
      
      // If we have a direct array
      if (Array.isArray(data)) {
        return data.map((item: any) => {
          // Ensure name and value properties
          if (item && typeof item === 'object') {
            return {
              name: String(item.name || item.label || item.key || ''),
              value: Number(item.value || item.count || 0)
            }
          }
          return { name: '', value: 0 }
        })
      }
      
      // No recognizable format found
      console.warn("Could not recognize chart data format")
      return []
    } catch (error) {
      console.error("Error formatting chart data:", error)
      return []
    }
  }
  
  // Get the formatted chart data
  const chartData = formatChartData()
  
  // Check if we have valid data to display
  const hasData = chartData && chartData.length > 0
  
  // Render the appropriate chart based on type
  const renderChart = () => {
    // If no data, show empty state
    if (!hasData) {
      return (
        <div className="flex items-center justify-center h-full">
          <div className="text-center text-gray-500">
            <p className="text-sm">No data available for visualization</p>
          </div>
        </div>
      )
    }
    
    // Based on chart type, render appropriate Recharts component
    switch (normalizedChartType) {
      case "line":
        return (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke={theme.gridColor} />
              <XAxis 
                dataKey="name" 
                tick={{ fill: theme.textColor }}
                stroke={theme.axisColor || theme.gridColor}
              />
              <YAxis 
                tick={{ fill: theme.textColor }}
                stroke={theme.axisColor || theme.gridColor}
              />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: theme.tooltipBackground || "#ffffff",
                  color: theme.tooltipText || "#000000",
                  border: `1px solid ${theme.tooltipBorder || "#e2e8f0"}`
                }}
              />
              <Legend />
              <Line 
                type="monotone" 
                dataKey="value" 
                stroke={theme.colors[0]} 
                activeDot={{ r: 6 }}
                strokeWidth={2}
              />
            </LineChart>
          </ResponsiveContainer>
        )
        
      case "pie":
        return (
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                outerRadius={80}
                label
              >
                {chartData.map((entry: any, index: number) => (
                  <Cell 
                    key={`cell-${index}`} 
                    fill={theme.colors[index % theme.colors.length]} 
                  />
                ))}
              </Pie>
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: theme.tooltipBackground || "#ffffff",
                  color: theme.tooltipText || "#000000",
                  border: `1px solid ${theme.tooltipBorder || "#e2e8f0"}`
                }}
              />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        )
        
      // Default to bar chart
      default:
        return (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke={theme.gridColor} />
              <XAxis 
                dataKey="name" 
                tick={{ fill: theme.textColor }}
                stroke={theme.axisColor || theme.gridColor}
              />
              <YAxis 
                tick={{ fill: theme.textColor }}
                stroke={theme.axisColor || theme.gridColor}
              />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: theme.tooltipBackground || "#ffffff",
                  color: theme.tooltipText || "#000000",
                  border: `1px solid ${theme.tooltipBorder || "#e2e8f0"}`
                }}
              />
              <Legend />
              <Bar 
                dataKey="value" 
                fill={theme.colors[0]}
                animationDuration={750}
              />
            </BarChart>
          </ResponsiveContainer>
        )
    }
  }
  
  // No debug data table needed
  
  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex justify-between items-center">
          <div>
            <CardTitle>{title}</CardTitle>
            {description && <CardDescription>{description}</CardDescription>}
          </div>
          
          {/* No debug controls */}
        </div>
      </CardHeader>
      
      <CardContent>
        {/* Chart container with fixed height */}
        <div className="h-64">
          {renderChart()}
        </div>
        
        {/* Clean UI with no debug displays */}
      </CardContent>
    </Card>
  )
}
