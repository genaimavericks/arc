"use client"

import type { ReactNode } from "react"
import { MainLayout } from "@/components/main-layout"
import ProtectedRoute from "@/components/protected-route"

interface AdminLayoutProps {
  children: ReactNode
}

export function AdminLayout({ children }: AdminLayoutProps) {
  return (
    <ProtectedRoute requiredPermission="datapuur:manage">
      <MainLayout>
        {children}
      </MainLayout>
    </ProtectedRoute>
  )
}
