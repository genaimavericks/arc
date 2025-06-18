"use client"

import type React from "react"

import { useAuth } from "@/lib/auth-context"
import { useRouter, usePathname } from "next/navigation"
import { useEffect } from "react"
import LoadingSpinner from "@/components/loading-spinner"

interface ProtectedRouteProps {
  children: React.ReactNode
  requiredPermission?: string
}

export default function ProtectedRoute({ children, requiredPermission }: ProtectedRouteProps) {
  const { user, isLoading } = useAuth()
  const router = useRouter()
  const pathname = usePathname()

  useEffect(() => {
    // Check for logout flag in sessionStorage
    const isLoggingOut = sessionStorage.getItem("isLoggingOut") === "true"

    if (!isLoading && !user) {
      // Always redirect to login page when not authenticated
      router.push(`/login?redirect=${encodeURIComponent(pathname)}`)
    } else if (!isLoading && user) {
      // Check permission-based access if a specific permission is required
      if (requiredPermission && user.permissions) {
        // Special case for KGraph Insights - allow access with either kginsights:read OR djinni:read
        const isKGraphInsightsPage = pathname.startsWith('/kginsights');
        const hasKGraphPermission = user.permissions.includes('kginsights:read');
        const hasDjinniPermission = user.permissions.includes('djinni:read');
        
        // Allow access to KGraph pages if user has either permission
        const hasRequiredPermission = requiredPermission === 'kginsights:read' && isKGraphInsightsPage
          ? (hasKGraphPermission || hasDjinniPermission)
          : user.permissions.includes(requiredPermission);
        
        // If the user doesn't have the required permission, redirect to an appropriate page
        if (!hasRequiredPermission) {
          // Instead of redirecting to home, redirect to the appropriate page based on permissions
          if (user.permissions.includes('datapuur:read')) {
            router.push('/datapuur')
          } else if (user.permissions.includes('kginsights:read')) {
            router.push('/kginsights')
          } else if (user.permissions.includes('dashboard:read')) {
            router.push('/dashboards')
          } else if (user.permissions.includes('djinni:read')) {
            router.push('/djinni')
          } else {
            // If no clear permissions, go to access denied
            router.push('/access-denied')
          }
        }
      }
    }
  }, [user, isLoading, router, pathname, requiredPermission])

  // Show loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-black/[0.96] flex items-center justify-center">
        <LoadingSpinner />
      </div>
    )
  }

  // If not authenticated, don't render children
  if (!user) {
    return null
  }

  // Check permission-based access
  if (requiredPermission && user.permissions) {
    // Special case for KGraph Insights - allow access with either kginsights:read OR djinni:read
    const isKGraphInsightsPage = pathname.startsWith('/kginsights');
    const hasKGraphPermission = user.permissions.includes('kginsights:read');
    const hasDjinniPermission = user.permissions.includes('djinni:read');
    
    // Check if user has required permission, with special handling for KGraph pages
    const hasRequiredPermission = requiredPermission === 'kginsights:read' && isKGraphInsightsPage
      ? (hasKGraphPermission || hasDjinniPermission)
      : user.permissions.includes(requiredPermission);
      
    if (!hasRequiredPermission) {
      return null
    }
  }

  // Render children if authenticated and authorized
  return <>{children}</>
}
