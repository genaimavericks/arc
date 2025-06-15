"use client"

import { useState, useEffect } from "react"
import * as echarts from 'echarts/core'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Users, User, Phone, CreditCard, UserCheck, Wallet } from "lucide-react"
import ReactECharts from 'echarts-for-react'
import { fetchCustomerProfile } from '@/app/churn_dashboard/services/api'

export default function CustomerProfile() {
  const [profileData, setProfileData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true)
      try {
        try {
          const data = await fetchCustomerProfile()
          setProfileData(data)
        } catch (apiError) {
          console.error("API error, using fallback data:", apiError)
          
          // Fallback data if API fails
          const fallbackData = {
            stats: {
              total_customers: 7043,
              monthly_charges: 456382.25,
              total_charges: 16563388.05
            },
            pie_charts: {
              gender: [
                { category: "Male", value: 3555 },
                { category: "Female", value: 3488 }
              ],
              tenure: [
                { category: "0-6 months", value: 1795 },
                { category: "7-12 months", value: 875 },
                { category: "1-2 years", value: 1021 },
                { category: "2-3 years", value: 825 },
                { category: "3-4 years", value: 652 },
                { category: "4-5 years", value: 585 },
                { category: "5+ years", value: 1290 }
              ],
              internet_service: [
                { category: "DSL", value: 2421 },
                { category: "Fiber optic", value: 3096 },
                { category: "No", value: 1526 }
              ],
              contract: [
                { category: "Month-to-month", value: 3875 },
                { category: "One year", value: 1473 },
                { category: "Two year", value: 1695 }
              ]
            },
            additional_stats: {
              senior_citizen_count: 1142,
              senior_citizen_percentage: 16.21,
              partner_count: 3402,
              partner_percentage: 48.30,
              phone_service_count: 6361,
              phone_service_percentage: 90.32
            },
            payment_methods: [
              { method: "Electronic check", count: 2365 },
              { method: "Mailed check", count: 1612 },
              { method: "Bank transfer (automatic)", count: 1544 },
              { method: "Credit card (automatic)", count: 1522 }
            ]
          }
          
          setProfileData(fallbackData)
        }
      } catch (error) {
        console.error("Failed to fetch customer profile data:", error)
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
        <p className="text-muted-foreground">Failed to load customer profile data</p>
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

  // Payment Method Bar Chart
  const paymentMethodOptions = {
    tooltip: {
      trigger: 'axis',
      formatter: '{b}: {c}',
      backgroundColor: 'rgba(0,0,0,0.7)',
      borderRadius: 4,
      padding: [5, 10],
      textStyle: {
        color: '#fff'
      }
    },
    xAxis: {
      type: 'category',
      data: profileData.payment_methods.map((item: any) => item.method),
      axisLabel: {
        interval: 0,
        rotate: 30,
        fontSize: 10
      }
    },
    yAxis: {
      type: 'value',
      name: 'Customers'
    },
    series: [
      {
        data: profileData.payment_methods.map((item: any) => item.count),
        type: 'bar',
        itemStyle: {
          color: '#3b82f6'
        },
        label: {
          show: true,
          position: 'top',
          formatter: '{c}'
        }
      }
    ]
  };

  return (
    <>
      {/* Customer Stats */}
      <div className="mb-8">
        <h2 className="text-2xl font-bold mb-4">Customer Statistics</h2>
        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                Total Customers
              </CardTitle>
              <Users className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {profileData.stats.total_customers.toLocaleString()}
              </div>
              <p className="text-xs text-muted-foreground">
                Active telecom subscribers
              </p>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                Monthly Charges
              </CardTitle>
              <Wallet className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                ${profileData.stats.monthly_charges.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}
              </div>
              <p className="text-xs text-muted-foreground">
                Total monthly revenue
              </p>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                Total Charges
              </CardTitle>
              <Wallet className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                ${(profileData.stats.total_charges / 1000000).toFixed(2)}M
              </div>
              <p className="text-xs text-muted-foreground">
                Lifetime customer value
              </p>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Demographics Pie Charts */}
      <div className="mb-8">
        <h2 className="text-2xl font-bold mb-4">Customer Demographics</h2>
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
        <h2 className="text-2xl font-bold mb-4">Customer Attributes</h2>
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
                {100 - profileData.additional_stats.senior_citizen_percentage.toFixed(2)}% are not senior citizens
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
                {100 - profileData.additional_stats.partner_percentage.toFixed(2)}% are without partners
              </p>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader>
              <CardTitle>Phone Service Subscribers</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm">Phone Service: {profileData.additional_stats.phone_service_count} ({profileData.additional_stats.phone_service_percentage.toFixed(2)}%)</p>
              </div>
              <Progress value={profileData.additional_stats.phone_service_percentage} max={100} className="h-2" />
              <p className="text-xs text-muted-foreground mt-2">
                {100 - profileData.additional_stats.phone_service_percentage.toFixed(2)}% do not have phone service
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
      
      {/* Payment Methods */}
      <div className="mb-8">
        <h2 className="text-2xl font-bold mb-4">Payment Methods</h2>
        <Card>
          <CardHeader>
            <CardTitle>Payment Method Distribution</CardTitle>
            <CardDescription>Customer preferred payment methods</CardDescription>
          </CardHeader>
          <CardContent className="h-[300px]">
            <ReactECharts 
              option={paymentMethodOptions} 
              style={{ height: '100%', width: '100%' }} 
              opts={{ renderer: 'canvas' }}
            />
          </CardContent>
        </Card>
      </div>
    </>
  )
}
