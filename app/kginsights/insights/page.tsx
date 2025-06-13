"use client"

import { useState, useEffect } from "react"
import dynamic from "next/dynamic"
import { KGInsightsLayout } from "@/components/kginsights/kginsights-layout"


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
  // Add state to track if component is mounted
  const [isMounted, setIsMounted] = useState(false);

  // Set mounted state on component mount
  useEffect(() => {
    setIsMounted(true);
    return () => setIsMounted(false);
  }, []);

  return (
    <div className="flex-1 p-6 overflow-hidden flex flex-col h-[calc(100vh-4rem)]">
      <div className="flex flex-col gap-4 mb-4">
        <h1 className="text-2xl font-bold tracking-tight">Knowledge Graph Insights</h1>
      </div>
      
      <div 
        className="bg-card/40 backdrop-blur-sm rounded-xl border shadow-sm overflow-hidden flex flex-col flex-1"
        style={{ 
          position: 'relative',
          display: isMounted ? 'flex' : 'none',
          height: 'calc(100% - 3rem)' // Ensure this takes remaining height minus header
        }}
      >
        {/* Custom styling to override the InsightsChat component layout */}
        <style jsx global>{`
          /* Flip the chat layout - make the sidebar appear on the right instead of left */
          .insights-chat-container {
            flex-direction: row-reverse !important;
          }
          
          /* Adjust border styles for the flipped layout */
          .insights-chat-container .sidebar {
            border-left: 1px solid var(--border) !important;
            border-right: none !important;
          }
          
          /* Ensure the main chat area takes appropriate space */
          .insights-chat-container .main-chat-area {
            flex: 1;
          }
        `}</style>
        
        <InsightsChat />
      </div>
    </div>
  )
}
