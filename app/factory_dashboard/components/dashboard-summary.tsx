"use client"

import { useState, useEffect } from "react"
import * as echarts from 'echarts/core'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ArrowUp, ArrowDown, Activity, BarChart2, Droplet, Factory, Thermometer, Wind, Zap } from "lucide-react"
import ReactECharts from 'echarts-for-react'
import { cn } from "@/lib/utils"

export default function DashboardSummary() {
  const [summaryData, setSummaryData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  
  useEffect(() => {
    // Fetch data from our API service
    const fetchData = async () => {
      setLoading(true)
      try {
        // Import the API service function
        const { fetchSummaryData } = await import('@/app/factory_dashboard/services/api');
        
        // Try to fetch real data from API
        try {
          const data = await fetchSummaryData();
          setSummaryData(data);
        } catch (apiError) {
          console.error("API error, using fallback data:", apiError);
          
          // Fallback to simulated data if API fails
          const fallbackData = {
            key_metrics: {
              total_production: 650000,
              avg_machine_utilization: 68.5,
              total_revenue: 12750000,
              avg_profit_margin: 18.3,
              total_downtime: 1250,
              downtime_cost: 825000,
              avg_quality: 91.7,
              avg_defect_rate: 3.2
            },
            environmental_impact: {
              total_emissions: 185000,
              total_energy: 220000,
              total_waste: 120000
            },
            production_trend: Array.from({ length: 12 }, (_, i) => ({
              month: `2024-${(i+1).toString().padStart(2, '0')}`,
              production: Math.floor(40000 + Math.random() * 25000)
            }))
          };
          
          setSummaryData(fallbackData);
        }
      } catch (error) {
        console.error("Failed to fetch summary data:", error);
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
  
  if (!summaryData) {
    return (
      <div className="w-full p-8 text-center">
        <p className="text-muted-foreground">Failed to load dashboard data</p>
      </div>
    )
  }
  
  // Production by month chart options
  const productionTrendOptions = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: summaryData.production_trend.map((item: any) => {
        const date = new Date(item.month)
        return date.toLocaleString('default', { month: 'short' })
      })
    },
    yAxis: {
      type: 'value',
      name: 'Units'
    },
    series: [
      {
        name: 'Production',
        type: 'bar',
        data: summaryData.production_trend.map((item: any) => item.production),
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#83bff6' },
            { offset: 0.5, color: '#188df0' },
            { offset: 1, color: '#188df0' }
          ])
        },
        emphasis: {
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: '#2378f7' },
              { offset: 0.7, color: '#2378f7' },
              { offset: 1, color: '#83bff6' }
            ])
          }
        }
      }
    ]
  }
  
  // Machine utilization gauge options
  const utilizationGaugeOptions = {
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
            color: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 1,
              y2: 0,
              colorStops: [
                { offset: 0, color: '#1d4ed8' },
                { offset: 1, color: '#3b82f6' }
              ]
            }
          }
        },
        axisLine: {
          lineStyle: {
            width: 20
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
            value: parseFloat(summaryData.key_metrics.avg_machine_utilization.toFixed(2)),
            name: 'Utilization',
            title: {
              offsetCenter: ['0%', '-10%']
            },
            detail: {
              valueAnimation: true,
              offsetCenter: ['0%', '10%']
            }
          }
        ],
        title: {
          fontSize: 14
        },
        detail: {
          width: 50,
          height: 14,
          fontSize: 20,
          color: 'auto',
          formatter: '{value}%'
        }
      }
    ]
  }
  
  // Quality vs Defect Rate gauge option
  const qualityDefectOptions = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      }
    },
    radar: {
      shape: 'circle',
      indicator: [
        { name: 'Quality Pass Rate', max: 100 },
        { name: 'Low Defects', max: 10, min: 0, 
          axisLabel: {
            formatter: (value: number) => 10 - value
          }
        },
        { name: 'Production Volume', max: 100 },
        { name: 'Machine Utilization', max: 100 },
        { name: 'Profit Margin', max: 30 },
      ]
    },
    series: [
      {
        type: 'radar',
        areaStyle: {
          opacity: 0.3
        },
        data: [
          {
            value: [
              summaryData.key_metrics.avg_quality,
              10 - summaryData.key_metrics.avg_defect_rate,
              75, // Normalized production volume
              summaryData.key_metrics.avg_machine_utilization,
              summaryData.key_metrics.avg_profit_margin
            ],
            name: 'Factory KPIs',
            itemStyle: {
              color: '#3b82f6'
            },
            lineStyle: {
              width: 2
            }
          },
          {
            value: [85, 6, 65, 60, 15],
            name: 'Industry Average',
            lineStyle: {
              width: 1,
              type: 'dashed'
            },
            itemStyle: {
              color: '#6b7280'
            },
            areaStyle: {
              opacity: 0.1
            }
          }
        ]
      }
    ]
  }
  
  // Environmental impact treemap
  const environmentalTreemapOptions = {
    tooltip: {
      formatter: '{b}: {c}'
    },
    series: [
      {
        type: 'treemap',
        data: [
          {
            name: 'CO2 Emissions',
            value: summaryData.environmental_impact.total_emissions,
            itemStyle: {
              color: '#ef4444'
            }
          },
          {
            name: 'Energy Consumption',
            value: summaryData.environmental_impact.total_energy,
            itemStyle: {
              color: '#eab308'
            }
          },
          {
            name: 'Waste Generated',
            value: summaryData.environmental_impact.total_waste,
            itemStyle: {
              color: '#84cc16'
            }
          }
        ]
      }
    ]
  }
  
  return (
    <>
      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-6">
        <Card>
          <CardHeader className="flex flex-col items-center text-center space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Total Production
            </CardTitle>
            <Factory className="h-4 w-4 text-muted-foreground mt-1" />
          </CardHeader>
          <CardContent className="text-center">
            <div className="text-2xl font-bold">
              {(summaryData.key_metrics.total_production/1000000).toFixed(2)}M units
            </div>
            <p className="text-xs text-muted-foreground">
              <span className="text-emerald-500 font-medium flex items-center justify-center">
                <ArrowUp className="h-3 w-3 mr-1" />
                12.2%
              </span>{" "}
              vs. previous period
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-col items-center text-center space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Total Revenue
            </CardTitle>
            <BarChart2 className="h-4 w-4 text-muted-foreground mt-1" />
          </CardHeader>
          <CardContent className="text-center">
            <div className="text-2xl font-bold">
              ${(summaryData.key_metrics.total_revenue/1000000).toFixed(2)}M
            </div>
            <p className="text-xs text-muted-foreground">
              <span className="text-emerald-500 font-medium flex items-center justify-center">
                <ArrowUp className="h-3 w-3 mr-1" />
                8.7%
              </span>{" "}
              vs. previous period
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-col items-center text-center space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Average Quality
            </CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground mt-1" />
          </CardHeader>
          <CardContent className="text-center">
            <div className="text-2xl font-bold">
              {summaryData.key_metrics.avg_quality.toFixed(1)}%
            </div>
            <p className="text-xs text-muted-foreground">
              <span className="text-emerald-500 font-medium flex items-center justify-center">
                <ArrowUp className="h-3 w-3 mr-1" />
                1.5%
              </span>{" "}
              vs. previous period
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-col items-center text-center space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Downtime Loss
            </CardTitle>
            <Badge variant="destructive" className="text-xs mt-1">Alert</Badge>
          </CardHeader>
          <CardContent className="text-center">
            <div className="text-2xl font-bold">
              ${(summaryData.key_metrics.downtime_cost/1000).toFixed(1)}K
            </div>
            <p className="text-xs text-muted-foreground">
              <span className="text-rose-500 font-medium flex items-center justify-center">
                <ArrowUp className="h-3 w-3 mr-1" />
                3.2%
              </span>{" "}
              vs. previous period
            </p>
          </CardContent>
        </Card>
      </div>
      
      {/* Production Trend & Machine Utilization */}
      <div className="grid gap-4 md:grid-cols-2 mb-6">
        <Card className="col-span-1">
          <CardHeader>
            <CardTitle>Production Volume Trend</CardTitle>
            <CardDescription>Monthly production output in units</CardDescription>
          </CardHeader>
          <CardContent className="h-[350px]">
            <ReactECharts 
              option={productionTrendOptions} 
              style={{ height: '100%', width: '100%' }}
              opts={{ renderer: 'canvas' }}
            />
          </CardContent>
        </Card>
        
        <Card className="col-span-1">
          <CardHeader>
            <CardTitle>Performance Metrics</CardTitle>
            <CardDescription>Current performance vs industry benchmarks</CardDescription>
          </CardHeader>
          <CardContent className="h-[350px]">
            <ReactECharts 
              option={qualityDefectOptions} 
              style={{ height: '100%', width: '100%' }}
              opts={{ renderer: 'canvas' }}
            />
          </CardContent>
        </Card>
      </div>
      
      {/* Machine Utilization & Environmental Impact */}
      <div className="grid gap-4 md:grid-cols-2 mb-6">
        <Card className="col-span-1">
          <CardHeader>
            <CardTitle>Machine Utilization</CardTitle>
            <CardDescription>Average utilization across all machines</CardDescription>
          </CardHeader>
          <CardContent className="h-[300px]">
            <ReactECharts 
              option={utilizationGaugeOptions} 
              style={{ height: '100%', width: '100%' }}
              opts={{ renderer: 'canvas' }}
            />
          </CardContent>
        </Card>
        
        <Card className="col-span-1">
          <CardHeader>
            <CardTitle>Environmental Impact</CardTitle>
            <CardDescription>Emissions, energy usage and waste generation</CardDescription>
          </CardHeader>
          <CardContent className="h-[300px]">
            <ReactECharts 
              option={environmentalTreemapOptions} 
              style={{ height: '100%', width: '100%' }}
              opts={{ renderer: 'canvas' }}
            />
          </CardContent>
        </Card>
      </div>
    </>
  )
}
