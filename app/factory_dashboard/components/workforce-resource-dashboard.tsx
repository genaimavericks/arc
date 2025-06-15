"use client"

import { useState, useEffect } from "react"
import * as echarts from 'echarts/core'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ArrowUp, ArrowDown, Users, PackageCheck, Leaf, DollarSign, Star } from "lucide-react"
import ReactECharts from 'echarts-for-react'
import { cn } from "@/lib/utils"

export default function WorkforceResourceDashboard() {
  const [workforceData, setWorkforceData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true)
      try {
        const { fetchWorkforceData } = await import('@/app/factory_dashboard/services/api');
        
        try {
          const data = await fetchWorkforceData();
          setWorkforceData(data);
        } catch (apiError) {
          console.error("API error, using fallback data:", apiError);
          
          const fallbackData = {
            operator_performance: [
              { name: "Team Alpha", efficiency: 92.5, quality_score: 94.2, training_hours: 45 },
              { name: "Team Beta", efficiency: 85.3, quality_score: 91.7, training_hours: 38 },
              { name: "Team Gamma", efficiency: 78.9, quality_score: 87.5, training_hours: 32 },
              { name: "Team Delta", efficiency: 88.1, quality_score: 90.3, training_hours: 41 }
            ],
            shift_comparison: {
              shifts: ["Morning", "Afternoon", "Night"],
              metrics: [
                { name: "Production Volume", data: [38500, 35200, 27800] },
                { name: "Quality Score", data: [93.5, 91.8, 87.2] },
                { name: "Defect Rate", data: [2.8, 3.5, 5.1] }
              ]
            },
            resource_efficiency: {
              categories: ["Raw Material A", "Raw Material B", "Raw Material C", "Raw Material D", "Raw Material E"],
              data: [
                { name: "Usage Efficiency", data: [94.2, 88.7, 91.5, 86.9, 90.8] },
                { name: "Cost Efficiency", data: [87.5, 92.1, 85.3, 90.7, 88.2] }
              ]
            },
            environmental_metrics: [
              { name: "Energy per Unit", value: 4.2, target: 5.0, trend: "down", unit: "kWh" },
              { name: "Water Usage", value: 3.8, target: 4.0, trend: "down", unit: "gal" },
              { name: "CO2 per Unit", value: 0.75, target: 0.7, trend: "up", unit: "kg" },
              { name: "Waste Recycled", value: 85.3, target: 80.0, trend: "up", unit: "%" }
            ]
          };
          
          setWorkforceData(fallbackData);
        }
      } catch (error) {
        console.error("Failed to fetch workforce data:", error);
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
  
  if (!workforceData) {
    return (
      <div className="w-full p-8 text-center">
        <p className="text-muted-foreground">Failed to load workforce data</p>
      </div>
    )
  }

  // Operator Performance Scatter Chart
  const operatorPerformanceOptions = {
    tooltip: {
      trigger: 'item',
      formatter: function(params: any) {
        return `${params.data.name}<br/>Efficiency: ${params.data.value[0].toFixed(2)}%<br/>Quality: ${params.data.value[1].toFixed(2)}%<br/>Training: ${params.data.value[2]} hrs`
      },
      backgroundColor: 'rgba(0,0,0,0.7)',
      borderRadius: 4,
      padding: [5, 10],
      textStyle: {
        color: '#fff'
      }
    },
    xAxis: {
      type: 'value',
      name: 'Efficiency (%)',
      min: 75,
      max: 100
    },
    yAxis: {
      type: 'value',
      name: 'Quality Score (%)',
      min: 85,
      max: 100
    },
    series: [
      {
        type: 'scatter',
        symbolSize: function(data: any) {
          return data[2] / 2 // Training hours determine bubble size
        },
        data: workforceData.operator_performance.map((item: any) => ({
          name: item.name,
          value: [item.efficiency, item.quality_score, item.training_hours]
        })),
        itemStyle: {
          color: function(params: any) {
            const score = (params.data.value[0] + params.data.value[1]) / 2
            if (score >= 90) return '#10b981' // Green for high performers
            if (score >= 85) return '#3b82f6' // Blue for good performers
            return '#f59e0b' // Amber for needs improvement
          }
        },
        label: {
          show: true,
          formatter: function(value: any) {
            return value.toFixed(2) + '%';
          },
          position: 'top'
        },
        emphasis: {
          focus: 'self'
        }
      }
    ]
  }

  // Shift Comparison Radar Chart
  const shiftComparisonOptions = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: function(params: any) {
        let tooltip = params[0].axisValueLabel + '<br/>';
        params.forEach((param: any) => {
          tooltip += `${param.marker} ${param.seriesName}: ${param.value.toFixed(2)}<br/>`;
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
      bottom: 0,
      textStyle: {
        color: '#fff',
        backgroundColor: 'rgba(0,0,0,0.7)',
        padding: [2, 4],
        borderRadius: 3
      },
      itemWidth: 12,
      itemHeight: 12
    },
    radar: {
      indicator: [
        { name: 'Production Volume', max: 40000 },
        { name: 'Quality Score', max: 100 },
        { name: '100 - Defect Rate', max: 100 } // Inverting to make higher = better
      ]
    },
    series: [
      {
        type: 'radar',
        data: workforceData.shift_comparison.shifts.map((shift: string, index: number) => ({
          value: [
            workforceData.shift_comparison.metrics[0].data[index], // Production Volume
            workforceData.shift_comparison.metrics[1].data[index], // Quality Score
            100 - workforceData.shift_comparison.metrics[2].data[index] // 100 - Defect Rate
          ],
          name: shift,
          areaStyle: {
            opacity: 0.3
          }
        }))
      }
    ]
  }

  // Resource Efficiency Chart
  const resourceEfficiencyOptions = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      }
    },
    legend: {
      data: workforceData.resource_efficiency.data.map((item: any) => item.name)
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: workforceData.resource_efficiency.categories
    },
    yAxis: {
      type: 'value',
      name: '%',
      min: 80,
      max: 100
    },
    series: workforceData.resource_efficiency.data.map((item: any) => ({
      name: item.name,
      type: 'line',
      data: item.data,
      symbol: 'circle',
      symbolSize: 8,
      emphasis: {
        focus: 'series'
      }
    }))
  }

  // Environmental Performance Gauge Chart
  const getGaugeOptions = (metric: any) => {
    const isHigherBetter = metric.trend === "up"
    let status = 'normal'
    const percentOfTarget = (metric.value / metric.target) * 100
    
    if (isHigherBetter) {
      status = percentOfTarget >= 100 ? 'success' : 'warning'
    } else {
      status = percentOfTarget <= 100 ? 'success' : 'warning'
    }
    
    const colors = {
      success: '#10b981',
      warning: '#f59e0b',
      danger: '#ef4444',
      normal: '#3b82f6'
    }
    
    return {
      series: [
        {
          type: 'gauge',
          startAngle: 90,
          endAngle: -270,
          pointer: {
            show: false
          },
          progress: {
            show: true,
            overlap: false,
            roundCap: true,
            clip: false,
            itemStyle: {
              color: colors[status as keyof typeof colors]
            }
          },
          axisLine: {
            lineStyle: {
              width: 25
            }
          },
          splitLine: {
            show: false
          },
          axisTick: {
            show: false
          },
          axisLabel: {
            show: false
          },
          data: [
            {
              value: isHigherBetter 
                ? (metric.value / metric.target) * 100 
                : 100 - ((metric.value / metric.target) * 100 - 100),
              name: metric.name,
              title: {
                offsetCenter: ['0%', '-30%']
              },
              detail: {
                valueAnimation: true,
                offsetCenter: ['0%', '0%']
              }
            }
          ],
          title: {
            fontSize: 14
          },
          detail: {
            width: 70,
            height: 14,
            fontSize: 18,
            color: colors[status as keyof typeof colors],
            formatter: `${metric.value} ${metric.unit}`
          }
        }
      ]
    }
  }

  return (
    <>
      {/* Key Metrics Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Workforce Efficiency
            </CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {(workforceData.operator_performance.reduce((acc: number, cur: any) => acc + cur.efficiency, 0) / 
                workforceData.operator_performance.length).toFixed(1)}%
            </div>
            <p className="text-xs text-muted-foreground">
              <span className="text-emerald-500 font-medium flex items-center">
                <ArrowUp className="h-3 w-3 mr-1" />
                3.8%
              </span>{" "}
              vs. previous period
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Quality Score
            </CardTitle>
            <Star className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {(workforceData.operator_performance.reduce((acc: number, cur: any) => acc + cur.quality_score, 0) / 
                workforceData.operator_performance.length).toFixed(1)}%
            </div>
            <p className="text-xs text-muted-foreground">
              <span className="text-emerald-500 font-medium flex items-center">
                <ArrowUp className="h-3 w-3 mr-1" />
                1.2%
              </span>{" "}
              vs. previous period
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Resource Efficiency
            </CardTitle>
            <PackageCheck className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {(workforceData.resource_efficiency.data[0].data.reduce((acc: number, cur: any) => acc + cur, 0) / 
                workforceData.resource_efficiency.data[0].data.length).toFixed(1)}%
            </div>
            <Badge className="bg-emerald-500 hover:bg-emerald-600">Meeting Target</Badge>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Environmental Score
            </CardTitle>
            <Leaf className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              89.2%
            </div>
            <p className="text-xs text-muted-foreground">
              <span className="text-emerald-500 font-medium flex items-center">
                <ArrowUp className="h-3 w-3 mr-1" />
                4.5%
              </span>{" "}
              vs. previous period
            </p>
          </CardContent>
        </Card>
      </div>
      
      {/* Workforce Performance & Shift Comparison */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card className="col-span-1">
          <CardHeader>
            <CardTitle>Workforce Performance Matrix</CardTitle>
            <CardDescription>Efficiency vs. quality score by team (bubble size = training hours)</CardDescription>
          </CardHeader>
          <CardContent className="h-[350px]">
            <ReactECharts 
              option={operatorPerformanceOptions} 
              style={{ height: '100%', width: '100%' }}
              opts={{ renderer: 'canvas' }}
            />
          </CardContent>
        </Card>
        
        <Card className="col-span-1">
          <CardHeader>
            <CardTitle>Shift Performance Comparison</CardTitle>
            <CardDescription>Production, quality & defect rate by shift</CardDescription>
          </CardHeader>
          <CardContent className="h-[350px]">
            <ReactECharts 
              option={shiftComparisonOptions} 
              style={{ height: '100%', width: '100%' }}
              opts={{ renderer: 'canvas' }}
            />
          </CardContent>
        </Card>
      </div>
      
      {/* Resource Efficiency & Environmental Impact */}
      <div className="grid gap-4">
        <Card>
          <CardHeader>
            <CardTitle>Resource Efficiency</CardTitle>
            <CardDescription>Usage and cost efficiency by raw material</CardDescription>
          </CardHeader>
          <CardContent className="h-[350px]">
            <ReactECharts 
              option={resourceEfficiencyOptions} 
              style={{ height: '100%', width: '100%' }}
              opts={{ renderer: 'canvas' }}
            />
          </CardContent>
        </Card>
      </div>
      
      <div className="grid gap-4 md:grid-cols-4">
        {workforceData.environmental_metrics.map((metric: any, index: number) => (
          <Card key={index} className="col-span-1">
            <CardHeader>
              <CardTitle className="text-sm">{metric.name}</CardTitle>
              <CardDescription>
                Target: {metric.target} {metric.unit}
              </CardDescription>
            </CardHeader>
            <CardContent className="h-[200px]">
              <ReactECharts 
                option={getGaugeOptions(metric)} 
                style={{ height: '100%', width: '100%' }}
                opts={{ renderer: 'canvas' }}
              />
            </CardContent>
          </Card>
        ))}
      </div>
    </>
  )
}
