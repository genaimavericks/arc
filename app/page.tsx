"use client"

import { useAuth } from "@/lib/auth-context"
import { useRouter, useSearchParams } from "next/navigation"
import { useEffect, Suspense, useState } from "react"
import { Card, CardContent, CardHeader, CardDescription, CardTitle } from "@/components/ui/card"
import { MainLayout } from "@/components/main-layout"
import ProtectedRoute from "@/components/protected-route"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import { BarChart2, Settings, User, Download, Zap } from "lucide-react"

// Import dashboard components
import DashboardSummary from "@/app/factory_dashboard/components/dashboard-summary"
import OperationsDashboard from "@/app/factory_dashboard/components/operations-dashboard"
import WorkforceResourceDashboard from "@/app/factory_dashboard/components/workforce-resource-dashboard"

export default function HomePage() {
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
  
  // Render the factory dashboard as the homepage
  return (
    <ProtectedRoute requiredPermission="command:read">
      <MainLayout>
        <header className="flex items-center justify-between py-4 mb-4">
          <div>
            <h1 className="text-3xl font-bold">Factory Dashboard</h1>
            <p className="text-muted-foreground">Foam Factory performance metrics and analytics</p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm">
              <Download className="h-4 w-4 mr-2" />
              Export Data
            </Button>
            <Button variant="outline" size="sm">
              <Zap className="h-4 w-4 mr-2" />
              Live Monitor
            </Button>
          </div>
        </header>

        <Suspense fallback={<div className="p-4 text-center">Loading dashboard...</div>}>
          <DashboardTabs />
        </Suspense>
      </MainLayout>
    </ProtectedRoute>
  )
}

// Client component for tab handling
function DashboardTabs() {
  const searchParams = useSearchParams()
  const tabParam = searchParams.get('tab')
  const initialTab = tabParam === 'operations' ? 'operations' : 
                    tabParam === 'workforce' ? 'workforce' : 'summary'
  
  const [activeTab, setActiveTab] = useState(initialTab)

  return (
    <Tabs defaultValue={activeTab} onValueChange={setActiveTab} className="w-full">
      <TabsList className="bg-card border mb-8">
        <TabsTrigger value="summary" className="data-[state=active]:bg-muted">
          <BarChart2 className="h-4 w-4 mr-2" />
          Performance Overview
        </TabsTrigger>
        <TabsTrigger value="operations" className="data-[state=active]:bg-muted">
          <Settings className="h-4 w-4 mr-2" />
          Operations & Maintenance
        </TabsTrigger>
        <TabsTrigger value="workforce" className="data-[state=active]:bg-muted">
          <User className="h-4 w-4 mr-2" />
          Workforce & Resources
        </TabsTrigger>
      </TabsList>
      
      <div className="space-y-6">
        <TabsContent value="summary">
          <DashboardSummary />
        </TabsContent>
        <TabsContent value="operations">
          <OperationsDashboard />
        </TabsContent>
        <TabsContent value="workforce">
          <WorkforceResourceDashboard />
        </TabsContent>
      </div>
    </Tabs>
  )
}
