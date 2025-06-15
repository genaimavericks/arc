"use client"

import { useState, useEffect } from "react"
import * as echarts from 'echarts/core'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ArrowUp, ArrowDown, Clock, Wrench, AlertTriangle, Activity, Settings, AlertCircle } from "lucide-react"
import ReactECharts from 'echarts-for-react'
import { cn } from "@/lib/utils"

export default function OperationsDashboard() {
  const [operationsData, setOperationsData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true)
      try {
        const { fetchOperationsData } = await import('@/app/factory_dashboard/services/api');
        
        try {
          const data = await fetchOperationsData();
          setOperationsData(data);
        } catch (apiError) {
          console.error("API error, using fallback data:", apiError);
          
          const fallbackData = {
            machine_utilization: [
              { name: "Extruder A", utilization: 78.5, uptime: 92.1, maintenance_cost: 34000 },
              { name: "Extruder B", utilization: 71.2, uptime: 88.5, maintenance_cost: 28000 },
              { name: "Mixer C", utilization: 85.3, uptime: 95.2, maintenance_cost: 22000 },
              { name: "Cutter D", utilization: 65.8, uptime: 86.7, maintenance_cost: 41000 },
              { name: "Packaging E", utilization: 68.2, uptime: 89.4, maintenance_cost: 18000 }
            ],
            downtime_reasons: [
              { reason: "Maintenance", hours: 348, percentage: 28 },
              { reason: "Equipment Failure", hours: 289, percentage: 23 },
              { reason: "Material Shortage", hours: 226, percentage: 18 },
              { reason: "Setup/Changeover", hours: 201, percentage: 16 },
              { reason: "Quality Issues", hours: 113, percentage: 9 },
              { reason: "Other", hours: 73, percentage: 6 }
            ],
            cycle_time: {
              product_categories: ["Standard", "Premium", "Specialty", "Custom"],
              data: [
                { name: "Setup Time", data: [12, 18, 25, 32] },
                { name: "Processing Time", data: [45, 52, 68, 82] },
                { name: "QC Time", data: [8, 12, 18, 22] },
                { name: "Packaging Time", data: [15, 18, 22, 30] }
              ]
            },
            maintenance_history: Array.from({ length: 12 }, (_, i) => ({
              month: `2024-${(i+1).toString().padStart(2, '0')}`,
              preventive: Math.floor(10000 + Math.random() * 5000),
              corrective: Math.floor(5000 + Math.random() * 10000)
            }))
          }
          
          setOperationsData(fallbackData);
        }
      } catch (error) {
        console.error("Failed to fetch operations data:", error);
      } finally {
        setLoading(false);
      }
    }
    
    fetchData()
  }, [])
  
  if (loading) {
    return (
      <div className="w-full h-64 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
      </div>
    )
  }
  
  if (!operationsData) {
    return (
      <div className="w-full p-8 text-center">
        <p className="text-muted-foreground">Failed to load operations data</p>
      </div>
    )
  }

  // Downtime Analysis Pie Chart
  const downtimeOptions = {
    tooltip: {
      trigger: 'item',
      formatter: '{a} <br/>{b}: {c.toFixed(2)} hours ({d.toFixed(2)}%)',
      backgroundColor: 'rgba(0,0,0,0.7)',
      borderRadius: 4,
      padding: [5, 10],
      textStyle: {
        color: '#fff'
      }
    },
    legend: {
      orient: 'horizontal',
      bottom: 0,
      left: 'center',
      data: operationsData.downtime_reasons.map((item: any) => item.reason),
      textStyle: {
        color: '#fff',
        backgroundColor: 'rgba(0,0,0,0.7)',
        padding: [2, 4],
        borderRadius: 3
      },
      itemWidth: 12,
      itemHeight: 12,
      itemGap: 10
    },
    series: [
      {
        name: 'Downtime',
        type: 'pie',
        radius: ['50%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 10,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: false,
          position: 'center'
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 20,
            fontWeight: 'bold'
          }
        },
        labelLine: {
          show: false
        },
        data: operationsData.downtime_reasons.map((item: any) => ({
          value: item.hours,
          name: item.reason,
        }))
      }
    ]
  }

  // Machine Performance Chart
  const machinePerformanceOptions = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      },
      formatter: function(params: any) {
        let tooltip = `${params[0].axisValue}<br/>`;
        params.forEach((param: any) => {
          tooltip += `${param.marker} ${param.seriesName}: ${param.value.toFixed(2)}%<br/>`;
        });
        return tooltip;
      },
      backgroundColor: 'rgba(0,0,0,0.7)',
      borderRadius: 4,
      padding: [5, 10],
      textStyle: {
        color: '#fff'
      }
    },
    legend: {
      data: ['Utilization', 'Uptime'],
      top: 0,
      textStyle: {
        color: '#fff',
        backgroundColor: 'rgba(0,0,0,0.7)',
        padding: [2, 4],
        borderRadius: 3
      },
      itemWidth: 12,
      itemHeight: 12
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'value',
      max: 100,
      name: '%'
    },
    yAxis: {
      type: 'category',
      data: operationsData.machine_utilization.map((item: any) => item.name)
    },
    series: [
      {
        name: 'Utilization',
        type: 'bar',
        data: operationsData.machine_utilization.map((item: any) => item.utilization),
        itemStyle: {
          color: '#3b82f6'
        }
      },
      {
        name: 'Uptime',
        type: 'bar',
        data: operationsData.machine_utilization.map((item: any) => item.uptime),
        itemStyle: {
          color: '#10b981'
        }
      }
    ]
  }

  // Maintenance Cost & History
  const maintenanceHistoryOptions = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      }
    },
    legend: {
      data: ['Preventive', 'Corrective'],
      top: 0,
      textStyle: {
        color: '#fff',
        backgroundColor: 'rgba(0,0,0,0.7)',
        padding: [2, 4],
        borderRadius: 3
      },
      itemWidth: 12,
      itemHeight: 12
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: operationsData.maintenance_history.map((item: any) => {
        const date = new Date(item.month)
        return date.toLocaleString('default', { month: 'short' })
      })
    },
    yAxis: {
      type: 'value',
      name: 'Cost ($)'
    },
    series: [
      {
        name: 'Preventive',
        type: 'bar',
        stack: 'total',
        emphasis: {
          focus: 'series'
        },
        data: operationsData.maintenance_history.map((item: any) => item.preventive)
      },
      {
        name: 'Corrective',
        type: 'bar',
        stack: 'total',
        emphasis: {
          focus: 'series'
        },
        data: operationsData.maintenance_history.map((item: any) => item.corrective)
      }
    ]
  }

  // Cycle Time Analysis
  const cycleTimeOptions = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      }
    },
    legend: {
      data: operationsData.cycle_time.data.map((item: any) => item.name)
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: operationsData.cycle_time.product_categories
    },
    yAxis: {
      type: 'value',
      name: 'Minutes'
    },
    series: operationsData.cycle_time.data.map((item: any) => ({
      name: item.name,
      type: 'bar',
      stack: 'total',
      emphasis: {
        focus: 'series'
      },
      data: item.data
    }))
  }

  return (
    <>
      {/* Key Metrics Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Avg Machine Utilization
            </CardTitle>
            <Settings className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {(operationsData.machine_utilization.reduce((acc: number, cur: any) => acc + cur.utilization, 0) / 
                operationsData.machine_utilization.length).toFixed(2)}%
            </div>
            <p className="text-xs text-muted-foreground">
              <span className="text-amber-500 font-medium flex items-center">
                <ArrowDown className="h-3 w-3 mr-1" />
                2.3%
              </span>{" "}
              vs. target (75%)
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Total Downtime
            </CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {operationsData.downtime_reasons.reduce((acc: number, cur: any) => acc + cur.hours, 0)} hrs
            </div>
            <p className="text-xs text-muted-foreground">
              <span className="text-rose-500 font-medium flex items-center">
                <ArrowUp className="h-3 w-3 mr-1" />
                15.2%
              </span>{" "}
              vs. previous period
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Maintenance Costs
            </CardTitle>
            <Wrench className="h-5 w-5 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              ${operationsData.machine_utilization.reduce((acc: number, cur: any) => acc + cur.maintenance_cost, 0).toLocaleString()}
            </div>
            <p className="text-xs text-muted-foreground">
              <span className="text-emerald-500 font-medium flex items-center">
                <ArrowDown className="h-3 w-3 mr-1" />
                3.8%
              </span>{" "}
              vs. previous period
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Equipment Failures
            </CardTitle>
            <AlertTriangle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              28
            </div>
            <Badge className="bg-amber-400 hover:bg-amber-500">Investigate</Badge>
          </CardContent>
        </Card>
      </div>
      
      {/* Machine Performance & Downtime Analysis */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card className="col-span-1">
          <CardHeader>
            <CardTitle>Machine Performance</CardTitle>
            <CardDescription>Utilization & uptime by machine</CardDescription>
          </CardHeader>
          <CardContent className="h-[350px]">
            <ReactECharts 
              option={machinePerformanceOptions} 
              style={{ height: '100%', width: '100%' }}
              opts={{ renderer: 'canvas' }}
            />
          </CardContent>
        </Card>
        
        <Card className="col-span-1">
          <CardHeader>
            <CardTitle>Downtime Analysis</CardTitle>
            <CardDescription>Root causes of production downtime</CardDescription>
          </CardHeader>
          <CardContent className="h-[350px]">
            <ReactECharts 
              option={downtimeOptions} 
              style={{ height: '100%', width: '100%' }}
              opts={{ renderer: 'canvas' }}
            />
          </CardContent>
        </Card>
      </div>
      
      {/* Maintenance History & Cycle Time */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card className="col-span-1">
          <CardHeader>
            <CardTitle>Maintenance Costs</CardTitle>
            <CardDescription>Preventive vs corrective maintenance</CardDescription>
          </CardHeader>
          <CardContent className="h-[350px]">
            <ReactECharts 
              option={maintenanceHistoryOptions} 
              style={{ height: '100%', width: '100%' }}
              opts={{ renderer: 'canvas' }}
            />
          </CardContent>
        </Card>
        
        <Card className="col-span-1">
          <CardHeader>
            <CardTitle>Production Cycle Time</CardTitle>
            <CardDescription>By product category and process stage</CardDescription>
          </CardHeader>
          <CardContent className="h-[350px]">
            <ReactECharts 
              option={cycleTimeOptions} 
              style={{ height: '100%', width: '100%' }}
              opts={{ renderer: 'canvas' }}
            />
          </CardContent>
        </Card>
      </div>
    </>
  )
}
