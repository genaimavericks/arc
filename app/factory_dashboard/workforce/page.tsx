"use client"

import { Suspense } from "react"
import { MainLayout } from "@/components/main-layout"
import ProtectedRoute from "@/components/protected-route"
import WorkforceResourceDashboard from "@/app/factory_dashboard/components/workforce-resource-dashboard"

export default function WorkforcePage() {
  return (
    <ProtectedRoute requiredPermission="command:read">
      <MainLayout>
        <header className="flex items-center justify-between py-4 mb-4">
          <div>
            <h1 className="text-3xl font-bold">Workforce & Resources</h1>
            <p className="text-muted-foreground">Factory workforce and resource allocation metrics</p>
          </div>
          {/* Buttons removed as requested */}
        </header>

        <Suspense fallback={<div className="p-4 text-center">Loading dashboard...</div>}>
          <WorkforceResourceDashboard />
        </Suspense>
      </MainLayout>
    </ProtectedRoute>
  )
}
