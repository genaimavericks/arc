"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { MainLayout } from "@/components/main-layout"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { BarChart, Gauge, PieChart, LineChart } from "../components/ui/charts"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useAuth } from "@/lib/auth-context"

export default function SalesDashboard() {
  const { user, isLoading } = useAuth()
  const router = useRouter()
  
  // Redirect to login page if user is not authenticated
  // or if user doesn't have the required permission
  useEffect(() => {
    if (!isLoading) {
      if (!user) {
        router.push('/login')
      } else if (!user.permissions?.includes('command:read')) {
        // Redirect based on user permissions with priority matching sidebar menu order
        if (user.permissions?.includes('dashboard:read')) {
          // Personal Dashboards category has priority
          router.push('/dashboards')
        } else if (user.permissions?.includes('djinni:read')) {
          // Djinni category comes after Personal Dashboards
          router.push('/djinni')
        } else if (user.permissions?.includes('datapuur:read')) {
          // DataPuur appears next in the Tools category
          router.push('/datapuur')
        } else if (user.permissions?.includes('kginsights:read')) {
          // Redirect directly to KGraph Dashboard page instead of the dummy K-Graff page
          router.push('/kginsights/dashboard')
        } else {
          // If they have none of the above permissions, show access denied page
          router.push('/access-denied')
        }
      }
    }
  }, [user, isLoading, router])
  
  // Don't render the dashboard until we know the user's authentication status
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
      </div>
    )
  }
  
  // If user is not authenticated or doesn't have the required permission, don't render anything (we're redirecting)
  if (!user || !user.permissions?.includes('command:read')) {
    return null
  }
  
  return (
    <MainLayout>
      <div className="flex-1 space-y-4 p-4 md:p-8 pt-6">
        <Tabs defaultValue="all-categories" className="space-y-4">
          <div className="flex items-center justify-between">
            <TabsList>
              <TabsTrigger value="all-categories">All Categories</TabsTrigger>
              <TabsTrigger value="all-regions">All Regions</TabsTrigger>
              <TabsTrigger value="north-america">North America</TabsTrigger>
              <TabsTrigger value="eu-asia-targets">EU & Asia Targets</TabsTrigger>
            </TabsList>
          </div>
          
          <TabsContent value="all-categories" className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Total Sales</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">$1.2M</div>
                  <p className="text-xs text-muted-foreground">
                    <span className="text-emerald-500">+5.1%</span> vs last period
                  </p>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Revenue Growth</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">86.2%</div>
                  <p className="text-xs text-muted-foreground">
                    <span className="text-emerald-500">+12.2%</span> vs last period
                  </p>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Average Order Value</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">$12,450</div>
                  <p className="text-xs text-muted-foreground">
                    <span className="text-emerald-500">+5.2%</span> vs last period
                  </p>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Lead Time</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">4.2 days</div>
                  <p className="text-xs text-muted-foreground">
                    <span className="text-emerald-500">+4.72%</span> vs last period
                  </p>
                </CardContent>
              </Card>
            </div>
            
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
              <Card className="col-span-4">
                <CardHeader>
                  <CardTitle>Sales vs Forecast</CardTitle>
                </CardHeader>
                <CardContent className="pl-2">
                  <BarChart
                    data={[
                      { name: 'Week 1', value: 400 },
                      { name: 'Week 2', value: 600 },
                      { name: 'Week 3', value: 500 },
                      { name: 'Week 4', value: 700 },
                    ]}
                    color="#8884d8"
                  />
                </CardContent>
              </Card>
              <Card className="col-span-3">
                <CardHeader>
                  <CardTitle>Sales by Region</CardTitle>
                </CardHeader>
                <CardContent>
                  <PieChart
                    data={[
                      { name: 'North America', value: 35, fill: '#8884d8' },
                      { name: 'Europe', value: 30, fill: '#82ca9d' },
                      { name: 'Asia Pacific', value: 25, fill: '#ffc658' },
                      { name: 'Other', value: 10, fill: '#ff8042' },
                    ]}
                  />
                </CardContent>
              </Card>
            </div>
            
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
              <Card className="col-span-4">
                <CardHeader>
                  <CardTitle>Forecast Accuracy Trend</CardTitle>
                </CardHeader>
                <CardContent>
                  <LineChart
                    data={[
                      { name: 'Month 1', value: 85 },
                      { name: 'Last Quarter', value: 83 },
                      { name: 'Rolling Average', value: 84 },
                      { name: 'Today QTD', value: 87 },
                    ]}
                    color="#8884d8"
                  />
                </CardContent>
              </Card>
              <Card className="col-span-3">
                <CardHeader>
                  <CardTitle>Price Point Analysis</CardTitle>
                </CardHeader>
                <CardContent>
                  <BarChart
                    data={[
                      { name: 'Budget', value: 30 },
                      { name: 'Mid-Range', value: 40 },
                      { name: 'Premium', value: 35 },
                    ]}
                    color="#8884d8"
                  />
                </CardContent>
              </Card>
            </div>
            
            <Card>
              <CardHeader>
                <CardTitle>Recent Orders</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex justify-between items-center border-b pb-2">
                  <div>
                    <div className="font-medium">ORD-001</div>
                    <div className="text-sm text-muted-foreground">Amazon Inc</div>
                  </div>
                  <div className="font-medium">$17,400</div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </MainLayout>
  )
}
