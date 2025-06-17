"use client"

import { useState, useEffect } from "react"
import * as echarts from 'echarts/core'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ArrowUp, ArrowDown, Users, Phone, Wallet, AlertTriangle, Activity } from "lucide-react"
import ReactECharts from 'echarts-for-react'
import { fetchChurnSummary } from '@/app/churn_dashboard/services/api'

export default function ChurnSummary() {
  const [summaryData, setSummaryData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true)
      try {
        try {
          const data = await fetchChurnSummary()
          setSummaryData(data)
        } catch (apiError) {
          console.error("API error, using fallback data:", apiError)
          
          // Fallback data if API fails
          const fallbackData = {
            customer_profile: {
              total_customers: 7043,
              avg_monthly_charges: 64.76,
              total_charges: 16563388.05
            },
            churn_profile: {
              total_churners: 1869,
              churn_rate: 26.54,
              avg_monthly_charges: 74.44,
              avg_total_charges: 1531.80
            },
            key_insights: {
              avg_tenure_non_churners: 32.42,
              avg_tenure_churners: 17.98,
              most_common_contract: "Month-to-month",
              most_common_internet_churners: "Fiber optic"
            },
            demographics: {
              gender: { "Male": 3555, "Female": 3488 },
              contract: { 
                "Month-to-month": 3875,
                "One year": 1473, 
                "Two year": 1695
              },
              internet_service: {
                "DSL": 2421,
                "Fiber optic": 3096,
                "No": 1526
              },
              tenure: {
                "0-6 months": 1795,
                "7-12 months": 875,
                "1-2 years": 1021,
                "2-3 years": 825,
                "3-4 years": 652,
                "4-5 years": 585,
                "5+ years": 1290
              }
            }
          }
          
          setSummaryData(fallbackData)
        }
      } catch (error) {
        console.error("Failed to fetch summary data:", error)
      } finally {
        setLoading(false)
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
        <p className="text-muted-foreground">Failed to load summary data</p>
      </div>
    )
  }

  // Churn Rate Gauge Chart
  const churnRateOptions = {
    series: [
      {
        type: 'gauge',
        startAngle: 180,
        endAngle: 0,
        min: 0,
        max: 100,
        splitNumber: 10,
        axisLine: {
          lineStyle: {
            width: 6,
            color: [
              [0.15, '#10b981'],
              [0.35, '#84cc16'],
              [0.65, '#eab308'],
              [0.9, '#f97316'],
              [1, '#ef4444']
            ]
          }
        },
        pointer: {
          icon: 'path://M12.8,0.7l12,40.1H0.7L12.8,0.7z',
          length: '12%',
          width: 20,
          offsetCenter: [0, '-60%'],
          itemStyle: {
            color: 'inherit'
          }
        },
        axisTick: {
          length: 12,
          lineStyle: {
            color: 'inherit',
            width: 2
          }
        },
        splitLine: {
          length: 20,
          lineStyle: {
            color: 'inherit',
            width: 5
          }
        },
        axisLabel: {
          color: '#464646',
          fontSize: 10,
          distance: -58,
          formatter: function (value: number) {
            if (value === 0 || value === 100) {
              return value + '%';
            } else {
              return '';
            }
          }
        },
        title: {
          offsetCenter: [0, '-10%'],
          fontSize: 14
        },
        detail: {
          fontSize: 24,
          offsetCenter: [0, '30%'],
          valueAnimation: true,
          formatter: function (value: number) {
            return Math.round(value * 100) / 100 + '%';
          },
          color: 'inherit'
        },
        data: [
          {
            value: summaryData.churn_profile.churn_rate,
            name: 'CHURN RATE',
            title: {
              color: '#464646'
            }
          }
        ]
      }
    ]
  };

  // Tenure Comparison Chart
  const tenureComparisonOptions = {
    tooltip: {
      trigger: 'axis',
      formatter: '{b}: {c} months',
      backgroundColor: 'rgba(0,0,0,0.7)',
      borderRadius: 4,
      padding: [5, 10],
      textStyle: {
        color: '#fff'
      }
    },
    xAxis: {
      type: 'category',
      data: ['Non-Churners', 'Churners'],
      axisLabel: {
        rotate: 0
      }
    },
    yAxis: {
      type: 'value',
      name: 'Months',
      nameLocation: 'middle',
      nameGap: 30,
    },
    series: [
      {
        data: [
          {
            value: parseFloat(summaryData.key_insights.avg_tenure_non_churners.toFixed(2)),
            itemStyle: { color: '#10b981' }
          },
          {
            value: parseFloat(summaryData.key_insights.avg_tenure_churners.toFixed(2)),
            itemStyle: { color: '#ef4444' }
          }
        ],
        type: 'bar',
        label: {
          show: true,
          position: 'top',
          formatter: '{c} months'
        }
      }
    ]
  };
  
  // Contract Types Distribution
  const contractDistributionOptions = {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)',
      backgroundColor: 'rgba(0,0,0,0.7)',
      borderRadius: 4,
      padding: [5, 10],
      textStyle: {
        color: '#fff'
      }
    },
    legend: {
      top: '5%',
      left: 'center',
      textStyle: {
        color: '#fff',
        backgroundColor: 'rgba(0,0,0,0.7)',
        padding: [2, 4],
        borderRadius: 3
      },
      itemWidth: 12,
      itemHeight: 12,
    },
    series: [
      {
        name: 'Contract Type',
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 4,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: false,
        },
        emphasis: {
          label: {
            show: true,
            fontSize: '18',
            fontWeight: 'bold'
          }
        },
        labelLine: {
          show: false
        },
        data: Object.entries(summaryData.demographics.contract).map(([key, value]) => ({
          value: value,
          name: key
        }))
      }
    ]
  };

  // Internet Service Distribution for Churners
  const internetServiceOptions = {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)',
      backgroundColor: 'rgba(0,0,0,0.7)',
      borderRadius: 4,
      padding: [5, 10],
      textStyle: {
        color: '#fff'
      }
    },
    legend: {
      top: '5%',
      left: 'center',
      textStyle: {
        color: '#fff',
        backgroundColor: 'rgba(0,0,0,0.7)',
        padding: [2, 4],
        borderRadius: 3
      },
      itemWidth: 12,
      itemHeight: 12,
    },
    series: [
      {
        name: 'Internet Service',
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 4,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: false,
        },
        emphasis: {
          label: {
            show: true,
            fontSize: '18',
            fontWeight: 'bold'
          }
        },
        labelLine: {
          show: false
        },
        data: Object.entries(summaryData.demographics.internet_service).map(([key, value]) => ({
          value: value,
          name: key
        }))
      }
    ]
  };

  return (
    <>
      {/* Customer Profile Overview */}
      <div className="mb-8">
        <h2 className="text-2xl font-bold mb-4">Customer Profile Overview</h2>
        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader className="flex flex-col items-center text-center space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                Total Customers
              </CardTitle>
              <Users className="h-4 w-4 text-muted-foreground mt-1" />
            </CardHeader>
            <CardContent className="text-center">
              <div className="text-2xl font-bold">
                {summaryData.customer_profile.total_customers.toLocaleString()}
              </div>
              <p className="text-xs text-muted-foreground">
                Active telecom customers
              </p>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader className="flex flex-col items-center text-center space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                Avg Monthly Charges
              </CardTitle>
              <Wallet className="h-4 w-4 text-muted-foreground mt-1" />
            </CardHeader>
            <CardContent className="text-center">
              <div className="text-2xl font-bold">
                ${summaryData.customer_profile.avg_monthly_charges.toFixed(2)}
              </div>
              <p className="text-xs text-muted-foreground">
                Per customer monthly
              </p>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader className="flex flex-col items-center text-center space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                Total Charges
              </CardTitle>
              <Wallet className="h-4 w-4 text-muted-foreground mt-1" />
            </CardHeader>
            <CardContent className="text-center">
              <div className="text-2xl font-bold">
                ${(summaryData.customer_profile.total_charges / 1000000).toFixed(2)}M
              </div>
              <p className="text-xs text-muted-foreground">
                Lifetime customer value
              </p>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Churn Profile Overview */}
      <div className="mb-8">
        <h2 className="text-2xl font-bold mb-4">Churn Profile Overview</h2>
        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader className="flex flex-col items-center text-center space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                Total Churners
              </CardTitle>
              <Users className="h-4 w-4 text-rose-500 mt-1" />
            </CardHeader>
            <CardContent className="text-center">
              <div className="text-2xl font-bold">
                {summaryData.churn_profile.total_churners.toLocaleString()}
              </div>
              <Badge className="bg-rose-500 hover:bg-rose-600">Critical</Badge>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader className="flex flex-col items-center text-center space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                Avg Monthly Charges
              </CardTitle>
              <Wallet className="h-4 w-4 text-muted-foreground mt-1" />
            </CardHeader>
            <CardContent className="text-center">
              <div className="text-2xl font-bold">
                ${summaryData.churn_profile.avg_monthly_charges.toFixed(2)}
              </div>
              <Badge className={summaryData.churn_profile.avg_monthly_charges > summaryData.customer_profile.avg_monthly_charges ? "bg-amber-500 hover:bg-amber-600" : "bg-emerald-500 hover:bg-emerald-600"}>
                {summaryData.churn_profile.avg_monthly_charges > summaryData.customer_profile.avg_monthly_charges ? "Higher than average" : "Lower than average"}
              </Badge>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader className="flex flex-col items-center text-center space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                Avg Total Charges
              </CardTitle>
              <Wallet className="h-4 w-4 text-muted-foreground mt-1" />
            </CardHeader>
            <CardContent className="text-center">
              <div className="text-2xl font-bold">
                ${summaryData.churn_profile.avg_total_charges.toFixed(2)}
              </div>
              <p className="text-xs text-muted-foreground">
                Per churned customer
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
      
      {/* Key Insights */}
      <div className="mb-8">
        <h2 className="text-2xl font-bold mb-4">Key Insights</h2>
        <div className="grid gap-4 md:grid-cols-2">
          <Card className="col-span-1">
            <CardHeader>
              <CardTitle>Churn Rate</CardTitle>
              <CardDescription>Overall customer churn percentage</CardDescription>
            </CardHeader>
            <CardContent className="h-[300px]">
              <ReactECharts 
                option={churnRateOptions} 
                style={{ height: '100%', width: '100%' }} 
                opts={{ renderer: 'canvas' }}
              />
            </CardContent>
          </Card>
          
          <Card className="col-span-1">
            <CardHeader>
              <CardTitle>Average Tenure Comparison</CardTitle>
              <CardDescription>Churners vs non-churners</CardDescription>
            </CardHeader>
            <CardContent className="h-[300px]">
              <ReactECharts 
                option={tenureComparisonOptions} 
                style={{ height: '100%', width: '100%' }} 
                opts={{ renderer: 'canvas' }}
              />
            </CardContent>
          </Card>
          
          <Card className="col-span-1">
            <CardHeader>
              <CardTitle>Contract Type Distribution</CardTitle>
              <CardDescription>Most common: {summaryData.key_insights.most_common_contract}</CardDescription>
            </CardHeader>
            <CardContent className="h-[300px]">
              <ReactECharts 
                option={contractDistributionOptions} 
                style={{ height: '100%', width: '100%' }} 
                opts={{ renderer: 'canvas' }}
              />
            </CardContent>
          </Card>
          
          <Card className="col-span-1">
            <CardHeader>
              <CardTitle>Internet Service Distribution</CardTitle>
              <CardDescription>Most common among churners: {summaryData.key_insights.most_common_internet_churners}</CardDescription>
            </CardHeader>
            <CardContent className="h-[300px]">
              <ReactECharts 
                option={internetServiceOptions} 
                style={{ height: '100%', width: '100%' }} 
                opts={{ renderer: 'canvas' }}
              />
            </CardContent>
          </Card>
        </div>
      </div>
    </>
  )
}
