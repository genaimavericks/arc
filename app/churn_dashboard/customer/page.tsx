"use client"

import { Suspense } from "react"
import { MainLayout } from "@/components/main-layout"
import ProtectedRoute from "@/components/protected-route"
import CustomerProfile from "@/app/components/churn_dashboard/customer-profile"

export default function CustomerProfilePage() {
  return (
    <ProtectedRoute requiredPermission="command:read">
      <MainLayout>
        <header className="flex items-center justify-between py-4 mb-4">
          <div>
            <h1 className="text-3xl font-bold">Customer Profile</h1>
            <p className="text-muted-foreground">Analysis of customer characteristics and behaviors</p>
          </div>
        </header>

        <Suspense fallback={<div className="w-full h-64 flex items-center justify-center">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
        </div>}>
          <CustomerProfile />
        </Suspense>
      </MainLayout>
    </ProtectedRoute>
  )
}
