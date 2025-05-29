"use client"

import React from 'react'
import {
  ResponsiveContainer,
  BarChart as RechartsBarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  PieChart as RechartsPieChart,
  Pie,
  LineChart as RechartsLineChart,
  Line,
  Cell,
  AreaChart as RechartsAreaChart,
  Area
} from 'recharts'

interface ChartData {
  name: string
  value: number
  fill?: string
}

interface ChartProps {
  data: ChartData[]
  color?: string
  height?: number
  categories?: string[]
  colors?: string[]
}

export function BarChart({ data, color = '#8884d8', height = 300 }: ChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <RechartsBarChart
        data={data}
        margin={{
          top: 20,
          right: 30,
          left: 20,
          bottom: 5,
        }}
      >
        <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
        <XAxis 
          dataKey="name" 
          tick={{ fill: 'var(--muted-foreground)' }}
          stroke="var(--border)"
        />
        <YAxis 
          tick={{ fill: 'var(--muted-foreground)' }}
          stroke="var(--border)"
        />
        <Tooltip 
          contentStyle={{ 
            backgroundColor: 'var(--card)',
            borderColor: 'var(--border)',
            borderRadius: '6px',
            color: 'var(--foreground)'
          }}
          cursor={{ fill: 'var(--muted)' }}
        />
        <Bar dataKey="value" fill={color} radius={[4, 4, 0, 0]} />
      </RechartsBarChart>
    </ResponsiveContainer>
  )
}

export function PieChart({ data, height = 300 }: ChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <RechartsPieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          labelLine={false}
          outerRadius={100}
          fill="#8884d8"
          dataKey="value"
          label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
        >
          {data.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.fill || `#${Math.floor(Math.random()*16777215).toString(16)}`} />
          ))}
        </Pie>
        <Tooltip 
          contentStyle={{ 
            backgroundColor: 'var(--card)',
            borderColor: 'var(--border)',
            borderRadius: '6px',
            color: 'var(--foreground)'
          }}
        />
      </RechartsPieChart>
    </ResponsiveContainer>
  )
}

export function LineChart({ data, color = '#8884d8', height = 300 }: ChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <RechartsLineChart
        data={data}
        margin={{
          top: 20,
          right: 30,
          left: 20,
          bottom: 5,
        }}
      >
        <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
        <XAxis 
          dataKey="name" 
          tick={{ fill: 'var(--muted-foreground)' }}
          stroke="var(--border)"
        />
        <YAxis 
          tick={{ fill: 'var(--muted-foreground)' }}
          stroke="var(--border)"
        />
        <Tooltip
          contentStyle={{ 
            backgroundColor: 'var(--card)',
            borderColor: 'var(--border)',
            borderRadius: '6px',
            color: 'var(--foreground)'
          }}
        />
        <Line
          type="monotone"
          dataKey="value"
          stroke={color}
          strokeWidth={2}
          dot={{ fill: color, strokeWidth: 2, r: 4 }}
          activeDot={{ r: 6 }}
        />
      </RechartsLineChart>
    </ResponsiveContainer>
  )
}

interface GaugeProps {
  value: number
  max: number
  label: string
  color?: string
}

export function AreaChart({ data, categories = [], colors = ['#8884d8'], height = 300 }: any) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <RechartsAreaChart
        data={data}
        margin={{
          top: 20,
          right: 30,
          left: 20,
          bottom: 5,
        }}
      >
        <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
        <XAxis 
          dataKey="name" 
          tick={{ fill: 'var(--muted-foreground)' }}
          stroke="var(--border)"
        />
        <YAxis 
          tick={{ fill: 'var(--muted-foreground)' }}
          stroke="var(--border)"
        />
        <Tooltip 
          contentStyle={{ 
            backgroundColor: 'var(--card)',
            borderColor: 'var(--border)',
            borderRadius: '6px',
            color: 'var(--foreground)'
          }}
        />
        {categories.map((category: string, index: number) => (
          <Area
            key={category}
            type="monotone"
            dataKey={category}
            stackId="1"
            stroke={colors[index % colors.length]}
            fill={colors[index % colors.length]}
            fillOpacity={0.8}
          />
        ))}
      </RechartsAreaChart>
    </ResponsiveContainer>
  )
}

export function Gauge({ value, max, label, color = '#8884d8' }: GaugeProps) {
  const percentage = (value / max) * 100
  
  return (
    <div className="relative w-full h-full flex flex-col items-center justify-center">
      <svg
        className="w-32 h-32"
        viewBox="0 0 100 100"
      >
        {/* Background circle */}
        <circle
          cx="50"
          cy="50"
          r="45"
          fill="none"
          stroke="var(--muted)"
          strokeWidth="10"
          strokeDasharray={`calc(${Math.PI * 90} * 0.75)`}
          strokeDashoffset={`calc(${Math.PI * 90} * 0.25)`}
          strokeLinecap="round"
          transform="rotate(-90 50 50)"
        />
        {/* Foreground circle */}
        <circle
          cx="50"
          cy="50"
          r="45"
          fill="none"
          stroke={color}
          strokeWidth="10"
          strokeDasharray={`calc(${Math.PI * 90} * 0.75)`}
          strokeDashoffset={`calc(${Math.PI * 90} * ${0.75 - (percentage / 100) * 0.75} + ${Math.PI * 90} * 0.25)`}
          strokeLinecap="round"
          transform="rotate(-90 50 50)"
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="text-2xl font-bold">{value}</span>
        <span className="text-xs text-muted-foreground">{label}</span>
      </div>
    </div>
  )
}
