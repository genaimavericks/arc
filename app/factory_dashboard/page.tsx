"use client"

import { useState, useEffect, Suspense } from "react"
import { useSearchParams } from "next/navigation"
import { MainLayout } from "@/components/main-layout"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import ProtectedRoute from "@/components/protected-route"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import ReactECharts from 'echarts-for-react'
import { Gauge } from "@/components/ui/charts"
import { Activity, BarChart2, Droplet, Factory, Thermometer, Wind, Zap, Settings, User, Download } from "lucide-react"
import Link from "next/link"

import DashboardSummary from "@/app/factory_dashboard/components/dashboard-summary"
import OperationsDashboard from "@/app/factory_dashboard/components/operations-dashboard"
import WorkforceResourceDashboard from "@/app/factory_dashboard/components/workforce-resource-dashboard"

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

export default function FactoryDashboardPage() {
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
