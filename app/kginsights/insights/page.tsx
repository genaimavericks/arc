"use client"

import { useState } from "react"
import Navbar from "@/components/navbar"
import { SparklesCore } from "@/components/sparkles"
import KGInsightsSidebar from "@/components/kginsights-sidebar"
import ProtectedRoute from "@/components/protected-route"
import dynamic from "next/dynamic"

// Use dynamic import for the chat component
const InsightsChat = dynamic(() => import("@/components/kginsights/insights-chat"), {
  ssr: false,
  loading: () => <div className="p-8 flex items-center justify-center">Loading chat interface...</div>
})

export default function KGInsightsPage() {
  return (
    <ProtectedRoute requiredPermission="kginsights:read">
      <KGInsightsContent />
    </ProtectedRoute>
  )
}

function KGInsightsContent() {
  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <div className="relative w-full">
        {/* Background sparkles effect */}
        <div className="absolute inset-0 h-[calc(100vh-76px)] w-full bg-background">
          <SparklesCore
            id="sparkles"
            background="transparent"
            minSize={0.6}
            maxSize={1.4}
            particleDensity={10}
            className="h-full w-full"
            particleColor="#888888"
          />
        </div>

        {/* Main content */}
        <div className="relative flex">
          <KGInsightsSidebar />
          <main className="flex-1 p-6 overflow-hidden">
            <div className="flex flex-col gap-4 mb-6">
              <h1 className="text-3xl font-bold">Knowledge Graph Insights</h1>
              <p className="text-muted-foreground max-w-3xl">
                Explore your knowledge graph using natural language queries. Ask questions about relationships, 
                patterns, and insights in your data. The AI assistant will use the knowledge graph to provide 
                accurate and contextual answers.  
              </p>
            </div>
            
            <div className="h-[calc(100vh-240px)] bg-card/40 backdrop-blur-sm rounded-xl border shadow-sm overflow-hidden">
              <InsightsChat />
            </div>
          </main>
        </div>
      </div>
    </div>
  )
}
