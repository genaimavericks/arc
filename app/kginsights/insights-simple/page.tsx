"use client"

import dynamic from "next/dynamic"

// Dynamically import the component with no SSR to avoid hydration issues
const InsightsSimpleChat = dynamic(
  () => import("@/components/kginsights/insights-simple-chat").then(mod => mod.InsightsSimpleChat),
  { ssr: false }
)

export default function InsightsSimplePage() {
  return (
    <div className="flex h-screen bg-background">
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        <div className="flex-1 flex flex-col">
          <InsightsSimpleChat />
        </div>
      </div>
    </div>
  )
}
