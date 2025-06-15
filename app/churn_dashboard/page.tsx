"use client"

import { useState, useEffect, Suspense } from "react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useRouter, useSearchParams } from "next/navigation"
import { MainLayout } from "@/components/main-layout"
import ProtectedRoute from "@/components/protected-route"
import ChurnSummary from "@/app/components/churn_dashboard/dashboard-summary"
import CustomerProfile from "@/app/components/churn_dashboard/customer-profile"
import ChurnerProfile from "@/app/components/churn_dashboard/churner-profile"

function ChurnDashboardContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [activeTab, setActiveTab] = useState("summary")
  
  useEffect(() => {
    const tab = searchParams.get("tab")
    if (tab && ["summary", "customer", "churner"].includes(tab)) {
      setActiveTab(tab)
    }
  }, [searchParams])
  
  const handleTabChange = (value: string) => {
    setActiveTab(value)
    router.push(`/churn_dashboard?tab=${value}`)
  }
  
  return (
    <ProtectedRoute requiredPermission="command:read">
      <MainLayout>
        <header className="flex items-center justify-between py-4 mb-4">
          <div>
            <h1 className="text-3xl font-bold">Telecom Customer Churn Dashboard</h1>
            <p className="text-muted-foreground">Customer retention analytics and insights</p>
          </div>
        </header>
        
        <Tabs value={activeTab} onValueChange={handleTabChange}>
          <TabsList className="grid w-full grid-cols-3 bg-card border mb-8">
            <TabsTrigger value="summary" className="data-[state=active]:bg-muted">Summary</TabsTrigger>
            <TabsTrigger value="customer" className="data-[state=active]:bg-muted">Customer Profile</TabsTrigger>
            <TabsTrigger value="churner" className="data-[state=active]:bg-muted">Churner Profile</TabsTrigger>
          </TabsList>
          <TabsContent value="summary" className="mt-4">
            <Suspense fallback={<div className="w-full h-64 flex items-center justify-center">
              <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
            </div>}>
              <ChurnSummary />
            </Suspense>
          </TabsContent>
          <TabsContent value="customer" className="mt-4">
            <Suspense fallback={<div className="w-full h-64 flex items-center justify-center">
              <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
            </div>}>
              <CustomerProfile />
            </Suspense>
          </TabsContent>
          <TabsContent value="churner" className="mt-4">
            <Suspense fallback={<div className="w-full h-64 flex items-center justify-center">
              <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
            </div>}>
              <ChurnerProfile />
            </Suspense>
          </TabsContent>
        </Tabs>
      </MainLayout>
    </ProtectedRoute>
  )
}

export default function ChurnDashboard() {
  return (
    <Suspense fallback={
      <div className="w-full h-64 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
      </div>
    }>
      <ChurnDashboardContent />
    </Suspense>
  )
}
