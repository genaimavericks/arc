"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { MainLayout } from "@/components/main-layout"
import { useAuth } from "@/lib/auth-context"
import { Button } from "@/components/ui/button"
import { ShieldAlert } from "lucide-react"

export default function AccessDenied() {
  const { user, isLoading } = useAuth()
  const router = useRouter()
  
  // Redirect to login page if user is not authenticated
  useEffect(() => {
    if (!isLoading && !user) {
      router.push('/login')
    }
  }, [user, isLoading, router])
  
  // Don't render the page until we know the user's authentication status
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

  // Find the first available module the user has access to
  // Following the same priority order as in the main page based on sidebar menu order
  const redirectToAvailableModule = () => {
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
      // If they have no module permissions, stay on this page
      // User will need to contact admin for permissions
    }
  }
  
  return (
    <MainLayout>
      <div className="flex flex-col items-center justify-center min-h-screen max-w-lg mx-auto text-center p-4">
        <div className="bg-destructive/10 p-6 rounded-full mb-6">
          <ShieldAlert className="h-12 w-12 text-destructive" />
        </div>
        
        <h1 className="text-3xl font-bold tracking-tight mb-2">Access Denied</h1>
        
        <p className="text-muted-foreground mb-6">
          You don't have permission to access this page. Contact your administrator if you believe this is an error.
        </p>
        
        <div className="space-y-3">
          <Button onClick={redirectToAvailableModule} className="w-full">
            Go to Available Module
          </Button>
          
          <Button variant="outline" onClick={() => router.back()} className="w-full">
            Go Back
          </Button>
        </div>
      </div>
    </MainLayout>
  )
}
