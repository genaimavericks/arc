"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { MainLayout } from "@/components/main-layout"
import { useAuth } from "@/lib/auth-context"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { LayoutDashboard, BarChart2, PlusCircle, Clock } from "lucide-react"
import { Button } from "@/components/ui/button"
import ProtectedRoute from "@/components/protected-route"

export default function MyDashboardsPage() {
  const { user, isLoading } = useAuth()
  const router = useRouter()
  
  // Redirect to login page if user is not authenticated
  useEffect(() => {
    if (!isLoading && !user) {
      router.push('/login')
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
  
  // If user is not authenticated, don't render anything (we're redirecting)
  if (!user) {
    return null
  }
  
  // Sample dashboard data
  const recentDashboards = [
    {
      id: 1,
      title: "Sales Performance",
      description: "Overall sales metrics and KPIs",
      lastViewed: "2 hours ago",
      charts: 4
    },
    {
      id: 2,
      title: "Inventory Management",
      description: "Stock levels and inventory projections",
      lastViewed: "Yesterday",
      charts: 6
    },
    {
      id: 3,
      title: "Customer Insights",
      description: "Customer behavior and segmentation analysis",
      lastViewed: "3 days ago",
      charts: 5
    }
  ]
  
  return (
    <ProtectedRoute requiredPermission="dashboard:read">
      <MainLayout>
        <div className="flex-1 space-y-4 p-4 md:p-8 pt-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold tracking-tight">My Dashboards</h2>
              <p className="text-muted-foreground">
                View, manage, and analyze your custom dashboards
              </p>
            </div>
            <Button className="gap-2">
              <PlusCircle className="h-4 w-4" />
              Create Dashboard
            </Button>
          </div>
          
          {/* Recent Dashboards */}
          <div>
            <h3 className="text-lg font-medium mb-4">Recent Dashboards</h3>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {recentDashboards.map((dashboard) => (
                <Card key={dashboard.id} className="hover:border-primary/50 transition-colors cursor-pointer">
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-base">{dashboard.title}</CardTitle>
                      <div className="bg-primary/10 p-1.5 rounded-md">
                        <LayoutDashboard className="h-4 w-4 text-primary" />
                      </div>
                    </div>
                    <CardDescription>{dashboard.description}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center justify-between text-sm">
                      <div className="flex items-center gap-1 text-muted-foreground">
                        <Clock className="h-3.5 w-3.5" />
                        <span>{dashboard.lastViewed}</span>
                      </div>
                      <div className="flex items-center gap-1 text-muted-foreground">
                        <BarChart2 className="h-3.5 w-3.5" />
                        <span>{dashboard.charts} charts</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
              
              {/* Create New Dashboard Card */}
              <Card className="border-dashed hover:border-primary/50 transition-colors cursor-pointer flex flex-col items-center justify-center p-6">
                <div className="bg-primary/10 p-3 rounded-full mb-3">
                  <PlusCircle className="h-6 w-6 text-primary" />
                </div>
                <h3 className="font-medium mb-1">Create New Dashboard</h3>
                <p className="text-sm text-muted-foreground text-center">
                  Build a custom dashboard with your own metrics and data
                </p>
              </Card>
            </div>
          </div>
          
          {/* Dashboard Categories */}
          <div>
            <h3 className="text-lg font-medium mb-4">Dashboard Categories</h3>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <Card className="hover:border-primary/50 transition-colors cursor-pointer">
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">Sales</CardTitle>
                  <CardDescription>Sales performance metrics</CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">5 dashboards</p>
                </CardContent>
              </Card>
              
              <Card className="hover:border-primary/50 transition-colors cursor-pointer">
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">Inventory</CardTitle>
                  <CardDescription>Stock and supply chain metrics</CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">3 dashboards</p>
                </CardContent>
              </Card>
              
              <Card className="hover:border-primary/50 transition-colors cursor-pointer">
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">Customers</CardTitle>
                  <CardDescription>Customer analytics and insights</CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">4 dashboards</p>
                </CardContent>
              </Card>
              
              <Card className="hover:border-primary/50 transition-colors cursor-pointer">
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">Finance</CardTitle>
                  <CardDescription>Financial metrics and KPIs</CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">2 dashboards</p>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </MainLayout>
    </ProtectedRoute>
  )
}
