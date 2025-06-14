"use client"

import React from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { useDjinniStore } from "@/lib/djinni/store"
import { formatDistanceToNow } from "date-fns"
import { Bot, User, Trash2, History } from "lucide-react"
import { useRouter } from "next/navigation"
import { DjinniLayout } from "@/components/djinni/djinni-layout"

export default function ConversationsPage() {
  const { chatHistory, clearChatHistory, activeModel } = useDjinniStore()
  const router = useRouter()
  
  // Get chat history for the active model only
  const modelHistory = chatHistory.find(chat => chat.model === activeModel)?.messages || []
  
  // Format timestamp to relative time (e.g., "2 hours ago")
  const formatTimestamp = (timestamp: number) => {
    try {
      return formatDistanceToNow(new Date(timestamp), { addSuffix: true })
    } catch (error) {
      return "Unknown time"
    }
  }
  
  // Handle clearing chat history for the active model
  const handleClearHistory = () => {
    if (confirm(`Are you sure you want to clear all ${activeModel === "factory_astro" ? "Factory Astro" : "Churn Astro"} conversations?`)) {
      clearChatHistory(activeModel)
    }
  }
  
  // Navigate to the Djinni page
  const navigateToDjinni = () => {
    router.push("/djinni")
  }
  
  return (
    <DjinniLayout>
      <div className="flex-1 space-y-4 p-4 md:p-8 pt-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <History className="h-6 w-6 text-primary" />
            <h2 className="text-2xl font-bold tracking-tight">
              {activeModel === "factory_astro" ? "Factory Astro" : "Churn Astro"} Conversation History
            </h2>
          </div>
          <Button variant="outline" size="sm" onClick={() => router.push('/djinni')}>Back to Assistant</Button>
        </div>
        
        <Card>
          <CardHeader className="flex flex-row items-start justify-between p-4">
            <div className="flex items-start">
              <div className="mr-4">
                <CardTitle className="text-left mb-1">
                  {activeModel === "factory_astro" ? "Factory Astro" : "Churn Astro"} Conversations
                </CardTitle>
                <CardDescription className="text-left">
                  {modelHistory.length > 0 
                    ? `${modelHistory.length} messages` 
                    : "No conversations yet"}
                </CardDescription>
              </div>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" onClick={navigateToDjinni}>
                New Chat
              </Button>
              <Button 
                variant="destructive" 
                size="icon" 
                onClick={handleClearHistory}
                disabled={modelHistory.length === 0}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[500px] pr-4">
              {modelHistory.length > 0 ? (
                <div className="space-y-6">
                  {/* Group messages by query-response pairs */}
                  {(() => {
                    const conversationPairs = [];
                    
                    // Group messages into query-response pairs
                    for (let i = 0; i < modelHistory.length; i += 2) {
                      const userMessage = modelHistory[i];
                      const assistantMessage = modelHistory[i + 1];
                      
                      if (userMessage && userMessage.role === 'user') {
                        conversationPairs.push({
                          query: userMessage,
                          response: assistantMessage,
                          timestamp: userMessage.timestamp
                        });
                      }
                    }
                    
                    // Handle any remaining single messages
                    if (modelHistory.length % 2 !== 0) {
                      const lastMessage = modelHistory[modelHistory.length - 1];
                      if (lastMessage.role === 'user') {
                        conversationPairs.push({
                          query: lastMessage,
                          response: null,
                          timestamp: lastMessage.timestamp
                        });
                      }
                    }
                      
                      return conversationPairs.map((pair, index) => (
                        <div key={index} className="border rounded-lg overflow-hidden">
                          {/* Query section */}
                          <div className="p-4 border-b">
                            <div className="flex items-center gap-2 mb-2">
                              <User className="h-5 w-5 text-blue-500" />
                              <span className="font-medium">You</span>
                              <span className="text-xs text-muted-foreground ml-auto">
                                {formatTimestamp(pair.query.timestamp)}
                              </span>
                            </div>
                            <p className="text-sm">{pair.query.content}</p>
                          </div>
                          
                          {/* Response section */}
                          {pair.response && (
                            <div className="p-4 bg-muted/20">
                              <div className="flex items-center gap-2 mb-2">
                                <Bot className="h-5 w-5 text-purple-500" />
                                <span className="font-medium">{activeModel === "factory_astro" ? "Factory Astro" : "Churn Astro"}</span>
                                <span className="text-xs text-muted-foreground ml-auto">
                                  {formatTimestamp(pair.response.timestamp)}
                                </span>
                              </div>
                              <p className="text-sm">{pair.response.content}</p>
                            </div>
                          )}
                        </div>
                      ));
                    })()} 
                  </div>
              ) : (
                <div className="flex flex-col items-center justify-center h-40 text-center">
                  <Bot className="h-12 w-12 text-muted-foreground mb-2" />
                  <p className="text-muted-foreground">
                    No conversations with {activeModel === "factory_astro" ? "Factory Astro" : "Churn Astro"} yet
                  </p>
                  <Button 
                    variant="outline" 
                    className="mt-4"
                    onClick={navigateToDjinni}
                  >
                    Start a conversation
                  </Button>
                </div>
              )}
            </ScrollArea>
          </CardContent>
        </Card>
      </div>
    </DjinniLayout>
  )
}
