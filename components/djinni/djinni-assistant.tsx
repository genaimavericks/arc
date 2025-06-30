"use client"

import React from 'react'
import { useAssistant, AssistantProvider } from './assistant-context'
import { UnifiedChatInterface } from './unified-chat'
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Button } from "@/components/ui/button"
import { Bot, Settings, SparklesIcon } from 'lucide-react'
import { MainSidebar } from "@/components/main-sidebar"

// Main wrapper component that includes the context provider
export function DjinniAssistantWrapper({ children }: { children?: React.ReactNode }) {
  return (
    <AssistantProvider>
      <DjinniAssistant>{children}</DjinniAssistant>
    </AssistantProvider>
  )
}

// Core DjinniAssistant component
function DjinniAssistant({ children }: { children?: React.ReactNode }) {
  const { activeAstroType, setActiveAstroType } = useAssistant()

  return (
    <div className="flex h-screen bg-background">
      {/* Main Sidebar */}
      <MainSidebar />
      
      {/* Main Content */}
      <div className="flex flex-col flex-1 h-full overflow-hidden">
        {/* Header */}
        <header className="border-b border-border p-4 flex justify-between items-center">
          <div className="flex items-center gap-2">
            <SparklesIcon className="h-5 w-5 text-primary" />
            <h1 className="text-lg font-semibold">Djinni Assistant</h1>
          </div>
        
                  {/* Navigation tabs removed as requested */}
        </header>
      
        {/* Main Content Area - Chat interface always visible */}
        <div className="flex-1 overflow-hidden">
          <div className="h-full">
            {/* Integrated UnifiedChatInterface */}
            <UnifiedChatInterface />
          </div>
        </div>
      </div>
    </div>
  )
}
