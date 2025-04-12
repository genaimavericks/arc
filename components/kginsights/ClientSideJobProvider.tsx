"use client"

import { useState, useEffect, ReactNode } from "react"
import { KGInsightsJobProvider } from "@/lib/kginsights-job-context"

export default function ClientSideJobProvider({ children }: { children: ReactNode }) {
  const [isClient, setIsClient] = useState(false)

  useEffect(() => {
    setIsClient(true)
  }, [])

  if (!isClient) {
    // Return null or a loading indicator while rendering on the server/initially
    return null;
  }

  // Once we're on the client, render the actual provider and its children
  return <KGInsightsJobProvider>{children}</KGInsightsJobProvider>
}
