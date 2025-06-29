"use client"

import React, { useState } from 'react'
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
  const [activeTab, setActiveTab] = useState<string>('chat') // 'chat' or 'settings'

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
        
          {/* Navigation tabs */}
          <div className="flex items-center gap-4">
            <Tabs value={activeTab} onValueChange={setActiveTab}>
              <TabsList>
                <TabsTrigger value="chat" className="flex items-center gap-1">
                  <Bot className="h-4 w-4" />
                  <span>Chat</span>
                </TabsTrigger>
                <TabsTrigger value="settings" className="flex items-center gap-1">
                  <Settings className="h-4 w-4" />
                  <span>Settings</span>
                </TabsTrigger>
              </TabsList>
            </Tabs>
          </div>
        </header>
      
        {/* Main Content Area */}
        <div className="flex-1 overflow-hidden">
          <Tabs value={activeTab} className="h-full">
            <TabsContent value="chat" className="h-full">
              {/* Integrated UnifiedChatInterface */}
              <UnifiedChatInterface />
            </TabsContent>
            
            <TabsContent value="settings" className="p-4">
              <div className="max-w-2xl mx-auto">
                <h2 className="text-xl font-semibold mb-4">Assistant Settings</h2>
                
                <div className="space-y-4">
                  <div className="border rounded-md p-4 bg-card">
                    <h3 className="font-medium mb-2">Intelligent Assistant</h3>
                    <p className="text-sm text-muted-foreground mb-3">
                      Djinni Assistant automatically routes your questions to the appropriate model.
                    </p>
                    
                    <div className="flex flex-col gap-2">
                      <div className="p-3 bg-accent/50 rounded-md">
                        <h4 className="font-medium text-sm">KG Insights Questions</h4>
                        <p className="text-xs text-muted-foreground">Questions about knowledge graphs, entity relationships, and data connections</p>
                      </div>
                      
                      <div className="p-3 bg-accent/50 rounded-md">
                        <h4 className="font-medium text-sm">Factory Astro</h4>
                        <p className="text-xs text-muted-foreground">Questions about production efficiency, factory operations, and forecasting</p>
                      </div>
                      
                      <div className="p-3 bg-accent/50 rounded-md">
                        <h4 className="font-medium text-sm">Churn Astro</h4>
                        <p className="text-xs text-muted-foreground">Questions about customer retention, churn prediction, and customer behavior</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  )
}
