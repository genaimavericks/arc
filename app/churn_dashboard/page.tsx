"use client"

import { Suspense } from "react"
import { MainLayout } from "@/components/main-layout"
import ProtectedRoute from "@/components/protected-route"
import ChurnSummary from "@/app/components/churn_dashboard/dashboard-summary"

function ChurnDashboardContent() {
  return (
    <ProtectedRoute requiredPermission="command:read">
      <MainLayout>
        <header className="flex items-center justify-between py-4 mb-4">
          <div>
            <h1 className="text-3xl font-bold">Telecom Customer Churn Dashboard</h1>
            <p className="text-muted-foreground">Customer retention analytics and insights</p>
          </div>
        </header>
        
        <div className="mt-4">
          <Suspense fallback={<div className="w-full h-64 flex items-center justify-center">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
          </div>}>
            <ChurnSummary />
          </Suspense>
        </div>
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
