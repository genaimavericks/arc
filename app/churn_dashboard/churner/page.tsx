"use client"

import { Suspense } from "react"
import { MainLayout } from "@/components/main-layout"
import ProtectedRoute from "@/components/protected-route"
import ChurnerProfile from "@/app/components/churn_dashboard/churner-profile"

export default function ChurnerProfilePage() {
  return (
    <ProtectedRoute requiredPermission="command:read">
      <MainLayout>
        <header className="flex items-center justify-between py-4 mb-4">
          <div>
            <h1 className="text-3xl font-bold">Churner Profile</h1>
            <p className="text-muted-foreground">Analysis of customers who have churned</p>
          </div>
        </header>

        <Suspense fallback={<div className="w-full h-64 flex items-center justify-center">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
        </div>}>
          <ChurnerProfile />
        </Suspense>
      </MainLayout>
    </ProtectedRoute>
  )
}
