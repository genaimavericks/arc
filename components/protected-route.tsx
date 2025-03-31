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
      if (isLoggingOut) {
        // If logging out, redirect to home and clear the flag
        sessionStorage.removeItem("isLoggingOut")
        router.push("/")
      } else {
        // Normal case - redirect to login if not authenticated
        router.push(`/login?redirect=${encodeURIComponent(pathname)}`)
      }
    } else if (!isLoading && user) {
      // Check permission-based access if a specific permission is required
      if (requiredPermission && user.permissions) {
        // If the user doesn't have the required permission, redirect
        if (!user.permissions.includes(requiredPermission)) {
          router.push("/")
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
    if (!user.permissions.includes(requiredPermission)) {
      return null
    }
  }

  // Render children if authenticated and authorized
  return <>{children}</>
}
