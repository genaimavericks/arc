"use client"

import { Suspense } from "react"
import { MainLayout } from "@/components/main-layout"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import ProtectedRoute from "@/components/protected-route"
import ReactECharts from 'echarts-for-react'
import { Gauge } from "@/components/ui/charts"

import DashboardSummary from "@/app/factory_dashboard/components/dashboard-summary"

// Dashboard content without tabs
function DashboardContent() {
  return (
    <div className="space-y-6">
      <DashboardSummary />
    </div>
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
          {/* Buttons removed as requested */}
        </header>

        <Suspense fallback={<div className="p-4 text-center">Loading dashboard...</div>}>
          <DashboardContent />
        </Suspense>
      </MainLayout>
    </ProtectedRoute>
  )
}
