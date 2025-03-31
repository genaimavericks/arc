"use client"

import { useState } from "react"
import dynamic from "next/dynamic"
import { KGInsightsLayout } from "@/components/kginsights/kginsights-layout"
import KGInsightsSidebar from "@/components/kginsights-sidebar"

// Use dynamic import for the chat component
const InsightsChat = dynamic(() => import("@/components/kginsights/insights-chat"), {
  ssr: false,
  loading: () => <div className="p-8 flex items-center justify-center">Loading chat interface...</div>
})

export default function KGInsightsPage() {
  return (
    <KGInsightsLayout>
      <KGInsightsContent />
    </KGInsightsLayout>
  )
}

function KGInsightsContent() {
  return (
    <div className="flex-1 p-6 overflow-hidden">
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
    </div>
  )
}
