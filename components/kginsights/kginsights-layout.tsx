"use client"

import type { ReactNode } from "react"
import { MainLayout } from "@/components/main-layout"
import ProtectedRoute from "@/components/protected-route"

interface KGInsightsLayoutProps {
  children: ReactNode
  requiredPermission?: string // Allow overriding the default permission
}

export function KGInsightsLayout({ 
  children, 
  requiredPermission = "kginsights:read" 
}: KGInsightsLayoutProps) {
  return (
    <ProtectedRoute requiredPermission={requiredPermission}>
      <MainLayout>
        {children}
      </MainLayout>
    </ProtectedRoute>
  )
}
