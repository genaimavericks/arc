"use client"

import type { ReactNode } from "react"
import { MainLayout } from "@/components/main-layout"
import ProtectedRoute from "@/components/protected-route"

interface DjinniLayoutProps {
  children: ReactNode
}

export function DjinniLayout({ children }: DjinniLayoutProps) {
  return (
    <ProtectedRoute requiredPermission="djinni:read">
      <MainLayout>
        {children}
      </MainLayout>
    </ProtectedRoute>
  )
}
