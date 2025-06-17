"use client"

import { useAuth } from "@/lib/auth-context"
import { useRouter } from "next/navigation"
import { useEffect, Suspense } from "react"
import { Card, CardContent, CardHeader, CardDescription, CardTitle } from "@/components/ui/card"
import { MainLayout } from "@/components/main-layout"
import ProtectedRoute from "@/components/protected-route"

// Import dashboard component
import DashboardSummary from "@/app/factory_dashboard/components/dashboard-summary"

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
          {/* Buttons removed as requested */}
        </header>

        <Suspense fallback={<div className="p-4 text-center">Loading dashboard...</div>}>
          <DashboardSummary />
        </Suspense>
      </MainLayout>
    </ProtectedRoute>
  )
}

// Dashboard component removed
