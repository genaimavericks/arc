"use client"

import type { ReactNode } from "react"
import Navbar from "@/components/navbar"
import { SparklesCore } from "@/components/sparkles"
import KGInsightsSidebar from "@/components/kginsights-sidebar"
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
      <main className="min-h-screen bg-background antialiased relative overflow-hidden">
        {/* Ambient background with moving particles */}
        <div className="h-full w-full absolute inset-0 z-[-1]">
          <SparklesCore
            id="tsparticlesfullpage"
            background="transparent"
            minSize={0.6}
            maxSize={1.4}
            particleDensity={100}
            className="w-full h-full"
            particleColor="var(--foreground)"
          />
        </div>

        <div className="relative z-10">
          <Navbar />

          <div className="flex">
            <KGInsightsSidebar />
            {children}
          </div>
        </div>
      </main>
    </ProtectedRoute>
  )
}
