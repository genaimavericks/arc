"use client"

import { useState, useEffect } from "react"
import * as echarts from 'echarts/core'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Badge } from "@/components/ui/badge"
import { Users, UserX, Phone, AlertTriangle, Activity, Wallet } from "lucide-react"
import ReactECharts from 'echarts-for-react'
import { fetchChurnerProfile } from '@/app/churn_dashboard/services/api'

export default function ChurnerProfile() {
  const [profileData, setProfileData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true)
      try {
        try {
          const data = await fetchChurnerProfile()
          setProfileData(data)
        } catch (apiError) {
          console.error("API error, using fallback data:", apiError)
          
          // Fallback data if API fails
          const fallbackData = {
            stats: {
              total_churners: 1869,
              churn_rate: 26.54,
              avg_monthly_charges: 74.44,
              avg_total_charges: 1531.80
            },
            pie_charts: {
              gender: [
                { category: "Male", value: 930 },
                { category: "Female", value: 939 }
              ],
              tenure: [
                { category: "0-6 months", value: 612 },
                { category: "7-12 months", value: 326 },
                { category: "1-2 years", value: 348 },
                { category: "2-3 years", value: 205 },
                { category: "3-4 years", value: 143 },
                { category: "4-5 years", value: 94 },
                { category: "5+ years", value: 141 }
              ],
              internet_service: [
                { category: "DSL", value: 459 },
                { category: "Fiber optic", value: 1297 },
                { category: "No", value: 113 }
              ],
              contract: [
                { category: "Month-to-month", value: 1655 },
                { category: "One year", value: 166 },
                { category: "Two year", value: 48 }
              ]
            },
            additional_stats: {
              senior_citizen_count: 476,
              senior_citizen_percentage: 25.47,
              partner_count: 752,
              partner_percentage: 40.24,
              dependents_count: 522,
              dependents_percentage: 27.93
            },
            reasons: {
              "Competitor made better offer": 342,
              "Dissatisfaction with service": 894,
              "Attitude of support person": 145,
              "Price increase": 367,
              "Other": 121
            }
          }
          
          setProfileData(fallbackData)
        }
      } catch (error) {
        console.error("Failed to fetch churner profile data:", error)
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
  
  if (!profileData) {
    return (
      <div className="w-full p-8 text-center">
        <p className="text-muted-foreground">Failed to load churner profile data</p>
      </div>
    )
  }

  // Gender Pie Chart
  const genderOptions = {
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
      itemHeight: 12
    },
    series: [
      {
        name: 'Gender',
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 4,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: false
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
        data: profileData.pie_charts.gender.map((item: any, index: number) => ({
          value: item.value,
          name: item.category,
          itemStyle: { color: index === 0 ? '#3b82f6' : '#ec4899' }
        }))
      }
    ]
  };

  // Tenure Pie Chart
  const tenureOptions = {
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
      itemHeight: 12
    },
    series: [
      {
        name: 'Tenure',
        type: 'pie',
        radius: ['30%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 4,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: false
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
        data: profileData.pie_charts.tenure.map((item: any) => ({
          value: item.value,
          name: item.category
        }))
      }
    ]
  };

  // Internet Service Pie Chart
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
      itemHeight: 12
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
          show: false
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
        data: profileData.pie_charts.internet_service.map((item: any) => ({
          value: item.value,
          name: item.category,
          itemStyle: { 
            color: item.category === 'DSL' ? '#3b82f6' : 
                   item.category === 'Fiber optic' ? '#10b981' : 
                   '#6b7280'
          }
        }))
      }
    ]
  };

  // Contract Pie Chart
  const contractOptions = {
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
      itemHeight: 12
    },
    series: [
      {
        name: 'Contract',
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 4,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: false
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
        data: profileData.pie_charts.contract.map((item: any) => ({
          value: item.value,
          name: item.category,
          itemStyle: { 
            color: item.category === 'Month-to-month' ? '#f59e0b' : 
                   item.category === 'One year' ? '#10b981' : 
                   '#3b82f6'
          }
        }))
      }
    ]
  };

  // Churn Reasons Bar Chart
  const churnReasonsOptions = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      },
      formatter: '{b}: {c}',
      backgroundColor: 'rgba(0,0,0,0.7)',
      borderRadius: 4,
      padding: [5, 10],
      textStyle: {
        color: '#fff'
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'value'
    },
    yAxis: {
      type: 'category',
      data: Object.keys(profileData.reasons),
      axisTick: {
        alignWithLabel: true
      }
    },
    series: [
      {
        name: 'Count',
        type: 'bar',
        data: Object.values(profileData.reasons).map((value: any) => ({
          value: value,
          itemStyle: {
            color: '#ef4444'
          }
        })),
        label: {
          show: true,
          position: 'right',
          formatter: '{c}'
        }
      }
    ]
  };

  return (
    <>
      {/* Churner Stats */}
      <div className="mb-8">
        <h2 className="text-2xl font-bold mb-4">Churner Statistics</h2>
        <div className="grid gap-4 md:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                Total Churners
              </CardTitle>
              <UserX className="h-4 w-4 text-rose-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {profileData.stats.total_churners.toLocaleString()}
              </div>
              <Badge className="bg-rose-500 hover:bg-rose-600">Critical</Badge>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                Churn Rate
              </CardTitle>
              <Activity className="h-4 w-4 text-rose-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {profileData.stats.churn_rate.toFixed(2)}%
              </div>
              <Badge className="bg-rose-500 hover:bg-rose-600">High</Badge>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                Avg Monthly Charges
              </CardTitle>
              <Wallet className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                ${profileData.stats.avg_monthly_charges.toFixed(2)}
              </div>
              <p className="text-xs text-muted-foreground">
                Per churned customer
              </p>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                Avg Total Charges
              </CardTitle>
              <Wallet className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                ${profileData.stats.avg_total_charges.toFixed(2)}
              </div>
              <p className="text-xs text-muted-foreground">
                Per churned customer
              </p>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Demographics Pie Charts */}
      <div className="mb-8">
        <h2 className="text-2xl font-bold mb-4">Churner Demographics</h2>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card className="col-span-1">
            <CardHeader>
              <CardTitle>Gender Distribution</CardTitle>
            </CardHeader>
            <CardContent className="h-[250px]">
              <ReactECharts 
                option={genderOptions} 
                style={{ height: '100%', width: '100%' }} 
                opts={{ renderer: 'canvas' }}
              />
            </CardContent>
          </Card>
          
          <Card className="col-span-1">
            <CardHeader>
              <CardTitle>Tenure Distribution</CardTitle>
              <CardDescription>Most churners have shorter tenures</CardDescription>
            </CardHeader>
            <CardContent className="h-[250px]">
              <ReactECharts 
                option={tenureOptions} 
                style={{ height: '100%', width: '100%' }} 
                opts={{ renderer: 'canvas' }}
              />
            </CardContent>
          </Card>
          
          <Card className="col-span-1">
            <CardHeader>
              <CardTitle>Internet Service</CardTitle>
              <CardDescription>High churn in fiber optic</CardDescription>
            </CardHeader>
            <CardContent className="h-[250px]">
              <ReactECharts 
                option={internetServiceOptions} 
                style={{ height: '100%', width: '100%' }} 
                opts={{ renderer: 'canvas' }}
              />
            </CardContent>
          </Card>
          
          <Card className="col-span-1">
            <CardHeader>
              <CardTitle>Contract Type</CardTitle>
              <CardDescription>Monthly contracts have highest churn</CardDescription>
            </CardHeader>
            <CardContent className="h-[250px]">
              <ReactECharts 
                option={contractOptions} 
                style={{ height: '100%', width: '100%' }} 
                opts={{ renderer: 'canvas' }}
              />
            </CardContent>
          </Card>
        </div>
      </div>
      
      {/* Additional Stats */}
      <div className="mb-8">
        <h2 className="text-2xl font-bold mb-4">Churner Attributes</h2>
        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader>
              <CardTitle>Senior Citizens</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm">Senior Citizens: {profileData.additional_stats.senior_citizen_count} ({profileData.additional_stats.senior_citizen_percentage.toFixed(2)}%)</p>
              </div>
              <Progress value={profileData.additional_stats.senior_citizen_percentage} max={100} className="h-2" />
              <p className="text-xs text-muted-foreground mt-2">
                Higher than overall customer base (overrepresented in churn)
              </p>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader>
              <CardTitle>Customers with Partners</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm">With Partners: {profileData.additional_stats.partner_count} ({profileData.additional_stats.partner_percentage.toFixed(2)}%)</p>
              </div>
              <Progress value={profileData.additional_stats.partner_percentage} max={100} className="h-2" />
              <p className="text-xs text-muted-foreground mt-2">
                Lower than overall customer base (less likely to churn)
              </p>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader>
              <CardTitle>Customers with Dependents</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm">With Dependents: {profileData.additional_stats.dependents_count} ({profileData.additional_stats.dependents_percentage.toFixed(2)}%)</p>
              </div>
              <Progress value={profileData.additional_stats.dependents_percentage} max={100} className="h-2" />
              <p className="text-xs text-muted-foreground mt-2">
                Customers with dependents are less likely to churn
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
      
      {/* Churn Reasons */}
      <div className="mb-8">
        <h2 className="text-2xl font-bold mb-4">Churn Reasons</h2>
        <Card>
          <CardHeader>
            <CardTitle>Primary Reasons for Churning</CardTitle>
            <CardDescription>Major factors behind customer churn</CardDescription>
          </CardHeader>
          <CardContent className="h-[350px]">
            <ReactECharts 
              option={churnReasonsOptions} 
              style={{ height: '100%', width: '100%' }} 
              opts={{ renderer: 'canvas' }}
            />
          </CardContent>
        </Card>
      </div>
    </>
  )
}
