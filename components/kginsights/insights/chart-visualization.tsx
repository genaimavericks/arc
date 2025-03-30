"use client"

import { useState, useEffect, useRef } from "react"
import { 
  Card, 
  CardContent, 
  CardHeader, 
  CardTitle, 
  CardDescription 
} from "@/components/ui/card"
import { 
  BarChart, 
  LineChart, 
  PieChart, 
  Area, 
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

interface ChartVisualizationProps {
  data: any
  chartType: "bar" | "pie" | "line" | "histogram" | "heatmap" | "none"
  title?: string
  description?: string
  className?: string
  theme?: ChartTheme
}

export interface ChartTheme {
  colors: string[]
  backgroundColor?: string
  textColor?: string
  gridColor?: string
}

const defaultTheme: ChartTheme = {
  colors: ["#6366f1", "#8b5cf6", "#ec4899", "#f43f5e", "#f97316", "#eab308", "#22c55e", "#06b6d4"],
  backgroundColor: "transparent",
  textColor: "#64748b", 
  gridColor: "#e2e8f0"
}

export function ChartVisualization({ 
  data, 
  chartType, 
  title = "Data Visualization", 
  description,
  className = "",
  theme = defaultTheme
}: ChartVisualizationProps) {

  // Format data based on the chart type
  const formatChartData = () => {
    if (!data) return []

    if (chartType === "bar" || chartType === "line") {
      if (data.x_axis?.values && data.y_axis?.values) {
        return data.x_axis.values.map((label: string, index: number) => ({
          name: label,
          value: data.y_axis.values[index] || 0
        }))
      } else if (data.series) {
        return data.x_axis.values.map((label: string, index: number) => {
          const item: any = { name: label }
          data.series.forEach((series: any) => {
            item[series.name] = series.data[index] || 0
          })
          return item
        })
      }
    } else if (chartType === "pie") {
      if (data.labels && data.values) {
        return data.labels.map((label: string, index: number) => ({
          name: label,
          value: data.values[index] || 0
        }))
      }
    } else if (chartType === "histogram") {
      if (data.x_axis?.values && data.y_axis?.values) {
        return data.x_axis.values.map((label: string, index: number) => ({
          name: label,
          value: data.y_axis.values[index] || 0
        }))
      }
    }

    // Default fallback for raw data
    if (data.raw_data) {
      // Try to convert raw data to a chart format
      if (Array.isArray(data.raw_data)) {
        return data.raw_data
      } else if (typeof data.raw_data === 'object') {
        return Object.entries(data.raw_data).map(([key, value]) => ({
          name: key,
          value: typeof value === 'number' ? value : 0
        }))
      }
    }

    return []
  }

  const chartData = formatChartData()
  const isEmpty = !chartData || chartData.length === 0
  
  // Determine if the chart should use multi-series format
  const isMultiSeries = data?.series && data.series.length > 0
  
  // Extract colors from theme
  const colors = theme?.colors || defaultTheme.colors
  
  return (
    <Card className={`w-full shadow-sm ${className}`}>
      <CardHeader className="py-3">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        {description && (
          <CardDescription className="text-xs">{description}</CardDescription>
        )}
      </CardHeader>
      <CardContent className="p-2">
        {isEmpty ? (
          <div className="flex items-center justify-center h-40 bg-muted/30 rounded-md">
            <div className="text-center text-muted-foreground">
              <p className="text-sm">No visualization data available</p>
            </div>
          </div>
        ) : (
          <div className="h-60">
            <ResponsiveContainer width="100%" height="100%">
              {chartType === "bar" && (
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke={theme?.gridColor || defaultTheme.gridColor} />
                  <XAxis 
                    dataKey="name" 
                    tick={{ fill: theme?.textColor || defaultTheme.textColor }}
                    tickLine={{ stroke: theme?.textColor || defaultTheme.textColor }}
                  />
                  <YAxis 
                    tick={{ fill: theme?.textColor || defaultTheme.textColor }}
                    tickLine={{ stroke: theme?.textColor || defaultTheme.textColor }}
                  />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: theme?.backgroundColor || "#ffffff",
                      borderColor: theme?.gridColor || defaultTheme.gridColor,
                      color: theme?.textColor || defaultTheme.textColor
                    }} 
                  />
                  <Legend />
                  {isMultiSeries ? (
                    // Multi-series bar chart
                    data.series.map((series: any, index: number) => (
                      <Bar 
                        key={series.name}
                        dataKey={series.name} 
                        fill={colors[index % colors.length]} 
                      />
                    ))
                  ) : (
                    // Single series bar chart
                    <Bar 
                      dataKey="value" 
                      fill={colors[0]} 
                    />
                  )}
                </BarChart>
              )}
              
              {chartType === "line" && (
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke={theme?.gridColor || defaultTheme.gridColor} />
                  <XAxis 
                    dataKey="name" 
                    tick={{ fill: theme?.textColor || defaultTheme.textColor }}
                    tickLine={{ stroke: theme?.textColor || defaultTheme.textColor }}
                  />
                  <YAxis 
                    tick={{ fill: theme?.textColor || defaultTheme.textColor }}
                    tickLine={{ stroke: theme?.textColor || defaultTheme.textColor }}
                  />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: theme?.backgroundColor || "#ffffff", 
                      borderColor: theme?.gridColor || defaultTheme.gridColor,
                      color: theme?.textColor || defaultTheme.textColor
                    }} 
                  />
                  <Legend />
                  {isMultiSeries ? (
                    // Multi-series line chart
                    data.series.map((series: any, index: number) => (
                      <Line 
                        key={series.name}
                        type="monotone" 
                        dataKey={series.name} 
                        stroke={colors[index % colors.length]} 
                        activeDot={{ r: 6 }} 
                      />
                    ))
                  ) : (
                    // Single series line chart
                    <Line 
                      type="monotone" 
                      dataKey="value" 
                      stroke={colors[0]} 
                      activeDot={{ r: 6 }} 
                    />
                  )}
                </LineChart>
              )}
              
              {chartType === "pie" && (
                <PieChart>
                  <Pie
                    data={chartData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    label={(entry) => entry.name}
                    labelLine={true}
                  >
                    {chartData.map((entry: any, index: number) => (
                      <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
                    ))}
                  </Pie>
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: theme?.backgroundColor || "#ffffff", 
                      borderColor: theme?.gridColor || defaultTheme.gridColor,
                      color: theme?.textColor || defaultTheme.textColor
                    }} 
                  />
                  <Legend />
                </PieChart>
              )}
              
              {/* Render histogram as a bar chart */}
              {chartType === "histogram" && (
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke={theme?.gridColor || defaultTheme.gridColor} />
                  <XAxis 
                    dataKey="name" 
                    tick={{ fill: theme?.textColor || defaultTheme.textColor }}
                    tickLine={{ stroke: theme?.textColor || defaultTheme.textColor }}
                  />
                  <YAxis 
                    tick={{ fill: theme?.textColor || defaultTheme.textColor }}
                    tickLine={{ stroke: theme?.textColor || defaultTheme.textColor }}
                  />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: theme?.backgroundColor || "#ffffff", 
                      borderColor: theme?.gridColor || defaultTheme.gridColor,
                      color: theme?.textColor || defaultTheme.textColor
                    }} 
                  />
                  <Bar 
                    dataKey="value" 
                    fill={colors[0]} 
                  />
                </BarChart>
              )}
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
